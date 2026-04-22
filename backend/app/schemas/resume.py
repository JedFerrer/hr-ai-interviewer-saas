"""Resume schema: validates LLM-extracted resume data before persistence.

The LLM may return arbitrary structures or extra fields. Validating with this
model ensures downstream consumers (interview prompt builder, evaluator, UI)
always receive a known shape and never crash on missing keys.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResumeExperience(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str | None = None
    company: str | None = None
    duration: str | None = None
    description: str | None = None


class ResumeEducation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    degree: str | None = None
    institution: str | None = None
    year: str | None = None


class ResumeData(BaseModel):
    """Normalized resume payload stored in `Candidate.resume_parsed_data`."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str = Field(default="")
    skills: list[str] = Field(default_factory=list)
    experience: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
