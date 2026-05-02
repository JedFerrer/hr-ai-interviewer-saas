"""Dashboard analytics response schemas.

Mirror of the contract documented in `plans/DASHBOARD_METRICS.md`. Any
change here MUST be reflected there first — that document is the source
of truth for metric definitions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

WindowLiteral = Literal["7d", "30d", "90d", "all"]


class OverviewKPIs(BaseModel):
    active_jobs: int
    applications: int
    pending_review: int
    completion_rate: float | None
    avg_cost_per_interview_usd: float | None
    completed_awaiting_decision: int


class OverviewFunnel(BaseModel):
    applied: int
    under_review: int
    invited: int
    started: int
    completed: int
    shortlisted: int
    rejected: int


class ActionItem(BaseModel):
    candidate_id: str
    job_id: str
    name: str | None = None
    email: str | None = None
    job_title: str
    since: datetime | None = None


class ActionBucket(BaseModel):
    count: int
    items: list[ActionItem]


class ActionNeeded(BaseModel):
    pending_review: ActionBucket
    awaiting_decision: ActionBucket
    stalled_invites: ActionBucket


class JobHealthRow(BaseModel):
    id: str
    title: str
    status: str
    candidate_count: int
    pending_review: int
    completion_rate: float | None
    avg_score: float | None
    avg_cost: float | None
    median_time_to_complete_minutes: float | None


class DailyTrendPoint(BaseModel):
    """One day in the windowed trend series.

    `date` is YYYY-MM-DD in UTC. Days with zero activity are emitted
    as zero rows so the frontend can render a continuous sparkline
    without gap-filling logic.
    """

    date: str
    applications: int
    completed: int


class CalibrationStats(BaseModel):
    """AI screening recommendation vs HR ground-truth agreement.

    `agreement_rate` is null until `sample_size >= MIN_SAMPLE` (20).
    UI should show a "needs more data" message while gated.
    """

    sample_size: int
    min_sample: int
    agreement_rate: float | None
    auto_invite_n: int
    auto_invite_agreed: int
    total_predictions: int


class OverviewResponse(BaseModel):
    window: WindowLiteral
    window_start: datetime | None
    generated_at: datetime
    kpis: OverviewKPIs
    funnel: OverviewFunnel
    action_needed: ActionNeeded
    jobs: list[JobHealthRow]
    trends: list[DailyTrendPoint]
    calibration: CalibrationStats


# --- Per-job analytics (Phase 3) ----------------------------------------

class HistogramBucket(BaseModel):
    """One bucket in a numeric histogram.

    `lo` inclusive, `hi` exclusive. The top bucket includes its upper
    bound so a perfect score lands somewhere.
    """

    lo: float
    hi: float
    label: str
    count: int


class JobAnalyticsResponse(BaseModel):
    """Per-job analytics page payload."""

    job_id: str
    job_title: str
    window: WindowLiteral
    window_start: datetime | None
    generated_at: datetime
    funnel: OverviewFunnel
    score_histogram: list[HistogramBucket]
    decision_breakdown: dict[str, int]
    avg_score: float | None
    avg_cost: float | None
    completion_rate: float | None
