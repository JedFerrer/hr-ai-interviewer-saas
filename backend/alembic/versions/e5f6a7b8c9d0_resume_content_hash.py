"""Add candidates.resume_content_hash for fraud / re-use detection.

SHA-256 hex digest (64 chars) of the raw resume bytes uploaded with each
application. Indexed so the fraud detection pass can do an O(log n)
lookup for prior applicants who submitted the exact same file under a
different email.

Existing rows get NULL — the fraud check skips collision detection when
no hash is present, so back-filling old rows is unnecessary.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("candidates", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("resume_content_hash", sa.String(length=64), nullable=True)
        )
        batch_op.create_index(
            "ix_candidates_resume_content_hash",
            ["resume_content_hash"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("candidates", schema=None) as batch_op:
        batch_op.drop_index("ix_candidates_resume_content_hash")
        batch_op.drop_column("resume_content_hash")
