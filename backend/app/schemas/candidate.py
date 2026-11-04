"""Candidate request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PreScreenSummary(BaseModel):
    """Resume-vs-JD pre-screen result, surfaced wherever a candidate is shown."""

    score: float | None = None
    confidence: float | None = None
    decision: str | None = None  # "auto_invite" | "review" | "reject" | "error"
    reason: str | None = None
    breakdown: dict | None = None
    pre_screened_at: datetime | None = None
    invite_sent_at: datetime | None = None


class CandidateListItem(BaseModel):
    id: str
    name: str | None
    email: str | None
    status: str
    overall_score: float | None = None
    # Per-dimension breakdown (mirrors EvaluationResponse.scores). Optional —
    # only present when the candidate has a completed evaluation.
    skill_match: float | None = None
    communication: float | None = None
    problem_solving: float | None = None
    cultural_fit: float | None = None
    recommendation: str | None = None
    completed_at: datetime | None = None
    resume_url: str | None = None
    # Pre-screen score (lightweight — full breakdown lives on the detail).
    resume_match_score: float | None = None
    pre_screen_decision: str | None = None

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
    interview_link: str | None = None
    evaluation: EvaluationResponse | None = None
    pre_screen: PreScreenSummary | None = None
    # Mirrors job_posting.auto_send_status_emails so the UI can warn HR
    # whether shortlist/reject will trigger an automatic email.
    job_auto_send_status_emails: bool = False
    # Last externally-visible notification we dispatched to the candidate.
    # The UI uses these to surface "Last notified: Rejected (5 minutes ago)"
    # and to warn HR before sending a contradictory email.
    last_notification_kind: str | None = None
    last_notification_sent_at: datetime | None = None
    created_at: datetime


class StatusUpdateRequest(BaseModel):
    note: str | None = None


class SendNotificationRequest(BaseModel):
    """Explicit request to email the candidate about their status.

    `kind` is the template to use (shortlist / reject / status_correction).
    `force=True` overrides the conflict guard (e.g. HR has acknowledged that
    the prior email was wrong and is intentionally sending a correction).
    """

    kind: str
    force: bool = False


class SendNotificationResponse(BaseModel):
    sent: bool
    kind: str
    last_notification_kind: str | None = None
    last_notification_sent_at: datetime | None = None

