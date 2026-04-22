"""Pydantic schemas for all data contracts in the POC.

Defines the shape of data flowing between modules. All LLM responses
are validated through these schemas before use.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Resume Parsing ---


class Experience(BaseModel):
    company: str
    role: str
    duration: str
    highlights: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str
    year: Optional[int] = None


class ResumeData(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    years_experience: int = 0
    current_role: str = ""
    current_company: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    summary: str = ""


# --- Question Generation ---


class QuestionCategory(str, Enum):
    RESUME_VERIFICATION = "resume_verification"
    ROLE_SPECIFIC = "role_specific"
    BEHAVIORAL = "behavioral"


class InterviewQuestion(BaseModel):
    question: str
    category: QuestionCategory
    intent: str
    follow_up_if_vague: str


# --- Interview Engine ---


class AnswerQuality(str, Enum):
    VAGUE = "vague"
    CONTRADICTORY = "contradictory"
    DETAILED = "detailed"


class FollowUpDecision(BaseModel):
    quality: AnswerQuality
    follow_up: str  # Question text or "NEXT"


class TranscriptMessage(BaseModel):
    role: str  # "interviewer" or "candidate"
    content: str
    timestamp: str = ""


# --- Evaluation ---


class Recommendation(str, Enum):
    STRONG_YES = "strong_yes"
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"
    STRONG_NO = "strong_no"


class EvaluationScores(BaseModel):
    skill_match: float = Field(ge=1, le=10)
    communication: float = Field(ge=1, le=10)
    problem_solving: float = Field(ge=1, le=10)
    cultural_fit: float = Field(ge=1, le=10)


class Evaluation(BaseModel):
    overall_score: float = Field(ge=1, le=10)
    scores: EvaluationScores
    summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    recommendation: Recommendation


# --- Token / Cost Tracking ---


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class CostEntry(BaseModel):
    operation: str
    model: str
    usage: TokenUsage
    cost_usd: float = 0.0
