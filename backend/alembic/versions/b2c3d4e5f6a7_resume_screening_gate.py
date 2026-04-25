"""Resume screening gate: per-job policy + per-candidate pre-screen fields.

Adds the schema needed to support the hybrid screening flow described in
RESUME_GATE_AND_INVITE_PLAN.md:

  * job_postings.screening_mode / auto_invite_threshold / review_threshold
  * candidates.resume_match_score / confidence / breakdown
  * candidates.pre_screen_decision / pre_screen_reason / pre_screened_at
  * candidates.invite_sent_at

The defaults preserve current behaviour: existing jobs keep `auto_all` mode,
so every parsed candidate continues to be auto-invited until HR opts in.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-23 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- job_postings: screening policy ---
    with op.batch_alter_table("job_postings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "screening_mode",
                sa.String(length=32),
                nullable=False,
                server_default="auto_all",
            )
        )
        batch_op.add_column(
            sa.Column(
                "auto_invite_threshold",
                sa.Integer(),
                nullable=False,
                server_default="75",
            )
        )
        batch_op.add_column(
            sa.Column(
                "review_threshold",
                sa.Integer(),
                nullable=False,
                server_default="55",
            )
        )

    # --- candidates: pre-screen fields ---
    with op.batch_alter_table("candidates", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("resume_match_score", sa.Numeric(precision=5, scale=2), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "resume_match_confidence", sa.Numeric(precision=3, scale=2), nullable=True
            )
        )
        batch_op.add_column(sa.Column("resume_match_breakdown", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("pre_screen_decision", sa.String(length=32), nullable=True)
        )
        batch_op.add_column(
            sa.Column("pre_screen_reason", sa.String(length=500), nullable=True)
        )
        batch_op.add_column(
            sa.Column("pre_screened_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("invite_sent_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("candidates", schema=None) as batch_op:
        batch_op.drop_column("invite_sent_at")
        batch_op.drop_column("pre_screened_at")
        batch_op.drop_column("pre_screen_reason")
        batch_op.drop_column("pre_screen_decision")
        batch_op.drop_column("resume_match_breakdown")
        batch_op.drop_column("resume_match_confidence")
        batch_op.drop_column("resume_match_score")

    with op.batch_alter_table("job_postings", schema=None) as batch_op:
        batch_op.drop_column("review_threshold")
        batch_op.drop_column("auto_invite_threshold")
        batch_op.drop_column("screening_mode")
