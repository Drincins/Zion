"""Add fingerprint history table and user flag.

Revision ID: a8c9d0e1f2a3
Revises: f7a8b9c0d1e2
Create Date: 2025-01-20 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("has_fingerprint", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "fingerprint_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("staff_code", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("slot", sa.Integer(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_fingerprint_events_user_id", "fingerprint_events", ["user_id"], unique=False)
    op.create_index("ix_fingerprint_events_staff_code", "fingerprint_events", ["staff_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fingerprint_events_staff_code", table_name="fingerprint_events")
    op.drop_index("ix_fingerprint_events_user_id", table_name="fingerprint_events")
    op.drop_table("fingerprint_events")
    op.drop_column("users", "has_fingerprint")
