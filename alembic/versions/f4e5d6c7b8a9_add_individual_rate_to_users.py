"""Add individual rate to users.

Revision ID: f4e5d6c7b8a9
Revises: e3d4f5a6b7c8
Create Date: 2025-12-24 10:10:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4e5d6c7b8a9"
down_revision: Union[str, Sequence[str], None] = "e3d4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("individual_rate", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "individual_rate")
