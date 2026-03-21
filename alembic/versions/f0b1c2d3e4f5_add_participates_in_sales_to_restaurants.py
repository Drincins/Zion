"""add_participates_in_sales_to_restaurants

Revision ID: f0b1c2d3e4f5
Revises: e6b7c8d9a0f1
Create Date: 2026-02-22 02:20:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "e6b7c8d9a0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "restaurants",
        sa.Column(
            "participates_in_sales",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("restaurants", "participates_in_sales")

