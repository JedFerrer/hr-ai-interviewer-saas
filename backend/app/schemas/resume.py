"""Resume schema: validates LLM-extracted resume data before persistence.

The LLM may return arbitrary structures or extra fields. Validating with this
model ensures downstream consumers (interview prompt builder, evaluator, UI)
always receive a known shape and never crash on missing keys.

The shape mirrors `RESUME_EXTRACTION_PROMPT` exactly so a contract drift
between prompt / schema / frontend can't silently drop fields. Older payloads
that used `title`/`description` still validate via `AliasChoices`.
"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class ResumeExperience(BaseModel):
    # `populate_by_name=True` lets us keep the canonical name `role` while
    # accepting legacy `title` payloads stored in older candidate rows.
    # `description` (legacy free-text) is intentionally dropped via
    # `extra="ignore"` because it's incompatible with the new
    # `highlights: list[str]` shape.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    company: str | None = None
    role: str | None = Field(
        default=None,
        validation_alias=AliasChoices("role", "title"),
    )
    duration: str | None = None
    highlights: list[str] = Field(default_factory=list)


class ResumeEducation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    degree: str | None = None
    institution: str | None = None
    # Year is kept as a string: resumes commonly use ranges ("2018-2022") or
    # partial dates ("Expected 2026") that don't fit a plain integer.
    # We coerce ints (LLM frequently returns 2023 instead of "2023") so
    # parsing doesn't fail on an otherwise-fine resume.
    year: str | None = None

    @field_validator("year", mode="before")
    @classmethod
    def _coerce_year(cls, v):  # noqa: ANN001
        if v is None or isinstance(v, str):
            return v
        # Accept int / float years from the LLM; everything else falls back
        # to str() so we never hard-fail on a numeric year.
        return str(v)


class ResumeData(BaseModel):
    """Normalized resume payload stored in `Candidate.resume_parsed_data`."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    years_experience: int | None = None
    current_role: str | None = None
    current_company: str | None = None
    summary: str = Field(default="")
    skills: list[str] = Field(default_factory=list)
    experience: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
