"""Add restaurant subdivisions and link positions.

Revision ID: 7e3b8af9d564
Revises: 6fb1c9986191
Create Date: 2025-11-22 15:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e3b8af9d564"
down_revision: Union[str, Sequence[str], None] = "6fb1c9986191"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "restaurant_subdivisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )

    op.add_column(
        "positions",
        sa.Column(
            "restaurant_subdivision_id",
            sa.Integer(),
            sa.ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_positions_restaurant_subdivision_id",
        "positions",
        ["restaurant_subdivision_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_positions_restaurant_subdivision_id", table_name="positions")
    op.drop_column("positions", "restaurant_subdivision_id")
    op.drop_table("restaurant_subdivisions")
