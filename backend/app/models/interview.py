"""Interview model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job_posting import JobPosting
    from app.models.evaluation import EvaluationRecord


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    job_posting_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )
    transcript: Mapped[dict] = mapped_column(JSON, default=list)
    planned_questions: Mapped[dict | None] = mapped_column(JSON)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="not_started", index=True)
    integrity_signals: Mapped[dict] = mapped_column(JSON, default=dict)
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    candidate: Mapped["Candidate"] = relationship(back_populates="interview")
    job_posting: Mapped["JobPosting"] = relationship()
    evaluation: Mapped["EvaluationRecord | None"] = relationship(
        back_populates="interview", uselist=False, cascade="all, delete-orphan"
    )
