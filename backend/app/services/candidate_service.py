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


# Map a candidate status to its corresponding email-template kind. Statuses
# without an entry have no canonical notification.
STATUS_TO_EMAIL_KIND: dict[str, str] = {
    "shortlisted": "shortlist",
    "rejected": "reject",
}

# Suppress duplicate sends if HR flips back-and-forth quickly.
_EMAIL_IDEMPOTENCY_WINDOW = timedelta(minutes=1)


class NotificationConflict(HTTPException):
    """Raised when sending a notification would contradict the previous one.

    HR can override by re-issuing the request with `force=True` (typically
    paired with a `status_correction` email so the candidate isn't whip-sawed).
    """

    def __init__(self, *, previous_kind: str, requested_kind: str, last_sent_at: datetime | None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "notification_conflict",
                "message": (
                    f"This candidate was previously notified with a '{previous_kind}' "
                    f"email. Sending a '{requested_kind}' email now may confuse them."
                ),
                "previous_kind": previous_kind,
                "requested_kind": requested_kind,
                "last_sent_at": last_sent_at.isoformat() if last_sent_at else None,
            },
        )


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

    NOTE: Status changes never send emails directly anymore. The internal
    decision (status) and the external notification (email to candidate) are
    intentionally decoupled so HR can change their mind without immediately
    blasting the candidate. Use `send_status_notification()` to dispatch the
    email when ready.
    """
    candidate = await get_candidate_detail(db, candidate_id, company_id)
    candidate.status = new_status
    await db.commit()
    await db.refresh(candidate)
    return candidate


async def send_status_notification(
    db: AsyncSession,
    candidate_id: str,
    company_id: str,
    *,
    kind: str,
    force: bool = False,
) -> tuple[Candidate, bool]:
    """Send a status email to the candidate. Returns (candidate, sent_bool).

    `kind` must be one of the supported template kinds (shortlist, reject,
    status_correction). When the candidate was previously notified with a
    DIFFERENT non-correction kind, the call raises `NotificationConflict`
    unless `force=True` — this is the safety net against contradictory
    emails (e.g. reject followed by shortlist).
    """
    from app.models.email_template import ALLOWED_TEMPLATE_KINDS

    if kind not in ALLOWED_TEMPLATE_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported notification kind: {kind}",
        )

    candidate = await get_candidate_detail(db, candidate_id, company_id)

    if not candidate.email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate has no email address on file.",
        )

    previous_kind = candidate.last_status_email_kind
    # Only shortlist/reject conflict with each other. status_correction is
    # explicitly an apology / clarification and can always be sent.
    decision_kinds = {"shortlist", "reject"}
    if (
        not force
        and kind in decision_kinds
        and previous_kind in decision_kinds
        and previous_kind != kind
    ):
        raise NotificationConflict(
            previous_kind=previous_kind,
            requested_kind=kind,
            last_sent_at=candidate.last_status_email_sent_at,
        )

    # Same-kind idempotency: don't double-send within the window.
    last_sent = candidate.last_status_email_sent_at
    if (
        previous_kind == kind
        and last_sent is not None
    ):
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last_sent < _EMAIL_IDEMPOTENCY_WINDOW:
            return candidate, False

    sent = await _dispatch_status_email(db, candidate, kind)
    return candidate, sent


async def approve_pre_screen(
    db: AsyncSession, candidate_id: str, company_id: str
) -> Candidate:
    """HR approves a `review_pending` candidate → generate interview + send invite.

    Idempotent-ish: if the candidate is already `ready`/`in_progress`/etc.,
    we return the current state without re-sending the invite. Only callable
    on candidates currently in `review_pending` (or `error` as a manual
    rescue path); everything else raises 409.
    """
    candidate = await get_candidate_detail(db, candidate_id, company_id)

    if candidate.status not in {"review_pending", "error"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot approve a candidate in status '{candidate.status}'. "
                "Only candidates awaiting HR review can be approved."
            ),
        )

    # We need the parsed resume to build personalized questions. If parsing
    # failed earlier the candidate cannot be approved without re-applying.
    if not candidate.resume_parsed_data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resume parsing did not complete; cannot generate an interview.",
        )

    # Lazy imports keep candidate_service free of LLM/email deps at module
    # load and avoid a circular import with interview_service.
    from app.services.interview_service import _build_interview_and_invite
    from app.services.llm_client import get_async_openai_client

    client = get_async_openai_client()
    job = candidate.job_posting

    await _build_interview_and_invite(
        db=db,
        candidate=candidate,
        job=job,
        resume_data=candidate.resume_parsed_data,
        client=client,
    )

    # Refresh to pull in any committed changes from _build_interview_and_invite.
    await db.refresh(candidate)
    return candidate


async def reject_pre_screen(
    db: AsyncSession, candidate_id: str, company_id: str
) -> Candidate:
    """HR rejects a `review_pending` candidate. Marks the candidate rejected and
    optionally fires the standard reject email when the job opt-in is on.
    """
    candidate = await get_candidate_detail(db, candidate_id, company_id)

    if candidate.status not in {"review_pending", "error"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot pre-screen reject a candidate in status '{candidate.status}'."
            ),
        )

    return await update_candidate_status(db, candidate_id, company_id, "rejected")


async def _dispatch_status_email(
    db: AsyncSession, candidate: Candidate, kind: str
) -> bool:
    """Render and send a status email. Returns True if Resend accepted the message.

    Failures are logged but never raised — callers treat email as best-effort.
    On success, `last_status_email_kind` / `last_status_email_sent_at` are
    persisted so the UI can surface "last notified" and the conflict guard
    can compare against future requests.
    """
    # Lazy imports avoid a circular dependency at module load.
    from app.services import email_service, email_template_service

    job = candidate.job_posting
    company = job.company if job is not None else None
    company_name = company.name if company else ""

    try:
        subject, body_html = await email_template_service.render_template(
            db,
            company_id=job.company_id,
            kind=kind,
            candidate_name=candidate.name or "",
            job_title=job.title if job else "",
            company_name=company_name,
        )
        sent = await email_service.send_status_email(
            candidate_email=candidate.email,
            subject=subject,
            body_html=body_html,
        )
    except Exception:
        logger.exception("Failed to send %s status email for candidate %s", kind, candidate.id)
        return False

    if sent:
        candidate.last_status_email_kind = kind
        candidate.last_status_email_sent_at = datetime.now(timezone.utc)
        await db.commit()
    return bool(sent)


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
            Candidate.resume_match_score,
            Candidate.pre_screen_decision,
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
        base_q = base_q.order_by(order_col.asc().nulls_last(), Candidate.created_at.desc())
    else:
        base_q = base_q.order_by(order_col.desc().nulls_last(), Candidate.created_at.desc())

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
            "resume_match_score": (
                float(row.resume_match_score) if row.resume_match_score is not None else None
            ),
            "pre_screen_decision": row.pre_screen_decision,
        }
        for row in rows
    ]
    return items, total
