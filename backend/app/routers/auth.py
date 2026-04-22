"""Auth router: signup, login, logout, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.rate_limiter import limiter
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
from app.utils.cookies import clear_session_cookie, set_session_cookie
from app.utils.security import csrf_protect, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    data: SignupRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Create a new company and user account, set session cookie."""
    user, company, token = await auth_service.signup(db, data)
    set_session_cookie(response, token, get_settings())
    return AuthResponse(
        user=UserResponse.model_validate(user),
        company=CompanyResponse.model_validate(company),
        access_token=token,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(
    request: Request,
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate, set session cookie, and also return JWT for API clients."""
    _, token = await auth_service.login(db, data.email, data.password)
    set_session_cookie(response, token, get_settings())
    return TokenResponse(access_token=token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(csrf_protect)],
)
async def logout():
    """Clear the session cookie. Idempotent — safe to call when not logged in."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Get the current user profile."""
    return MeResponse(
        user=UserResponse.model_validate(current_user),
        company=CompanyResponse.model_validate(current_user.company),
    )
