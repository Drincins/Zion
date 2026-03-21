"""add_iiko_catalog_and_sales_tables

Revision ID: 469769308d46
Revises: 89ac788cc639
Create Date: 2026-02-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "469769308d46"
down_revision: Union[str, Sequence[str], None] = "89ac788cc639"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iiko_products",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "source_restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("parent_id", sa.String(), nullable=True),
        sa.Column("num", sa.String(), nullable=True, unique=True),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("product_type", sa.String(), nullable=True),
        sa.Column("product_group_type", sa.String(), nullable=True),
        sa.Column("cooking_place_type", sa.String(), nullable=True),
        sa.Column("main_unit", sa.String(), nullable=True),
        sa.Column("product_category", sa.String(), nullable=True),
        sa.Column("containers", sa.Text(), nullable=True),
        sa.Column("barcodes", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_xml", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_iiko_products_company_id", "iiko_products", ["company_id"], unique=False)
    op.create_index("ix_iiko_products_source_restaurant_id", "iiko_products", ["source_restaurant_id"], unique=False)
    op.create_index("ix_iiko_products_num", "iiko_products", ["num"], unique=False)
    op.create_index("ix_iiko_products_code", "iiko_products", ["code"], unique=False)
    op.create_index("ix_iiko_products_company_num", "iiko_products", ["company_id", "num"], unique=False)
    op.create_index("ix_iiko_products_company_code", "iiko_products", ["company_id", "code"], unique=False)

    op.create_table(
        "iiko_product_restaurants",
        sa.Column(
            "product_id",
            sa.String(),
            sa.ForeignKey("iiko_products.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_iiko_product_restaurants_restaurant_id",
        "iiko_product_restaurants",
        ["restaurant_id"],
        unique=False,
    )

    op.create_table(
        "iiko_product_settings",
        sa.Column(
            "product_id",
            sa.String(),
            sa.ForeignKey("iiko_products.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("portion_coef_kitchen", sa.Numeric(10, 4), nullable=True),
        sa.Column("portion_coef_hall", sa.Numeric(10, 4), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "iiko_product_name_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            sa.String(),
            sa.ForeignKey("iiko_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("old_name", sa.String(), nullable=True),
        sa.Column("new_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_iiko_product_name_history_product_id", "iiko_product_name_history", ["product_id"], unique=False)
    op.create_index(
        "ix_iiko_product_name_history_restaurant_id",
        "iiko_product_name_history",
        ["restaurant_id"],
        unique=False,
    )
    op.create_index(
        "ix_iiko_product_name_history_product_created",
        "iiko_product_name_history",
        ["product_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "iiko_payment_methods",
        sa.Column("guid", sa.String(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "guid", name="uq_iiko_payment_methods_company_guid"),
    )
    op.create_index("ix_iiko_payment_methods_company_id", "iiko_payment_methods", ["company_id"], unique=False)
    op.create_index(
        "ix_iiko_payment_methods_company_name",
        "iiko_payment_methods",
        ["company_id", "name"],
        unique=False,
    )

    op.create_table(
        "iiko_sale_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "restaurant_id",
            sa.Integer(),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("iiko_order_id", sa.String(), nullable=False),
        sa.Column("order_num", sa.String(), nullable=True),
        sa.Column("open_date", sa.Date(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("table_num", sa.String(), nullable=True),
        sa.Column("guest_num", sa.Integer(), nullable=True),
        sa.Column("order_waiter_iiko_id", sa.String(), nullable=True),
        sa.Column("order_waiter_name", sa.String(), nullable=True),
        sa.Column("cashier_iiko_id", sa.String(), nullable=True),
        sa.Column("cashier_code", sa.String(), nullable=True),
        sa.Column("auth_user_iiko_id", sa.String(), nullable=True),
        sa.Column("order_waiter_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cashier_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("auth_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("restaurant_id", "iiko_order_id", name="uq_iiko_sale_orders_rest_order"),
    )
    op.create_index("ix_iiko_sale_orders_company_id", "iiko_sale_orders", ["company_id"], unique=False)
    op.create_index("ix_iiko_sale_orders_restaurant_id", "iiko_sale_orders", ["restaurant_id"], unique=False)
    op.create_index("ix_iiko_sale_orders_iiko_order_id", "iiko_sale_orders", ["iiko_order_id"], unique=False)
    op.create_index("ix_iiko_sale_orders_order_num", "iiko_sale_orders", ["order_num"], unique=False)
    op.create_index("ix_iiko_sale_orders_open_date", "iiko_sale_orders", ["open_date"], unique=False)
    op.create_index("ix_iiko_sale_orders_order_waiter_iiko_id", "iiko_sale_orders", ["order_waiter_iiko_id"], unique=False)
    op.create_index("ix_iiko_sale_orders_cashier_iiko_id", "iiko_sale_orders", ["cashier_iiko_id"], unique=False)
    op.create_index("ix_iiko_sale_orders_cashier_code", "iiko_sale_orders", ["cashier_code"], unique=False)
    op.create_index("ix_iiko_sale_orders_auth_user_iiko_id", "iiko_sale_orders", ["auth_user_iiko_id"], unique=False)
    op.create_index("ix_iiko_sale_orders_order_waiter_user_id", "iiko_sale_orders", ["order_waiter_user_id"], unique=False)
    op.create_index("ix_iiko_sale_orders_cashier_user_id", "iiko_sale_orders", ["cashier_user_id"], unique=False)
    op.create_index("ix_iiko_sale_orders_auth_user_id", "iiko_sale_orders", ["auth_user_id"], unique=False)
    op.create_index("ix_iiko_sale_orders_rest_open_date", "iiko_sale_orders", ["restaurant_id", "open_date"], unique=False)

    op.create_table(
        "iiko_sale_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("iiko_sale_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("open_date", sa.Date(), nullable=True),
        sa.Column("line_key", sa.String(), nullable=False),
        sa.Column("dish_code", sa.String(), nullable=True),
        sa.Column("dish_name", sa.String(), nullable=True),
        sa.Column("dish_group", sa.String(), nullable=True),
        sa.Column("dish_category_id", sa.String(), nullable=True),
        sa.Column("dish_measure_unit", sa.String(), nullable=True),
        sa.Column("cooking_place", sa.String(), nullable=True),
        sa.Column("qty", sa.Numeric(14, 3), nullable=True),
        sa.Column("sum", sa.Numeric(14, 2), nullable=True),
        sa.Column("discount_sum", sa.Numeric(14, 2), nullable=True),
        sa.Column("iiko_product_id", sa.String(), sa.ForeignKey("iiko_products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("auth_user_iiko_id", sa.String(), nullable=True),
        sa.Column("auth_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_waiter_iiko_id", sa.String(), nullable=True),
        sa.Column("cashier_code", sa.String(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("order_id", "line_key", name="uq_iiko_sale_items_order_line"),
    )
    op.create_index("ix_iiko_sale_items_order_id", "iiko_sale_items", ["order_id"], unique=False)
    op.create_index("ix_iiko_sale_items_company_id", "iiko_sale_items", ["company_id"], unique=False)
    op.create_index("ix_iiko_sale_items_restaurant_id", "iiko_sale_items", ["restaurant_id"], unique=False)
    op.create_index("ix_iiko_sale_items_open_date", "iiko_sale_items", ["open_date"], unique=False)
    op.create_index("ix_iiko_sale_items_dish_code", "iiko_sale_items", ["dish_code"], unique=False)
    op.create_index("ix_iiko_sale_items_iiko_product_id", "iiko_sale_items", ["iiko_product_id"], unique=False)
    op.create_index("ix_iiko_sale_items_auth_user_iiko_id", "iiko_sale_items", ["auth_user_iiko_id"], unique=False)
    op.create_index("ix_iiko_sale_items_auth_user_id", "iiko_sale_items", ["auth_user_id"], unique=False)
    op.create_index("ix_iiko_sale_items_order_waiter_iiko_id", "iiko_sale_items", ["order_waiter_iiko_id"], unique=False)
    op.create_index("ix_iiko_sale_items_cashier_code", "iiko_sale_items", ["cashier_code"], unique=False)
    op.create_index("ix_iiko_sale_items_rest_open_date", "iiko_sale_items", ["restaurant_id", "open_date"], unique=False)
    op.create_index("ix_iiko_sale_items_rest_dish_code", "iiko_sale_items", ["restaurant_id", "dish_code"], unique=False)

    # Backfill canonical products from the legacy per-restaurant table, if present.
    op.execute(
        sa.text(
            """
            INSERT INTO iiko_products (
                id,
                company_id,
                source_restaurant_id,
                parent_id,
                num,
                code,
                name,
                product_type,
                product_group_type,
                cooking_place_type,
                main_unit,
                product_category,
                containers,
                barcodes,
                raw_payload,
                raw_xml,
                created_at,
                updated_at,
                last_seen_at
            )
            SELECT
                p.id,
                r.company_id,
                p.restaurant_id,
                p.parent_id,
                p.num,
                p.code,
                p.name,
                p.product_type,
                p.product_group_type,
                p.cooking_place_type,
                p.main_unit,
                p.product_category,
                p.containers,
                p.barcodes,
                p.raw_payload,
                p.raw_xml,
                COALESCE(p.created_at, now()),
                now(),
                COALESCE(p.created_at, now())
            FROM iiko_product_rows p
            LEFT JOIN restaurants r ON r.id = p.restaurant_id
            ON CONFLICT (id) DO UPDATE SET
                company_id = EXCLUDED.company_id,
                source_restaurant_id = EXCLUDED.source_restaurant_id,
                parent_id = EXCLUDED.parent_id,
                num = EXCLUDED.num,
                code = EXCLUDED.code,
                name = EXCLUDED.name,
                product_type = EXCLUDED.product_type,
                product_group_type = EXCLUDED.product_group_type,
                cooking_place_type = EXCLUDED.cooking_place_type,
                main_unit = EXCLUDED.main_unit,
                product_category = EXCLUDED.product_category,
                containers = EXCLUDED.containers,
                barcodes = EXCLUDED.barcodes,
                raw_payload = EXCLUDED.raw_payload,
                raw_xml = EXCLUDED.raw_xml,
                updated_at = now(),
                last_seen_at = now()
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO iiko_product_restaurants (product_id, restaurant_id, last_seen_at)
            SELECT p.id, p.restaurant_id, now()
            FROM iiko_product_rows p
            WHERE p.restaurant_id IS NOT NULL
            ON CONFLICT (product_id, restaurant_id) DO UPDATE SET
                last_seen_at = EXCLUDED.last_seen_at
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_iiko_sale_items_rest_dish_code", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_rest_open_date", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_cashier_code", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_order_waiter_iiko_id", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_auth_user_id", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_auth_user_iiko_id", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_iiko_product_id", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_dish_code", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_open_date", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_restaurant_id", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_company_id", table_name="iiko_sale_items")
    op.drop_index("ix_iiko_sale_items_order_id", table_name="iiko_sale_items")
    op.drop_table("iiko_sale_items")

    op.drop_index("ix_iiko_sale_orders_rest_open_date", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_auth_user_id", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_cashier_user_id", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_order_waiter_user_id", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_auth_user_iiko_id", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_cashier_code", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_cashier_iiko_id", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_order_waiter_iiko_id", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_open_date", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_order_num", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_iiko_order_id", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_restaurant_id", table_name="iiko_sale_orders")
    op.drop_index("ix_iiko_sale_orders_company_id", table_name="iiko_sale_orders")
    op.drop_table("iiko_sale_orders")

    op.drop_index("ix_iiko_payment_methods_company_name", table_name="iiko_payment_methods")
    op.drop_index("ix_iiko_payment_methods_company_id", table_name="iiko_payment_methods")
    op.drop_table("iiko_payment_methods")

    op.drop_index("ix_iiko_product_name_history_product_created", table_name="iiko_product_name_history")
    op.drop_index("ix_iiko_product_name_history_restaurant_id", table_name="iiko_product_name_history")
    op.drop_index("ix_iiko_product_name_history_product_id", table_name="iiko_product_name_history")
    op.drop_table("iiko_product_name_history")

    op.drop_table("iiko_product_settings")

    op.drop_index("ix_iiko_product_restaurants_restaurant_id", table_name="iiko_product_restaurants")
    op.drop_table("iiko_product_restaurants")

    op.drop_index("ix_iiko_products_company_code", table_name="iiko_products")
    op.drop_index("ix_iiko_products_company_num", table_name="iiko_products")
    op.drop_index("ix_iiko_products_code", table_name="iiko_products")
    op.drop_index("ix_iiko_products_num", table_name="iiko_products")
    op.drop_index("ix_iiko_products_source_restaurant_id", table_name="iiko_products")
    op.drop_index("ix_iiko_products_company_id", table_name="iiko_products")
    op.drop_table("iiko_products")

