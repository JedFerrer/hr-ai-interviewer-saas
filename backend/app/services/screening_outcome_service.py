"""Service helpers for the `screening_outcomes` audit log.

Two responsibilities:
1. `record_prediction` — invoked once at the moment the screening engine
   returns a decision for a candidate. Inserts an immutable row.
2. `record_hr_decision` / `record_interview_outcome` / `record_hire_outcome`
   — invoked from the HR action endpoints to back-fill ground truth on the
   most recent prediction row for the candidate.

All functions are best-effort: they catch and log their own exceptions so
a logging failure can never block the candidate workflow they hang off of.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.screening_outcome import ScreeningOutcome

logger = logging.getLogger(__name__)


HRDecision = Literal[
    "invited",
    "rejected_by_hr",
    "shortlisted",
    "rejected_after_review",
]
InterviewOutcomeKind = Literal["passed", "failed", "no_show"]
HireOutcomeKind = Literal["hired", "declined", "rejected_after_interview"]


async def record_prediction(
    db: AsyncSession,
    *,
    candidate_id: str,
    job_posting_id: str,
    score: float | None,
    confidence: float | None,
    decision: str,
    matched_skills: list[str] | None,
    missing_skills: list[str] | None,
    deterministic_recall: float | None,
) -> ScreeningOutcome | None:
    """Append a prediction row. Caller is responsible for committing the
    surrounding transaction; we flush so the row is visible to the same
    session, but commits are left to the caller to keep the prediction
    atomic with the candidate update.

    Returns the inserted row, or None if persistence failed (logged).
    """
    try:
        outcome = ScreeningOutcome(
            candidate_id=candidate_id,
            job_posting_id=job_posting_id,
            score=score,
            confidence=confidence,
            decision=decision,
            matched_skills=list(matched_skills) if matched_skills is not None else None,
            missing_skills=list(missing_skills) if missing_skills is not None else None,
            deterministic_recall=deterministic_recall,
            predicted_at=datetime.now(timezone.utc),
        )
        db.add(outcome)
        await db.flush()
        return outcome
    except Exception:
        logger.exception(
            "Failed to record screening prediction for candidate %s", candidate_id
        )
        return None


async def _latest_for_candidate(
    db: AsyncSession, candidate_id: str
) -> ScreeningOutcome | None:
    """Most recent prediction row for a candidate, or None.

    A candidate is rarely re-screened today, but the schema supports it —
    so we always anchor ground-truth updates to the latest prediction.
    """
    stmt = (
        select(ScreeningOutcome)
        .where(ScreeningOutcome.candidate_id == candidate_id)
        .order_by(ScreeningOutcome.predicted_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def record_hr_decision(
    db: AsyncSession,
    *,
    candidate_id: str,
    decision: HRDecision,
    note: str | None = None,
) -> None:
    """Back-fill the HR decision on the latest prediction row.

    Only sets `hr_decision` if it is currently NULL — once HR has made a
    call, subsequent overrides are recorded but the ORIGINAL decision is
    preserved (we add a note, we don't rewrite history).
    """
    try:
        outcome = await _latest_for_candidate(db, candidate_id)
        if outcome is None:
            # No prediction was recorded (e.g. legacy candidate). Skip
            # silently — calibration just won't include this row.
            return
        if outcome.hr_decision is None:
            outcome.hr_decision = decision
            outcome.hr_decision_at = datetime.now(timezone.utc)
        if note:
            existing = outcome.hr_note or ""
            outcome.hr_note = (existing + "\n" + note).strip() if existing else note
        await db.flush()
    except Exception:
        logger.exception(
            "Failed to record HR decision %s for candidate %s",
            decision,
            candidate_id,
        )


async def record_interview_outcome(
    db: AsyncSession,
    *,
    candidate_id: str,
    outcome_kind: InterviewOutcomeKind,
) -> None:
    try:
        row = await _latest_for_candidate(db, candidate_id)
        if row is None:
            return
        row.interview_outcome = outcome_kind
        row.interview_outcome_at = datetime.now(timezone.utc)
        await db.flush()
    except Exception:
        logger.exception(
            "Failed to record interview outcome %s for candidate %s",
            outcome_kind,
            candidate_id,
        )


async def record_hire_outcome(
    db: AsyncSession,
    *,
    candidate_id: str,
    outcome_kind: HireOutcomeKind,
) -> None:
    try:
        row = await _latest_for_candidate(db, candidate_id)
        if row is None:
            return
        row.hire_outcome = outcome_kind
        row.hire_outcome_at = datetime.now(timezone.utc)
        await db.flush()
    except Exception:
        logger.exception(
            "Failed to record hire outcome %s for candidate %s",
            outcome_kind,
            candidate_id,
        )
