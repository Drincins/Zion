from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


def combine_date_time(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)


def overlap_minutes(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> int:
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if end <= start:
        return 0
    return int((end - start).total_seconds() // 60)


def calc_night_minutes(opened_dt: datetime, closed_dt: datetime) -> int:
    total = 0
    day = opened_dt.date()
    last_day = closed_dt.date()
    while day <= last_day:
        night_start = datetime(day.year, day.month, day.day, 0, 0, 0)
        night_end = datetime(day.year, day.month, day.day, 6, 0, 0)
        total += overlap_minutes(opened_dt, closed_dt, night_start, night_end)
        day = day + timedelta(days=1)
    return total


def calc_duration_minutes(opened_dt: datetime, closed_dt: datetime) -> int:
    return int((closed_dt - opened_dt).total_seconds() // 60)


MONEY_QUANT = Decimal("0.01")


def _dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def calc_attendance_pay(
    *,
    rate,
    calculation_mode: Optional[str],
    duration_minutes: Optional[int],
    night_minutes: Optional[int],
    hours_per_shift: Optional[Decimal],
    monthly_shift_norm: Optional[Decimal],
    night_bonus_enabled: bool,
    night_bonus_percent,
) -> Decimal:
    """Calculate pay for a single attendance record."""
    rate_dec = _dec(rate)
    hours = _dec(duration_minutes or 0) / Decimal(60)
    night_hours = _dec(night_minutes or 0) / Decimal(60)

    pay = Decimal("0")

    if calculation_mode == "hourly":
        pay = rate_dec * hours
    elif calculation_mode == "fixed":
        pay = Decimal("0")  # фикс не размазываем по сменам
    elif calculation_mode == "shift_norm":
        hps = hours_per_shift or Decimal("0")
        norm = monthly_shift_norm or Decimal("0")
        if hps > 0 and norm > 0:
            pay = rate_dec * (hours / (hps * norm))

    pay = pay.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    if night_bonus_enabled and _dec(night_bonus_percent) > 0 and night_hours > 0:
        night_bonus = (rate_dec * night_hours * (_dec(night_bonus_percent) / Decimal("100"))).quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
        pay += night_bonus

    return pay.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
