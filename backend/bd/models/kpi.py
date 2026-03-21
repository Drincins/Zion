"""KPI domain models for metrics, rules, and results."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.bd.database import Base

KPI_CALCULATION_BASE = Enum(
    "none",
    "salary",
    "hours_sum",
    "rate",
    name="kpi_calculation_base",
)
KPI_THRESHOLD_TYPE = Enum("single", "dual", name="kpi_threshold_type")
KPI_EFFECT_TYPE = Enum("none", "fixed", "percent", name="kpi_effect_type")
KPI_VALUE_BASE = Enum("none", "salary", "hours_sum", "rate", name="kpi_value_base")
KPI_RESULT_STATUS = Enum("draft", "confirmed", name="kpi_result_status")
KPI_RESULT_SOURCE = Enum("manual", "import", "calculated", name="kpi_result_source")
KPI_COMPARISON_OPERATOR = Enum("gte", "gt", "lte", "lt", "eq", name="kpi_comparison_operator")
KPI_PAYOUT_STATUS = Enum("draft", "posted", name="kpi_payout_status")
KPI_PLAN_DIRECTION = Enum("higher_better", "lower_better", name="kpi_plan_direction")
KPI_RULE_COMPARISON_BASIS = Enum(
    "absolute",
    "plan_percent",
    "plan_delta_percent",
    name="kpi_rule_comparison_basis",
)


class KpiMetric(Base):
    __tablename__ = "kpi_metrics"

    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    unit = Column(String(32), nullable=True)
    calculation_base = Column(KPI_CALCULATION_BASE, nullable=False, default="none")
    use_max_scale = Column(Boolean, nullable=False, default=False)
    max_scale_value = Column(Numeric(14, 4), nullable=True)
    plan_direction = Column(KPI_PLAN_DIRECTION, nullable=False, default="higher_better")
    is_active = Column(Boolean, nullable=False, default=True)
    group_id = Column(Integer, ForeignKey("kpi_metric_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    all_restaurants = Column(Boolean, nullable=False, default=True)
    restaurant_ids = Column(JSON, nullable=True)
    bonus_adjustment_type_id = Column(
        Integer,
        ForeignKey("payroll_adjustment_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    penalty_adjustment_type_id = Column(
        Integer,
        ForeignKey("payroll_adjustment_types.id", ondelete="SET NULL"),
        nullable=True,
    )

    group = relationship("KpiMetricGroup", back_populates="metrics")
    rules = relationship(
        "KpiRule",
        back_populates="metric",
        cascade="all, delete-orphan",
    )
    results = relationship(
        "KpiResult",
        back_populates="metric",
        cascade="all, delete-orphan",
    )
    plan_facts = relationship(
        "KpiPlanFact",
        back_populates="metric",
        cascade="all, delete-orphan",
    )
    plan_preference = relationship(
        "KpiPlanPreference",
        back_populates="metric",
        uselist=False,
        cascade="all, delete-orphan",
    )


class KpiMetricGroup(Base):
    __tablename__ = "kpi_metric_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    unit = Column(String(32), nullable=True)
    use_max_scale = Column(Boolean, nullable=False, default=False)
    max_scale_value = Column(Numeric(14, 4), nullable=True)
    plan_direction = Column(KPI_PLAN_DIRECTION, nullable=False, default="higher_better")
    plan_target_percent = Column(Numeric(5, 2), nullable=False, default=100)
    bonus_adjustment_type_id = Column(
        Integer,
        ForeignKey("payroll_adjustment_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    penalty_adjustment_type_id = Column(
        Integer,
        ForeignKey("payroll_adjustment_types.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    metrics = relationship("KpiMetric", back_populates="group")
    rules = relationship(
        "KpiMetricGroupRule",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    plan_facts = relationship(
        "KpiMetricGroupPlanFact",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    plan_preference = relationship(
        "KpiMetricGroupPlanPreference",
        back_populates="group",
        uselist=False,
        cascade="all, delete-orphan",
    )


class KpiMetricGroupRule(Base):
    __tablename__ = "kpi_metric_group_rules"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("kpi_metric_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=True, index=True)
    department_code = Column(String(64), nullable=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    threshold_type = Column(KPI_THRESHOLD_TYPE, nullable=False, default="single")
    comparison_basis = Column(KPI_RULE_COMPARISON_BASIS, nullable=False, default="absolute")
    target_value = Column(Numeric(14, 4), nullable=False)
    warning_value = Column(Numeric(14, 4), nullable=True)
    bonus_condition = Column(KPI_COMPARISON_OPERATOR, nullable=False, default="gte")
    bonus_type = Column(KPI_EFFECT_TYPE, nullable=False, default="none")
    bonus_value = Column(Numeric(12, 2), nullable=False, default=0)
    bonus_base = Column(KPI_VALUE_BASE, nullable=False, default="none")
    penalty_condition = Column(KPI_COMPARISON_OPERATOR, nullable=False, default="lte")
    penalty_type = Column(KPI_EFFECT_TYPE, nullable=False, default="none")
    penalty_value = Column(Numeric(12, 2), nullable=False, default=0)
    penalty_base = Column(KPI_VALUE_BASE, nullable=False, default="none")
    is_active = Column(Boolean, nullable=False, default=True)
    comment = Column(Text, nullable=True)

    group = relationship("KpiMetricGroup", back_populates="rules")
    restaurant = relationship("Restaurant")
    position = relationship("Position")
    employee = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "restaurant_id",
            "department_code",
            "position_id",
            "employee_id",
            "period_start",
            "period_end",
            name="uq_kpi_group_rules_scope_period",
        ),
        Index(
            "ix_kpi_group_rules_scope",
            "group_id",
            "restaurant_id",
            "position_id",
            "employee_id",
        ),
        Index(
            "ix_kpi_group_rules_group_active_period",
            "group_id",
            "is_active",
            "period_start",
            "period_end",
        ),
    )


class KpiRule(Base):
    __tablename__ = "kpi_rules"

    id = Column(Integer, primary_key=True)
    metric_id = Column(Integer, ForeignKey("kpi_metrics.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=True, index=True)
    department_code = Column(String(64), nullable=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    threshold_type = Column(KPI_THRESHOLD_TYPE, nullable=False, default="single")
    comparison_basis = Column(KPI_RULE_COMPARISON_BASIS, nullable=False, default="plan_percent")
    target_value = Column(Numeric(14, 4), nullable=False)
    warning_value = Column(Numeric(14, 4), nullable=True)
    bonus_condition = Column(KPI_COMPARISON_OPERATOR, nullable=False, default="gte")
    bonus_type = Column(KPI_EFFECT_TYPE, nullable=False, default="none")
    bonus_value = Column(Numeric(12, 2), nullable=False, default=0)
    bonus_base = Column(KPI_VALUE_BASE, nullable=False, default="none")
    penalty_condition = Column(KPI_COMPARISON_OPERATOR, nullable=False, default="lte")
    penalty_type = Column(KPI_EFFECT_TYPE, nullable=False, default="none")
    penalty_value = Column(Numeric(12, 2), nullable=False, default=0)
    penalty_base = Column(KPI_VALUE_BASE, nullable=False, default="none")
    is_active = Column(Boolean, nullable=False, default=True)
    comment = Column(Text, nullable=True)

    metric = relationship("KpiMetric", back_populates="rules")
    restaurant = relationship("Restaurant")
    position = relationship("Position")
    employee = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "metric_id",
            "restaurant_id",
            "department_code",
            "position_id",
            "employee_id",
            "period_start",
            "period_end",
            name="uq_kpi_rules_scope_period",
        ),
        Index(
            "ix_kpi_rules_scope",
            "metric_id",
            "restaurant_id",
            "position_id",
            "employee_id",
        ),
        Index(
            "ix_kpi_rules_metric_active_period",
            "metric_id",
            "is_active",
            "period_start",
            "period_end",
        ),
    )


class KpiResult(Base):
    __tablename__ = "kpi_results"

    id = Column(Integer, primary_key=True)
    metric_id = Column(Integer, ForeignKey("kpi_metrics.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=True, index=True)
    department_code = Column(String(64), nullable=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    fact_value = Column(Numeric(14, 4), nullable=False)
    status = Column(KPI_RESULT_STATUS, nullable=False, default="draft")
    source = Column(KPI_RESULT_SOURCE, nullable=False, default="manual")
    comment = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    metric = relationship("KpiMetric", back_populates="results")
    restaurant = relationship("Restaurant")
    position = relationship("Position")
    employee = relationship("User", foreign_keys=[employee_id])
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])

    __table_args__ = (
        UniqueConstraint(
            "metric_id",
            "restaurant_id",
            "department_code",
            "position_id",
            "employee_id",
            "period_start",
            "period_end",
            name="uq_kpi_results_scope_period",
        ),
        Index(
            "ix_kpi_results_scope",
            "metric_id",
            "restaurant_id",
            "position_id",
            "employee_id",
        ),
        Index(
            "ix_kpi_results_metric_status_period",
            "metric_id",
            "status",
            "period_start",
            "period_end",
        ),
    )


class KpiPlanFact(Base):
    __tablename__ = "kpi_plan_facts"

    id = Column(Integer, primary_key=True)
    metric_id = Column(Integer, ForeignKey("kpi_metrics.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    plan_value = Column(Numeric(14, 4), nullable=True)
    fact_value = Column(Numeric(14, 4), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    metric = relationship("KpiMetric", back_populates="plan_facts")
    restaurant = relationship("Restaurant")

    __table_args__ = (
        UniqueConstraint(
            "metric_id",
            "restaurant_id",
            "year",
            "month",
            name="uq_kpi_plan_facts_metric_period",
        ),
        Index("ix_kpi_plan_facts_metric_period", "metric_id", "restaurant_id", "year", "month"),
        Index("ix_kpi_plan_facts_year_rest_metric_month", "year", "restaurant_id", "metric_id", "month"),
    )


class KpiPlanPreference(Base):
    __tablename__ = "kpi_plan_preferences"

    id = Column(Integer, primary_key=True)
    metric_id = Column(
        Integer,
        ForeignKey("kpi_metrics.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    plan_mode = Column(String(32), nullable=False, default="shared")
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    is_dynamic = Column(Boolean, nullable=False, default=False)
    selected_month = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    metric = relationship("KpiMetric", back_populates="plan_preference")
    restaurant = relationship("Restaurant")


class KpiMetricGroupPlanFact(Base):
    __tablename__ = "kpi_metric_group_plan_facts"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("kpi_metric_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    plan_value = Column(Numeric(14, 4), nullable=True)
    fact_value = Column(Numeric(14, 4), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    group = relationship("KpiMetricGroup", back_populates="plan_facts")
    restaurant = relationship("Restaurant")

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "restaurant_id",
            "year",
            "month",
            name="uq_kpi_metric_group_plan_facts_group_period",
        ),
        Index(
            "ix_kpi_metric_group_plan_facts_group_period",
            "group_id",
            "restaurant_id",
            "year",
            "month",
        ),
    )


class KpiMetricGroupPlanPreference(Base):
    __tablename__ = "kpi_metric_group_plan_preferences"

    id = Column(Integer, primary_key=True)
    group_id = Column(
        Integer,
        ForeignKey("kpi_metric_groups.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    plan_mode = Column(String(32), nullable=False, default="shared")
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    is_dynamic = Column(Boolean, nullable=False, default=False)
    selected_month = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    group = relationship("KpiMetricGroup", back_populates="plan_preference")
    restaurant = relationship("Restaurant")


class KpiPayoutBatch(Base):
    __tablename__ = "kpi_payout_batches"

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("kpi_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    result_id = Column(Integer, ForeignKey("kpi_results.id", ondelete="SET NULL"), nullable=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(KPI_PAYOUT_STATUS, nullable=False, default="draft")
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    posted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    rule = relationship("KpiRule")
    result = relationship("KpiResult")
    restaurant = relationship("Restaurant")
    position = relationship("Position")
    created_by = relationship("User", foreign_keys=[created_by_id])
    posted_by = relationship("User", foreign_keys=[posted_by_id])
    items = relationship("KpiPayoutItem", back_populates="batch", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "ix_kpi_payout_batches_scope_period",
            "restaurant_id",
            "position_id",
            "period_start",
            "period_end",
        ),
        Index(
            "ix_kpi_payout_batches_status_created",
            "status",
            "created_at",
            "id",
        ),
        Index(
            "ix_kpi_payout_batches_created",
            "created_at",
            "id",
        ),
        Index(
            "ix_kpi_payout_batches_status_period",
            "status",
            "period_start",
            "period_end",
        ),
    )


class KpiPayoutItem(Base):
    __tablename__ = "kpi_payout_items"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("kpi_payout_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    base_amount = Column(Numeric(12, 2), nullable=False, default=0)
    bonus_amount = Column(Numeric(12, 2), nullable=False, default=0)
    penalty_amount = Column(Numeric(12, 2), nullable=False, default=0)
    bonus_enabled = Column(Boolean, nullable=False, default=True)
    penalty_enabled = Column(Boolean, nullable=False, default=True)
    manual = Column(Boolean, nullable=False, default=False)
    comment = Column(Text, nullable=True)
    calc_snapshot = Column(JSON, nullable=True)
    bonus_adjustment_id = Column(Integer, ForeignKey("payroll_adjustments.id", ondelete="SET NULL"), nullable=True)
    penalty_adjustment_id = Column(Integer, ForeignKey("payroll_adjustments.id", ondelete="SET NULL"), nullable=True)

    batch = relationship("KpiPayoutBatch", back_populates="items")
    user = relationship("User")
    restaurant = relationship("Restaurant")
    bonus_adjustment = relationship("PayrollAdjustment", foreign_keys=[bonus_adjustment_id])
    penalty_adjustment = relationship("PayrollAdjustment", foreign_keys=[penalty_adjustment_id])

    __table_args__ = (
        UniqueConstraint("batch_id", "user_id", name="uq_kpi_payout_items_batch_user"),
    )
