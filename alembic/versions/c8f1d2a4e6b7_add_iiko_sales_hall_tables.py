"""add_iiko_sales_hall_tables

Revision ID: c8f1d2a4e6b7
Revises: b5a1f2c9d4e7
Create Date: 2026-02-12
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c8f1d2a4e6b7"
down_revision: Union[str, Sequence[str], None] = "b5a1f2c9d4e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iiko_sales_hall_tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "source_restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("table_num", sa.String(), nullable=True),
        sa.Column("department_norm", sa.String(), nullable=False, server_default=""),
        sa.Column("table_num_norm", sa.String(), nullable=False, server_default=""),
        sa.Column("hall_name", sa.String(), nullable=False),
        sa.Column("hall_name_norm", sa.String(), nullable=False, server_default=""),
        sa.Column("table_name", sa.String(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "company_id",
            "restaurant_id",
            "source_restaurant_id",
            "department_norm",
            "table_num_norm",
            name="uq_iiko_sales_hall_table_scope",
        ),
    )
    op.create_index(
        "ix_iiko_sales_hall_tables_company_id",
        "iiko_sales_hall_tables",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_sales_hall_tables_restaurant_id",
        "iiko_sales_hall_tables",
        ["restaurant_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_sales_hall_tables_source_restaurant_id",
        "iiko_sales_hall_tables",
        ["source_restaurant_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_sales_hall_table_rest_hall",
        "iiko_sales_hall_tables",
        ["restaurant_id", "hall_name_norm"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_sales_hall_table_source_department",
        "iiko_sales_hall_tables",
        ["source_restaurant_id", "department_norm"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_iiko_sales_hall_table_source_department", table_name="iiko_sales_hall_tables")
    op.drop_index("ix_iiko_sales_hall_table_rest_hall", table_name="iiko_sales_hall_tables")
    op.drop_index("ix_iiko_sales_hall_tables_source_restaurant_id", table_name="iiko_sales_hall_tables")
    op.drop_index("ix_iiko_sales_hall_tables_restaurant_id", table_name="iiko_sales_hall_tables")
    op.drop_index("ix_iiko_sales_hall_tables_company_id", table_name="iiko_sales_hall_tables")
    op.drop_table("iiko_sales_hall_tables")
