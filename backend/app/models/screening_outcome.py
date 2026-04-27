"""Append-only audit log of every screening prediction.

One row is inserted at the moment the screening engine returns a decision
for a candidate. As HR moves the candidate through the funnel
(invite / reject / shortlist / hire), the same row is updated with the
ground-truth outcome. The row is never deleted — even if the candidate
record is later removed — so we keep historical calibration data.

Why a separate table (vs. extending `candidates`):
- A candidate may be re-screened in the future (e.g. JD changes); each
  prediction deserves its own row so we can compare drift.
- Ground-truth fields nullable today, populated as the funnel advances.
- Decoupling means analytics queries don't tangle with hot-path candidate
  reads.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class ScreeningOutcome(Base, TimestampMixin):
    __tablename__ = "screening_outcomes"
    __table_args__ = (
        Index("ix_screening_outcomes_candidate_job", "candidate_id", "job_posting_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # FKs are nullable + ON DELETE SET NULL so an outcome row outlives the
    # candidate / job it referenced (we still want the calibration data).
    candidate_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="SET NULL"), index=True
    )
    job_posting_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("job_postings.id", ondelete="SET NULL"), index=True
    )

    # ---- Prediction (immutable, set once at insert time) ----
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    decision: Mapped[str] = mapped_column(String(32), index=True)
    deterministic_recall: Mapped[float | None] = mapped_column(Numeric(3, 2))
    matched_skills: Mapped[list | None] = mapped_column(JSON)
    missing_skills: Mapped[list | None] = mapped_column(JSON)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # ---- Ground truth (populated by HR actions over time) ----
    # First HR decision after the prediction: "invited" | "rejected_by_hr"
    # | "shortlisted" | "rejected_after_review". NULL until HR acts.
    hr_decision: Mapped[str | None] = mapped_column(String(32), index=True)
    hr_decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Eventually, after the interview: "passed" | "failed" | "no_show".
    interview_outcome: Mapped[str | None] = mapped_column(String(32))
    interview_outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Final hire signal: "hired" | "declined" | "rejected_after_interview".
    hire_outcome: Mapped[str | None] = mapped_column(String(32))
    hire_outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Optional free-text note from HR explaining the disagreement (used when
    # HR overrides the algorithmic recommendation).
    hr_note: Mapped[str | None] = mapped_column(String(2000))
