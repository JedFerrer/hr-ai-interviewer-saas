"""Auth service: signup, login business logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.company import Company
from app.models.user import User
from app.schemas.auth import SignupRequest
from app.utils.audit import audit
from app.utils.security import create_access_token, hash_password, verify_password


async def signup(db: AsyncSession, data: SignupRequest) -> tuple[User, Company, str]:
    """Create a new company + user. Returns (user, company, access_token).

    Raises HTTPException 409 if email is already taken (race-safe via DB unique constraint).
    """
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    company = Company(name=data.company_name)
    db.add(company)
    await db.flush()  # Get company.id

    now = datetime.now(timezone.utc)
    user = User(
        company_id=company.id,
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        role="admin",
        password_changed_at=now,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    await db.refresh(user)
    await db.refresh(company)

    audit("user.signup", user_id=user.id, company_id=company.id)
    token = create_access_token(
        user.id, company.id, user.role, password_changed_at=user.password_changed_at
    )
    return user, company, token


async def login(db: AsyncSession, email: str, password: str) -> tuple[User, str]:
    """Verify credentials and return (user, access_token).

    Implements account lockout after N failed attempts within a window.
    Raises HTTPException 401 on invalid credentials, 423 when locked.
    """
    settings = get_settings()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    # Reject locked accounts before checking password.
    if user and user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            audit("user.login.locked", user_id=user.id, email=email)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed logins. Try again later.",
            )

    if not user or not verify_password(password, user.password_hash):
        if user is not None:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= settings.max_failed_login_attempts:
                user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
                user.failed_login_count = 0
                audit("user.login.lockout_triggered", user_id=user.id, email=email)
            await db.commit()
        audit("user.login.failed", email=email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    # Successful login — reset counters.
    if user.failed_login_count or user.locked_until:
        user.failed_login_count = 0
        user.locked_until = None
        await db.commit()

    audit("user.login", user_id=user.id, company_id=user.company_id)
    token = create_access_token(
        user.id, user.company_id, user.role, password_changed_at=user.password_changed_at
    )
    return user, token

