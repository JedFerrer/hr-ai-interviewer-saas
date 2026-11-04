"""Dashboard analytics aggregations.

Single entry point: `get_overview()`. All queries are scoped to the
caller's `company_id` via the `JobPosting.company_id` join. Definitions
match `docs/architecture.md` exactly — when changing metrics,
update the dictionary first.

Performance contract (see metrics doc): one round-trip per logical
section, no per-job fan-out. Median time-to-complete is computed in
Python because SQLite has no MEDIAN aggregate; we fetch per-job
durations in a single query and reduce in memory.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException, status as http_status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.evaluation import EvaluationRecord
from app.models.interview import Interview
from app.models.job_posting import JobPosting
from app.models.screening_outcome import ScreeningOutcome

WindowLiteral = Literal["7d", "30d", "90d", "all"]

# Cap per action-needed bucket. Keep small — the panel is meant to be
# scannable, not a queue UI.
_ACTION_ITEM_CAP = 20

# Stale thresholds, in hours. Constants for v1; per-job overrides later.
_AWAITING_DECISION_HOURS = 48
_STALLED_INVITE_HOURS = 48

# Per-job table cap. Companies with more active jobs need pagination
# (Phase 2). Until then, we surface the busiest jobs.
_JOB_TABLE_CAP = 50

# Calibration agreement is hidden until we have at least this many
# screened-then-decided cases. Smaller samples are too noisy to act on.
_CALIBRATION_MIN_SAMPLE = 20

# Score histogram buckets for the per-job analytics page. Overall_score
# is on a 0-10 scale; we use 1-point buckets and treat the top bucket
# as inclusive on its upper bound so a perfect 10 lands somewhere.
_SCORE_BUCKETS: list[tuple[float, float, str]] = [
    (0.0, 2.0, "0-2"),
    (2.0, 4.0, "2-4"),
    (4.0, 6.0, "4-6"),
    (6.0, 7.0, "6-7"),
    (7.0, 8.0, "7-8"),
    (8.0, 9.0, "8-9"),
    (9.0, 10.01, "9-10"),
]


def _window_cutoff(window: WindowLiteral, now: datetime) -> datetime | None:
    """Return the inclusive lower bound for the given window, or None for 'all'."""
    if window == "all":
        return None
    days = {"7d": 7, "30d": 30, "90d": 90}[window]
    return now - timedelta(days=days)


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(numerator / denominator, 4)


async def get_overview(
    db: AsyncSession,
    company_id: str,
    window: WindowLiteral,
) -> dict:
    """Build the full dashboard payload for one company / one window."""
    now = datetime.now(timezone.utc)
    cutoff = _window_cutoff(window, now)

    # ------------------------------------------------------------------
    # Helpers: window predicates against specific timestamp columns. When
    # cutoff is None ("all") the predicate degrades to an always-true
    # IS NOT NULL check on the column we're windowing on.
    # ------------------------------------------------------------------
    def _in_window(col):
        if cutoff is None:
            return col.is_not(None)
        return and_(col.is_not(None), col >= cutoff)

    # ------------------------------------------------------------------
    # KPIs (live counts + windowed counts).
    # All candidate/interview reads are scoped via the JobPosting join.
    # ------------------------------------------------------------------
    # Live: active jobs, pending review, completed-awaiting-decision.
    live_q = select(
        func.count(func.distinct(JobPosting.id)).filter(
            JobPosting.status == "active"
        ).label("active_jobs"),
    ).where(JobPosting.company_id == company_id)
    live_row = (await db.execute(live_q)).one()
    active_jobs = int(live_row.active_jobs or 0)

    # Live candidate state buckets (not windowed).
    live_cand_q = (
        select(Candidate.status, func.count(Candidate.id))
        .join(JobPosting, JobPosting.id == Candidate.job_posting_id)
        .where(JobPosting.company_id == company_id)
        .group_by(Candidate.status)
    )
    live_cand_rows = (await db.execute(live_cand_q)).all()
    live_status_counts = {row[0]: int(row[1] or 0) for row in live_cand_rows}
    pending_review = live_status_counts.get("review_pending", 0)
    completed_awaiting_decision = live_status_counts.get("completed", 0)

    # Windowed candidate metrics (applied / shortlisted / rejected).
    cand_window_q = (
        select(
            func.count().filter(_in_window(Candidate.created_at)).label("applied"),
            func.count().filter(_in_window(Candidate.invite_sent_at)).label("invited"),
            func.count().filter(
                and_(
                    Candidate.status == "shortlisted",
                    _in_window(Candidate.completed_at),
                )
            ).label("shortlisted"),
            func.count().filter(
                and_(
                    Candidate.status == "rejected",
                    _in_window(Candidate.completed_at),
                )
            ).label("rejected"),
            func.count().filter(
                and_(
                    Candidate.status == "review_pending",
                    _in_window(Candidate.created_at),
                )
            ).label("under_review"),
        )
        .select_from(Candidate)
        .join(JobPosting, JobPosting.id == Candidate.job_posting_id)
        .where(JobPosting.company_id == company_id)
    )
    cand_window = (await db.execute(cand_window_q)).one()

    # Windowed interview metrics (started / completed / cost).
    interview_window_q = (
        select(
            func.count().filter(_in_window(Interview.started_at)).label("started"),
            func.count().filter(_in_window(Interview.completed_at)).label("completed"),
            func.coalesce(
                func.sum(Interview.cost_usd).filter(
                    _in_window(Interview.completed_at)
                ),
                0,
            ).label("cost_sum"),
        )
        .select_from(Interview)
        .join(JobPosting, JobPosting.id == Interview.job_posting_id)
        .where(JobPosting.company_id == company_id)
    )
    interview_window = (await db.execute(interview_window_q)).one()

    applications = int(cand_window.applied or 0)
    invited = int(cand_window.invited or 0)
    started = int(interview_window.started or 0)
    completed = int(interview_window.completed or 0)
    shortlisted = int(cand_window.shortlisted or 0)
    rejected = int(cand_window.rejected or 0)
    under_review = int(cand_window.under_review or 0)
    cost_sum = float(interview_window.cost_sum or 0)

    completion_rate = _safe_ratio(completed, invited)
    avg_cost = round(cost_sum / completed, 4) if completed else None

    kpis = {
        "active_jobs": active_jobs,
        "applications": applications,
        "pending_review": pending_review,
        "completion_rate": completion_rate,
        "avg_cost_per_interview_usd": avg_cost,
        "completed_awaiting_decision": completed_awaiting_decision,
    }

    funnel = {
        "applied": applications,
        "under_review": under_review,
        "invited": invited,
        "started": started,
        "completed": completed,
        "shortlisted": shortlisted,
        "rejected": rejected,
    }

    # ------------------------------------------------------------------
    # Action-needed buckets. Each is its own query (different filters,
    # different ORDER BY). Capped at _ACTION_ITEM_CAP rows; the count
    # column is unbounded so the badge stays accurate.
    # ------------------------------------------------------------------
    action_needed = {
        "pending_review": await _action_pending_review(db, company_id),
        "awaiting_decision": await _action_awaiting_decision(db, company_id, now),
        "stalled_invites": await _action_stalled_invites(db, company_id, now),
    }

    # ------------------------------------------------------------------
    # Per-job health table.
    # ------------------------------------------------------------------
    jobs = await _job_health(db, company_id, cutoff)

    # ------------------------------------------------------------------
    # Phase 2: daily trend series + calibration mini-panel.
    # ------------------------------------------------------------------
    trends = await _daily_trends(db, company_id, cutoff, now)
    calibration = await _calibration(db, company_id, cutoff)

    return {
        "window": window,
        "window_start": cutoff,
        "generated_at": now,
        "kpis": kpis,
        "funnel": funnel,
        "action_needed": action_needed,
        "jobs": jobs,
        "trends": trends,
        "calibration": calibration,
    }


# ----------------------------------------------------------------------
# Action-needed helpers
# ----------------------------------------------------------------------

async def _action_pending_review(db: AsyncSession, company_id: str) -> dict:
    base = (
        select(
            Candidate.id,
            Candidate.job_posting_id,
            Candidate.name,
            Candidate.email,
            JobPosting.title,
            func.coalesce(Candidate.pre_screened_at, Candidate.created_at).label("since"),
        )
        .join(JobPosting, JobPosting.id == Candidate.job_posting_id)
        .where(
            JobPosting.company_id == company_id,
            Candidate.status == "review_pending",
        )
    )
    return await _materialize_action_bucket(db, base, order_col="since")


async def _action_awaiting_decision(
    db: AsyncSession, company_id: str, now: datetime
) -> dict:
    threshold = now - timedelta(hours=_AWAITING_DECISION_HOURS)
    base = (
        select(
            Candidate.id,
            Candidate.job_posting_id,
            Candidate.name,
            Candidate.email,
            JobPosting.title,
            Candidate.completed_at.label("since"),
        )
        .join(JobPosting, JobPosting.id == Candidate.job_posting_id)
        .where(
            JobPosting.company_id == company_id,
            Candidate.status == "completed",
            Candidate.completed_at.is_not(None),
            Candidate.completed_at <= threshold,
        )
    )
    return await _materialize_action_bucket(db, base, order_col="since")


async def _action_stalled_invites(
    db: AsyncSession, company_id: str, now: datetime
) -> dict:
    threshold = now - timedelta(hours=_STALLED_INVITE_HOURS)
    # Stalled = invite sent > 48h ago, candidate hasn't progressed past
    # ready/applied state, no interview started yet.
    excluded_statuses = ("shortlisted", "rejected", "completed", "in_progress")
    base = (
        select(
            Candidate.id,
            Candidate.job_posting_id,
            Candidate.name,
            Candidate.email,
            JobPosting.title,
            Candidate.invite_sent_at.label("since"),
        )
        .join(JobPosting, JobPosting.id == Candidate.job_posting_id)
        .outerjoin(Interview, Interview.candidate_id == Candidate.id)
        .where(
            JobPosting.company_id == company_id,
            Candidate.invite_sent_at.is_not(None),
            Candidate.invite_sent_at <= threshold,
            ~Candidate.status.in_(excluded_statuses),
            # Either no interview row, or interview never started.
            (Interview.id.is_(None)) | (Interview.started_at.is_(None)),
        )
    )
    return await _materialize_action_bucket(db, base, order_col="since")


async def _materialize_action_bucket(
    db: AsyncSession, base_select, order_col: str
) -> dict:
    """Run COUNT(*) and a capped SELECT for an action-needed bucket.

    `base_select` must already include a column aliased as the value of
    `order_col` (we sort oldest-first so the most urgent rows surface
    first).
    """
    sub = base_select.subquery()

    count = (
        await db.execute(select(func.count()).select_from(sub))
    ).scalar() or 0

    items_q = (
        select(sub)
        .order_by(sub.c[order_col].asc().nullslast())
        .limit(_ACTION_ITEM_CAP)
    )
    rows = (await db.execute(items_q)).all()

    items = [
        {
            "candidate_id": row[0],
            "job_id": row[1],
            "name": row[2],
            "email": row[3],
            "job_title": row[4],
            "since": row[5],
        }
        for row in rows
    ]
    return {"count": int(count), "items": items}


# ----------------------------------------------------------------------
# Per-job health
# ----------------------------------------------------------------------

async def _job_health(
    db: AsyncSession, company_id: str, cutoff: datetime | None
) -> list[dict]:
    """Aggregate per-job metrics for all non-archived jobs.

    Three queries:
      1. Per-job candidate counters (applied/invited windowed,
         pending_review live).
      2. Per-job interview aggregates (completed count, cost avg, score
         avg) windowed.
      3. Per-job interview durations (raw rows) for median computation.

    Then merge in Python keyed by job_id.
    """
    in_window = (
        (lambda col: col.is_not(None))
        if cutoff is None
        else (lambda col: and_(col.is_not(None), col >= cutoff))
    )

    # 1) Job + candidate counters.
    cand_q = (
        select(
            JobPosting.id.label("job_id"),
            JobPosting.title,
            JobPosting.status,
            func.count(Candidate.id)
            .filter(in_window(Candidate.created_at))
            .label("candidate_count"),
            func.count(Candidate.id)
            .filter(Candidate.status == "review_pending")
            .label("pending_review"),
            func.count(Candidate.id)
            .filter(in_window(Candidate.invite_sent_at))
            .label("invited"),
        )
        .outerjoin(Candidate, Candidate.job_posting_id == JobPosting.id)
        .where(
            JobPosting.company_id == company_id,
            JobPosting.status != "archived",
        )
        .group_by(JobPosting.id)
        .order_by(JobPosting.created_at.desc())
        .limit(_JOB_TABLE_CAP)
    )
    cand_rows = (await db.execute(cand_q)).all()
    if not cand_rows:
        return []

    job_ids = [row.job_id for row in cand_rows]

    # 2) Interview aggregates (completed count, cost avg, score avg).
    int_q = (
        select(
            Interview.job_posting_id.label("job_id"),
            func.count(Interview.id)
            .filter(in_window(Interview.completed_at))
            .label("completed"),
            func.avg(Interview.cost_usd)
            .filter(in_window(Interview.completed_at))
            .label("avg_cost"),
            func.avg(EvaluationRecord.overall_score)
            .filter(in_window(Interview.completed_at))
            .label("avg_score"),
        )
        .outerjoin(
            EvaluationRecord, EvaluationRecord.interview_id == Interview.id
        )
        .where(Interview.job_posting_id.in_(job_ids))
        .group_by(Interview.job_posting_id)
    )
    int_rows = (await db.execute(int_q)).all()
    int_by_job = {row.job_id: row for row in int_rows}

    # 3) Per-job durations for median (Python-side reduce).
    dur_q = (
        select(
            Interview.job_posting_id.label("job_id"),
            Interview.started_at,
            Interview.completed_at,
        )
        .where(
            Interview.job_posting_id.in_(job_ids),
            Interview.started_at.is_not(None),
            in_window(Interview.completed_at),
        )
    )
    dur_rows = (await db.execute(dur_q)).all()
    durations: dict[str, list[float]] = {}
    for row in dur_rows:
        delta = (row.completed_at - row.started_at).total_seconds() / 60.0
        if delta <= 0:
            continue
        durations.setdefault(row.job_id, []).append(delta)

    out: list[dict] = []
    for row in cand_rows:
        ints = int_by_job.get(row.job_id)
        completed = int(ints.completed) if ints and ints.completed else 0
        invited = int(row.invited or 0)
        avg_cost = (
            round(float(ints.avg_cost), 4)
            if ints and ints.avg_cost is not None
            else None
        )
        avg_score = (
            round(float(ints.avg_score), 1)
            if ints and ints.avg_score is not None
            else None
        )
        d = durations.get(row.job_id) or []
        median_minutes = round(statistics.median(d), 1) if d else None

        out.append(
            {
                "id": row.job_id,
                "title": row.title,
                "status": row.status,
                "candidate_count": int(row.candidate_count or 0),
                "pending_review": int(row.pending_review or 0),
                "completion_rate": _safe_ratio(completed, invited),
                "avg_score": avg_score,
                "avg_cost": avg_cost,
                "median_time_to_complete_minutes": median_minutes,
            }
        )

    # Final sort: busiest first (matches metrics doc).
    out.sort(key=lambda r: (-r["candidate_count"], r["title"]))
    return out


# ----------------------------------------------------------------------
# Phase 2: daily trend series
# ----------------------------------------------------------------------

# Trends are capped to avoid unbounded series for window=all on very old
# tenants. ~6 months of daily points is plenty for a sparkline.
_TREND_MAX_DAYS = 180


async def _daily_trends(
    db: AsyncSession,
    company_id: str,
    cutoff: datetime | None,
    now: datetime,
) -> list[dict]:
    """Per-day applications + completed-interviews series for sparklines.

    Returns one entry per day in the window with zero-fill so the
    frontend can render a continuous line without gap-filling. For
    window=all we use the older of (first activity, now - 180d) so the
    chart stays readable.
    """
    # Lower bound of the chart x-axis (UTC midnight).
    if cutoff is not None:
        start_date = cutoff.date()
    else:
        start_date = (now - timedelta(days=_TREND_MAX_DAYS - 1)).date()
    end_date = now.date()

    # Two grouped queries — one per metric — both scoped via JobPosting.
    apps_q = (
        select(
            func.date(Candidate.created_at).label("d"),
            func.count(Candidate.id).label("n"),
        )
        .join(JobPosting, JobPosting.id == Candidate.job_posting_id)
        .where(
            JobPosting.company_id == company_id,
            Candidate.created_at.is_not(None),
            func.date(Candidate.created_at) >= start_date.isoformat(),
        )
        .group_by(func.date(Candidate.created_at))
    )
    comp_q = (
        select(
            func.date(Interview.completed_at).label("d"),
            func.count(Interview.id).label("n"),
        )
        .join(JobPosting, JobPosting.id == Interview.job_posting_id)
        .where(
            JobPosting.company_id == company_id,
            Interview.completed_at.is_not(None),
            func.date(Interview.completed_at) >= start_date.isoformat(),
        )
        .group_by(func.date(Interview.completed_at))
    )

    apps_rows = (await db.execute(apps_q)).all()
    comp_rows = (await db.execute(comp_q)).all()

    apps_by_day = {str(r.d): int(r.n) for r in apps_rows}
    comp_by_day = {str(r.d): int(r.n) for r in comp_rows}

    out: list[dict] = []
    cur = start_date
    while cur <= end_date:
        key = cur.isoformat()
        out.append(
            {
                "date": key,
                "applications": apps_by_day.get(key, 0),
                "completed": comp_by_day.get(key, 0),
            }
        )
        cur = cur + timedelta(days=1)
    return out


# ----------------------------------------------------------------------
# Phase 2: calibration mini-panel
# ----------------------------------------------------------------------

async def _calibration(
    db: AsyncSession,
    company_id: str,
    cutoff: datetime | None,
) -> dict:
    """Agreement between auto-invite predictions and HR ground truth.

    Mirrors the logic in `routers/admin.py::get_calibration` but shrunk
    to the single rate the dashboard cares about. Hidden until
    `_CALIBRATION_MIN_SAMPLE` cases exist (per the metrics doc).
    """
    q = (
        select(ScreeningOutcome.decision, ScreeningOutcome.hr_decision)
        .join(Candidate, Candidate.id == ScreeningOutcome.candidate_id)
        .join(JobPosting, JobPosting.id == Candidate.job_posting_id)
        .where(JobPosting.company_id == company_id)
    )
    if cutoff is not None:
        q = q.where(ScreeningOutcome.predicted_at >= cutoff)

    rows = (await db.execute(q)).all()
    total_predictions = len(rows)

    auto_invite_n = 0
    auto_invite_agreed = 0
    for decision, hr in rows:
        if decision != "auto_invite" or hr is None:
            continue
        auto_invite_n += 1
        if hr in ("invited", "shortlisted"):
            auto_invite_agreed += 1

    agreement = (
        round(auto_invite_agreed / auto_invite_n, 4)
        if auto_invite_n >= _CALIBRATION_MIN_SAMPLE
        else None
    )

    return {
        "sample_size": auto_invite_n,
        "min_sample": _CALIBRATION_MIN_SAMPLE,
        "agreement_rate": agreement,
        "auto_invite_n": auto_invite_n,
        "auto_invite_agreed": auto_invite_agreed,
        "total_predictions": total_predictions,
    }


# ----------------------------------------------------------------------
# Phase 3: per-job analytics
# ----------------------------------------------------------------------

async def get_job_analytics(
    db: AsyncSession,
    company_id: str,
    job_id: str,
    window: WindowLiteral,
) -> dict:
    """Analytics payload for one job: funnel + score histogram + decisions.

    Enforces `company_id` ownership before running any aggregations.
    """
    now = datetime.now(timezone.utc)
    cutoff = _window_cutoff(window, now)

    # Ownership + title lookup in one round-trip.
    job_q = select(JobPosting.id, JobPosting.title).where(
        JobPosting.id == job_id, JobPosting.company_id == company_id
    )
    job_row = (await db.execute(job_q)).first()
    if not job_row:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    def _in_window(col):
        if cutoff is None:
            return col.is_not(None)
        return and_(col.is_not(None), col >= cutoff)

    # ---- Funnel (job-scoped variant of the company funnel) ----
    cand_q = select(
        func.count().filter(_in_window(Candidate.created_at)).label("applied"),
        func.count().filter(_in_window(Candidate.invite_sent_at)).label("invited"),
        func.count()
        .filter(
            and_(
                Candidate.status == "review_pending",
                _in_window(Candidate.created_at),
            )
        )
        .label("under_review"),
        func.count()
        .filter(
            and_(
                Candidate.status == "shortlisted",
                _in_window(Candidate.completed_at),
            )
        )
        .label("shortlisted"),
        func.count()
        .filter(
            and_(
                Candidate.status == "rejected",
                _in_window(Candidate.completed_at),
            )
        )
        .label("rejected"),
    ).where(Candidate.job_posting_id == job_id)
    cand = (await db.execute(cand_q)).one()

    int_q = select(
        func.count().filter(_in_window(Interview.started_at)).label("started"),
        func.count().filter(_in_window(Interview.completed_at)).label("completed"),
        func.coalesce(
            func.sum(Interview.cost_usd).filter(_in_window(Interview.completed_at)),
            0,
        ).label("cost_sum"),
        func.avg(Interview.cost_usd)
        .filter(_in_window(Interview.completed_at))
        .label("avg_cost"),
    ).where(Interview.job_posting_id == job_id)
    ints = (await db.execute(int_q)).one()

    invited = int(cand.invited or 0)
    completed = int(ints.completed or 0)

    funnel = {
        "applied": int(cand.applied or 0),
        "under_review": int(cand.under_review or 0),
        "invited": invited,
        "started": int(ints.started or 0),
        "completed": completed,
        "shortlisted": int(cand.shortlisted or 0),
        "rejected": int(cand.rejected or 0),
    }

    # ---- Score histogram (overall_score from completed evaluations) ----
    scores_q = (
        select(EvaluationRecord.overall_score)
        .join(Interview, Interview.id == EvaluationRecord.interview_id)
        .where(
            Interview.job_posting_id == job_id,
            EvaluationRecord.overall_score.is_not(None),
            _in_window(Interview.completed_at),
        )
    )
    score_values = [
        float(s) for (s,) in (await db.execute(scores_q)).all() if s is not None
    ]
    histogram = _bucketize_scores(score_values)
    avg_score = (
        round(sum(score_values) / len(score_values), 1) if score_values else None
    )

    # ---- Pre-screen decision breakdown (windowed by predicted_at) ----
    dec_q = select(ScreeningOutcome.decision, func.count()).where(
        ScreeningOutcome.job_posting_id == job_id
    )
    if cutoff is not None:
        dec_q = dec_q.where(ScreeningOutcome.predicted_at >= cutoff)
    dec_q = dec_q.group_by(ScreeningOutcome.decision)
    decision_breakdown = {
        str(d or "unknown"): int(n) for d, n in (await db.execute(dec_q)).all()
    }

    return {
        "job_id": job_id,
        "job_title": job_row.title,
        "window": window,
        "window_start": cutoff,
        "generated_at": now,
        "funnel": funnel,
        "score_histogram": histogram,
        "decision_breakdown": decision_breakdown,
        "avg_score": avg_score,
        "avg_cost": round(float(ints.avg_cost), 4) if ints.avg_cost is not None else None,
        "completion_rate": _safe_ratio(completed, invited),
    }


def _bucketize_scores(values: list[float]) -> list[dict]:
    """Distribute scores across `_SCORE_BUCKETS` (Python-side reduce)."""
    buckets = [
        {"lo": lo, "hi": hi, "label": label, "count": 0}
        for (lo, hi, label) in _SCORE_BUCKETS
    ]
    for v in values:
        for b in buckets:
            if b["lo"] <= v < b["hi"]:
                b["count"] += 1
                break
    return buckets
