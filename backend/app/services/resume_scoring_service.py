"""Resume-vs-JD scoring service.

Given parsed resume data + a job posting, ask the LLM to produce a 0-100 fit
score with a structured breakdown. Used by the screening pipeline to drive
auto-invite vs. HR-review routing.

The function is intentionally pure-ish: it only calls the LLM and validates
output. Persistence + decision routing live in their own modules.
"""

from __future__ import annotations

import json
import logging
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.llm_client import llm_chat_completion
from app.services.llm_utils import strip_code_fences
from app.services.prompts import RESUME_SCORING_PROMPT

logger = logging.getLogger(__name__)


class ResumeMatchBreakdown(BaseModel):
    """Validated LLM output for a resume-vs-JD score."""

    model_config = ConfigDict(extra="ignore")

    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    matched_skills: list[str] = Field(default_factory=list)
    missing_must_haves: list[str] = Field(default_factory=list)
    rationale: str = ""


class ResumeMatchResult(TypedDict):
    """Wire-format dict the rest of the codebase consumes."""
    score: int
    confidence: float
    matched_skills: list[str]
    missing_must_haves: list[str]
    rationale: str
    prompt_tokens: int
    completion_tokens: int


async def score_resume_match(
    *,
    resume_data: dict,
    job_title: str,
    job_description: str,
    required_skills: list[str],
) -> ResumeMatchResult:
    """Score how well a parsed resume matches a job posting.

    Raises ValueError on invalid LLM output so the caller can route to the
    `error` decision branch rather than persisting garbage.
    """
    prompt = RESUME_SCORING_PROMPT.format(
        job_title=job_title,
        required_skills=", ".join(required_skills) if required_skills else "(none specified)",
        job_description=job_description,
        resume_data=json.dumps(resume_data, indent=2, default=str),
    )

    response, _model = await llm_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        json_mode=True,
    )
    raw = response.choices[0].message.content or ""
    cleaned = strip_code_fences(raw)

    try:
        raw_data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Resume scorer did not return valid JSON: {exc}") from exc

    if not isinstance(raw_data, dict):
        raise ValueError("Resume scorer did not return a JSON object")

    try:
        validated = ResumeMatchBreakdown.model_validate(raw_data)
    except ValidationError as exc:
        raise ValueError(f"Resume score failed validation: {exc}") from exc

    pt = response.usage.prompt_tokens if response.usage else 0
    ct = response.usage.completion_tokens if response.usage else 0

    return ResumeMatchResult(
        score=validated.score,
        confidence=validated.confidence,
        matched_skills=validated.matched_skills,
        missing_must_haves=validated.missing_must_haves,
        rationale=validated.rationale,
        prompt_tokens=pt,
        completion_tokens=ct,
    )
