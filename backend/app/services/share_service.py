"""Share-token service: create / resolve / revoke shareable evaluation links.

Tokens are stored hashed (SHA-256) at rest. The raw token is shown to the
creator exactly once and used in the public URL. Public consumers exchange the
raw token for the report; the server hashes the incoming value and looks up
the row.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job_posting import JobPosting
from app.models.share_token import CandidateShareToken
from app.models.user import User
from app.services.candidate_service import get_candidate_detail


_TOKEN_BYTES = 32  # 256 bits — unguessable


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def create_share_token(
    db: AsyncSession,
    candidate_id: str,
    user: User,
    ttl_days: int | None = None,
) -> tuple[CandidateShareToken, str]:
    """Create a new share token for a candidate. Returns (record, raw_token).

    Tenant isolation is enforced via `get_candidate_detail`.
    """
    # Ownership check — raises 404 if the candidate is in another company.
    candidate = await get_candidate_detail(db, candidate_id, user.company_id)

    settings = get_settings()
    days = ttl_days if ttl_days and ttl_days > 0 else settings.share_link_ttl_days
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
    record = CandidateShareToken(
        candidate_id=candidate.id,
        token_hash=_hash_token(raw_token),
        created_by=user.id,
        expires_at=expires_at,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record, raw_token


async def revoke_share_token(
    db: AsyncSession, candidate_id: str, token_id: str, user: User
) -> None:
    """Revoke a previously issued token. Tenant isolation enforced."""
    # Validate candidate ownership first.
    await get_candidate_detail(db, candidate_id, user.company_id)
    result = await db.execute(
        select(CandidateShareToken).where(
            CandidateShareToken.id == token_id,
            CandidateShareToken.candidate_id == candidate_id,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    token.revoked_at = datetime.now(timezone.utc)
    await db.commit()


async def resolve_share_token(db: AsyncSession, raw_token: str) -> Candidate:
    """Resolve a raw token to its candidate (with interview/evaluation eagerly loaded).

    Raises 404 on any failure mode (not found / expired / revoked) — never leak
    which condition triggered the rejection.
    """
    if not raw_token or len(raw_token) < 16:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    token_hash = _hash_token(raw_token)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(CandidateShareToken).where(CandidateShareToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()
    if not token or token.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    cand_result = await db.execute(
        select(Candidate)
        .options(
            selectinload(Candidate.interview).selectinload(Interview.evaluation),
            selectinload(Candidate.job_posting).selectinload(JobPosting.company),
        )
        .where(Candidate.id == token.candidate_id)
    )
    candidate = cand_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Best-effort view tracking; never block the read on this.
    token.view_count = (token.view_count or 0) + 1
    token.last_viewed_at = now
    await db.commit()

    # Stash expires_at on the candidate object for convenience; not persisted.
    candidate.__share_expires_at = expires_at  # type: ignore[attr-defined]
    return candidate


async def list_share_tokens(
    db: AsyncSession, candidate_id: str, user: User
) -> list[CandidateShareToken]:
    """List all (active + revoked) share tokens for a candidate."""
    await get_candidate_detail(db, candidate_id, user.company_id)
    result = await db.execute(
        select(CandidateShareToken)
        .where(CandidateShareToken.candidate_id == candidate_id)
        .order_by(CandidateShareToken.created_at.desc())
    )
    return list(result.scalars().all())
