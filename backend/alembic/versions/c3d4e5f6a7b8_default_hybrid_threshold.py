"""Default new jobs to hybrid_threshold screening mode.

Flips `job_postings.screening_mode`'s server default from "auto_all" to
"hybrid_threshold" so newly-created jobs use the resume scoring gate by
default. Existing rows that still hold the old default are also migrated
to the new value; rows that have been explicitly set to another mode
(e.g. "manual_all") are left untouched.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate any rows still holding the old default. We deliberately do
    # NOT touch rows already on "hybrid_threshold" or "manual_all" — those
    # are explicit choices.
    op.execute(
        "UPDATE job_postings SET screening_mode = 'hybrid_threshold' "
        "WHERE screening_mode = 'auto_all'"
    )

    # Flip the server default. Under SQLite this requires a batch op
    # because ALTER COLUMN ... SET DEFAULT isn't supported.
    with op.batch_alter_table("job_postings", schema=None) as batch_op:
        batch_op.alter_column(
            "screening_mode",
            existing_type=sa.String(length=32),
            existing_nullable=False,
            server_default="hybrid_threshold",
        )


def downgrade() -> None:
    with op.batch_alter_table("job_postings", schema=None) as batch_op:
        batch_op.alter_column(
            "screening_mode",
            existing_type=sa.String(length=32),
            existing_nullable=False,
            server_default="auto_all",
        )
    # We don't revert row values: the upgrade is informational about new
    # rows, and reverting would clobber HR's explicit choices.
