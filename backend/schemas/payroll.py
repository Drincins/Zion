"""Schemas for payroll adjustments."""
from __future__ import annotations

import datetime
from typing import Any, List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PayrollAdjustmentTypeCreate(BaseModel):
    name: str
    kind: Literal["accrual", "deduction"]
    show_in_report: bool = False
    is_advance: bool = False


class PayrollAdjustmentTypeUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[Literal["accrual", "deduction"]] = None
    show_in_report: Optional[bool] = None
    is_advance: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> str:
        if value is None:
            raise ValueError("name may not be null")
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name must not be empty")
        return trimmed

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: Optional[str]) -> str:
        if value is None:
            raise ValueError("kind may not be null")
        return value


class PayrollAdjustmentTypePublic(BaseModel):
    id: int
    name: str
    kind: Literal["accrual", "deduction"]
    show_in_report: bool
    is_advance: bool = False

    model_config = ConfigDict(from_attributes=True)


class PayrollAdjustmentTypeListResponse(BaseModel):
    items: List[PayrollAdjustmentTypePublic]


class PayrollAdjustmentBase(BaseModel):
    user_id: int
    adjustment_type_id: int
    amount: float
    date: datetime.date
    restaurant_id: Optional[int] = None
    responsible_id: Optional[int] = None
    comment: Optional[str] = None


class PayrollAdjustmentCreate(PayrollAdjustmentBase):
    restaurant_id: int


class PayrollAdjustmentUpdate(BaseModel):
    adjustment_type_id: Optional[int] = None
    amount: Optional[float] = None
    date: Optional[datetime.date] = None
    restaurant_id: Optional[int] = None
    responsible_id: Optional[int] = None
    comment: Optional[str] = None

    @field_validator("adjustment_type_id")
    @classmethod
    def validate_adjustment_type_id(cls, value: Optional[int]) -> int:
        if value is None:
            raise ValueError("adjustment_type_id may not be null")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Optional[float]) -> float:
        if value is None:
            raise ValueError("amount may not be null")
        return value

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: Optional[datetime.date]) -> datetime.date:
        if value is None:
            raise ValueError("date may not be null")
        return value

    @field_validator("restaurant_id")
    @classmethod
    def validate_restaurant_id(cls, value: Optional[int]) -> int:
        if value is None:
            raise ValueError("restaurant_id may not be null")
        return value


class PayrollAdjustmentBulkRow(BaseModel):
    staff_code: str
    amount: float


class PayrollAdjustmentBulkCreate(BaseModel):
    restaurant_id: int
    period_from: datetime.date
    period_to: datetime.date
    date: datetime.date
    adjustment_type_id: int
    comment: Optional[str] = None
    rows: List[PayrollAdjustmentBulkRow]
    dry_run: bool = False


class PayrollAdjustmentBulkResultItem(BaseModel):
    staff_code: str
    user_id: Optional[int] = None
    full_name: Optional[str] = None
    reason: str


class PayrollAdjustmentBulkStatusItem(BaseModel):
    staff_code: str
    user_id: Optional[int] = None
    full_name: Optional[str] = None
    status: Literal["created", "skipped", "error"]
    reason: Optional[str] = None


class PayrollAdjustmentBulkResponse(BaseModel):
    created_count: int = 0
    created_total: float = 0
    skipped: List[PayrollAdjustmentBulkResultItem] = Field(default_factory=list)
    errors: List[PayrollAdjustmentBulkResultItem] = Field(default_factory=list)
    results: List[PayrollAdjustmentBulkStatusItem] = Field(default_factory=list)


class PayrollAdjustmentPublic(PayrollAdjustmentBase):
    id: int
    amount: Optional[float] = None
    adjustment_type: Optional[PayrollAdjustmentTypePublic] = None
    restaurant_name: Optional[str] = None
    responsible_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PayrollAdjustmentListResponse(BaseModel):
    items: List[PayrollAdjustmentPublic]


class PayrollSalaryResultPublic(BaseModel):
    id: int
    user_id: int
    period_start: datetime.date
    period_end: datetime.date
    base_amount: float
    adjustments_amount: float
    gross_amount: float
    details: Optional[dict[str, Any]] = None
    calculated_at: datetime.datetime
    calculated_by_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PayrollSalaryResultListResponse(BaseModel):
    items: List[PayrollSalaryResultPublic]


class PayrollSalaryRecalcRequest(BaseModel):
    user_ids: List[int] = Field(default_factory=list)
    period_start: Optional[datetime.date] = None
    period_end: Optional[datetime.date] = None


# --- Payroll advances ---
class PayrollAdvanceCreateRequest(BaseModel):
    date_from: datetime.date
    date_to: datetime.date
    restaurant_id: int
    subdivision_id: Optional[int] = None
    salary_percent: Optional[float] = None
    statement_kind: Literal["advance", "salary"] = "advance"
    title: Optional[str] = None
    user_ids: Optional[List[int]] = None


class PayrollAdvanceItemUpdateRequest(BaseModel):
    final_amount: float
    comment: Optional[str] = None


class PayrollAdvanceItemBulkUpdateItem(BaseModel):
    item_id: int
    final_amount: float
    comment: Optional[str] = None


class PayrollAdvanceItemsBulkUpdateRequest(BaseModel):
    items: List[PayrollAdvanceItemBulkUpdateItem] = Field(default_factory=list)


class PayrollAdvanceStatusUpdate(BaseModel):
    status: Literal["draft", "review", "confirmed", "ready", "posted"]


class PayrollAdvanceItemPublic(BaseModel):
    id: int
    user_id: int
    staff_code: Optional[str] = None
    full_name: str
    position_name: Optional[str] = None
    subdivision_name: Optional[str] = None
    restaurant_id: Optional[int] = None
    restaurant_name: Optional[str] = None
    fact_hours: float
    night_hours: float
    rate: Optional[float] = None
    accrual_amount: float
    deduction_amount: float
    calculated_amount: float
    final_amount: float
    manual: bool
    fired: bool = False
    fire_date: Optional[datetime.date] = None
    comment: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PayrollAdvanceItemPatchResponse(BaseModel):
    statement_id: int
    item: PayrollAdvanceItemPublic
    updated_at: Optional[datetime.datetime] = None
    updated_by_id: Optional[int] = None


class PayrollAdvanceItemsBulkPatchResponse(BaseModel):
    statement_id: int
    items: List[PayrollAdvanceItemPublic] = Field(default_factory=list)
    updated_at: Optional[datetime.datetime] = None
    updated_by_id: Optional[int] = None


class PayrollAdvanceStatementAdjustmentSummaryPublic(BaseModel):
    adjustment_type_id: Optional[int] = None
    name: str
    kind: Literal["accrual", "deduction"]
    show_in_report: bool = False
    is_advance: bool = False
    amount: float = 0


class PayrollAdvanceStatementPublic(BaseModel):
    id: int
    status: str
    statement_kind: Literal["advance", "salary"] = "advance"
    date_from: datetime.date
    date_to: datetime.date
    restaurant_id: Optional[int] = None
    restaurant_name: Optional[str] = None
    subdivision_id: Optional[int] = None
    subdivision_name: Optional[str] = None
    salary_percent: Optional[float] = None
    fixed_only: bool = True
    title: Optional[str] = None
    created_by_id: Optional[int] = None
    updated_by_id: Optional[int] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    posted_at: Optional[datetime.datetime] = None
    items: List[PayrollAdvanceItemPublic] = Field(default_factory=list)
    adjustment_summaries: List[PayrollAdvanceStatementAdjustmentSummaryPublic] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PayrollAdvanceListResponse(BaseModel):
    items: List[PayrollAdvanceStatementPublic]


class PayrollAdvanceStatementTotalsPublic(BaseModel):
    statement_id: int
    row_count: int = 0
    accrual_total: float = 0
    deduction_total: float = 0
    final_total: float = 0
    accrual_rows_count: int = 0
    deduction_rows_count: int = 0


class PayrollAdvanceStatementTotalsResponse(BaseModel):
    items: List[PayrollAdvanceStatementTotalsPublic] = Field(default_factory=list)
    missing_ids: List[int] = Field(default_factory=list)


class PayrollAdvancePostRequest(BaseModel):
    adjustment_type_id: int
    date: datetime.date
    comment: Optional[str] = None
    restaurant_id: Optional[int] = None


class PayrollAdvanceConsolidatedDownloadRequest(BaseModel):
    statement_ids: List[int] = Field(default_factory=list)


class PayrollAdvanceConsolidatedCreateRequest(BaseModel):
    statement_ids: List[int] = Field(default_factory=list)
    title: Optional[str] = None


class PayrollAdvanceConsolidatedPublic(BaseModel):
    id: int
    title: Optional[str] = None
    date_from: datetime.date
    date_to: datetime.date
    statement_ids: List[int] = Field(default_factory=list)
    created_by_id: Optional[int] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PayrollAdvanceConsolidatedListResponse(BaseModel):
    items: List[PayrollAdvanceConsolidatedPublic]
