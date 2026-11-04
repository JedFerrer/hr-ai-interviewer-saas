"""Candidate model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.job_posting import JobPosting
    from app.models.interview import Interview


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
    # SHA-256 of the raw uploaded resume bytes. Indexed so the fraud
    # detection pass can spot the same file submitted by a different
    # applicant. Nullable for legacy rows imported before the check existed.
    resume_content_hash: Mapped[str | None] = mapped_column(
        String(64), index=True
    )
    resume_parsed_data: Mapped[dict | None] = mapped_column(JSON)
    # Statuses: applied → processing → ready → in_progress → completed → shortlisted / rejected
    # plus: review_pending (awaiting HR pre-screen approval), error (parse / processing failure)
    status: Mapped[str] = mapped_column(String(20), default="applied", index=True)
    overall_score: Mapped[float | None] = mapped_column(Numeric(3, 1))
    # Resume-vs-JD match score (0-100). Populated by the screening pipeline
    # before any interview-related decision is made.
    resume_match_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    # LLM-reported confidence in the match score (0-1).
    resume_match_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    # Structured breakdown returned by the scorer (matched_skills, missing,
    # rationale, etc.). Stored as opaque JSON so we can iterate the schema
    # without migrations.
    resume_match_breakdown: Mapped[dict | None] = mapped_column(JSON)
    # Final pre-screen routing decision: "auto_invite" | "review" | "reject"
    # | "error". Mirrored separately from `status` so HR can see the
    # automated recommendation even after manually approving / rejecting.
    pre_screen_decision: Mapped[str | None] = mapped_column(String(32))
    pre_screen_reason: Mapped[str | None] = mapped_column(String(500))
    pre_screened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invite_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    interview_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True
    )
    interview_link_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Idempotency for status emails: avoid double-sending on repeated flips.
    last_status_email_kind: Mapped[str | None] = mapped_column(String(32))
    last_status_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Relationships
    job_posting: Mapped["JobPosting"] = relationship(back_populates="candidates")
    interview: Mapped["Interview | None"] = relationship(
        back_populates="candidate", uselist=False, cascade="all, delete-orphan"
    )
