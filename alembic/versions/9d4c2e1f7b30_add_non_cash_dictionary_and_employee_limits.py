"""add_non_cash_dictionary_and_employee_limits

Revision ID: 9d4c2e1f7b30
Revises: 8b6e4d2a9c10
Create Date: 2026-02-11
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9d4c2e1f7b30"
down_revision: Union[str, Sequence[str], None] = "8b6e4d2a9c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iiko_non_cash_payment_types",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "id", name="uq_iiko_non_cash_payment_types_company_id"),
    )
    op.create_index(
        "ix_iiko_non_cash_payment_types_company_id",
        "iiko_non_cash_payment_types",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_non_cash_payment_types_company_name",
        "iiko_non_cash_payment_types",
        ["company_id", "name"],
        unique=False,
    )

    op.create_table(
        "iiko_non_cash_employee_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "non_cash_type_id",
            sa.String(),
            sa.ForeignKey("iiko_non_cash_payment_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_type", sa.String(), server_default="month", nullable=False),
        sa.Column("limit_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "company_id",
            "non_cash_type_id",
            "user_id",
            "period_type",
            name="uq_iiko_non_cash_employee_limits_scope",
        ),
    )
    op.create_index(
        "ix_iiko_non_cash_employee_limits_company_id",
        "iiko_non_cash_employee_limits",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_non_cash_employee_limits_non_cash_type_id",
        "iiko_non_cash_employee_limits",
        ["non_cash_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_non_cash_employee_limits_user_id",
        "iiko_non_cash_employee_limits",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_non_cash_employee_limits_company_user",
        "iiko_non_cash_employee_limits",
        ["company_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_iiko_non_cash_employee_limits_company_user", table_name="iiko_non_cash_employee_limits")
    op.drop_index("ix_iiko_non_cash_employee_limits_user_id", table_name="iiko_non_cash_employee_limits")
    op.drop_index("ix_iiko_non_cash_employee_limits_non_cash_type_id", table_name="iiko_non_cash_employee_limits")
    op.drop_index("ix_iiko_non_cash_employee_limits_company_id", table_name="iiko_non_cash_employee_limits")
    op.drop_table("iiko_non_cash_employee_limits")

    op.drop_index("ix_iiko_non_cash_payment_types_company_name", table_name="iiko_non_cash_payment_types")
    op.drop_index("ix_iiko_non_cash_payment_types_company_id", table_name="iiko_non_cash_payment_types")
    op.drop_table("iiko_non_cash_payment_types")

