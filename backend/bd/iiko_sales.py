from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.bd.database import Base

__all__ = [
    "IikoSaleOrder",
    "IikoSaleItem",
    "IikoSalesLocationMapping",
    "IikoSalesHall",
    "IikoSalesHallZone",
    "IikoSalesHallTable",
    "IikoSalesSyncSetting",
]


class IikoSaleOrder(Base):
    """
    Order-level sales facts from iiko OLAP.

    iiko order identifier: `iiko_order_id` = `UniqOrderId.Id` (GUID string).
    """

    __tablename__ = "iiko_sale_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    source_restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    iiko_order_id = Column(String, nullable=False, index=True)
    order_num = Column(String, nullable=True, index=True)

    open_date = Column(Date, nullable=True, index=True)
    opened_at = Column(DateTime(timezone=False), nullable=True)
    closed_at = Column(DateTime(timezone=False), nullable=True)

    department = Column(String, nullable=True)
    table_num = Column(String, nullable=True)
    guest_num = Column(Integer, nullable=True)

    order_waiter_iiko_id = Column(String, nullable=True, index=True)
    order_waiter_name = Column(String, nullable=True)
    cashier_iiko_id = Column(String, nullable=True, index=True)
    cashier_code = Column(String, nullable=True, index=True)
    auth_user_iiko_id = Column(String, nullable=True, index=True)

    order_waiter_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    cashier_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    auth_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    raw_payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    items = relationship("IikoSaleItem", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("restaurant_id", "iiko_order_id", name="uq_iiko_sale_orders_rest_order"),
        Index("ix_iiko_sale_orders_rest_open_date", "restaurant_id", "open_date"),
    )


class IikoSaleItem(Base):
    """
    Item-level sales facts (aggregated per OLAP group definition).

    We keep string fields as snapshots for history; on resync we update numeric amounts but preserve snapshots.
    """

    __tablename__ = "iiko_sale_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    order_id = Column(UUID(as_uuid=True), ForeignKey("iiko_sale_orders.id", ondelete="CASCADE"), nullable=False, index=True)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    source_restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    open_date = Column(Date, nullable=True, index=True)

    # Stable item key inside an order for UPSERT (hash of OLAP grouping fields we use).
    line_key = Column(String, nullable=False)

    # iiko dish code used in OLAP (matches product.num from /products).
    dish_code = Column(String, nullable=True, index=True)

    dish_name = Column(String, nullable=True)
    dish_group = Column(String, nullable=True)
    dish_category_id = Column(String, nullable=True)
    dish_measure_unit = Column(String, nullable=True)
    cooking_place = Column(String, nullable=True)

    qty = Column(Numeric(14, 3), nullable=True)
    sum = Column(Numeric(14, 2), nullable=True)
    discount_sum = Column(Numeric(14, 2), nullable=True)

    iiko_product_id = Column(String, ForeignKey("iiko_products.id", ondelete="SET NULL"), nullable=True, index=True)

    # Who "sold" the item (used for hookah masters etc.).
    auth_user_iiko_id = Column(String, nullable=True, index=True)
    auth_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Convenience snapshots for analytics without joins.
    order_waiter_iiko_id = Column(String, nullable=True, index=True)
    cashier_code = Column(String, nullable=True, index=True)

    raw_payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order = relationship("IikoSaleOrder", back_populates="items")

    __table_args__ = (
        UniqueConstraint("order_id", "line_key", name="uq_iiko_sale_items_order_line"),
        Index("ix_iiko_sale_items_rest_open_date", "restaurant_id", "open_date"),
        Index("ix_iiko_sale_items_rest_dish_code", "restaurant_id", "dish_code"),
    )


class IikoSalesLocationMapping(Base):
    """
    Mapping between iiko sales location and target restaurant in this system.

    Supports both source-bound and global mappings:
    - source_restaurant_id + department (+ optional table_num)
    - global (source_restaurant_id is NULL) + department (+ optional table_num)
    """

    __tablename__ = "iiko_sales_location_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    source_restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    department = Column(String, nullable=True)
    table_num = Column(String, nullable=True)
    department_norm = Column(String, nullable=False, server_default="")
    table_num_norm = Column(String, nullable=False, server_default="")

    comment = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "source_restaurant_id",
            "department_norm",
            "table_num_norm",
            name="uq_iiko_sales_location_mapping_scope",
        ),
        Index(
            "ix_iiko_sales_location_mapping_source_department",
            "source_restaurant_id",
            "department_norm",
        ),
        Index(
            "ix_iiko_sales_location_mapping_target_department",
            "target_restaurant_id",
            "department_norm",
        ),
    )


class IikoSalesHall(Base):
    """
    Universal sales hall dictionary (shared across restaurants within company scope).
    """

    __tablename__ = "iiko_sales_halls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String, nullable=False)
    name_norm = Column(String, nullable=False, server_default="")
    comment = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", "name_norm", name="uq_iiko_sales_halls_company_name"),
        Index("ix_iiko_sales_halls_name_norm", "name_norm"),
    )


class IikoSalesHallZone(Base):
    """
    Hall zones are configured per restaurant.
    """

    __tablename__ = "iiko_sales_hall_zones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    hall_id = Column(UUID(as_uuid=True), ForeignKey("iiko_sales_halls.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    name_norm = Column(String, nullable=False, server_default="")
    comment = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "hall_id",
            "restaurant_id",
            "name_norm",
            name="uq_iiko_sales_hall_zone_scope",
        ),
        Index("ix_iiko_sales_hall_zones_rest_name", "restaurant_id", "name_norm"),
    )


class IikoSalesHallTable(Base):
    """
    Hall/table dictionary for sales analytics.

    Maps iiko location (department/table) to a user-defined hall name and table settings
    (display name, capacity) inside a target restaurant.
    """

    __tablename__ = "iiko_sales_hall_tables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    hall_id = Column(UUID(as_uuid=True), ForeignKey("iiko_sales_halls.id", ondelete="SET NULL"), nullable=True, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("iiko_sales_hall_zones.id", ondelete="SET NULL"), nullable=True, index=True)
    source_restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    department = Column(String, nullable=True)
    table_num = Column(String, nullable=True)
    department_norm = Column(String, nullable=False, server_default="")
    table_num_norm = Column(String, nullable=False, server_default="")

    hall_name = Column(String, nullable=False)
    hall_name_norm = Column(String, nullable=False, server_default="")
    zone_name = Column(String, nullable=True)
    zone_name_norm = Column(String, nullable=False, server_default="")
    table_name = Column(String, nullable=True)
    capacity = Column(Integer, nullable=True)

    comment = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "restaurant_id",
            "source_restaurant_id",
            "department_norm",
            "table_num_norm",
            name="uq_iiko_sales_hall_table_scope",
        ),
        Index(
            "ix_iiko_sales_hall_table_rest_hall",
            "restaurant_id",
            "hall_name_norm",
        ),
        Index(
            "ix_iiko_sales_hall_table_source_department",
            "source_restaurant_id",
            "department_norm",
        ),
    )


class IikoSalesSyncSetting(Base):
    """
    Per-restaurant schedule settings for automatic iiko sales sync.

    The loop runs daily and can optionally run a wider weekly backfill.
    """

    __tablename__ = "iiko_sales_sync_settings"

    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        primary_key=True,
    )

    auto_sync_enabled = Column(Boolean, nullable=False, server_default="false")
    daily_sync_time = Column(String(5), nullable=False, server_default="07:00")
    daily_lookback_days = Column(Integer, nullable=False, server_default="1")

    weekly_sync_enabled = Column(Boolean, nullable=False, server_default="true")
    weekly_sync_weekday = Column(Integer, nullable=False, server_default="0")  # 0=Monday ... 6=Sunday
    weekly_sync_time = Column(String(5), nullable=False, server_default="08:00")
    weekly_lookback_days = Column(Integer, nullable=False, server_default="14")

    manual_default_lookback_days = Column(Integer, nullable=False, server_default="1")

    last_daily_run_on = Column(Date, nullable=True)
    last_weekly_run_on = Column(Date, nullable=True)

    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_manual_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_scope = Column(String, nullable=True)  # daily / weekly / manual
    last_sync_status = Column(String, nullable=True)  # ok / error
    last_sync_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_iiko_sales_sync_settings_auto_enabled", "auto_sync_enabled"),
    )
