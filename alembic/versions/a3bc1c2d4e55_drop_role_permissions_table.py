"""Drop role_permissions linking table.

Revision ID: a3bc1c2d4e55
Revises: 8f4a0b8b9a77
Create Date: 2025-10-31 14:40:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a3bc1c2d4e55"
down_revision: Union[str, Sequence[str], None] = "8f4a0b8b9a77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("role_permissions")


def downgrade() -> None:
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )
