"""Schemas for labor summary reporting."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class LaborSummaryPosition(BaseModel):
    position_id: Optional[int] = None
    position_name: Optional[str] = None
    hours: float
    night_hours: float
    amount: Optional[float] = None
    accrual_amount: Optional[float] = None
    deduction_amount: Optional[float] = None
    total_cost: Optional[float] = None


class LaborSummarySubdivision(BaseModel):
    subdivision_id: Optional[int] = None
    subdivision_name: Optional[str] = None
    hours: float
    night_hours: float
    amount: Optional[float] = None
    accrual_amount: Optional[float] = None
    deduction_amount: Optional[float] = None
    total_cost: Optional[float] = None
    positions: Optional[List[LaborSummaryPosition]] = None


class LaborSummaryTotals(BaseModel):
    hours: float
    night_hours: float
    amount: Optional[float] = None
    accrual_amount: Optional[float] = None
    deduction_amount: Optional[float] = None
    total_cost: Optional[float] = None
    revenue_amount: Optional[float] = None


class LaborSummaryResponse(BaseModel):
    restaurant_id: int
    date_from: date
    date_to: date
    subdivisions: List[LaborSummarySubdivision]
    totals: LaborSummaryTotals


class LaborSummaryOptionSubdivision(BaseModel):
    id: int
    name: str


class LaborSummaryOptionPosition(BaseModel):
    id: int
    name: str
    restaurant_id: Optional[int] = None
    restaurant_subdivision_id: Optional[int] = None


class LaborSummaryOptionsResponse(BaseModel):
    subdivisions: List[LaborSummaryOptionSubdivision]
    positions: List[LaborSummaryOptionPosition]


class LaborSummarySettingsBase(BaseModel):
    include_base_cost: bool = True
    include_accrual_cost: bool = True
    include_deduction_cost: bool = True
    accrual_adjustment_type_ids: Optional[List[int]] = None
    deduction_adjustment_type_ids: Optional[List[int]] = None
    revenue_real_money_only: bool = True
    revenue_exclude_deleted: bool = True
    revenue_amount_mode: str = "sum_without_discount"


class LaborSummarySettingsUpdate(LaborSummarySettingsBase):
    pass


class LaborSummarySettingsPublic(LaborSummarySettingsBase):
    company_id: Optional[int] = None
    updated_by_id: Optional[int] = None
    updated_at: Optional[datetime] = None
