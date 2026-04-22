"""Job posting router: CRUD + candidate listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.candidate import CandidateListItem, CandidateListResponse
from app.schemas.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobDetailResponse,
    JobListItem,
    JobListResponse,
    JobResponse,
    JobUpdateRequest,
)
from app.services import candidate_service, job_service
from app.utils.security import get_current_user

settings = get_settings()
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreateResponse, status_code=201)
async def create_job(
    data: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new job posting."""
    job = await job_service.create_job(db, user, data)
    interview_link = f"{settings.app_url}/interview/{job.interview_link_token}"
    return JobCreateResponse(
        job=JobResponse.model_validate(job),
        interview_link=interview_link,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all jobs for the current user's company."""
    items, total = await job_service.list_jobs(db, user.company_id, limit, offset)
    return JobListResponse(
        jobs=[JobListItem(**item) for item in items],
        total=total,
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get job detail with candidate summary."""
    job = await job_service.get_job(db, job_id, user.company_id)
    summary = await job_service.get_candidates_summary(db, job_id)
    return JobDetailResponse(
        job=JobResponse.model_validate(job),
        candidates_summary=summary,
    )


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    data: JobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a job posting."""
    job = await job_service.update_job(db, job_id, user.company_id, data)
    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=200)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Archive a job posting (soft delete)."""
    await job_service.delete_job(db, job_id, user.company_id)
    return {"message": "Job archived"}


@router.get("/{job_id}/candidates", response_model=CandidateListResponse)
async def list_candidates(
    job_id: str,
    status: str | None = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List candidates for a job with filtering and sorting."""
    # Validate job ownership
    await job_service.get_job(db, job_id, user.company_id)
    candidates, total = await candidate_service.list_candidates(
        db, job_id, user.company_id, status, sort, order, limit, offset
    )
    return CandidateListResponse(
        candidates=[CandidateListItem.model_validate(c) for c in candidates],
        total=total,
    )
