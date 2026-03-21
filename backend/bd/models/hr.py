"""HR-related models (positions, attendance)."""
from __future__ import annotations

from sqlalchemy import Column, Date, ForeignKey, Index, Integer, Numeric, String, Time, Enum, Boolean
from sqlalchemy.orm import relationship

from backend.bd.database import Base

PAYMENT_CALCULATION_MODE = Enum("hourly", "fixed", "shift_norm", name="payment_calculation_mode")


class PaymentFormat(Base):
    __tablename__ = "payment_formats"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=False, unique=True)
    calculation_mode = Column(PAYMENT_CALCULATION_MODE, nullable=False, default="hourly")


class RestaurantSubdivision(Base):
    __tablename__ = "restaurant_subdivisions"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    is_multi = Column(Boolean, nullable=False, default=False)

    positions = relationship("Position", back_populates="restaurant_subdivision")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=True, unique=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    rate = Column(Numeric(10, 2), nullable=True)
    payment_format_id = Column(Integer, ForeignKey("payment_formats.id", ondelete="RESTRICT"), nullable=True)
    parent_id = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)
    hierarchy_level = Column(Integer, nullable=False, default=0)
    hours_per_shift = Column(Numeric(6, 2), nullable=True)
    monthly_shift_norm = Column(Numeric(6, 2), nullable=True)
    restaurant_subdivision_id = Column(
        Integer,
        ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    night_bonus_enabled = Column(Boolean, nullable=False, default=False)
    night_bonus_percent = Column(Numeric(5, 2), nullable=False, default=0)

    role = relationship("Role", backref="positions")
    parent = relationship("Position", remote_side=[id], backref="children")
    payment_format = relationship("PaymentFormat")
    restaurant_subdivision = relationship("RestaurantSubdivision", back_populates="positions")
    users = relationship("User", back_populates="position")
    attendances = relationship("Attendance", back_populates="position")
    permission_links = relationship(
        "PositionPermission",
        back_populates="position",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    permissions = relationship(
        "Permission",
        secondary="position_permissions",
        viewonly=True,
        lazy="selectin",
    )
    training_requirements = relationship(
        "PositionTrainingRequirement",
        back_populates="position",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_positions_role_id", "role_id"),
        Index("ix_positions_payment_format_id", "payment_format_id"),
        Index("ix_positions_parent_id", "parent_id"),
        Index("ix_positions_restaurant_subdivision_id", "restaurant_subdivision_id"),
    )

    @property
    def permission_codes(self) -> list[str]:
        """Return normalized permission codes assigned directly to the position."""
        def _collect(perms) -> set[str]:
            collected: set[str] = set()
            for permission in perms or []:
                raw = getattr(permission, "api_router", None) or getattr(permission, "code", None)
                if not raw:
                    continue
                normalized = raw.strip().lower()
                if normalized:
                    collected.add(normalized)
            return collected

        codes: set[str] = set()
        codes.update(_collect(self.permissions))
        return sorted(codes)


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True)
    rate = Column(Numeric(10, 2), nullable=True)
    pay_amount = Column(Numeric(12, 2), nullable=True)
    open_date = Column(Date, nullable=False)
    open_time = Column(Time, nullable=False)
    close_date = Column(Date, nullable=True)
    close_time = Column(Time, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    night_minutes = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="attendances")
    position = relationship("Position", back_populates="attendances")
    restaurant = relationship("Restaurant", back_populates="attendances")

    __table_args__ = (
        Index("ix_attendances_user_id", "user_id"),
        Index("ix_attendances_restaurant_id", "restaurant_id"),
        Index("ix_attendances_position_id", "position_id"),
        Index("ix_attendances_open_date_user", "open_date", "user_id"),
        Index("ix_attendances_open_date_position", "open_date", "position_id"),
    )
