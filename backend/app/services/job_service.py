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
    """List jobs for a company with candidate count and avg score."""
    # Count total
    count_q = select(func.count(JobPosting.id)).where(
        JobPosting.company_id == company_id
    )
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch jobs
    q = (
        select(JobPosting)
        .where(JobPosting.company_id == company_id)
        .order_by(JobPosting.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    jobs = result.scalars().all()

    items = []
    for job in jobs:
        # Candidate count
        cc = await db.execute(
            select(func.count(Candidate.id)).where(Candidate.job_posting_id == job.id)
        )
        candidate_count = cc.scalar() or 0

        # Average score
        avg_q = (
            select(func.avg(EvaluationRecord.overall_score))
            .join(Interview, EvaluationRecord.interview_id == Interview.id)
            .where(Interview.job_posting_id == job.id)
        )
        avg_score = (await db.execute(avg_q)).scalar()

        items.append({
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "department": job.department,
            "location": job.location,
            "candidate_count": candidate_count,
            "avg_score": round(float(avg_score), 1) if avg_score else None,
            "created_at": job.created_at,
        })

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
