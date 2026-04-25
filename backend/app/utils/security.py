"""Security utilities: password hashing (bcrypt) and JWT (PyJWT)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.utils.cookies import COOKIE_NAME


# --- Password hashing ---


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# --- JWT ---


def create_access_token(
    user_id: str,
    company_id: str,
    role: str,
    password_changed_at: datetime | None = None,
) -> str:
    """Create a short-lived JWT access token.

    `password_changed_at` is embedded so tokens issued before a password change
    can be rejected server-side without per-token storage.
    """
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": user_id,
        "company_id": company_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=s.jwt_expiry_minutes),
    }
    if password_changed_at is not None:
        # Store as integer epoch seconds to keep payload compact
        if password_changed_at.tzinfo is None:
            password_changed_at = password_changed_at.replace(tzinfo=timezone.utc)
        payload["pwd_iat"] = int(password_changed_at.timestamp())
    return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    s = get_settings()
    try:
        return jwt.decode(
            token,
            s.jwt_secret_key,
            algorithms=[s.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def token_expires_in_seconds(token: str) -> int:
    """Return seconds remaining until the token's `exp` claim, clamped to >= 0.

    Returns 0 for malformed/expired tokens rather than raising — callers use
    this purely for surfacing TTL to clients, not for auth decisions.
    """
    s = get_settings()
    try:
        payload = jwt.decode(
            token,
            s.jwt_secret_key,
            algorithms=[s.jwt_algorithm],
        )
    except jwt.PyJWTError:
        return 0
    exp = payload.get("exp")
    if exp is None:
        return 0
    remaining = int(exp) - int(datetime.now(timezone.utc).timestamp())
    return max(remaining, 0)


# --- FastAPI dependency ---


def _extract_token(request: Request) -> str:
    """Return JWT from cookie (preferred) or `Authorization: Bearer` header."""
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("Authorization", "")
    scheme, _, value = auth_header.partition(" ")
    if scheme.lower() == "bearer" and value:
        return value

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: extract and validate JWT from cookie or header."""
    token = _extract_token(request)
    payload = decode_access_token(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(
        select(User)
        .options(selectinload(User.company))
        .where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Reject tokens issued before the user's last password change.
    token_pwd_iat = payload.get("pwd_iat")
    if user.password_changed_at is not None:
        pwd_changed = user.password_changed_at
        if pwd_changed.tzinfo is None:
            pwd_changed = pwd_changed.replace(tzinfo=timezone.utc)
        pwd_changed_ts = int(pwd_changed.timestamp())
        if token_pwd_iat is None or int(token_pwd_iat) < pwd_changed_ts:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
            )
    return user


# --- CSRF guard ---

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_CSRF_HEADER = "X-Requested-With"
_CSRF_VALUE = "XMLHttpRequest"


async def csrf_protect(request: Request) -> None:
    """Block CSRF on cookie-authenticated mutating requests.

    A browser will not attach the `X-Requested-With` header on a cross-site
    HTML form submission, so requiring it on POST/PUT/PATCH/DELETE blocks
    CSRF without needing per-request tokens. Requests authenticated with a
    Bearer header (programmatic clients, server-to-server) are exempt.
    """
    if request.method.upper() in _SAFE_METHODS:
        return

    # Bearer-only requests skip the check; they're not browser navigations.
    if not request.cookies.get(COOKIE_NAME):
        return

    if request.headers.get(_CSRF_HEADER) != _CSRF_VALUE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing or invalid {_CSRF_HEADER} header",
        )
