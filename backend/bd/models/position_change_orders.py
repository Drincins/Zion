"""Scheduled position change orders."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.orm import relationship

from backend.bd.database import Base

POSITION_CHANGE_ORDER_STATUS = Enum(
    "pending",
    "applied",
    "cancelled",
    "failed",
    name="position_change_order_status",
)


class PositionChangeOrder(Base):
    __tablename__ = "position_change_orders"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False)
    effective_date = Column(Date, nullable=False)
    status = Column(
        POSITION_CHANGE_ORDER_STATUS,
        nullable=False,
        default="pending",
        server_default="pending",
    )

    rate_new = Column(Numeric(10, 2), nullable=False)
    apply_to_attendances = Column(Boolean, nullable=False, default=False, server_default="false")
    comment = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    position = relationship("Position", foreign_keys=[position_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])

    __table_args__ = (
        Index("ix_position_change_orders_status_effective", "status", "effective_date"),
        Index("ix_position_change_orders_position_status_effective", "position_id", "status", "effective_date"),
        Index("ix_position_change_orders_created_at_id", "created_at", "id"),
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
    def position_name(self) -> Optional[str]:
        return getattr(self.position, "name", None) if self.position else None
