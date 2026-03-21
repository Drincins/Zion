"""Payroll domain models."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.bd.database import Base

PAYROLL_ADJUSTMENT_KIND = Enum("accrual", "deduction", name="payroll_adjustment_kind")
PAYROLL_ADVANCE_STATUS = Enum("draft", "review", "confirmed", "ready", "posted", name="payroll_advance_status")
PAYROLL_STATEMENT_KIND = Enum("advance", "salary", name="payroll_statement_kind")


class PayrollAdjustmentType(Base):
    __tablename__ = "payroll_adjustment_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    kind = Column(PAYROLL_ADJUSTMENT_KIND, nullable=False, default="accrual")
    show_in_report = Column(Boolean, nullable=False, default=False, server_default="false")
    is_advance = Column(Boolean, nullable=False, default=False, server_default="false")

    adjustments = relationship(
        "PayrollAdjustment",
        back_populates="adjustment_type",
        cascade="all, delete-orphan",
    )


class PayrollAdjustment(Base):
    __tablename__ = "payroll_adjustments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    adjustment_type_id = Column(Integer, ForeignKey("payroll_adjustment_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    date = Column(Date, nullable=False)
    responsible_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    comment = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="payroll_adjustments")
    responsible = relationship("User", foreign_keys=[responsible_id], back_populates="payroll_adjustments_entered")
    adjustment_type = relationship("PayrollAdjustmentType", back_populates="adjustments")
    restaurant = relationship("Restaurant")

    __table_args__ = (
        Index("ix_payroll_adjustments_user_date", "user_id", "date"),
        Index(
            "ix_payroll_adjustments_rest_type_date_user",
            "restaurant_id",
            "adjustment_type_id",
            "date",
            "user_id",
        ),
        Index("ix_payroll_adjustments_responsible_date", "responsible_id", "date"),
    )


class PayrollSalaryResult(Base):
    __tablename__ = "payroll_salary_results"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    base_amount = Column(Numeric(12, 2), nullable=False, default=0)
    adjustments_amount = Column(Numeric(12, 2), nullable=False, default=0)
    gross_amount = Column(Numeric(12, 2), nullable=False, default=0)
    details = Column(Text, nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    calculated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="salary_results")
    calculated_by = relationship("User", foreign_keys=[calculated_by_id])

    __table_args__ = (
        UniqueConstraint("user_id", "period_start", "period_end", name="uq_payroll_salary_result_user_period"),
        Index("ix_payroll_salary_results_period_user", "period_start", "period_end", "user_id"),
    )


class PayrollAdvanceStatement(Base):
    __tablename__ = "payroll_advance_statements"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=True)
    status = Column(PAYROLL_ADVANCE_STATUS, nullable=False, default="draft")
    statement_kind = Column(PAYROLL_STATEMENT_KIND, nullable=False, default="advance", server_default="advance")
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    subdivision_id = Column(Integer, ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"), nullable=True, index=True)
    salary_percent = Column(Numeric(5, 2), nullable=True)
    fixed_only = Column(Boolean, nullable=False, default=True)
    filters = Column(JSON, nullable=True)
    adjustments_snapshot = Column(JSON, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    posted_at = Column(DateTime(timezone=True), nullable=True)

    restaurant = relationship("Restaurant")
    subdivision = relationship("RestaurantSubdivision")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="advance_statements_created")
    updated_by = relationship("User", foreign_keys=[updated_by_id], back_populates="advance_statements_updated")
    items = relationship("PayrollAdvanceItem", back_populates="statement", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_payroll_advance_statements_rest_created", "restaurant_id", "created_at"),
        Index("ix_payroll_advance_statements_status_created", "status", "created_at"),
        Index("ix_payroll_advance_statements_creator_created", "created_by_id", "created_at"),
    )


class PayrollAdvanceItem(Base):
    __tablename__ = "payroll_advance_items"

    id = Column(Integer, primary_key=True)
    statement_id = Column(
        Integer,
        ForeignKey("payroll_advance_statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True, index=True)
    staff_code = Column(String, nullable=True)
    full_name = Column(String, nullable=False)
    position_name = Column(String, nullable=True)
    calculated_amount = Column(Numeric(12, 2), nullable=False, default=0)
    final_amount = Column(Numeric(12, 2), nullable=False, default=0)
    manual = Column(Boolean, nullable=False, default=False)
    comment = Column(Text, nullable=True)
    accrual_amount = Column(Numeric(12, 2), nullable=False, default=0)
    deduction_amount = Column(Numeric(12, 2), nullable=False, default=0)
    calc_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    statement = relationship("PayrollAdvanceStatement", back_populates="items")
    user = relationship("User", foreign_keys=[user_id])
    restaurant = relationship("Restaurant", foreign_keys=[restaurant_id])
    position = relationship("Position", foreign_keys=[position_id])
    fact_hours = Column(Numeric(10, 2), nullable=False, default=0)
    night_hours = Column(Numeric(10, 2), nullable=False, default=0)
    rate = Column(Numeric(12, 2), nullable=True)

    __table_args__ = (
        Index("ix_payroll_advance_items_statement_user", "statement_id", "user_id"),
    )


class PayrollAdvanceConsolidatedStatement(Base):
    __tablename__ = "payroll_advance_consolidated_statements"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=True)
    # List[int] with PayrollAdvanceStatement ids in the desired order.
    statement_ids = Column(JSON, nullable=False)
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    created_by = relationship("User", foreign_keys=[created_by_id])


class LaborSummarySettings(Base):
    __tablename__ = "labor_summary_settings"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    include_base_cost = Column(Boolean, nullable=False, default=True, server_default="true")
    include_accrual_cost = Column(Boolean, nullable=False, default=True, server_default="true")
    include_deduction_cost = Column(Boolean, nullable=False, default=True, server_default="true")
    accrual_adjustment_type_ids = Column(JSON, nullable=True)
    deduction_adjustment_type_ids = Column(JSON, nullable=True)
    revenue_real_money_only = Column(Boolean, nullable=False, default=True, server_default="true")
    revenue_exclude_deleted = Column(Boolean, nullable=False, default=True, server_default="true")
    revenue_amount_mode = Column(String(32), nullable=False, default="sum_without_discount", server_default="sum_without_discount")
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    company = relationship("Company")
    updated_by = relationship("User", foreign_keys=[updated_by_id])

    __table_args__ = (
        UniqueConstraint("company_id", name="uq_labor_summary_settings_company"),
    )
