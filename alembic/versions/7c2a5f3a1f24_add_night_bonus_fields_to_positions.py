"""Add night bonus settings to positions.

Revision ID: 7c2a5f3a1f24
Revises: 9c7b4b6e6a3c
Create Date: 2025-12-01 00:30:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7c2a5f3a1f24"
down_revision: Union[str, Sequence[str], None] = "9c7b4b6e6a3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "positions",
        sa.Column("night_bonus_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "positions",
        sa.Column("night_bonus_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
    )
    op.alter_column("positions", "night_bonus_enabled", server_default=None)
    op.alter_column("positions", "night_bonus_percent", server_default=None)


def downgrade() -> None:
    op.drop_column("positions", "night_bonus_percent")
    op.drop_column("positions", "night_bonus_enabled")
