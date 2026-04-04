"""Pydantic schemas for KPI management."""
from __future__ import annotations

import datetime as dt
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict, validator


class KpiCalculationBase(str, Enum):
    NONE = "none"
    SALARY = "salary"
    HOURS_SUM = "hours_sum"
    RATE = "rate"


class KpiThresholdType(str, Enum):
    SINGLE = "single"
    DUAL = "dual"


class KpiEffectType(str, Enum):
    NONE = "none"
    FIXED = "fixed"
    PERCENT = "percent"


class KpiValueBase(str, Enum):
    NONE = "none"
    SALARY = "salary"
    HOURS_SUM = "hours_sum"
    RATE = "rate"


class KpiComparisonOperator(str, Enum):
    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"
    EQ = "eq"


class KpiRuleComparisonBasis(str, Enum):
    ABSOLUTE = "absolute"
    PLAN_PERCENT = "plan_percent"
    PLAN_DELTA_PERCENT = "plan_delta_percent"


DEFAULT_RULE_PERIOD_START = date(2000, 1, 1)
DEFAULT_RULE_PERIOD_END = date(2099, 12, 31)


class KpiResultStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"


class KpiResultSource(str, Enum):
    MANUAL = "manual"
    IMPORT = "import"
    CALCULATED = "calculated"


class KpiPayoutStatus(str, Enum):
    DRAFT = "draft"
    POSTED = "posted"


class KpiPlanMode(str, Enum):
    SHARED = "shared"
    PER_RESTAURANT = "per_restaurant"


class KpiPlanDirection(str, Enum):
    HIGHER_BETTER = "higher_better"
    LOWER_BETTER = "lower_better"


class KpiMetricAggregationMode(str, Enum):
    AVERAGE = "average"
    SUM = "sum"


class KpiMetricGroupBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    unit: Optional[str] = Field(default=None, max_length=32)
    use_max_scale: bool = False
    max_scale_value: Optional[Decimal] = Field(default=None, gt=0)
    plan_direction: KpiPlanDirection = KpiPlanDirection.HIGHER_BETTER
    plan_target_percent: Decimal = Field(default=Decimal("100"), ge=0, le=100)
    bonus_adjustment_type_id: Optional[int] = None
    penalty_adjustment_type_id: Optional[int] = None


class KpiMetricGroupCreate(KpiMetricGroupBase):
    pass


class KpiMetricGroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    unit: Optional[str] = Field(default=None, max_length=32)
    use_max_scale: Optional[bool] = None
    max_scale_value: Optional[Decimal] = Field(default=None, gt=0)
    plan_direction: Optional[KpiPlanDirection] = None
    plan_target_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    bonus_adjustment_type_id: Optional[int] = None
    penalty_adjustment_type_id: Optional[int] = None


class KpiMetricGroupPublic(KpiMetricGroupBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KpiMetricGroupListResponse(BaseModel):
    total: int
    items: List[KpiMetricGroupPublic]


class KpiMetricGroupRuleBase(BaseModel):
    group_id: int
    restaurant_id: Optional[int] = None
    department_code: Optional[str] = Field(default=None, max_length=64)
    position_id: Optional[int] = None
    employee_id: Optional[int] = None
    period_start: date = Field(default=DEFAULT_RULE_PERIOD_START)
    period_end: date = Field(default=DEFAULT_RULE_PERIOD_END)
    threshold_type: KpiThresholdType = KpiThresholdType.SINGLE
    comparison_basis: KpiRuleComparisonBasis = KpiRuleComparisonBasis.ABSOLUTE
    target_value: Decimal
    warning_value: Optional[Decimal] = None
    bonus_condition: KpiComparisonOperator = KpiComparisonOperator.GTE
    bonus_type: KpiEffectType = KpiEffectType.NONE
    bonus_value: Decimal = Decimal("0")
    bonus_base: KpiValueBase = KpiValueBase.NONE
    penalty_condition: KpiComparisonOperator = KpiComparisonOperator.LTE
    penalty_type: KpiEffectType = KpiEffectType.NONE
    penalty_value: Decimal = Decimal("0")
    penalty_base: KpiValueBase = KpiValueBase.NONE
    is_active: bool = True
    comment: Optional[str] = None

    @validator("period_end")
    def _validate_group_rule_period_range(cls, end_date: date, values):  # type: ignore[override]
        start_date = values.get("period_start")
        if start_date and end_date < start_date:
            raise ValueError("period_end must be greater or equal to period_start")
        return end_date


class KpiMetricGroupRuleCreate(KpiMetricGroupRuleBase):
    pass


class KpiMetricGroupRuleUpdate(BaseModel):
    group_id: Optional[int] = None
    restaurant_id: Optional[int] = None
    department_code: Optional[str] = Field(default=None, max_length=64)
    position_id: Optional[int] = None
    employee_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    threshold_type: Optional[KpiThresholdType] = None
    comparison_basis: Optional[KpiRuleComparisonBasis] = None
    target_value: Optional[Decimal] = None
    warning_value: Optional[Decimal] = None
    bonus_condition: Optional[KpiComparisonOperator] = None
    bonus_type: Optional[KpiEffectType] = None
    bonus_value: Optional[Decimal] = None
    bonus_base: Optional[KpiValueBase] = None
    penalty_condition: Optional[KpiComparisonOperator] = None
    penalty_type: Optional[KpiEffectType] = None
    penalty_value: Optional[Decimal] = None
    penalty_base: Optional[KpiValueBase] = None
    is_active: Optional[bool] = None
    comment: Optional[str] = None


class KpiMetricGroupRulePublic(BaseModel):
    id: int
    group_id: int
    restaurant_id: Optional[int]
    department_code: Optional[str]
    position_id: Optional[int]
    employee_id: Optional[int]
    period_start: date
    period_end: date
    threshold_type: KpiThresholdType
    comparison_basis: KpiRuleComparisonBasis
    target_value: Decimal
    warning_value: Optional[Decimal]
    bonus_condition: KpiComparisonOperator
    bonus_type: KpiEffectType
    bonus_value: Decimal
    bonus_base: KpiValueBase
    penalty_condition: KpiComparisonOperator
    penalty_type: KpiEffectType
    penalty_value: Decimal
    penalty_base: KpiValueBase
    is_active: bool
    comment: Optional[str]
    group: Optional[KpiMetricGroupPublic] = None

    model_config = ConfigDict(from_attributes=True)


class KpiMetricGroupRuleListResponse(BaseModel):
    total: int
    items: List[KpiMetricGroupRulePublic]


class KpiMetricBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    unit: Optional[str] = Field(default=None, max_length=32)
    calculation_base: KpiCalculationBase = KpiCalculationBase.NONE
    use_max_scale: bool = False
    max_scale_value: Optional[Decimal] = Field(default=None, gt=0)
    plan_direction: KpiPlanDirection = KpiPlanDirection.HIGHER_BETTER
    result_aggregation_mode: KpiMetricAggregationMode = KpiMetricAggregationMode.AVERAGE
    is_active: bool = True
    group_id: Optional[int] = None
    all_restaurants: bool = True
    restaurant_ids: Optional[List[int]] = None
    bonus_adjustment_type_id: Optional[int] = None
    penalty_adjustment_type_id: Optional[int] = None


class KpiMetricCreate(KpiMetricBase):
    pass


class KpiMetricUpdate(BaseModel):
    code: Optional[str] = Field(default=None, max_length=100)
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    unit: Optional[str] = Field(default=None, max_length=32)
    calculation_base: Optional[KpiCalculationBase] = None
    use_max_scale: Optional[bool] = None
    max_scale_value: Optional[Decimal] = Field(default=None, gt=0)
    plan_direction: Optional[KpiPlanDirection] = None
    result_aggregation_mode: Optional[KpiMetricAggregationMode] = None
    is_active: Optional[bool] = None
    group_id: Optional[int] = None
    all_restaurants: Optional[bool] = None
    restaurant_ids: Optional[List[int]] = None
    bonus_adjustment_type_id: Optional[int] = None
    penalty_adjustment_type_id: Optional[int] = None


class KpiMetricPublic(KpiMetricBase):
    id: int
    group: Optional[KpiMetricGroupPublic] = None

    model_config = ConfigDict(from_attributes=True)


class KpiMetricListResponse(BaseModel):
    total: int
    items: List[KpiMetricPublic]


class KpiRuleBase(BaseModel):
    metric_id: int
    restaurant_id: Optional[int] = None
    department_code: Optional[str] = Field(default=None, max_length=64)
    position_id: Optional[int] = None
    employee_id: Optional[int] = None
    period_start: date = Field(default=DEFAULT_RULE_PERIOD_START)
    period_end: date = Field(default=DEFAULT_RULE_PERIOD_END)
    threshold_type: KpiThresholdType = KpiThresholdType.SINGLE
    comparison_basis: KpiRuleComparisonBasis = KpiRuleComparisonBasis.PLAN_PERCENT
    target_value: Decimal
    warning_value: Optional[Decimal] = None
    bonus_condition: KpiComparisonOperator = KpiComparisonOperator.GTE
    bonus_type: KpiEffectType = KpiEffectType.NONE
    bonus_value: Decimal = Decimal("0")
    bonus_base: KpiValueBase = KpiValueBase.NONE
    penalty_condition: KpiComparisonOperator = KpiComparisonOperator.LTE
    penalty_type: KpiEffectType = KpiEffectType.NONE
    penalty_value: Decimal = Decimal("0")
    penalty_base: KpiValueBase = KpiValueBase.NONE
    is_active: bool = True
    comment: Optional[str] = None

    @validator("period_end")
    def _validate_period_range(cls, end_date: date, values):  # type: ignore[override]
        start_date = values.get("period_start")
        if start_date and end_date < start_date:
            raise ValueError("period_end must be greater or equal to period_start")
        return end_date


class KpiRuleCreate(KpiRuleBase):
    pass


class KpiRuleUpdate(BaseModel):
    metric_id: Optional[int] = None
    restaurant_id: Optional[int] = None
    department_code: Optional[str] = Field(default=None, max_length=64)
    position_id: Optional[int] = None
    employee_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    threshold_type: Optional[KpiThresholdType] = None
    comparison_basis: Optional[KpiRuleComparisonBasis] = None
    target_value: Optional[Decimal] = None
    warning_value: Optional[Decimal] = None
    bonus_condition: Optional[KpiComparisonOperator] = None
    bonus_type: Optional[KpiEffectType] = None
    bonus_value: Optional[Decimal] = None
    bonus_base: Optional[KpiValueBase] = None
    penalty_condition: Optional[KpiComparisonOperator] = None
    penalty_type: Optional[KpiEffectType] = None
    penalty_value: Optional[Decimal] = None
    penalty_base: Optional[KpiValueBase] = None
    is_active: Optional[bool] = None
    comment: Optional[str] = None


class KpiRulePublic(BaseModel):
    id: int
    metric_id: int
    restaurant_id: Optional[int]
    department_code: Optional[str]
    position_id: Optional[int]
    employee_id: Optional[int]
    period_start: date
    period_end: date
    threshold_type: KpiThresholdType
    comparison_basis: KpiRuleComparisonBasis
    target_value: Decimal
    warning_value: Optional[Decimal]
    bonus_condition: KpiComparisonOperator
    bonus_type: KpiEffectType
    bonus_value: Decimal
    bonus_base: KpiValueBase
    penalty_condition: KpiComparisonOperator
    penalty_type: KpiEffectType
    penalty_value: Decimal
    penalty_base: KpiValueBase
    is_active: bool
    comment: Optional[str]
    metric: Optional[KpiMetricPublic] = None

    model_config = ConfigDict(from_attributes=True)


class KpiRuleListResponse(BaseModel):
    total: int
    items: List[KpiRulePublic]


class KpiResultBase(BaseModel):
    metric_id: int
    restaurant_id: Optional[int] = None
    department_code: Optional[str] = Field(default=None, max_length=64)
    position_id: Optional[int] = None
    employee_id: Optional[int] = None
    period_start: date
    period_end: date
    fact_value: Decimal
    status: KpiResultStatus = KpiResultStatus.DRAFT
    source: KpiResultSource = KpiResultSource.MANUAL
    comment: Optional[str] = None
    recorded_by_id: Optional[int] = None

    @validator("period_end")
    def _validate_result_period(cls, end_date: date, values):  # type: ignore[override]
        start_date = values.get("period_start")
        if start_date and end_date < start_date:
            raise ValueError("period_end must be greater or equal to period_start")
        return end_date


class KpiResultCreate(KpiResultBase):
    pass


class KpiResultUpdate(BaseModel):
    metric_id: Optional[int] = None
    restaurant_id: Optional[int] = None
    department_code: Optional[str] = Field(default=None, max_length=64)
    position_id: Optional[int] = None
    employee_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    fact_value: Optional[Decimal] = None
    status: Optional[KpiResultStatus] = None
    source: Optional[KpiResultSource] = None
    comment: Optional[str] = None
    recorded_by_id: Optional[int] = None


class KpiResultPublic(BaseModel):
    id: int
    metric_id: int
    restaurant_id: Optional[int]
    department_code: Optional[str]
    position_id: Optional[int]
    employee_id: Optional[int]
    period_start: date
    period_end: date
    fact_value: Decimal
    status: KpiResultStatus
    source: KpiResultSource
    comment: Optional[str]
    recorded_at: datetime
    recorded_by_id: Optional[int]
    metric: Optional[KpiMetricPublic] = None

    model_config = ConfigDict(from_attributes=True)


class KpiResultListResponse(BaseModel):
    total: int
    items: List[KpiResultPublic]


class KpiPlanFactBase(BaseModel):
    metric_id: int
    restaurant_id: int
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    plan_value: Optional[Decimal] = None
    fact_value: Optional[Decimal] = None


class KpiPlanFactCreate(KpiPlanFactBase):
    pass


class KpiPlanFactUpdate(BaseModel):
    plan_value: Optional[Decimal] = None
    fact_value: Optional[Decimal] = None


class KpiPlanFactPublic(KpiPlanFactBase):
    id: int
    metric: Optional[KpiMetricPublic] = None

    model_config = ConfigDict(from_attributes=True)


class KpiPlanFactListResponse(BaseModel):
    total: int
    items: List[KpiPlanFactPublic]


class KpiPlanFactBulkItem(BaseModel):
    metric_id: int
    restaurant_id: int
    year: int
    month: int
    plan_value: Optional[Decimal] = None
    fact_value: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class KpiPlanFactBulkResponse(BaseModel):
    total: int
    items: List[KpiPlanFactBulkItem]


class KpiPlanPreferenceBase(BaseModel):
    metric_id: int
    plan_mode: KpiPlanMode = KpiPlanMode.SHARED
    restaurant_id: Optional[int] = None
    is_dynamic: bool = False
    selected_month: Optional[int] = Field(default=None, ge=1, le=12)


class KpiPlanPreferenceCreate(KpiPlanPreferenceBase):
    pass


class KpiPlanPreferenceUpdate(BaseModel):
    plan_mode: Optional[KpiPlanMode] = None
    restaurant_id: Optional[int] = None
    is_dynamic: Optional[bool] = None
    selected_month: Optional[int] = Field(default=None, ge=1, le=12)


class KpiPlanPreferencePublic(KpiPlanPreferenceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KpiPlanPreferenceListResponse(BaseModel):
    total: int
    items: List[KpiPlanPreferencePublic]


class KpiMetricGroupPlanFactBase(BaseModel):
    group_id: int
    restaurant_id: int
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    plan_value: Optional[Decimal] = None
    fact_value: Optional[Decimal] = None


class KpiMetricGroupPlanFactCreate(KpiMetricGroupPlanFactBase):
    pass


class KpiMetricGroupPlanFactUpdate(BaseModel):
    plan_value: Optional[Decimal] = None
    fact_value: Optional[Decimal] = None


class KpiMetricGroupPlanFactPublic(KpiMetricGroupPlanFactBase):
    id: int
    group: Optional[KpiMetricGroupPublic] = None

    model_config = ConfigDict(from_attributes=True)


class KpiMetricGroupPlanFactListResponse(BaseModel):
    total: int
    items: List[KpiMetricGroupPlanFactPublic]


class KpiMetricGroupPlanFactBulkItem(BaseModel):
    group_id: int
    restaurant_id: int
    year: int
    month: int
    plan_value: Optional[Decimal] = None
    fact_value: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class KpiMetricGroupPlanFactBulkResponse(BaseModel):
    total: int
    items: List[KpiMetricGroupPlanFactBulkItem]


class KpiMetricGroupPlanPreferenceBase(BaseModel):
    group_id: int
    plan_mode: KpiPlanMode = KpiPlanMode.SHARED
    restaurant_id: Optional[int] = None
    is_dynamic: bool = False
    selected_month: Optional[int] = Field(default=None, ge=1, le=12)


class KpiMetricGroupPlanPreferenceCreate(KpiMetricGroupPlanPreferenceBase):
    pass


class KpiMetricGroupPlanPreferenceUpdate(BaseModel):
    plan_mode: Optional[KpiPlanMode] = None
    restaurant_id: Optional[int] = None
    is_dynamic: Optional[bool] = None
    selected_month: Optional[int] = Field(default=None, ge=1, le=12)


class KpiMetricGroupPlanPreferencePublic(KpiMetricGroupPlanPreferenceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KpiMetricGroupPlanPreferenceListResponse(BaseModel):
    total: int
    items: List[KpiMetricGroupPlanPreferencePublic]


class KpiPayoutPreviewRequest(BaseModel):
    rule_id: int
    result_id: Optional[int] = None
    restaurant_id: Optional[int] = None
    year: Optional[int] = Field(default=None, ge=2000, le=2100)
    month: Optional[int] = Field(default=None, ge=1, le=12)
    comment: Optional[str] = None


class KpiPayoutPreviewByMetricRequest(BaseModel):
    metric_id: int
    restaurant_id: int
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    comment: Optional[str] = None


class KpiPayoutItemUpdate(BaseModel):
    amount: Optional[Decimal] = None
    bonus_enabled: Optional[bool] = None
    penalty_enabled: Optional[bool] = None
    bonus_amount: Optional[Decimal] = None
    penalty_amount: Optional[Decimal] = None
    comment: Optional[str] = None


class KpiPayoutPostRequest(BaseModel):
    adjustment_type_id: Optional[int] = None
    bonus_adjustment_type_id: Optional[int] = None
    penalty_adjustment_type_id: Optional[int] = None
    # NOTE: use dt.date explicitly to avoid name collision with field name "date"
    # under postponed annotations.
    date: Optional[dt.date] = None
    comment: Optional[str] = None


class KpiPayoutItemPublic(BaseModel):
    id: int
    user_id: int
    staff_code: Optional[str] = None
    full_name: Optional[str] = None
    base_amount: Decimal
    amount: Decimal
    bonus_amount: Decimal
    penalty_amount: Decimal
    bonus_enabled: bool
    penalty_enabled: bool
    manual: bool
    comment: Optional[str] = None
    calc_snapshot: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class KpiPayoutBatchPublic(BaseModel):
    id: int
    rule_id: int
    metric_id: int
    result_id: Optional[int]
    restaurant_id: Optional[int]
    position_id: Optional[int]
    period_start: date
    period_end: date
    status: KpiPayoutStatus
    comment: Optional[str] = None
    created_at: datetime
    created_by_id: Optional[int]
    posted_at: Optional[datetime] = None
    posted_by_id: Optional[int] = None
    calc_summary: Optional[dict] = None
    items: List[KpiPayoutItemPublic] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class KpiPayoutBatchListResponse(BaseModel):
    total: int
    items: List[KpiPayoutBatchPublic]
