"""Shared helpers for applying employee-related changes to attendances."""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.bd.models import Attendance, Position, Restaurant
from backend.services.attendance_calculations import calc_attendance_pay


def recalculate_attendance_pay(attendance: Attendance, db: Session) -> None:
    position = attendance.position
    if position is None and attendance.position_id:
        position = (
            db.query(Position)
            .options(joinedload(Position.payment_format))
            .filter(Position.id == attendance.position_id)
            .first()
        )

    payment_format = getattr(position, "payment_format", None) if position else None
    calc_mode = getattr(payment_format, "calculation_mode", None) if payment_format else None
    hours_per_shift = getattr(position, "hours_per_shift", None) if position else None
    monthly_shift_norm = getattr(position, "monthly_shift_norm", None) if position else None
    night_bonus_enabled = bool(getattr(position, "night_bonus_enabled", False)) if position else False
    night_bonus_percent = getattr(position, "night_bonus_percent", None) if position else None

    attendance.pay_amount = calc_attendance_pay(
        rate=attendance.rate,
        calculation_mode=calc_mode,
        duration_minutes=attendance.duration_minutes,
        night_minutes=attendance.night_minutes,
        hours_per_shift=hours_per_shift,
        monthly_shift_norm=monthly_shift_norm,
        night_bonus_enabled=night_bonus_enabled,
        night_bonus_percent=night_bonus_percent,
    )


def apply_employee_updates_to_attendances(
    *,
    db: Session,
    user_id: int,
    date_from: date,
    date_to: date | None = None,
    position_changed: bool,
    restaurant_changed: bool,
    rate_changed: bool,
    position: Position | None,
    restaurant: Restaurant | None,
    rate: Optional[float],
) -> int:
    if not (position_changed or restaurant_changed or rate_changed):
        return 0

    query = (
        db.query(Attendance)
        .options(
            joinedload(Attendance.position).joinedload(Position.payment_format),
            joinedload(Attendance.restaurant),
        )
        .filter(
            Attendance.user_id == user_id,
            Attendance.open_date >= date_from,
        )
    )
    if date_to is not None:
        query = query.filter(Attendance.open_date <= date_to)
    attendances = query.all()

    updated_count = 0
    for attendance in attendances:
        touched = False

        if position_changed:
            attendance.position = position
            attendance.position_id = position.id if position else None
            touched = True

        if restaurant_changed:
            attendance.restaurant = restaurant
            attendance.restaurant_id = restaurant.id if restaurant else None
            touched = True

        if rate_changed:
            attendance.rate = rate
            touched = True

        if not touched:
            continue

        if position_changed or rate_changed:
            if attendance.close_date and attendance.close_time and attendance.duration_minutes is not None:
                recalculate_attendance_pay(attendance, db)
            else:
                attendance.pay_amount = None

        updated_count += 1

    return updated_count
