"""Revoke pending legacy admin invitations; new invitations grant recruiter.
Existing users are unchanged. Downgrade does not resurrect revoked tokens.
"""

import sqlalchemy as sa
from alembic import op

revision = "g7a8b9c0d1e2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "UPDATE user_invites SET revoked_at = CURRENT_TIMESTAMP WHERE accepted_at IS NULL AND revoked_at IS NULL"
        )
    )
    with op.batch_alter_table("user_invites") as batch:
        batch.alter_column(
            "role",
            existing_type=sa.String(50),
            server_default="recruiter",
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("user_invites") as batch:
        batch.alter_column(
            "role",
            existing_type=sa.String(50),
            server_default="admin",
            existing_nullable=False,
        )
