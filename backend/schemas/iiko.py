"""Schemas for iiko integrations (attendance, OLAP, products)."""
from __future__ import annotations

from datetime import datetime, date
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttendanceRead(BaseModel):
    id: str
    employee_id: str
    employee_name: str
    role_id: Optional[str] = None
    role_name: Optional[str] = None
    restaurant_id: Optional[int] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    start: datetime
    end: Optional[datetime] = None
    duration: Optional[float] = None
    regular_minutes: Optional[int] = None
    regular_payment_sum: Optional[float] = None
    overtime_minutes: Optional[int] = None
    overtime_payment_sum: Optional[float] = None
    attendance_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IikoOlapRowCreate(BaseModel):
    restaurant_id: Optional[int] = None
    open_date: Optional[date] = None
    department: Optional[str] = None
    dish_code: Optional[str] = None
    dish_full_name: Optional[str] = None
    dish_measure_unit: Optional[str] = None
    dish_group: Optional[str] = None
    cooking_place: Optional[str] = None
    non_cash_payment_type: Optional[str] = None
    pay_types: Optional[str] = None
    dish_amount_int: Optional[int] = None
    dish_sum_int: Optional[float] = None
    discount_sum: Optional[float] = None
    raw_row: Optional[dict[str, Any]] = None


class IikoOlapRowRead(IikoOlapRowCreate):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IikoProductRowCreate(BaseModel):
    id: str
    restaurant_id: Optional[int] = None
    parent_id: Optional[str] = None
    num: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    product_type: Optional[str] = None
    product_group_type: Optional[str] = None
    cooking_place_type: Optional[str] = None
    main_unit: Optional[str] = None
    product_category: Optional[str] = None
    containers: Optional[str] = None
    barcodes: Optional[str] = None
    raw_payload: Optional[dict[str, Any]] = None
    raw_xml: Optional[str] = None


class IikoProductRowRead(IikoProductRowCreate):
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class IikoProductRead(BaseModel):
    id: str
    company_id: Optional[int] = None
    source_restaurant_id: Optional[int] = None
    parent_id: Optional[str] = None
    num: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    product_type: Optional[str] = None
    product_group_type: Optional[str] = None
    iiko_product_group_type: Optional[str] = None
    custom_product_group_type: Optional[str] = None
    cooking_place_type: Optional[str] = None
    main_unit: Optional[str] = None
    product_category: Optional[str] = None
    iiko_product_category: Optional[str] = None
    custom_product_category: Optional[str] = None
    containers: Optional[str] = None
    barcodes: Optional[str] = None
    default_sale_price: Optional[float] = None
    estimated_cost: Optional[float] = None
    tech_card_id: Optional[str] = None
    tech_card_date_from: Optional[date] = None
    tech_card_date_to: Optional[date] = None
    tech_card_payload: Optional[dict[str, Any]] = None
    raw_v2_payload: Optional[dict[str, Any]] = None
    raw_payload: Optional[dict[str, Any]] = None
    raw_xml: Optional[str] = None
    portion_coef_kitchen: Optional[float] = None
    portion_coef_hall: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
