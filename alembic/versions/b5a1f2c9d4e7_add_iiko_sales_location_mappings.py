"""add_iiko_sales_location_mappings

Revision ID: b5a1f2c9d4e7
Revises: 9d4c2e1f7b30
Create Date: 2026-02-12
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b5a1f2c9d4e7"
down_revision: Union[str, Sequence[str], None] = "9d4c2e1f7b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "iiko_sale_orders",
        sa.Column(
            "source_restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_iiko_sale_orders_source_restaurant_id",
        "iiko_sale_orders",
        ["source_restaurant_id"],
        unique=False,
    )

    op.add_column(
        "iiko_sale_items",
        sa.Column(
            "source_restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_iiko_sale_items_source_restaurant_id",
        "iiko_sale_items",
        ["source_restaurant_id"],
        unique=False,
    )

    op.create_table(
        "iiko_sales_location_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "source_restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "target_restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("table_num", sa.String(), nullable=True),
        sa.Column("department_norm", sa.String(), nullable=False, server_default=""),
        sa.Column("table_num_norm", sa.String(), nullable=False, server_default=""),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "company_id",
            "source_restaurant_id",
            "department_norm",
            "table_num_norm",
            name="uq_iiko_sales_location_mapping_scope",
        ),
    )
    op.create_index(
        "ix_iiko_sales_location_mappings_company_id",
        "iiko_sales_location_mappings",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_sales_location_mappings_source_restaurant_id",
        "iiko_sales_location_mappings",
        ["source_restaurant_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_sales_location_mappings_target_restaurant_id",
        "iiko_sales_location_mappings",
        ["target_restaurant_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_sales_location_mapping_source_department",
        "iiko_sales_location_mappings",
        ["source_restaurant_id", "department_norm"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_sales_location_mapping_target_department",
        "iiko_sales_location_mappings",
        ["target_restaurant_id", "department_norm"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_iiko_sales_location_mapping_target_department", table_name="iiko_sales_location_mappings")
    op.drop_index("ix_iiko_sales_location_mapping_source_department", table_name="iiko_sales_location_mappings")
    op.drop_index("ix_iiko_sales_location_mappings_target_restaurant_id", table_name="iiko_sales_location_mappings")
    op.drop_index("ix_iiko_sales_location_mappings_source_restaurant_id", table_name="iiko_sales_location_mappings")
    op.drop_index("ix_iiko_sales_location_mappings_company_id", table_name="iiko_sales_location_mappings")
    op.drop_table("iiko_sales_location_mappings")

    op.drop_index("ix_iiko_sale_items_source_restaurant_id", table_name="iiko_sale_items")
    op.drop_column("iiko_sale_items", "source_restaurant_id")

    op.drop_index("ix_iiko_sale_orders_source_restaurant_id", table_name="iiko_sale_orders")
    op.drop_column("iiko_sale_orders", "source_restaurant_id")
