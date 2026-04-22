"""Candidate service: detail, shortlist, reject."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.evaluation import EvaluationRecord
from app.models.interview import Interview
from app.models.job_posting import JobPosting

logger = logging.getLogger(__name__)


# Map a candidate status to an email-template kind. A status with no entry
# triggers no email.
_STATUS_TO_EMAIL_KIND: dict[str, str] = {
    "shortlisted": "shortlist",
    "rejected": "reject",
}

# Suppress duplicate sends if HR flips back-and-forth quickly.
_EMAIL_IDEMPOTENCY_WINDOW = timedelta(minutes=1)


async def get_candidate_detail(
    db: AsyncSession, candidate_id: str, company_id: str
) -> Candidate:
    """Get full candidate detail with interview + evaluation. Enforces company ownership."""
    result = await db.execute(
        select(Candidate)
        .options(
            selectinload(Candidate.interview).selectinload(Interview.evaluation),
            selectinload(Candidate.job_posting).selectinload(JobPosting.company),
        )
        .where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Tenant isolation
    if candidate.job_posting.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    return candidate


async def update_candidate_status(
    db: AsyncSession, candidate_id: str, company_id: str, new_status: str
) -> Candidate:
    """Update candidate status (shortlist/reject). Enforces company ownership.

    Side effect: when the new status maps to a notification kind, the job has
    `auto_send_status_emails` enabled, and we haven't already sent the same
    kind very recently, an email is dispatched. Email failures never break
    the status change.
    """
    candidate = await get_candidate_detail(db, candidate_id, company_id)
    previous_status = candidate.status
    candidate.status = new_status
    await db.commit()
    await db.refresh(candidate)

    if new_status != previous_status:
        await _maybe_send_status_email(db, candidate, new_status)

    return candidate


async def _maybe_send_status_email(
    db: AsyncSession, candidate: Candidate, new_status: str
) -> None:
    """Send a status notification email if all conditions are satisfied."""
    kind = _STATUS_TO_EMAIL_KIND.get(new_status)
    if kind is None:
        return

    # Need an email address to send anything.
    if not candidate.email:
        return

    # Job-level toggle.
    job = candidate.job_posting
    if job is None or not getattr(job, "auto_send_status_emails", False):
        return

    # Idempotency: skip if the same kind was sent very recently.
    last_sent = candidate.last_status_email_sent_at
    if last_sent is not None and candidate.last_status_email_kind == kind:
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last_sent < _EMAIL_IDEMPOTENCY_WINDOW:
            return

    # Lazy imports avoid a circular dependency at module load.
    from app.services import email_service, email_template_service

    company = job.company
    company_name = company.name if company else ""

    try:
        subject, body_html = await email_template_service.render_template(
            db,
            company_id=job.company_id,
            kind=kind,
            candidate_name=candidate.name or "",
            job_title=job.title,
            company_name=company_name,
        )
        sent = await email_service.send_status_email(
            candidate_email=candidate.email,
            subject=subject,
            body_html=body_html,
        )
    except Exception:
        # Never let a notification failure roll back the status change.
        logger.exception("Failed to send %s status email for candidate %s", kind, candidate.id)
        return

    if sent:
        candidate.last_status_email_kind = kind
        candidate.last_status_email_sent_at = datetime.now(timezone.utc)
        await db.commit()


async def list_candidates(
    db: AsyncSession,
    job_id: str,
    company_id: str,
    status_filter: str | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List candidates for a job with optional filtering and sorting.

    Returns dicts (not ORM rows) so the per-dimension scores from the
    evaluation join are materialised in a single round-trip — no N+1.
    """
    from sqlalchemy import func

    base_q = (
        select(
            Candidate.id,
            Candidate.name,
            Candidate.email,
            Candidate.status,
            Candidate.resume_url,
            Candidate.completed_at,
            EvaluationRecord.overall_score.label("overall_score"),
            EvaluationRecord.skill_match.label("skill_match"),
            EvaluationRecord.communication.label("communication"),
            EvaluationRecord.problem_solving.label("problem_solving"),
            EvaluationRecord.cultural_fit.label("cultural_fit"),
            EvaluationRecord.recommendation.label("recommendation"),
        )
        .join(JobPosting, Candidate.job_posting_id == JobPosting.id)
        .outerjoin(Interview, Interview.candidate_id == Candidate.id)
        .outerjoin(EvaluationRecord, EvaluationRecord.interview_id == Interview.id)
        .where(Candidate.job_posting_id == job_id, JobPosting.company_id == company_id)
    )
    count_q = (
        select(func.count(Candidate.id))
        .join(JobPosting, Candidate.job_posting_id == JobPosting.id)
        .where(Candidate.job_posting_id == job_id, JobPosting.company_id == company_id)
    )

    if status_filter:
        base_q = base_q.where(Candidate.status == status_filter)
        count_q = count_q.where(Candidate.status == status_filter)

    total = (await db.execute(count_q)).scalar() or 0

    # Sortable columns. Anything else falls back to created_at.
    sort_columns = {
        "score": EvaluationRecord.overall_score,
        "overall_score": EvaluationRecord.overall_score,
        "skill_match": EvaluationRecord.skill_match,
        "communication": EvaluationRecord.communication,
        "problem_solving": EvaluationRecord.problem_solving,
        "cultural_fit": EvaluationRecord.cultural_fit,
        "name": Candidate.name,
        "status": Candidate.status,
        "completed_at": Candidate.completed_at,
        "created_at": Candidate.created_at,
    }
    order_col = sort_columns.get(sort_by, Candidate.created_at)

    if order == "asc":
        base_q = base_q.order_by(order_col.asc().nulls_last())
    else:
        base_q = base_q.order_by(order_col.desc().nulls_last())

    base_q = base_q.limit(limit).offset(offset)
    rows = (await db.execute(base_q)).all()

    items = [
        {
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "status": row.status,
            "resume_url": row.resume_url,
            "completed_at": row.completed_at,
            "overall_score": float(row.overall_score) if row.overall_score is not None else None,
            "skill_match": float(row.skill_match) if row.skill_match is not None else None,
            "communication": (
                float(row.communication) if row.communication is not None else None
            ),
            "problem_solving": (
                float(row.problem_solving) if row.problem_solving is not None else None
            ),
            "cultural_fit": float(row.cultural_fit) if row.cultural_fit is not None else None,
            "recommendation": row.recommendation,
        }
        for row in rows
    ]
    return items, total
