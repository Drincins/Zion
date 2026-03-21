"""add_custom_group_category_to_iiko_product_settings

Revision ID: 8b6e4d2a9c10
Revises: 7f81c9b8a1d2
Create Date: 2026-02-11
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b6e4d2a9c10"
down_revision: Union[str, Sequence[str], None] = "7f81c9b8a1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "iiko_product_settings",
        sa.Column("custom_product_group_type", sa.String(), nullable=True),
    )
    op.add_column(
        "iiko_product_settings",
        sa.Column("custom_product_category", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("iiko_product_settings", "custom_product_category")
    op.drop_column("iiko_product_settings", "custom_product_group_type")
