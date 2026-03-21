"""Add per-item switch for individual instance codes.

Revision ID: e2f3a4b5c6d8
Revises: d1f2e3a4b5c6
Create Date: 2026-03-11 22:25:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d8"
down_revision: Union[str, Sequence[str], None] = "d1f2e3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inv_items",
        sa.Column("use_instance_codes", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column(
        "inv_item_instances",
        "instance_code",
        existing_type=sa.String(length=80),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE inv_item_instances AS ii
            SET instance_code = CONCAT(i.code, '-', ii.sequence_no)
            FROM inv_items AS i
            WHERE ii.item_id = i.id
              AND ii.instance_code IS NULL
            """
        )
    )
    op.alter_column(
        "inv_item_instances",
        "instance_code",
        existing_type=sa.String(length=80),
        nullable=False,
    )
    op.drop_column("inv_items", "use_instance_codes")
