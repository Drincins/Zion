from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.bd.database import SessionLocal
from backend.bd.models import Attendance, Position
from backend.services.attendance_calculations import (
    combine_date_time,
    calc_duration_minutes,
    calc_night_minutes,
    calc_attendance_pay,
)
from backend.utils import now_local

logger = logging.getLogger(__name__)
AUTO_CLOSE_THRESHOLD = timedelta(hours=24)


def close_stale_attendances(db: Session, now: datetime) -> int:
    position_cache: dict[int, Position] = {}
    rows = (
        db.query(Attendance)
        .filter(Attendance.close_date.is_(None), Attendance.close_time.is_(None))
        .all()
    )
    closed = 0
    for attendance in rows:
        opened_dt = combine_date_time(attendance.open_date, attendance.open_time)
        if now - opened_dt >= AUTO_CLOSE_THRESHOLD:
            closed_dt = opened_dt + AUTO_CLOSE_THRESHOLD
            attendance.close_date = closed_dt.date()
            attendance.close_time = closed_dt.time()
            attendance.duration_minutes = calc_duration_minutes(opened_dt, closed_dt)
            attendance.night_minutes = calc_night_minutes(opened_dt, closed_dt)
            position = None
            if attendance.position_id:
                position = position_cache.get(attendance.position_id)
                if position is None:
                    position = db.query(Position).get(attendance.position_id)
                    if position:
                        position_cache[position.id] = position
            payment_format = getattr(position, "payment_format", None)
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
            closed += 1
    if closed:
        db.commit()
    else:
        db.rollback()
    return closed


async def attendance_auto_close_loop(interval_seconds: int = 300) -> None:
    while True:
        try:
            with SessionLocal() as db:
                now = now_local().replace(tzinfo=None)
                closed = close_stale_attendances(db, now)
                if closed:
                    logger.info("Auto-closed %s stale attendances", closed)
        except Exception:
            logger.exception("Failed to auto-close attendances")
        await asyncio.sleep(interval_seconds)
