"""tier1 share tokens, email templates, status email tracking

Revision ID: a1b2c3d4e5f6
Revises: 9a015b1daa4d
Create Date: 2026-04-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9a015b1daa4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- candidate_share_tokens ---
    op.create_table(
        "candidate_share_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("candidate_share_tokens", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_candidate_share_tokens_candidate_id"),
            ["candidate_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_candidate_share_tokens_token_hash"),
            ["token_hash"],
            unique=True,
        )

    # --- email_templates ---
    op.create_table(
        "email_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "kind", name="uq_email_template_company_kind"),
    )
    with op.batch_alter_table("email_templates", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_email_templates_company_id"),
            ["company_id"],
            unique=False,
        )

    # --- job_postings.auto_send_status_emails (default false for existing rows) ---
    with op.batch_alter_table("job_postings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "auto_send_status_emails",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )

    # --- candidates.last_status_email_kind / last_status_email_sent_at ---
    with op.batch_alter_table("candidates", schema=None) as batch_op:
        batch_op.add_column(sa.Column("last_status_email_kind", sa.String(length=32), nullable=True))
        batch_op.add_column(
            sa.Column("last_status_email_sent_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("candidates", schema=None) as batch_op:
        batch_op.drop_column("last_status_email_sent_at")
        batch_op.drop_column("last_status_email_kind")

    with op.batch_alter_table("job_postings", schema=None) as batch_op:
        batch_op.drop_column("auto_send_status_emails")

    with op.batch_alter_table("email_templates", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_email_templates_company_id"))
    op.drop_table("email_templates")

    with op.batch_alter_table("candidate_share_tokens", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_candidate_share_tokens_token_hash"))
        batch_op.drop_index(batch_op.f("ix_candidate_share_tokens_candidate_id"))
    op.drop_table("candidate_share_tokens")
