"""add_sales_halls_and_zones

Revision ID: d5b8f1a3c2e4
Revises: c4e7b9a1d2f3
Create Date: 2026-02-20
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d5b8f1a3c2e4"
down_revision: Union[str, Sequence[str], None] = "c4e7b9a1d2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iiko_sales_halls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_norm", sa.String(), nullable=False, server_default=""),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "name_norm", name="uq_iiko_sales_halls_company_name"),
    )
    op.create_index("ix_iiko_sales_halls_company_id", "iiko_sales_halls", ["company_id"], unique=False)
    op.create_index("ix_iiko_sales_halls_name_norm", "iiko_sales_halls", ["name_norm"], unique=False)

    op.create_table(
        "iiko_sales_hall_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("hall_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("iiko_sales_halls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_norm", sa.String(), nullable=False, server_default=""),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "company_id",
            "hall_id",
            "restaurant_id",
            "name_norm",
            name="uq_iiko_sales_hall_zone_scope",
        ),
    )
    op.create_index("ix_iiko_sales_hall_zones_company_id", "iiko_sales_hall_zones", ["company_id"], unique=False)
    op.create_index("ix_iiko_sales_hall_zones_hall_id", "iiko_sales_hall_zones", ["hall_id"], unique=False)
    op.create_index("ix_iiko_sales_hall_zones_restaurant_id", "iiko_sales_hall_zones", ["restaurant_id"], unique=False)
    op.create_index("ix_iiko_sales_hall_zones_rest_name", "iiko_sales_hall_zones", ["restaurant_id", "name_norm"], unique=False)

    op.add_column("iiko_sales_hall_tables", sa.Column("hall_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("iiko_sales_hall_tables", sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("iiko_sales_hall_tables", sa.Column("zone_name", sa.String(), nullable=True))
    op.add_column("iiko_sales_hall_tables", sa.Column("zone_name_norm", sa.String(), nullable=False, server_default=""))

    op.create_foreign_key(
        "fk_iiko_sales_hall_tables_hall_id",
        "iiko_sales_hall_tables",
        "iiko_sales_halls",
        ["hall_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_iiko_sales_hall_tables_zone_id",
        "iiko_sales_hall_tables",
        "iiko_sales_hall_zones",
        ["zone_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_iiko_sales_hall_tables_hall_id", "iiko_sales_hall_tables", ["hall_id"], unique=False)
    op.create_index("ix_iiko_sales_hall_tables_zone_id", "iiko_sales_hall_tables", ["zone_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_iiko_sales_hall_tables_zone_id", table_name="iiko_sales_hall_tables")
    op.drop_index("ix_iiko_sales_hall_tables_hall_id", table_name="iiko_sales_hall_tables")
    op.drop_constraint("fk_iiko_sales_hall_tables_zone_id", "iiko_sales_hall_tables", type_="foreignkey")
    op.drop_constraint("fk_iiko_sales_hall_tables_hall_id", "iiko_sales_hall_tables", type_="foreignkey")
    op.drop_column("iiko_sales_hall_tables", "zone_name_norm")
    op.drop_column("iiko_sales_hall_tables", "zone_name")
    op.drop_column("iiko_sales_hall_tables", "zone_id")
    op.drop_column("iiko_sales_hall_tables", "hall_id")

    op.drop_index("ix_iiko_sales_hall_zones_rest_name", table_name="iiko_sales_hall_zones")
    op.drop_index("ix_iiko_sales_hall_zones_restaurant_id", table_name="iiko_sales_hall_zones")
    op.drop_index("ix_iiko_sales_hall_zones_hall_id", table_name="iiko_sales_hall_zones")
    op.drop_index("ix_iiko_sales_hall_zones_company_id", table_name="iiko_sales_hall_zones")
    op.drop_table("iiko_sales_hall_zones")

    op.drop_index("ix_iiko_sales_halls_name_norm", table_name="iiko_sales_halls")
    op.drop_index("ix_iiko_sales_halls_company_id", table_name="iiko_sales_halls")
    op.drop_table("iiko_sales_halls")
