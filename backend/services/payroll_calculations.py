from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from backend.bd.models import Position, User

MONEY_QUANT = Decimal("0.01")


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def resolve_rate(
    user: User,
    position: Optional[Position],
    payment_mode: Optional[str],
    *,
    stats_rate: Optional[Decimal] = None,
) -> Decimal:
    """
    Resolve the rate exactly as in payroll statements.

    Notes:
    - fixed/оклад: user.rate -> position.rate -> attendance.rate
    - other modes: attendance.rate -> position.rate -> user.rate (only for the main position)
    - individual_rate is intentionally ignored (like in payroll exports).
    """
    if payment_mode == "fixed":
        if getattr(user, "rate", None) is not None:
            return _decimal(user.rate)
        if getattr(position, "rate", None) is not None:
            return _decimal(position.rate)
        if stats_rate is not None:
            return _decimal(stats_rate)
        return Decimal("0")

    if stats_rate is not None:
        return _decimal(stats_rate)
    if getattr(position, "rate", None) is not None:
        return _decimal(position.rate)
    position_id = getattr(position, "id", None) if position else None
    if position is None or position_id == getattr(user, "position_id", None):
        if getattr(user, "rate", None) is not None:
            return _decimal(user.rate)
    return Decimal("0")


def calc_amounts(
    *,
    rate: Decimal,
    payment_mode: Optional[str],
    fact_hours: Decimal,
    hours_per_shift: Optional[Decimal],
    monthly_shift_norm: Optional[Decimal],
    night_hours: Decimal,
    night_bonus_enabled: bool,
    night_bonus_percent: Decimal,
    salary_factor: Decimal = Decimal("1"),
) -> tuple[Decimal, Optional[Decimal], Decimal, Decimal]:
    """
    Calculate payroll base amounts:
    - base_amount: base salary amount (without night bonus)
    - fact_shifts: worked shifts (if shift_norm and hours_per_shift is set)
    - night_bonus: night bonus amount
    - hours_total: "Итого за часы" (base_amount + night_bonus)
    """
    fact_shifts: Optional[Decimal] = None
    base_amount = Decimal("0")
    if payment_mode == "hourly":
        base_amount = rate * fact_hours
    elif payment_mode == "fixed":
        base_amount = rate * salary_factor
    elif payment_mode == "shift_norm":
        hps = hours_per_shift or Decimal("0")
        norm = monthly_shift_norm or Decimal("0")
        if hps > 0:
            fact_shifts = fact_hours / hps
        if hps > 0 and norm > 0:
            fact_shifts = fact_shifts or (fact_hours / hps)
            worked_ratio = min(fact_shifts, norm) / norm if norm > 0 else Decimal("0")
            base_amount = rate * worked_ratio
    base_amount = _quantize(base_amount)

    night_bonus = Decimal("0")
    if night_bonus_enabled and night_bonus_percent > 0 and night_hours > 0:
        if payment_mode == "shift_norm":
            hps = hours_per_shift or Decimal("0")
            norm = monthly_shift_norm or Decimal("0")
            if hps > 0 and norm > 0:
                hourly_rate = rate / norm / hps
                night_bonus = _quantize(
                    hourly_rate * night_hours * (night_bonus_percent / Decimal("100"))
                )
        else:
            night_bonus = _quantize(rate * night_hours * (night_bonus_percent / Decimal("100")))

    hours_total = _quantize(base_amount + night_bonus)
    return base_amount, fact_shifts, night_bonus, hours_total

