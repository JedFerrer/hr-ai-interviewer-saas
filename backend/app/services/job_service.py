"""Job posting service: CRUD + stats."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.candidate import Candidate
from app.models.evaluation import EvaluationRecord
from app.models.interview import Interview
from app.models.job_posting import JobPosting
from app.models.user import User
from app.schemas.job import JobCreateRequest, JobUpdateRequest

settings = get_settings()


async def create_job(db: AsyncSession, user: User, data: JobCreateRequest) -> JobPosting:
    """Create a job posting with a unique interview link token."""
    token = secrets.token_urlsafe(24)

    job = JobPosting(
        company_id=user.company_id,
        created_by=user.id,
        title=data.title,
        description=data.description,
        department=data.department,
        location=data.location,
        employment_type=data.employment_type,
        required_skills=data.required_skills,
        custom_questions=data.custom_questions,
        interview_config=data.interview_config.model_dump() if data.interview_config else {"num_questions": 8, "style": "standard"},
        interview_link_token=token,
        auto_send_status_emails=(
            data.auto_send_status_emails if data.auto_send_status_emails is not None else True
        ),
        screening_mode=data.screening_mode or "auto_all",
        auto_invite_threshold=(
            data.auto_invite_threshold if data.auto_invite_threshold is not None else 75
        ),
        review_threshold=(
            data.review_threshold if data.review_threshold is not None else 55
        ),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def list_jobs(
    db: AsyncSession,
    company_id: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """List jobs for a company with candidate count and avg score.

    Single grouped query (was N+1: 1 + 2 per job).
    """
    # Total count
    count_q = select(func.count(JobPosting.id)).where(
        JobPosting.company_id == company_id
    )
    total = (await db.execute(count_q)).scalar() or 0

    # Aggregate: candidate count + avg overall score per job in one round-trip.
    candidate_count = func.count(func.distinct(Candidate.id)).label("candidate_count")
    avg_score = func.avg(EvaluationRecord.overall_score).label("avg_score")

    q = (
        select(
            JobPosting.id,
            JobPosting.title,
            JobPosting.status,
            JobPosting.department,
            JobPosting.location,
            JobPosting.created_at,
            candidate_count,
            avg_score,
        )
        .outerjoin(Candidate, Candidate.job_posting_id == JobPosting.id)
        .outerjoin(Interview, Interview.job_posting_id == JobPosting.id)
        .outerjoin(EvaluationRecord, EvaluationRecord.interview_id == Interview.id)
        .where(JobPosting.company_id == company_id)
        .group_by(JobPosting.id)
        .order_by(JobPosting.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(q)).all()

    items = [
        {
            "id": row.id,
            "title": row.title,
            "status": row.status,
            "department": row.department,
            "location": row.location,
            "candidate_count": row.candidate_count or 0,
            "avg_score": round(float(row.avg_score), 1) if row.avg_score is not None else None,
            "created_at": row.created_at,
        }
        for row in rows
    ]

    return items, total


async def get_job(db: AsyncSession, job_id: str, company_id: str) -> JobPosting:
    """Get a single job, enforcing company ownership."""
    result = await db.execute(
        select(JobPosting).where(
            JobPosting.id == job_id,
            JobPosting.company_id == company_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


async def update_job(
    db: AsyncSession, job_id: str, company_id: str, data: JobUpdateRequest
) -> JobPosting:
    """Update a job posting. Only non-None fields are updated."""
    job = await get_job(db, job_id, company_id)
    update_data = data.model_dump(exclude_unset=True)
    # Convert InterviewConfig model to dict for JSON column storage
    if "interview_config" in update_data and update_data["interview_config"] is not None:
        from app.schemas.job import InterviewConfig
        if isinstance(data.interview_config, InterviewConfig):
            update_data["interview_config"] = data.interview_config.model_dump()
    for field, value in update_data.items():
        setattr(job, field, value)
    await db.commit()
    await db.refresh(job)
    return job


async def delete_job(db: AsyncSession, job_id: str, company_id: str) -> None:
    """Soft-delete (archive) a job posting."""
    job = await get_job(db, job_id, company_id)
    job.status = "archived"
    await db.commit()


async def get_candidates_summary(db: AsyncSession, job_id: str) -> dict:
    """Get candidate count grouped by status for a job."""
    q = (
        select(Candidate.status, func.count(Candidate.id))
        .where(Candidate.job_posting_id == job_id)
        .group_by(Candidate.status)
    )
    result = await db.execute(q)
    counts = {row[0]: row[1] for row in result.all()}
    counts["total"] = sum(counts.values())
    return counts
