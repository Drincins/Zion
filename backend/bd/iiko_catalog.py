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
    "IikoProduct",
    "IikoProductRestaurant",
    "IikoProductSetting",
    "IikoProductNameHistory",
    "IikoPaymentMethod",
    "IikoNonCashPaymentType",
    "IikoNonCashEmployeeLimit",
    "IikoWaiterTurnoverSetting",
]


class IikoProduct(Base):
    """
    Canonical iiko product catalog for the whole company/network.

    We key by iiko product GUID (productDto.id). Dish code used in OLAP is stored in `num`.
    """

    __tablename__ = "iiko_products"

    id = Column(String, primary_key=True)  # iiko product GUID (productDto.id)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    source_restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)

    parent_id = Column(String, nullable=True)
    num = Column(String, nullable=True, index=True, unique=True)  # DishCode in OLAP (article)
    code = Column(String, nullable=True, index=True)  # quick code
    name = Column(String, nullable=True)
    product_type = Column(String, nullable=True)
    product_group_type = Column(String, nullable=True)
    cooking_place_type = Column(String, nullable=True)
    main_unit = Column(String, nullable=True)
    product_category = Column(String, nullable=True)
    containers = Column(Text, nullable=True)
    barcodes = Column(Text, nullable=True)

    default_sale_price = Column(Numeric(14, 2), nullable=True)
    estimated_cost = Column(Numeric(14, 4), nullable=True)
    tech_card_id = Column(String, nullable=True)
    tech_card_date_from = Column(Date, nullable=True)
    tech_card_date_to = Column(Date, nullable=True)
    tech_card_payload = Column(JSONB, nullable=True)
    raw_v2_payload = Column(JSONB, nullable=True)

    raw_payload = Column(JSONB, nullable=True)
    raw_xml = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    restaurants = relationship("IikoProductRestaurant", back_populates="product", cascade="all, delete-orphan")
    settings = relationship("IikoProductSetting", back_populates="product", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_iiko_products_company_num", "company_id", "num"),
        Index("ix_iiko_products_company_code", "company_id", "code"),
    )


class IikoProductRestaurant(Base):
    """Presence of a canonical product in a given restaurant."""

    __tablename__ = "iiko_product_restaurants"

    product_id = Column(String, ForeignKey("iiko_products.id", ondelete="CASCADE"), primary_key=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True)

    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    product = relationship("IikoProduct", back_populates="restaurants")
    restaurant = relationship("Restaurant")

    __table_args__ = (
        Index("ix_iiko_product_restaurants_restaurant_id", "restaurant_id"),
    )


class IikoProductSetting(Base):
    """
    Local (non-iiko) settings for a canonical product.

    We keep it separate so sync from iiko never overwrites custom business fields.
    """

    __tablename__ = "iiko_product_settings"

    product_id = Column(String, ForeignKey("iiko_products.id", ondelete="CASCADE"), primary_key=True)

    portion_coef_kitchen = Column(Numeric(10, 4), nullable=True)
    portion_coef_hall = Column(Numeric(10, 4), nullable=True)
    custom_product_group_type = Column(String, nullable=True)
    custom_product_category = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    product = relationship("IikoProduct", back_populates="settings")


class IikoProductNameHistory(Base):
    """History of iiko product name changes observed during sync."""

    __tablename__ = "iiko_product_name_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(String, ForeignKey("iiko_products.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)

    old_name = Column(String, nullable=True)
    new_name = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_iiko_product_name_history_product_created", "product_id", "created_at"),
    )


class IikoPaymentMethod(Base):
    """
    Payment method reference from iiko.

    For now we populate it from OLAP (PayTypes.GUID + PayTypes), later we can extend with a direct iiko endpoint.
    """

    __tablename__ = "iiko_payment_methods"

    guid = Column(String, primary_key=True)  # PayTypes.GUID
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String, nullable=False)

    # Custom classification fields (filled by the user in UI later).
    category = Column(String, nullable=True)  # e.g. real_money, staff, certificate, etc.
    comment = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", "guid", name="uq_iiko_payment_methods_company_guid"),
        Index("ix_iiko_payment_methods_company_name", "company_id", "name"),
    )


class IikoNonCashPaymentType(Base):
    """
    Stable dictionary for iiko non-cash payment types.

    Key: NonCashPaymentType.Id (stable), name can change in iiko.
    """

    __tablename__ = "iiko_non_cash_payment_types"

    id = Column(String, primary_key=True)  # NonCashPaymentType.Id
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", "id", name="uq_iiko_non_cash_payment_types_company_id"),
        Index("ix_iiko_non_cash_payment_types_company_name", "company_id", "name"),
    )


class IikoNonCashEmployeeLimit(Base):
    """
    Mapping of a non-cash type to employee and their limit.

    This is used for staff food/drink allowance tracking.
    """

    __tablename__ = "iiko_non_cash_employee_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    non_cash_type_id = Column(
        String,
        ForeignKey("iiko_non_cash_payment_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scope of limit (month/day/custom). Start with month as default.
    period_type = Column(String, nullable=False, server_default="month")
    limit_amount = Column(Numeric(14, 2), nullable=True)
    comment = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    non_cash_type = relationship("IikoNonCashPaymentType")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "non_cash_type_id",
            "user_id",
            "period_type",
            name="uq_iiko_non_cash_employee_limits_scope",
        ),
        Index("ix_iiko_non_cash_employee_limits_company_user", "company_id", "user_id"),
    )


class IikoWaiterTurnoverSetting(Base):
    """
    Configurable rules for waiter turnover calculation.

    This setting is company-scoped and drives:
    - admin analytics filters
    - employee-facing number in Time Tracking
    """

    __tablename__ = "iiko_waiter_turnover_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_name = Column(String, nullable=False, server_default="Основное правило")

    is_active = Column(Boolean, nullable=False, server_default="true")
    real_money_only = Column(Boolean, nullable=False, server_default="true")
    amount_mode = Column(String, nullable=False, server_default="sum_without_discount")
    deleted_mode = Column(String, nullable=False, server_default="without_deleted")
    waiter_mode = Column(String, nullable=False, server_default="order_close")

    # Empty/null means "all positions".
    position_ids = Column(JSONB, nullable=True)

    include_groups = Column(JSONB, nullable=True)
    exclude_groups = Column(JSONB, nullable=True)
    include_categories = Column(JSONB, nullable=True)
    exclude_categories = Column(JSONB, nullable=True)
    include_positions = Column(JSONB, nullable=True)
    exclude_positions = Column(JSONB, nullable=True)
    include_payment_method_guids = Column(JSONB, nullable=True)

    comment = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index(
            "ix_iiko_waiter_turnover_settings_company_active_updated",
            "company_id",
            "is_active",
            "updated_at",
        ),
        Index("ix_iiko_waiter_turnover_settings_company_updated", "company_id", "updated_at"),
    )
