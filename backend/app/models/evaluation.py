"""Evaluation model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.interview import Interview


class EvaluationRecord(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    interview_id: Mapped[str] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), unique=True
    )
    overall_score: Mapped[float | None] = mapped_column(Numeric(3, 1))
    skill_match: Mapped[float | None] = mapped_column(Numeric(3, 1))
    communication: Mapped[float | None] = mapped_column(Numeric(3, 1))
    problem_solving: Mapped[float | None] = mapped_column(Numeric(3, 1))
    cultural_fit: Mapped[float | None] = mapped_column(Numeric(3, 1))
    summary: Mapped[str | None] = mapped_column(Text)
    strengths: Mapped[dict | None] = mapped_column(JSON)  # list of strings
    gaps: Mapped[dict | None] = mapped_column(JSON)
    red_flags: Mapped[dict | None] = mapped_column(JSON)
    recommendation: Mapped[str | None] = mapped_column(String(20))
    evaluation_tokens: Mapped[int | None] = mapped_column(Integer)
    evaluation_cost_usd: Mapped[float | None] = mapped_column(Numeric(8, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    interview: Mapped["Interview"] = relationship(back_populates="evaluation")
