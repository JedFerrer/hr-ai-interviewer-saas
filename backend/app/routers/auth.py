"""Auth router: signup, login, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    CompanyResponse,
    LoginRequest,
    MeResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Create a new company and user account."""
    user, company, token = await auth_service.signup(db, data)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        company=CompanyResponse.model_validate(company),
        access_token=token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and receive a JWT."""
    _, token = await auth_service.login(db, data.email, data.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Get the current user profile."""
    return MeResponse(
        user=UserResponse.model_validate(current_user),
        company=CompanyResponse.model_validate(current_user.company),
    )
