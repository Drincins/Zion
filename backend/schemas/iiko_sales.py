"""Request schemas for iiko sales and layout administration."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class SyncIikoSalesRequest(BaseModel):
    restaurant_id: int
    from_date: str  # 'DD.MM.YYYY' or 'YYYY-MM-DD'
    to_date: str    # 'DD.MM.YYYY' or 'YYYY-MM-DD'


class SyncIikoSalesNetworkRequest(BaseModel):
    from_date: str  # 'DD.MM.YYYY' or 'YYYY-MM-DD'
    to_date: str    # 'DD.MM.YYYY' or 'YYYY-MM-DD'
    restaurant_ids: Optional[List[int]] = None
    stop_on_error: bool = False


class ClearIikoSalesRequest(BaseModel):
    restaurant_id: Optional[int] = None


class UpdateIikoPaymentMethodRequest(BaseModel):
    category: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class UpdateIikoNonCashTypeRequest(BaseModel):
    category: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class CreateIikoNonCashTypeRequest(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    comment: Optional[str] = None
    is_active: bool = True


class UpsertIikoNonCashEmployeeLimitRequest(BaseModel):
    non_cash_type_id: str
    user_id: int
    period_type: str = "month"
    limit_amount: Optional[float] = None
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoNonCashEmployeeLimitRequest(BaseModel):
    period_type: Optional[str] = None
    limit_amount: Optional[float] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class UpsertIikoSalesLocationMappingRequest(BaseModel):
    source_restaurant_id: Optional[int] = None
    target_restaurant_id: int
    department: Optional[str] = None
    table_num: Optional[str] = None
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoSalesLocationMappingRequest(BaseModel):
    source_restaurant_id: Optional[int] = None
    target_restaurant_id: Optional[int] = None
    department: Optional[str] = None
    table_num: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class UpsertIikoSalesHallTableRequest(BaseModel):
    restaurant_id: int
    source_restaurant_id: Optional[int] = None
    department: Optional[str] = None
    table_num: Optional[str] = None
    hall_name: str
    table_name: Optional[str] = None
    capacity: Optional[int] = None
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoSalesHallTableRequest(BaseModel):
    restaurant_id: Optional[int] = None
    source_restaurant_id: Optional[int] = None
    department: Optional[str] = None
    table_num: Optional[str] = None
    hall_name: Optional[str] = None
    table_name: Optional[str] = None
    capacity: Optional[int] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class CreateIikoSalesHallRequest(BaseModel):
    name: str
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoSalesHallRequest(BaseModel):
    name: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class CreateIikoSalesHallZoneRequest(BaseModel):
    hall_id: UUID
    restaurant_id: int
    name: str
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoSalesHallZoneRequest(BaseModel):
    name: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class AssignIikoSalesZoneTableItemRequest(BaseModel):
    source_restaurant_id: Optional[int] = None
    department: str
    table_num: Optional[str] = None
    table_name: Optional[str] = None
    capacity: Optional[int] = None
    comment: Optional[str] = None
    is_active: bool = True


class AssignIikoSalesZoneTablesRequest(BaseModel):
    items: List[AssignIikoSalesZoneTableItemRequest]
    replace_zone_tables: bool = False


class UpdateIikoWaiterTurnoverSettingsRequest(BaseModel):
    rule_name: Optional[str] = None
    is_active: Optional[bool] = None
    real_money_only: Optional[bool] = None
    amount_mode: Optional[str] = None
    deleted_mode: Optional[str] = None
    waiter_mode: Optional[str] = None
    position_ids: Optional[List[int]] = None
    include_groups: Optional[List[str]] = None
    exclude_groups: Optional[List[str]] = None
    include_categories: Optional[List[str]] = None
    exclude_categories: Optional[List[str]] = None
    include_positions: Optional[List[str]] = None
    exclude_positions: Optional[List[str]] = None
    include_payment_method_guids: Optional[List[str]] = None
    comment: Optional[str] = None
