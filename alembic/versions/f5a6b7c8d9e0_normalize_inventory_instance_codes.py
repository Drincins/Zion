"""Normalize inventory instance codes without restaurant suffixes.

Revision ID: f5a6b7c8d9e0
Revises: f4a5b6c7d8e9
Create Date: 2026-03-18 14:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE inv_item_instances AS inst
            SET instance_code = NULL
            FROM inv_items AS item
            WHERE inst.item_id = item.id
              AND COALESCE(item.use_instance_codes, false) = false
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE inv_item_instances AS inst
            SET instance_code = CASE
                WHEN inst.location_kind = 'restaurant' AND inst.restaurant_id IS NOT NULL
                    THEN item.code || '-' || inst.restaurant_id || '-' || inst.sequence_no
                ELSE NULL
            END
            FROM inv_items AS item
            WHERE inst.item_id = item.id
              AND COALESCE(item.use_instance_codes, false) = false
            """
        )
    )
