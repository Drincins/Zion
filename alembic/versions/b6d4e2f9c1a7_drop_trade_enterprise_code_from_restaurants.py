"""Drop trade_enterprise_code from restaurants.

Revision ID: b6d4e2f9c1a7
Revises: a1c9e4f7b2d0
Create Date: 2026-02-20 18:40:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6d4e2f9c1a7"
down_revision: Union[str, Sequence[str], None] = "a1c9e4f7b2d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_restaurants_trade_enterprise_code")
    if _has_column("restaurants", "trade_enterprise_code"):
        op.drop_column("restaurants", "trade_enterprise_code")


def downgrade() -> None:
    if not _has_column("restaurants", "trade_enterprise_code"):
        op.add_column("restaurants", sa.Column("trade_enterprise_code", sa.String(), nullable=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_restaurants_trade_enterprise_code "
        "ON restaurants (trade_enterprise_code)"
    )
