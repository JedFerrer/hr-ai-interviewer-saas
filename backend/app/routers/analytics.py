"""Analytics router — HR home dashboard data.

Single endpoint: `GET /analytics/overview?window=30d`. Replaces the
client-side aggregation that used to fan out N+1 calls (jobs.list +
candidates per job). See `plans/DASHBOARD_METRICS.md` for metric
definitions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    JobAnalyticsResponse,
    OverviewResponse,
    WindowLiteral,
)
from app.services import analytics_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    window: WindowLiteral = Query("30d"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OverviewResponse:
    """Return KPIs, funnel, action queues and per-job health for the
    authenticated user's company.
    """
    payload = await analytics_service.get_overview(db, user.company_id, window)
    return OverviewResponse.model_validate(payload)


@router.get("/jobs/{job_id}", response_model=JobAnalyticsResponse)
async def get_job_analytics(
    job_id: str,
    window: WindowLiteral = Query("30d"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobAnalyticsResponse:
    """Per-job analytics: funnel, score histogram, pre-screen decisions.

    404 if the job doesn't exist or doesn't belong to the caller's
    company (ownership enforced inside the service).
    """
    payload = await analytics_service.get_job_analytics(
        db, user.company_id, job_id, window
    )
    return JobAnalyticsResponse.model_validate(payload)
