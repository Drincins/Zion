"""Add iiko olap raw rows table.

Revision ID: c7f8e9a0b1c2
Revises: f4e5d6c7b8a9
Create Date: 2025-12-24 12:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c7f8e9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "f4e5d6c7b8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iiko_olap_rows_raw",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("open_date", sa.Date(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_iiko_olap_rows_raw_rest_date",
        "iiko_olap_rows_raw",
        ["restaurant_id", "open_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_iiko_olap_rows_raw_rest_date", table_name="iiko_olap_rows_raw")
    op.drop_table("iiko_olap_rows_raw")
