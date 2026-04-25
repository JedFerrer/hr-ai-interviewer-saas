"""Auth router: signup, login, logout, me, refresh."""

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
from app.utils.audit import audit
from app.utils.cookies import COOKIE_NAME, clear_session_cookie, set_session_cookie
from app.utils.security import (
    create_access_token,
    csrf_protect,
    get_current_user,
    token_expires_in_seconds,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _ttl_seconds() -> int:
    """Configured access-token lifetime in seconds."""
    return get_settings().jwt_expiry_minutes * 60


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
        expires_in=_ttl_seconds(),
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
    return TokenResponse(access_token=token, expires_in=_ttl_seconds())


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
async def me(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get the current user profile and remaining session lifetime."""
    cookie_token = request.cookies.get(COOKIE_NAME) or ""
    return MeResponse(
        user=UserResponse.model_validate(current_user),
        company=CompanyResponse.model_validate(current_user.company),
        expires_in=token_expires_in_seconds(cookie_token) if cookie_token else _ttl_seconds(),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(csrf_protect)],
)
@limiter.limit("60/minute")
async def refresh(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    """Issue a fresh access token + cookie from a still-valid session.

    Sliding session: requires the current cookie/token to still be valid.
    Preserves `pwd_iat` so password-change revocation continues to work.
    Returns 401 (via `get_current_user`) if the existing token is expired
    or revoked — clients must redirect to /login in that case.
    """
    settings = get_settings()
    new_token = create_access_token(
        current_user.id,
        current_user.company_id,
        current_user.role,
        password_changed_at=current_user.password_changed_at,
    )
    set_session_cookie(response, new_token, settings)
    audit("user.token.refresh", user_id=current_user.id, company_id=current_user.company_id)
    return TokenResponse(access_token=new_token, expires_in=_ttl_seconds())
