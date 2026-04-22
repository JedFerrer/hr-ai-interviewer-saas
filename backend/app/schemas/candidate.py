"""Candidate request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CandidateListItem(BaseModel):
    id: str
    name: str | None
    email: str | None
    status: str
    overall_score: float | None = None
    completed_at: datetime | None = None
    resume_url: str | None = None

    model_config = {"from_attributes": True}


class CandidateListResponse(BaseModel):
    candidates: list[CandidateListItem]
    total: int


class EvaluationResponse(BaseModel):
    overall_score: float | None
    scores: dict | None = None
    summary: str | None
    strengths: list[str] | None = None
    gaps: list[str] | None = None
    red_flags: list[str] | None = None
    recommendation: str | None


class InterviewSummaryResponse(BaseModel):
    id: str
    status: str
    transcript: list[dict] | None = None
    transcript_length: int = 0
    integrity_signals: dict | None = None
    cost_usd: float = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CandidateDetailResponse(BaseModel):
    id: str
    name: str | None
    email: str | None
    status: str
    resume_url: str | None
    resume_parsed_data: dict | None
    interview: InterviewSummaryResponse | None = None
    evaluation: EvaluationResponse | None = None
    created_at: datetime


class StatusUpdateRequest(BaseModel):
    note: str | None = None
