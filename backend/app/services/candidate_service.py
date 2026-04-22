"""Candidate service: detail, shortlist, reject."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.evaluation import EvaluationRecord
from app.models.interview import Interview


async def get_candidate_detail(
    db: AsyncSession, candidate_id: str, company_id: str
) -> Candidate:
    """Get full candidate detail with interview + evaluation. Enforces company ownership."""
    result = await db.execute(
        select(Candidate)
        .options(
            selectinload(Candidate.interview).selectinload(Interview.evaluation),
            selectinload(Candidate.job_posting),
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
    """Update candidate status (shortlist/reject). Enforces company ownership."""
    candidate = await get_candidate_detail(db, candidate_id, company_id)
    candidate.status = new_status
    await db.commit()
    await db.refresh(candidate)
    return candidate


async def list_candidates(
    db: AsyncSession,
    job_id: str,
    company_id: str,
    status_filter: str | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Candidate], int]:
    """List candidates for a job with optional filtering and sorting."""
    from sqlalchemy import func

    base_q = select(Candidate).where(Candidate.job_posting_id == job_id)
    count_q = select(func.count(Candidate.id)).where(Candidate.job_posting_id == job_id)

    if status_filter:
        base_q = base_q.where(Candidate.status == status_filter)
        count_q = count_q.where(Candidate.status == status_filter)

    total = (await db.execute(count_q)).scalar() or 0

    # Sorting
    if sort_by == "score":
        base_q = (
            base_q
            .outerjoin(Interview, Candidate.id == Interview.candidate_id)
            .outerjoin(EvaluationRecord, Interview.id == EvaluationRecord.interview_id)
        )
        order_col = EvaluationRecord.overall_score
    else:
        order_col = Candidate.created_at

    if order == "asc":
        base_q = base_q.order_by(order_col.asc())
    else:
        base_q = base_q.order_by(order_col.desc())

    base_q = base_q.limit(limit).offset(offset)
    result = await db.execute(base_q)
    return list(result.scalars().all()), total
