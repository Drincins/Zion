"""Add purchase cost to inventory item instances.

Revision ID: a1c9e4f7b2d0
Revises: f4c2a9e7d1b6
Create Date: 2026-02-18 23:55:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1c9e4f7b2d0"
down_revision: Union[str, Sequence[str], None] = "f4c2a9e7d1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inv_item_instances", sa.Column("purchase_cost", sa.Numeric(12, 2), nullable=True))
    op.execute(
        """
        UPDATE inv_item_instances ii
        SET purchase_cost = COALESCE(i.default_cost, i.cost, 0)
        FROM inv_items i
        WHERE i.id = ii.item_id
          AND ii.purchase_cost IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("inv_item_instances", "purchase_cost")
