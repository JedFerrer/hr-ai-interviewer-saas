"""Team / invite request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator
from app.utils.passwords import validate_password_bytes


class InviteCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    email: EmailStr


class InviteResponse(BaseModel):
    id: str
    email: str
    role: str
    invited_by_user_id: str | None
    expires_at: datetime
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InviteListResponse(BaseModel):
    invites: list[InviteResponse]


class TeamMemberResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class TeamMembersResponse(BaseModel):
    members: list[TeamMemberResponse]


class InvitePreviewResponse(BaseModel):
    """Returned by the public ``GET /auth/invite/{token}`` endpoint.

    Lets the accept-invite page render the company name and pre-fill the
    invitee email before they choose a password.
    """

    email: str
    company_name: str
    expires_at: datetime


class InviteAcceptRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_complexity(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError(
                "Password must contain at least one letter and one digit."
            )
        return validate_password_bytes(v)
