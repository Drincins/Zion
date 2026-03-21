"""Add inv_item_stock table for aggregated balances.

Revision ID: fb2b3c4d5e6f
Revises: fa1a2b3c4d5e
Create Date: 2026-01-12 00:10:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "fb2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "fa1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inv_item_stock",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("inv_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("restaurant_id", "item_id", name="uq_inv_item_stock_rest_item"),
    )
    op.create_index("ix_inv_item_stock_rest_item", "inv_item_stock", ["restaurant_id", "item_id"])

    op.execute(
        """
        INSERT INTO inv_item_stock (restaurant_id, item_id, quantity, avg_cost, updated_at)
        SELECT
            r.restaurant_id,
            r.item_id,
            SUM(r.quantity) AS quantity,
            CASE
                WHEN SUM(r.quantity) = 0 THEN NULL
                ELSE SUM(r.quantity * COALESCE(r.cost, i.default_cost, i.cost)) / NULLIF(SUM(r.quantity), 0)
            END AS avg_cost,
            NOW()
        FROM inv_item_records r
        JOIN inv_items i ON i.id = r.item_id
        GROUP BY r.restaurant_id, r.item_id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_inv_item_stock_rest_item", table_name="inv_item_stock")
    op.drop_table("inv_item_stock")
