"""Add additional info fields to inventory items.

Revision ID: 1a2b3c4d5e6f
Revises: 0f1e2d3c4b5a, b7f8c9d0e1f2
Create Date: 2026-03-10 19:30:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = ("0f1e2d3c4b5a", "b7f8c9d0e1f2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inv_items", sa.Column("manufacturer", sa.String(length=255), nullable=True))
    op.add_column("inv_items", sa.Column("storage_conditions", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("inv_items", "storage_conditions")
    op.drop_column("inv_items", "manufacturer")
