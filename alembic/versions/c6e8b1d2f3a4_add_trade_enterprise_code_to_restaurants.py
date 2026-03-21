"""Add trade_enterprise_code to restaurants.

Revision ID: c6e8b1d2f3a4
Revises: ab29c7e1f4d8
Create Date: 2026-02-13 22:35:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c6e8b1d2f3a4"
down_revision: Union[str, Sequence[str], None] = "ab29c7e1f4d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("restaurants", sa.Column("trade_enterprise_code", sa.String(), nullable=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_restaurants_trade_enterprise_code "
        "ON restaurants (trade_enterprise_code)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_restaurants_trade_enterprise_code")
    op.drop_column("restaurants", "trade_enterprise_code")

