"""Scheduled employee change orders."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.orm import relationship

from backend.bd.database import Base

EMPLOYEE_CHANGE_ORDER_STATUS = Enum(
    "pending",
    "applied",
    "cancelled",
    "failed",
    name="employee_change_order_status",
)


class EmployeeChangeOrder(Base):
    __tablename__ = "employee_change_orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    effective_date = Column(Date, nullable=False)
    status = Column(
        EMPLOYEE_CHANGE_ORDER_STATUS,
        nullable=False,
        default="pending",
        server_default="pending",
    )

    change_position = Column(Boolean, nullable=False, default=False, server_default="false")
    position_id_new = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)

    change_workplace_restaurant = Column(Boolean, nullable=False, default=False, server_default="false")
    workplace_restaurant_id_new = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
    )

    change_rate = Column(Boolean, nullable=False, default=False, server_default="false")
    rate_new = Column(Numeric(10, 2), nullable=True)

    change_individual_rate = Column(Boolean, nullable=False, default=False, server_default="false")
    individual_rate_new = Column(Numeric(10, 2), nullable=True)

    apply_to_attendances = Column(Boolean, nullable=False, default=False, server_default="false")
    comment = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    position_new = relationship("Position", foreign_keys=[position_id_new])
    workplace_restaurant_new = relationship("Restaurant", foreign_keys=[workplace_restaurant_id_new])

    __table_args__ = (
        Index("ix_employee_change_orders_status_effective", "status", "effective_date"),
        Index("ix_employee_change_orders_user_status_effective", "user_id", "status", "effective_date"),
        Index("ix_employee_change_orders_created_at_id", "created_at", "id"),
    )

    @property
    def created_by_name(self) -> Optional[str]:
        user = self.created_by
        if not user:
            return None
        parts = [user.last_name, user.first_name, user.middle_name]
        name = " ".join(part for part in parts if part)
        return name or user.username

    @property
    def cancelled_by_name(self) -> Optional[str]:
        user = self.cancelled_by
        if not user:
            return None
        parts = [user.last_name, user.first_name, user.middle_name]
        name = " ".join(part for part in parts if part)
        return name or user.username

    @property
    def position_name_new(self) -> Optional[str]:
        position = self.position_new
        return getattr(position, "name", None) if position else None

    @property
    def workplace_restaurant_name_new(self) -> Optional[str]:
        restaurant = self.workplace_restaurant_new
        return getattr(restaurant, "name", None) if restaurant else None
