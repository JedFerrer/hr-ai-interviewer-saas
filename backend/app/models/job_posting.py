"""JobPosting model."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class JobPosting(Base, TimestampMixin):
    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str] = mapped_column(String(50), default="full_time")
    required_skills: Mapped[dict | None] = mapped_column(JSON)  # stored as JSON list
    custom_questions: Mapped[dict | None] = mapped_column(JSON)
    interview_config: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"num_questions": 8, "style": "standard"}
    )
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    interview_link_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True
    )
    cached_jd_questions: Mapped[dict | None] = mapped_column(JSON)  # cached JD-based questions
    # When True, candidates are emailed automatically on shortlist / reject.
    auto_send_status_emails: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="0"
    )
    # Resume-based screening policy.
    # screening_mode:
    #   "auto_all"         — invite every candidate whose resume parses (legacy)
    #   "hybrid_threshold" — score-based; clear-fit auto-invite, borderline → HR review
    #   "manual_all"       — every applicant lands in HR review queue
    screening_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="auto_all", server_default="auto_all"
    )
    # Score (0-100) at/above which candidates are auto-invited under hybrid mode.
    auto_invite_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=75, server_default="75"
    )
    # Score (0-100) below which candidates are queued for HR review under
    # hybrid mode. Anything in [review_threshold, auto_invite_threshold) goes
    # to the review queue. Below review_threshold is also routed to HR review
    # by default — strict auto-rejection is intentionally not implemented in
    # v1 (see RESUME_GATE_AND_INVITE_PLAN §13.2).
    review_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=55, server_default="55"
    )

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="job_postings")
    creator: Mapped["User | None"] = relationship()
    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="job_posting", cascade="all, delete-orphan"
    )
