"""Candidate model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Candidate(Base, TimestampMixin):
    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("normalized_email", "job_posting_id", name="uq_candidate_email_job"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_posting_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    normalized_email: Mapped[str | None] = mapped_column(String(255), index=True)
    resume_url: Mapped[str | None] = mapped_column(String(500))
    resume_parsed_data: Mapped[dict | None] = mapped_column(JSON)
    # Statuses: applied → processing → ready → in_progress → completed → shortlisted / rejected
    status: Mapped[str] = mapped_column(String(20), default="applied", index=True)
    overall_score: Mapped[float | None] = mapped_column(Numeric(3, 1))
    interview_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True
    )
    interview_link_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    job_posting: Mapped["JobPosting"] = relationship(back_populates="candidates")
    interview: Mapped["Interview | None"] = relationship(
        back_populates="candidate", uselist=False, cascade="all, delete-orphan"
    )
