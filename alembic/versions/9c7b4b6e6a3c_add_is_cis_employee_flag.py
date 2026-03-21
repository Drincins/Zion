"""Add is_cis_employee flag to users.

Revision ID: 9c7b4b6e6a3c
Revises: c4b8d9a1c7fe
Create Date: 2025-12-01 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9c7b4b6e6a3c"
down_revision: Union[str, Sequence[str], None] = "c4b8d9a1c7fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_cis_employee", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("users", "is_cis_employee", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "is_cis_employee")
