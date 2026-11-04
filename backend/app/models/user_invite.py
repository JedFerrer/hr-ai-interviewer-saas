"""User invitation model.

A pending invite for a new user to join an existing company. Created by
an authenticated user via the team-management UI; consumed by a public
``/auth/invite/{token}/accept`` endpoint that creates the new ``User``
and starts a session.

Security
--------
The raw token is a cryptographically random URL-safe string sent only in
the invitation email and never persisted. The DB stores only the SHA-256
hex digest of the token, so a leaked database snapshot does not contain
usable invite links (same pattern as password-reset tokens).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.company import Company


class UserInvite(Base, TimestampMixin):
    __tablename__ = "user_invites"
    __table_args__ = (
        # Prevent two simultaneous outstanding invites for the same address
        # in the same company (UI also revokes/replaces, but defence-in-depth).
        UniqueConstraint("company_id", "email", name="uq_invite_company_email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    invited_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(50), default="recruiter", nullable=False)

    # SHA-256 hex digest of the raw invite token. Indexed for O(log n) lookup.
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    company: Mapped["Company"] = relationship()
