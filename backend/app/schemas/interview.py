"""Interview (public) request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class InterviewLandingResponse(BaseModel):
    job_title: str
    company_name: str
    description: str


# --- Application (Phase A) ---

class ApplicationResponse(BaseModel):
    """Returned immediately after candidate submits application.

    Note: interview_token is intentionally NOT exposed here — it is delivered
    only via the (rate-limited, server-side) invite email to prevent hijack.
    """
    message: str
    candidate_id: str
    status: str  # "processing"


class ApplicationStatusResponse(BaseModel):
    """Poll endpoint to check if application processing is done."""
    status: str  # applied, processing, ready, in_progress, completed
    interview_link: str | None = None


# --- Interview Session (Phase B) ---

class SessionLandingResponse(BaseModel):
    """Returned when candidate opens their interview link."""
    job_title: str
    company_name: str
    candidate_name: str
    total_questions: int
    status: str
    current_question_index: int = 0  # Populated for in_progress sessions so the frontend can restore progress on refresh


class SessionStartResponse(BaseModel):
    """Returned when candidate starts the interview (instant — questions pre-loaded)."""
    interview_token: str
    first_message: str
    total_questions: int


# --- Legacy (kept for backward compat) ---

class InterviewStartResponse(BaseModel):
    interview_token: str
    first_question: str
    total_questions: int


class InterviewMessageRequest(BaseModel):
    interview_token: str
    message: str
    integrity_signals: dict | None = None


class InterviewMessageResponse(BaseModel):
    ai_response: str
    progress: str  # e.g. "3/8"
    is_complete: bool
    is_last_question: bool = False


class InterviewStatusResponse(BaseModel):
    status: str
    progress: str
