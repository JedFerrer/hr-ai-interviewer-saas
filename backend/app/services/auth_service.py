"""Auth service: signup, login business logic."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.user import User
from app.schemas.auth import SignupRequest
from app.utils.security import create_access_token, hash_password, verify_password


async def signup(db: AsyncSession, data: SignupRequest) -> tuple[User, Company, str]:
    """Create a new company + user. Returns (user, company, access_token).

    Raises HTTPException 409 if email is already taken.
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

    user = User(
        company_id=company.id,
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        role="admin",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await db.refresh(company)

    token = create_access_token(user.id, company.id, user.role)
    return user, company, token


async def login(db: AsyncSession, email: str, password: str) -> tuple[User, str]:
    """Verify credentials and return (user, access_token).

    Raises HTTPException 401 on invalid credentials.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    token = create_access_token(user.id, user.company_id, user.role)
    return user, token
