"""Job posting request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal["active", "paused", "archived"]


class InterviewConfig(BaseModel):
    """Validated interview configuration."""
    num_questions: int = Field(default=8, ge=1, le=20)
    time_limit_minutes: int | None = Field(default=None, ge=5, le=120)


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


class JobUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=50)
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    required_skills: list[str] | None = None
    custom_questions: list[dict] | None = None
    interview_config: InterviewConfig | None = None
    status: JobStatus | None = None


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
    status: JobStatus
    interview_link_token: str | None = None
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
