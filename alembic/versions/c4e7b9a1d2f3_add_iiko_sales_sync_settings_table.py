"""Add iiko sales sync settings table.

Revision ID: c4e7b9a1d2f3
Revises: b6d4e2f9c1a7
Create Date: 2026-02-20 20:05:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4e7b9a1d2f3"
down_revision: Union[str, Sequence[str], None] = "b6d4e2f9c1a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iiko_sales_sync_settings",
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("auto_sync_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("daily_sync_time", sa.String(length=5), nullable=False, server_default="07:00"),
        sa.Column("daily_lookback_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("weekly_sync_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("weekly_sync_weekday", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weekly_sync_time", sa.String(length=5), nullable=False, server_default="08:00"),
        sa.Column("weekly_lookback_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("manual_default_lookback_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_daily_run_on", sa.Date(), nullable=True),
        sa.Column("last_weekly_run_on", sa.Date(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_manual_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_scope", sa.String(), nullable=True),
        sa.Column("last_sync_status", sa.String(), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("restaurant_id"),
        sa.CheckConstraint("weekly_sync_weekday between 0 and 6", name="ck_iiko_sales_sync_settings_weekday"),
        sa.CheckConstraint("daily_lookback_days >= 0", name="ck_iiko_sales_sync_settings_daily_lookback"),
        sa.CheckConstraint("weekly_lookback_days >= 0", name="ck_iiko_sales_sync_settings_weekly_lookback"),
        sa.CheckConstraint(
            "manual_default_lookback_days >= 0",
            name="ck_iiko_sales_sync_settings_manual_lookback",
        ),
    )
    op.create_index(
        "ix_iiko_sales_sync_settings_auto_enabled",
        "iiko_sales_sync_settings",
        ["auto_sync_enabled"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_iiko_sales_sync_settings_auto_enabled", table_name="iiko_sales_sync_settings")
    op.drop_table("iiko_sales_sync_settings")
