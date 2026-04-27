"""Internal calibration analytics for the screening pipeline.

Exposes aggregate statistics over the `screening_outcomes` audit log so
HR / engineering can sanity-check whether the algorithmic recommendation
agrees with eventual HR decisions.

This is an internal endpoint scoped to the authenticated user's company.
There is no public dashboard yet — the JSON response is enough until we
have ~200 ground-truth data points worth charting.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.candidate import Candidate
from app.models.job_posting import JobPosting
from app.models.screening_outcome import ScreeningOutcome
from app.models.user import User
from app.utils.security import get_current_user

router = APIRouter(prefix="/admin/calibration", tags=["admin"])


# Score buckets for the distribution histogram.
_SCORE_BUCKETS: list[tuple[int, int, str]] = [
    (0, 25, "0-24"),
    (25, 50, "25-49"),
    (50, 75, "50-74"),
    (75, 90, "75-89"),
    (90, 101, "90-100"),
]


def _score_bucket(score: float | None) -> str:
    if score is None:
        return "unknown"
    s = int(score)
    for lo, hi, label in _SCORE_BUCKETS:
        if lo <= s < hi:
            return label
    return "unknown"


def _confidence_bucket(c: float | None) -> str:
    if c is None:
        return "unknown"
    if c < 0.4:
        return "low (<0.4)"
    if c < 0.7:
        return "medium (0.4-0.7)"
    return "high (>=0.7)"


@router.get("")
async def get_calibration(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return aggregate calibration stats for the caller's company.

    Joins `screening_outcomes` -> `candidates` -> `job_postings` so we can
    filter by `company_id` (an outcome row has no company column directly
    because it survives candidate deletion).
    """
    stmt = (
        select(ScreeningOutcome)
        .join(Candidate, Candidate.id == ScreeningOutcome.candidate_id)
        .join(JobPosting, JobPosting.id == Candidate.job_posting_id)
        .where(JobPosting.company_id == user.company_id)
    )
    rows = (await db.execute(stmt)).scalars().all()

    total = len(rows)

    # ---- Decision distribution ----
    decision_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        decision_counts[r.decision] += 1

    # ---- Score x HR-decision crosstab ----
    score_x_hr: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        bucket = _score_bucket(float(r.score) if r.score is not None else None)
        hr = r.hr_decision or "pending"
        score_x_hr[bucket][hr] += 1

    # ---- Confidence x HR-invite agreement ----
    # For each confidence bucket, what fraction of predictions ended up
    # invited (or shortlisted) vs rejected by HR?
    conf_buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"invited_or_short": 0, "rejected": 0, "pending": 0, "n": 0}
    )
    for r in rows:
        cb = _confidence_bucket(
            float(r.confidence) if r.confidence is not None else None
        )
        conf_buckets[cb]["n"] += 1
        if r.hr_decision in {"invited", "shortlisted"}:
            conf_buckets[cb]["invited_or_short"] += 1
        elif r.hr_decision in {"rejected_by_hr", "rejected_after_review"}:
            conf_buckets[cb]["rejected"] += 1
        else:
            conf_buckets[cb]["pending"] += 1

    # ---- Agreement rate (where ground truth exists) ----
    # We say the algorithm "agrees" with HR when:
    #   auto_invite -> invited or shortlisted
    #   review      -> any HR decision counts as "we asked HR, HR decided" (informative but not strictly agreement)
    #   reject      -> rejected_by_hr (rare today since reject mode is unused)
    agree_pred_truth = 0
    disagree_pred_truth = 0
    for r in rows:
        if r.hr_decision is None:
            continue
        if r.decision == "auto_invite" and r.hr_decision in {"invited", "shortlisted"}:
            agree_pred_truth += 1
        elif r.decision == "auto_invite" and r.hr_decision in {
            "rejected_by_hr",
            "rejected_after_review",
        }:
            disagree_pred_truth += 1
        # `review` predictions don't have a ground-truth-disagreement
        # interpretation — HR was always the decision-maker there.

    total_with_truth = agree_pred_truth + disagree_pred_truth
    auto_invite_agreement = (
        agree_pred_truth / total_with_truth if total_with_truth else None
    )

    return {
        "total_predictions": total,
        "decision_counts": dict(decision_counts),
        "score_x_hr_decision": {k: dict(v) for k, v in score_x_hr.items()},
        "confidence_buckets": {k: dict(v) for k, v in conf_buckets.items()},
        "auto_invite_agreement_rate": auto_invite_agreement,
        "auto_invite_agreement_sample_size": total_with_truth,
        "ground_truth_coverage": (
            sum(1 for r in rows if r.hr_decision is not None) / total
            if total else 0.0
        ),
    }
