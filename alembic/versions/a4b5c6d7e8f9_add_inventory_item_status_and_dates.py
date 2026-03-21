"""Add inventory item status and creation/arrival dates.

Revision ID: a4b5c6d7e8f9
Revises: e2f3a4b5c6d8
Create Date: 2026-03-11 23:45:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inv_items",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "inv_items",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        "inv_item_instances",
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Backfill historical items using the earliest known inventory traces.
    op.execute(
        sa.text(
            """
            UPDATE inv_items AS i
            SET created_at = COALESCE(
                (
                    SELECT MIN(ii.created_at)
                    FROM inv_item_instances AS ii
                    WHERE ii.item_id = i.id
                ),
                (
                    SELECT MIN(ir.created_at)
                    FROM inv_item_records AS ir
                    WHERE ir.item_id = i.id
                ),
                NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE inv_item_instances
            SET arrived_at = created_at
            WHERE arrived_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("inv_item_instances", "arrived_at")
    op.drop_column("inv_items", "created_at")
    op.drop_column("inv_items", "is_active")
