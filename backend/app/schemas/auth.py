"""Auth request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


# --- Requests ---


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# --- Responses ---


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class CompanyResponse(BaseModel):
    id: str
    name: str
    logo_url: str | None = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse
    company: CompanyResponse
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user: UserResponse
    company: CompanyResponse
