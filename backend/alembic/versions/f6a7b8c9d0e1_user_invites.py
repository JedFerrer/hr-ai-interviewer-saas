"""Add user_invites table for multi-user-per-company invitation flow.

The raw invite token is never persisted; only its SHA-256 hex digest goes
into ``token_hash``. This means a leaked database snapshot does not
contain any usable invite links.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_invites",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "company_id",
            sa.String(length=36),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "invited_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="admin"),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("company_id", "email", name="uq_invite_company_email"),
        sa.UniqueConstraint("token_hash", name="uq_invite_token_hash"),
    )
    op.create_index(
        "ix_user_invites_company_id", "user_invites", ["company_id"], unique=False
    )
    op.create_index("ix_user_invites_email", "user_invites", ["email"], unique=False)
    op.create_index(
        "ix_user_invites_token_hash", "user_invites", ["token_hash"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_user_invites_token_hash", table_name="user_invites")
    op.drop_index("ix_user_invites_email", table_name="user_invites")
    op.drop_index("ix_user_invites_company_id", table_name="user_invites")
    op.drop_table("user_invites")
