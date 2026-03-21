"""add_waiter_turnover_settings

Revision ID: d4f8a1c2b7e9
Revises: c8f1d2a4e6b7
Create Date: 2026-02-13
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d4f8a1c2b7e9"
down_revision: Union[str, Sequence[str], None] = "c8f1d2a4e6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iiko_waiter_turnover_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("real_money_only", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("amount_mode", sa.String(), server_default="sum_without_discount", nullable=False),
        sa.Column("deleted_mode", sa.String(), server_default="without_deleted", nullable=False),
        sa.Column("position_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("include_groups", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exclude_groups", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("include_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exclude_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("include_positions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exclude_positions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "include_payment_method_guids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", name="uq_iiko_waiter_turnover_settings_company"),
    )
    op.create_index(
        "ix_iiko_waiter_turnover_settings_company_id",
        "iiko_waiter_turnover_settings",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_waiter_turnover_settings_company_updated",
        "iiko_waiter_turnover_settings",
        ["company_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_iiko_waiter_turnover_settings_company_updated", table_name="iiko_waiter_turnover_settings")
    op.drop_index("ix_iiko_waiter_turnover_settings_company_id", table_name="iiko_waiter_turnover_settings")
    op.drop_table("iiko_waiter_turnover_settings")

