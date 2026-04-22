"""Schemas for shareable evaluation reports."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ShareTokenCreateResponse(BaseModel):
    """Returned exactly once when a share link is created."""

    token: str
    url: str
    expires_at: datetime
    token_id: str


class PublicEvaluation(BaseModel):
    overall_score: float | None
    scores: dict | None = None
    summary: str | None = None
    strengths: list[str] | None = None
    gaps: list[str] | None = None
    recommendation: str | None = None


class PublicTranscriptMessage(BaseModel):
    role: str
    content: str
    timestamp: str | None = None


class PublicReportResponse(BaseModel):
    candidate_name: str | None
    job_title: str
    company_name: str
    completed_at: datetime | None = None
    evaluation: PublicEvaluation | None = None
    transcript: list[PublicTranscriptMessage] = []
    expires_at: datetime
