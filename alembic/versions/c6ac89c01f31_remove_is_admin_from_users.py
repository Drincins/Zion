"""remove is_admin column from users

Revision ID: c6ac89c01f31
Revises: b7bf2fa9d4f3
Create Date: 2025-10-07 13:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6ac89c01f31"
down_revision: Union[str, Sequence[str], None] = "b7bf2fa9d4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop legacy is_admin flag from users table."""
    op.drop_column("users", "is_admin")


def downgrade() -> None:
    """Restore is_admin flag on users table."""
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=True, server_default=sa.false()),
    )
    op.execute(sa.text("UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL"))
    op.alter_column("users", "is_admin", server_default=None)
