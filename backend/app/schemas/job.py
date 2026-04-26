"""Job posting request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

JobStatus = Literal["active", "paused", "archived"]
ScreeningMode = Literal["auto_all", "hybrid_threshold", "manual_all"]


class InterviewConfig(BaseModel):
    """Validated interview configuration."""
    num_questions: int = Field(default=8, ge=1, le=20)
    time_limit_minutes: int | None = Field(default=None, ge=5, le=120)


class ScreeningPolicy(BaseModel):
    """Per-job resume screening policy.

    Validates that thresholds are coherent: review_threshold must not exceed
    auto_invite_threshold (otherwise no candidate could ever land in the
    review band under hybrid mode).
    """
    screening_mode: ScreeningMode = "hybrid_threshold"
    auto_invite_threshold: int = Field(default=75, ge=0, le=100)
    review_threshold: int = Field(default=55, ge=0, le=100)

    @model_validator(mode="after")
    def _thresholds_ordered(self) -> "ScreeningPolicy":
        if self.review_threshold > self.auto_invite_threshold:
            raise ValueError(
                "review_threshold must be <= auto_invite_threshold"
            )
        return self


# --- Requests ---


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=50)
    department: str | None = None
    location: str | None = None
    employment_type: str = "full_time"
    required_skills: list[str] = Field(default_factory=list)
    custom_questions: list[dict] | None = None
    interview_config: InterviewConfig | None = None
    auto_send_status_emails: bool | None = None
    # Screening policy (all optional; defaults applied server-side).
    screening_mode: ScreeningMode | None = None
    auto_invite_threshold: int | None = Field(default=None, ge=0, le=100)
    review_threshold: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def _thresholds_ordered(self) -> "JobCreateRequest":
        if (
            self.review_threshold is not None
            and self.auto_invite_threshold is not None
            and self.review_threshold > self.auto_invite_threshold
        ):
            raise ValueError(
                "review_threshold must be <= auto_invite_threshold"
            )
        return self


class JobUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=50)
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    required_skills: list[str] | None = None
    custom_questions: list[dict] | None = None
    interview_config: InterviewConfig | None = None
    auto_send_status_emails: bool | None = None
    status: JobStatus | None = None
    screening_mode: ScreeningMode | None = None
    auto_invite_threshold: int | None = Field(default=None, ge=0, le=100)
    review_threshold: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def _thresholds_ordered(self) -> "JobUpdateRequest":
        # Only validate when both supplied in the same patch; otherwise we
        # don't know the resulting combined values.
        if (
            self.review_threshold is not None
            and self.auto_invite_threshold is not None
            and self.review_threshold > self.auto_invite_threshold
        ):
            raise ValueError(
                "review_threshold must be <= auto_invite_threshold"
            )
        return self


# --- Responses ---


class JobResponse(BaseModel):
    id: str
    title: str
    description: str
    department: str | None = None
    location: str | None = None
    employment_type: str
    required_skills: list[str] | None = None
    custom_questions: list[dict] | None = None
    interview_config: dict
    auto_send_status_emails: bool = True
    status: JobStatus
    interview_link_token: str | None = None
    screening_mode: ScreeningMode = "auto_all"
    auto_invite_threshold: int = 75
    review_threshold: int = 55
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    id: str
    title: str
    status: JobStatus
    department: str | None = None
    location: str | None = None
    candidate_count: int = 0
    avg_score: float | None = None
    created_at: datetime


class JobCreateResponse(BaseModel):
    job: JobResponse
    interview_link: str


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
    total: int


class JobDetailResponse(BaseModel):
    job: JobResponse
    candidates_summary: dict

