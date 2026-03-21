# backend/bd/iiko_olap.py
from __future__ import annotations
import uuid
from sqlalchemy import (
    Column, Integer, String, Date, Numeric, DateTime, ForeignKey, func,
    Index, UniqueConstraint, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from backend.bd.database import Base  # единый Base из backend/bd/database.py

__all__ = ["IikoOlapRow", "IikoOlapRawRow", "IikoProductRow"]


class IikoOlapRow(Base):
    """
    Строка из OLAP SALES (лист 'SALES_RAW').
    Храним «сырые» поля без преобразований + исходный JSON.
    """
    __tablename__ = "iiko_olap_rows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"),
                           nullable=True, index=True)
    restaurant = relationship("Restaurant", backref="olap_rows")

    # Бизнес-поля (всё опционально, тянем как отдаёт OLAP)
    open_date = Column(Date, index=True, nullable=True)               # OpenDate.Typed (если группируешь по дате)
    department = Column(String, nullable=True)                        # Department
    dish_code = Column(String, nullable=True, index=True)             # DishCode
    dish_full_name = Column(String, nullable=True)                    # DishFullName
    dish_measure_unit = Column(String, nullable=True)                 # DishMeasureUnit
    dish_group = Column(String, nullable=True)                        # DishGroup
    cooking_place = Column(String, nullable=True)                     # CookingPlace
    non_cash_payment_type = Column(String, nullable=True)             # NonCashPaymentType
    pay_types = Column(String, nullable=True)                         # PayTypes

    # Агрегаты (как есть)
    dish_amount_int = Column(Integer, nullable=True)                  # DishAmountInt (если сохраняешь)
    dish_sum_int = Column(Numeric(14, 2), nullable=True)              # DishSumInt
    discount_sum = Column(Numeric(14, 2), nullable=True)              # DiscountSum

    # Полная «сырая» строка (как вернул API /reports/olap)
    raw_row = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_iiko_olap_rows_rest_date", "restaurant_id", "open_date"),
        # Если хочешь дедуп и апсерты по бизнес-ключу — раскомментируй:
        # UniqueConstraint("restaurant_id", "open_date", "dish_code", "pay_types",
        #                  name="uq_iiko_olap_business_key"),
    )


class IikoOlapRawRow(Base):
    __tablename__ = "iiko_olap_rows_raw"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"),
                           nullable=True, index=True)
    restaurant = relationship("Restaurant", backref="olap_rows_raw")

    open_date = Column(Date, index=True, nullable=True)
    row_key = Column(String, nullable=True)
    payload_hash = Column(String, nullable=True)
    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_iiko_olap_rows_raw_rest_date", "restaurant_id", "open_date"),
        UniqueConstraint("restaurant_id", "row_key", name="uq_iiko_olap_rows_raw_rest_key"),
    )


class IikoProductRow(Base):
    """
    Строка из /resto/api/products (лист 'PRODUCTS_RAW').
    Храним основные поля из XSD + «сырые» данные.
    """
    __tablename__ = "iiko_product_rows"

    # PK — id продукта из iiko (GUID как строка). Если один и тот же GUID может приходить с разных ресторанов,
    # можно заменить PK на surrogate + сделать уникальность по (restaurant_id, id).
    id = Column(String, primary_key=True)  # productDto.id

    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"),
                           nullable=True, index=True)
    restaurant = relationship("Restaurant", backref="product_rows")

    # Поля XSD ProductDto (всё как есть)
    parent_id = Column(String, nullable=True)                # parentId
    num = Column(String, nullable=True)                      # num (артикул)
    code = Column(String, nullable=True, index=True)         # code (быстрый набор)
    name = Column(String, nullable=True)                     # name
    product_type = Column(String, nullable=True)             # productType (GOODS/DISH/...)
    product_group_type = Column(String, nullable=True)       # productGroupType (PRODUCTS/MODIFIERS)
    cooking_place_type = Column(String, nullable=True)       # cookingPlaceType
    main_unit = Column(String, nullable=True)                # mainUnit
    product_category = Column(String, nullable=True)         # productCategory

    # Коллекции из XML — у тебя уже склеены в строки (оставляем текстом «как есть»)
    containers = Column(Text, nullable=True)                 # containers
    barcodes = Column(Text, nullable=True)                   # barcodes

    # Полностью «сырой» payload (если парсишь в dict) и/или исходный XML (опционально)
    raw_payload = Column(JSONB, nullable=True)               # распарсенный dict
    raw_xml = Column(Text, nullable=True)                    # исходный XML-фрагмент

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_iiko_product_rows_rest_code", "restaurant_id", "code"),
        # Если GUID может повторяться в разных ресторанах — убери PK на id,
        # добавь surrogate PK и включи уникальность на (restaurant_id, id):
        # UniqueConstraint("restaurant_id", "id", name="uq_iiko_product_rest_id"),
    )
