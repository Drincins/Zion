"""Add item code and default_cost; backfill existing.

Revision ID: fa1a2b3c4d5e
Revises: f9a0b1c2d3e4
Create Date: 2026-01-12 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "fa1a2b3c4d5e"
down_revision: Union[str, Sequence[str], None] = "f9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inv_items", sa.Column("code", sa.String(length=64), nullable=True))
    op.add_column("inv_items", sa.Column("default_cost", sa.Numeric(12, 2), nullable=True))

    # Backfill code and default_cost from existing data
    op.execute(
        """
        UPDATE inv_items
        SET code = COALESCE(code, 'ITEM-' || LPAD(id::text, 6, '0')),
            default_cost = COALESCE(default_cost, cost)
        """
    )

    # Enforce uniqueness and non-null code
    op.alter_column("inv_items", "code", nullable=False)
    op.create_unique_constraint("uq_inv_items_code", "inv_items", ["code"])
    op.create_index("ix_inv_items_code", "inv_items", ["code"])


def downgrade() -> None:
    op.drop_index("ix_inv_items_code", table_name="inv_items")
    op.drop_constraint("uq_inv_items_code", "inv_items", type_="unique")
    op.drop_column("inv_items", "default_cost")
    op.drop_column("inv_items", "code")
