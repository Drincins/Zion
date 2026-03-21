"""add is_formalized to users

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a9bc_add_closing_received_edo
Create Date: 2026-01-16 12:20:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5e6f7a8b9c0d"
down_revision = "4d5e6f7a9bc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("is_formalized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade():
    op.drop_column("users", "is_formalized")

