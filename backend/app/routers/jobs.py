"""Job posting router: CRUD + candidate listing."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
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
from app.utils.pubsub import get_pubsub, job_channel
from app.utils.security import csrf_protect, get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(csrf_protect)])


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


# ---------------------------------------------------------------------------
# Real-time updates (Server-Sent Events)
# ---------------------------------------------------------------------------

# Heartbeat cadence. Long enough to avoid wakeup churn, short enough to keep
# proxies (nginx, cloudflare) from killing the connection at their default
# 30–60s idle timeout.
_SSE_HEARTBEAT_SECONDS = 25.0


async def _candidate_event_stream(
    job_id: str,
) -> AsyncIterator[bytes]:
    """Generator that yields SSE-framed bytes for one subscriber.

    Sends a one-shot ``connected`` event so the client knows the channel is
    live, then alternates between forwarding pub/sub events and emitting an
    SSE comment line as a heartbeat.
    """
    pubsub = get_pubsub()
    channel = job_channel(job_id)

    async with pubsub.subscribe(channel) as queue:
        # Initial “connected” frame — lets the frontend distinguish a live
        # connection from a hung one and dismiss any reconnect spinner.
        yield b"event: connected\ndata: {}\n\n"
        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=_SSE_HEARTBEAT_SECONDS
                    )
                except asyncio.TimeoutError:
                    # SSE comment line — ignored by EventSource but keeps the
                    # TCP connection (and any intermediary) alive.
                    yield b": keepalive\n\n"
                    continue

                event_name = event.get("type", "message")
                payload = json.dumps(event, separators=(",", ":"), default=str)
                yield (
                    f"event: {event_name}\n".encode()
                    + f"data: {payload}\n\n".encode()
                )
        except asyncio.CancelledError:
            # Client disconnected — the async-context-manager cleans up the
            # subscription. Re-raise so Starlette can finalize the response.
            raise


@router.get("/{job_id}/stream")
async def stream_candidate_updates(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Server-Sent Events stream of candidate-status updates for a job.

    Pushes one ``candidate_updated`` event per status change — from the
    background screening pipeline as well as from manual HR actions made by
    other users in the same company. The frontend patches the matching row
    in place; no full re-fetch needed.
    """
    # Authorise: this also 404s if the job belongs to another company.
    await job_service.get_job(db, job_id, user.company_id)

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        # Disable nginx response buffering so events are flushed immediately.
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        _candidate_event_stream(job_id),
        media_type="text/event-stream",
        headers=headers,
    )
