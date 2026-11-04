"""Invite service: business logic for the multi-user-per-company flow.

Responsibilities
----------------
* Create a pending invite (with a hashed token) and dispatch the email.
* Look up an invite by raw token (constant-time hash compare via DB index).
* Accept an invite \u2014 atomically create the ``User`` and mark the invite
  consumed.
* Revoke a pending invite.

Tokens
------
The raw token is generated with :func:`secrets.token_urlsafe(32)` (256 bits
of entropy). It appears in exactly two places: the email body and the URL
path the recruiter clicks. The DB stores only ``sha256(token).hex``,
so a leaked DB snapshot cannot be used to claim invites.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.company import Company
from app.models.user import User
from app.models.user_invite import UserInvite
from app.utils.audit import audit
from app.utils.operation_locks import serialized
from app.utils.security import create_access_token, hash_password

logger = logging.getLogger(__name__)

INVITE_TTL_DAYS = 7


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@serialized("invite-company", "company_id")
async def create_invite(
    db: AsyncSession,
    *,
    company_id: str,
    inviter: User,
    email: str,
) -> tuple[UserInvite, str]:
    """Create a pending invite and return ``(invite, raw_token)``.

    Raises 409 if there is already an outstanding (non-consumed) invite for
    the same email in the same company, or if a user with that email already
    exists anywhere in the system.
    """
    if inviter.role != "admin" or inviter.company_id != company_id:
        raise HTTPException(status_code=403, detail="Administrator access required")
    normalized = _normalize_email(email)

    # User already exists globally? Don't overwrite or imply we'd merge.
    existing_user = await db.execute(select(User).where(User.email == normalized))
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists.",
        )

    existing_invite = (await db.execute(select(UserInvite).where(
        UserInvite.company_id == company_id, UserInvite.email == normalized
    ))).scalar_one_or_none()
    if existing_invite and existing_invite.revoked_at is None and existing_invite.accepted_at is None:
        expires = existing_invite.expires_at.replace(tzinfo=timezone.utc) if existing_invite.expires_at.tzinfo is None else existing_invite.expires_at
        if expires > _now():
            raise HTTPException(status_code=409, detail="An outstanding invite already exists for this email.")
    raw_token = secrets.token_urlsafe(32)
    invite = existing_invite or UserInvite(company_id=company_id, email=normalized)
    invite.invited_by_user_id = inviter.id
    invite.role = "recruiter"
    invite.token_hash = _hash_token(raw_token)
    invite.expires_at = _now() + timedelta(days=INVITE_TTL_DAYS)
    invite.accepted_at = None
    invite.revoked_at = None
    db.add(invite)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Race with a concurrent invite creation.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An outstanding invite already exists for this email.",
        ) from None
    await db.refresh(invite)

    audit(
        "user.invite.created",
        invite_id=invite.id,
        company_id=company_id,
        inviter_id=inviter.id,
        invitee_email=normalized,
    )
    return invite, raw_token


async def list_invites(
    db: AsyncSession, company_id: str, *, include_consumed: bool = False
) -> list[UserInvite]:
    """List invites for a company. By default only outstanding ones."""
    stmt = select(UserInvite).where(UserInvite.company_id == company_id)
    if not include_consumed:
        stmt = stmt.where(
            UserInvite.accepted_at.is_(None), UserInvite.revoked_at.is_(None)
        )
    stmt = stmt.order_by(UserInvite.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def revoke_invite(
    db: AsyncSession, invite_id: str, company_id: str, *, revoker: User
) -> UserInvite:
    """Mark an invite revoked. 404 if it isn't this company's, 409 if already
    consumed.
    """
    if revoker.role != "admin" or revoker.company_id != company_id:
        raise HTTPException(status_code=403, detail="Administrator access required")
    invite = await db.get(UserInvite, invite_id)
    if invite is None or invite.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found."
        )
    if invite.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot revoke an invite that has already been accepted.",
        )
    if invite.revoked_at is not None:
        return invite  # Idempotent.

    changed = await db.execute(update(UserInvite).where(
        UserInvite.id == invite.id, UserInvite.accepted_at.is_(None)
    ).values(revoked_at=_now()))
    if changed.rowcount != 1:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Invitation is no longer pending")
    await db.commit()
    await db.refresh(invite)
    audit(
        "user.invite.revoked",
        invite_id=invite.id,
        company_id=company_id,
        revoker_id=revoker.id,
    )
    return invite


async def get_invite_by_token(
    db: AsyncSession, raw_token: str
) -> tuple[UserInvite, Company]:
    """Look up an invite by raw token. Returns ``(invite, company)``.

    Raises 404 for unknown / expired / consumed tokens. We do **not**
    distinguish between those reasons in the error to avoid leaking which
    tokens once existed.
    """
    token_hash = _hash_token(raw_token)
    stmt = (
        select(UserInvite)
        .where(UserInvite.token_hash == token_hash)
        .options(selectinload(UserInvite.company))
    )
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invite."
        )
    if invite.role != "recruiter" or invite.revoked_at is not None or invite.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invite."
        )
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < _now():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invite."
        )
    return invite, invite.company


@serialized("invite-token", "raw_token")
async def accept_invite(
    db: AsyncSession,
    *,
    raw_token: str,
    name: str,
    password: str,
) -> tuple[User, Company, str]:
    """Consume an invite, create the User, and return ``(user, company, jwt)``.

    The whole operation is a single DB transaction \u2014 if the user insert
    fails (e.g. someone signed up with that email between preview and
    accept), the invite stays pending and can be retried.
    """
    invite, company = await get_invite_by_token(db, raw_token)

    # Reject if a user with that email exists by the time we accept (race
    # against an independent self-signup).
    existing = await db.execute(select(User).where(User.email == invite.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists.",
        )

    now = _now()
    user = User(
        company_id=invite.company_id,
        email=invite.email,
        password_hash=hash_password(password),
        name=name,
        role="recruiter",
        password_changed_at=now,
    )
    claimed = await db.execute(update(UserInvite).where(
        UserInvite.id == invite.id, UserInvite.token_hash == _hash_token(raw_token),
        UserInvite.accepted_at.is_(None), UserInvite.revoked_at.is_(None),
        UserInvite.expires_at > now, UserInvite.role == "recruiter",
    ).values(accepted_at=now).execution_options(synchronize_session=False))
    if claimed.rowcount != 1:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Invitation is no longer pending")
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists.",
        ) from None
    await db.refresh(user)
    await db.refresh(company)

    audit(
        "user.invite.accepted",
        invite_id=invite.id,
        user_id=user.id,
        company_id=company.id,
    )
    token = create_access_token(
        user.id, company.id, user.role, password_changed_at=user.password_changed_at
    )
    return user, company, token


# ---------------------------------------------------------------------------
# Email dispatch
# ---------------------------------------------------------------------------


async def send_invite_email(
    *,
    invitee_email: str,
    inviter_name: str,
    company_name: str,
    raw_token: str,
) -> bool:
    """Send the invitation email. Best-effort \u2014 returns False on failure
    instead of raising. The router revokes undelivered tokens and returns
    503 so an admin can retry with a fresh token.
    """
    settings = get_settings()
    if settings.portfolio_demo:
        from app.demo.adapters import capture
        return capture("team", invitee_email, f"Join {company_name}", f"Synthetic invitation from {inviter_name}", f"{settings.app_url}/accept-invite/{raw_token}")
    if not settings.resend_api_key:
        logger.warning("Invitation delivery unavailable: email provider is not configured")
        return False

    import html as _html

    import resend

    resend.api_key = settings.resend_api_key
    accept_url = f"{settings.app_url}/accept-invite/{raw_token}"
    safe_inviter = _html.escape(inviter_name)
    safe_company = _html.escape(company_name)

    try:
        resend.Emails.send(
            {
                "from": settings.from_email,
                "to": [invitee_email],
                "subject": f"You've been invited to join {safe_company}",
                "html": f"""
                    <h2>Hi,</h2>
                    <p><strong>{safe_inviter}</strong> has invited you to join
                    the <strong>{safe_company}</strong> team on the AI HR
                    Interviewer platform.</p>
                    <p><a href="{accept_url}"
                       style="background:#2563eb;color:white;padding:12px 24px;
                              text-decoration:none;border-radius:6px;display:inline-block;">
                       Accept invitation</a></p>
                    <p>This invitation expires in {INVITE_TTL_DAYS} days.</p>
                    <p style="color:#6b7280;font-size:12px;">If you weren't
                    expecting this email you can safely ignore it.</p>
                """,
            }
        )
        return True
    except Exception:
        logger.exception("Failed to send invite email to %s", invitee_email)
        return False
