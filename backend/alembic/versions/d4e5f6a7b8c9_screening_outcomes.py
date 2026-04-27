"""Add screening_outcomes audit log table.

Append-only audit log of every screening prediction. One row per prediction;
ground-truth columns (`hr_decision`, `interview_outcome`, `hire_outcome`)
are populated as HR moves the candidate through the funnel.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "screening_outcomes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("candidates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_posting_id",
            sa.String(length=36),
            sa.ForeignKey("job_postings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Prediction (immutable)
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("deterministic_recall", sa.Numeric(3, 2), nullable=True),
        sa.Column("matched_skills", sa.JSON(), nullable=True),
        sa.Column("missing_skills", sa.JSON(), nullable=True),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        # Ground truth (populated over time)
        sa.Column("hr_decision", sa.String(length=32), nullable=True),
        sa.Column("hr_decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interview_outcome", sa.String(length=32), nullable=True),
        sa.Column("interview_outcome_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hire_outcome", sa.String(length=32), nullable=True),
        sa.Column("hire_outcome_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hr_note", sa.String(length=2000), nullable=True),
        # Bookkeeping
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_screening_outcomes_candidate_id",
        "screening_outcomes",
        ["candidate_id"],
    )
    op.create_index(
        "ix_screening_outcomes_job_posting_id",
        "screening_outcomes",
        ["job_posting_id"],
    )
    op.create_index(
        "ix_screening_outcomes_decision",
        "screening_outcomes",
        ["decision"],
    )
    op.create_index(
        "ix_screening_outcomes_predicted_at",
        "screening_outcomes",
        ["predicted_at"],
    )
    op.create_index(
        "ix_screening_outcomes_hr_decision",
        "screening_outcomes",
        ["hr_decision"],
    )
    op.create_index(
        "ix_screening_outcomes_candidate_job",
        "screening_outcomes",
        ["candidate_id", "job_posting_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_screening_outcomes_candidate_job", table_name="screening_outcomes"
    )
    op.drop_index(
        "ix_screening_outcomes_hr_decision", table_name="screening_outcomes"
    )
    op.drop_index(
        "ix_screening_outcomes_predicted_at", table_name="screening_outcomes"
    )
    op.drop_index(
        "ix_screening_outcomes_decision", table_name="screening_outcomes"
    )
    op.drop_index(
        "ix_screening_outcomes_job_posting_id", table_name="screening_outcomes"
    )
    op.drop_index(
        "ix_screening_outcomes_candidate_id", table_name="screening_outcomes"
    )
    op.drop_table("screening_outcomes")
