"""Add row key and hash to iiko olap raw rows.

Revision ID: d8f9a0b1c2d3
Revises: c7f8e9a0b1c2
Create Date: 2025-12-24 12:45:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "c7f8e9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("iiko_olap_rows_raw", sa.Column("row_key", sa.String(), nullable=True))
    op.add_column("iiko_olap_rows_raw", sa.Column("payload_hash", sa.String(), nullable=True))
    op.add_column(
        "iiko_olap_rows_raw",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_iiko_olap_rows_raw_rest_key",
        "iiko_olap_rows_raw",
        ["restaurant_id", "row_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_iiko_olap_rows_raw_rest_key", "iiko_olap_rows_raw", type_="unique")
    op.drop_column("iiko_olap_rows_raw", "updated_at")
    op.drop_column("iiko_olap_rows_raw", "payload_hash")
    op.drop_column("iiko_olap_rows_raw", "row_key")
