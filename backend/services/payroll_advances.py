"""Helpers for payroll advance statements."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional, Sequence

from sqlalchemy.orm import Session, joinedload

from backend.bd.models import (
    PaymentFormat,
    Position,
    Restaurant,
    User,
)
from backend.services.payroll_export import (
    UserPayrollRow,
    _calc_amounts,
    _collect_adjustments,
    _collect_attendance,
    _decimal,
    _resolve_rate,
    resolve_payroll_export_bounds,
)


@dataclass
class AdvanceCalcResult:
    rows: list[UserPayrollRow]
    used_accrual_type_ids: list[int]
    used_deduction_type_ids: list[int]
    adjustments_snapshot: list[dict]


def _month_bounds(day: date) -> tuple[date, date]:
    start = date(day.year, day.month, 1)
    end = date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])
    return start, end


def _format_fire_date(fire_date: date) -> str:
    return fire_date.strftime("%d.%m.%Y")


def _merge_fire_comment(existing: Optional[str], fire_date: Optional[date]) -> Optional[str]:
    if not fire_date:
        return existing
    auto_comment = f"Уволен {_format_fire_date(fire_date)}"
    current = (existing or "").strip()
    if not current:
        return auto_comment
    if auto_comment in current:
        return current
    return f"{current} | {auto_comment}"


def _row_sort_key(row: UserPayrollRow) -> tuple[str, str, str, str]:
    pos_name = getattr(row.position, "name", "") or ""
    last = row.user.last_name or ""
    first = row.user.first_name or ""
    username = row.user.username or ""
    return (pos_name.lower(), last.lower(), first.lower(), username.lower())


def calculate_advance_rows(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    company_id: Optional[int],
    restaurant_id: Optional[int],
    subdivision_id: Optional[int],
    user_ids: Optional[Sequence[int]] = None,
    salary_percent: Optional[float] = None,
    fixed_only: bool = True,
) -> AdvanceCalcResult:
    """
    Build payroll rows for the given period.
    This mirrors build_payroll_report but returns structured rows instead of Excel.
    """
    start, end = resolve_payroll_export_bounds(period=None, date_from=date_from, date_to=date_to)
    if date_from.year == date_to.year and date_from.month == date_to.month:
        month_start, month_end = _month_bounds(date_from)
    else:
        month_start, month_end = date_from, date_to
    salary_factor = (
        Decimal(str(salary_percent)) / Decimal("100") if salary_percent is not None else Decimal("1")
    )

    requested_user_ids: Optional[list[int]] = None
    if user_ids is not None:
        requested_user_ids = list({int(uid) for uid in user_ids})
        if not requested_user_ids:
            return AdvanceCalcResult(
                rows=[],
                used_accrual_type_ids=[],
                used_deduction_type_ids=[],
                adjustments_snapshot=[],
            )

    attendance = _collect_attendance(
        db,
        start,
        end,
        company_id=company_id,
        restaurant_id=restaurant_id,
        subdivision_id=subdivision_id,
        user_ids=requested_user_ids,
    )
    attendance_user_ids = set(attendance.keys())

    adj_by_user, adj_type_map, adj_rows = _collect_adjustments(
        db,
        start,
        end,
        requested_user_ids,
        company_id=company_id,
        restaurant_id=restaurant_id,
        subdivision_id=subdivision_id,
    )
    used_type_ids = sorted(adj_type_map.keys(), key=lambda i: adj_type_map[i].name.lower() if adj_type_map[i].name else "")
    used_accrual_type_ids = [t_id for t_id in used_type_ids if adj_type_map[t_id].kind == "accrual"]
    used_deduction_type_ids = [t_id for t_id in used_type_ids if adj_type_map[t_id].kind == "deduction"]
    adjustments_snapshot: list[dict] = []
    for adj in adj_rows:
        adj_type = adj_type_map.get(adj.adjustment_type_id)
        if not adj_type:
            continue
        adjustments_snapshot.append(
            {
                "user_id": adj.user_id,
                "adjustment_type_id": adj.adjustment_type_id,
                "type_name": adj_type.name,
                "kind": adj_type.kind,
                "amount": float(adj.amount or 0),
                "date": adj.date.isoformat() if adj.date else None,
                "comment": adj.comment,
            }
        )

    fixed_user_ids: set[int] = set()
    fixed_q = (
        db.query(User.id)
        .join(Position, Position.id == User.position_id)
        .join(PaymentFormat, PaymentFormat.id == Position.payment_format_id)
    )
    if company_id:
        fixed_q = fixed_q.filter(User.company_id == company_id)
    if restaurant_id:
        fixed_q = fixed_q.filter(User.workplace_restaurant_id == restaurant_id)
    if subdivision_id:
        fixed_q = fixed_q.filter(Position.restaurant_subdivision_id == subdivision_id)
    if requested_user_ids is not None:
        fixed_q = fixed_q.filter(User.id.in_(requested_user_ids))
    if fixed_only:
        fixed_q = fixed_q.filter(PaymentFormat.calculation_mode == "fixed")
    fixed_user_ids = {row[0] for row in fixed_q.distinct().all()}

    candidate_user_ids = set(attendance_user_ids) | set(adj_by_user.keys()) | fixed_user_ids
    if requested_user_ids:
        candidate_user_ids.update(requested_user_ids)
    if not candidate_user_ids:
        return AdvanceCalcResult(
            rows=[],
            used_accrual_type_ids=used_accrual_type_ids,
            used_deduction_type_ids=used_deduction_type_ids,
            adjustments_snapshot=adjustments_snapshot,
        )

    for uid in candidate_user_ids:
        attendance.setdefault(uid, [])

    users = (
        db.query(User)
        .options(
            joinedload(User.position).joinedload(Position.payment_format),
            joinedload(User.position).joinedload(Position.restaurant_subdivision),
            joinedload(User.company),
            joinedload(User.workplace_restaurant),
            joinedload(User.restaurants),
        )
        .filter(User.id.in_(candidate_user_ids) if candidate_user_ids else False)
        .all()
    )
    user_map = {u.id: u for u in users}

    restaurant_ids: set[int] = set()
    if restaurant_id:
        restaurant_ids.add(restaurant_id)
    for stats_list in attendance.values():
        for stats in stats_list:
            rid = stats.get("restaurant_id")
            if rid:
                restaurant_ids.add(rid)
    for user in users:
        rid = getattr(user, "workplace_restaurant_id", None)
        if rid:
            restaurant_ids.add(rid)
    restaurant_map = {}
    if restaurant_ids:
        restaurant_map = {
            r.id: r for r in db.query(Restaurant).filter(Restaurant.id.in_(restaurant_ids)).all()
        }

    position_ids: set[int] = set()
    for stats_list in attendance.values():
        for stats in stats_list:
            if stats.get("position_id"):
                position_ids.add(stats["position_id"])
    position_map = {}
    if position_ids:
        position_map = {
            p.id: p
            for p in db.query(Position)
            .options(joinedload(Position.payment_format), joinedload(Position.restaurant_subdivision))
            .filter(Position.id.in_(position_ids))
            .all()
        }

    results: list[UserPayrollRow] = []

    requested_user_id_set = set(requested_user_ids or [])

    def _passes_filters(user: User, stats: dict) -> bool:
        if company_id and getattr(user, "company_id", None) != company_id:
            return False
        if restaurant_id:
            has_attendance_in_restaurant = stats.get("restaurant_id") == restaurant_id
            has_workplace_in_restaurant = getattr(user, "workplace_restaurant_id", None) == restaurant_id
            if not has_attendance_in_restaurant and not has_workplace_in_restaurant and user.id not in requested_user_id_set:
                return False
        if subdivision_id:
            pos = getattr(user, "position", None)
            if getattr(pos, "restaurant_subdivision_id", None) != subdivision_id:
                return False
        return True

    for user_id in candidate_user_ids:
        user = user_map.get(user_id)
        if not user:
            continue

        stats_list = attendance.get(user_id, [])
        adj_map_full = adj_by_user.get(user_id, {})
        requested = user_id in requested_user_id_set
        has_attendance = user_id in attendance_user_ids
        has_adjustments = bool(adj_map_full)
        has_activity = has_attendance or has_adjustments

        is_fixed_user = user_id in fixed_user_ids

        fired = bool(getattr(user, "fired", False))
        fire_date = getattr(user, "fire_date", None)
        fired_in_month = bool(fired and fire_date and month_start <= fire_date <= month_end)
        # Fired employees should still be included if they have attendance/adjustments in the period
        # (or were explicitly requested). Otherwise, skip them.
        if fired and not fired_in_month and not has_activity and not requested:
            continue

        if not stats_list and not adj_map_full and not requested and not is_fixed_user:
            continue
        if restaurant_id and adj_map_full and not stats_list:
            stats_list = [
                {
                    "position_id": getattr(user, "position_id", None),
                    "rate": None,
                    "duration_minutes": 0,
                    "night_minutes": 0,
                    "restaurant_id": restaurant_id,
                    "adjustments_only": True,
                }
            ]
        if not stats_list:
            fallback_restaurant = getattr(user, "workplace_restaurant_id", None)
            if fallback_restaurant is None and user.restaurants:
                first_restaurant = next((r for r in user.restaurants if getattr(r, "id", None) is not None), None)
                if first_restaurant:
                    fallback_restaurant = first_restaurant.id
            stats_list = [
                {
                    "position_id": getattr(user, "position_id", None),
                    "rate": None,
                    "duration_minutes": 0,
                    "night_minutes": 0,
                    "restaurant_id": fallback_restaurant,
                }
            ]

        main_position_id = getattr(user, "position_id", None)
        adjust_position_id = None
        if main_position_id is not None and any(
            stats.get("position_id") == main_position_id for stats in stats_list
        ):
            adjust_position_id = main_position_id
        elif stats_list:
            adjust_position_id = stats_list[0].get("position_id")
        adjustments_applied = False

        for stats in stats_list:
            if not _passes_filters(user, stats):
                continue

            pos_id = stats.get("position_id")
            position = None
            if pos_id:
                position = position_map.get(pos_id) or (getattr(user, "position", None) if pos_id == main_position_id else None)
            else:
                position = getattr(user, "position", None)

            company = getattr(user, "company", None)
            restaurant_obj = None
            if restaurant_id:
                restaurant_obj = restaurant_map.get(restaurant_id)
            if restaurant_obj is None and stats.get("restaurant_id"):
                rid = stats["restaurant_id"]
                restaurant_obj = restaurant_map.get(rid)
            if restaurant_obj is None:
                workplace_id = getattr(user, "workplace_restaurant_id", None)
                if workplace_id:
                    restaurant_obj = restaurant_map.get(workplace_id) or getattr(user, "workplace_restaurant", None)
            if restaurant_obj is None and user.restaurants:
                restaurant_obj = user.restaurants[0]

            minutes = stats.get("duration_minutes", 0) or 0
            night_minutes = stats.get("night_minutes", 0) or 0
            adjustments_only = bool(stats.get("adjustments_only"))
            stats_restaurant_id = stats.get("restaurant_id")
            workplace_restaurant_id = getattr(user, "workplace_restaurant_id", None)
            is_workplace_row = (
                workplace_restaurant_id is not None
                and stats_restaurant_id == workplace_restaurant_id
            )

            payment_format = getattr(position, "payment_format", None) if position else None
            payment_mode = getattr(payment_format, "calculation_mode", None)

            # For restaurant-scoped advances, fixed-salary base applies only to the
            # workplace restaurant; other restaurants should show adjustments only.
            if (
                payment_mode == "fixed"
                and restaurant_id
                and workplace_restaurant_id
                and workplace_restaurant_id != restaurant_id
            ):
                adjustments_only = True

            if fixed_only and payment_mode != "fixed":
                continue

            if fired_in_month and not has_activity and payment_mode != "fixed":
                continue

            # Fixed-salary base should only appear in the workplace restaurant row.
            if adjustments_only and payment_mode == "fixed" and is_workplace_row:
                adjustments_only = False

            factor_for_calc = salary_factor if payment_mode != "fixed" else Decimal("1")

            if adjustments_only:
                fact_hours = Decimal("0")
                night_hours = Decimal("0")
                rate = Decimal("0")
                base_amount = Decimal("0")
                night_bonus = Decimal("0")
                hours_total = Decimal("0")
                fact_shifts = None
            else:
                fact_hours = Decimal(minutes) / Decimal(60) if minutes else Decimal("0")
                night_hours = Decimal(night_minutes) / Decimal(60) if night_minutes else Decimal("0")

                hours_per_shift = (
                    _decimal(getattr(position, "hours_per_shift", None))
                    if position and getattr(position, "hours_per_shift", None)
                    else None
                )
                monthly_shift_norm = (
                    _decimal(getattr(position, "monthly_shift_norm", None))
                    if position and getattr(position, "monthly_shift_norm", None)
                    else None
                )
                night_enabled = bool(getattr(position, "night_bonus_enabled", False)) if position else False
                night_percent = _decimal(getattr(position, "night_bonus_percent", None)) if position else Decimal("0")
                rate = _resolve_rate(
                    user,
                    position,
                    payment_mode,
                    stats_rate=stats.get("rate"),
                )

                base_amount, fact_shifts, night_bonus, hours_total = _calc_amounts(
                    rate=rate,
                    payment_mode=payment_mode,
                    fact_hours=fact_hours,
                    hours_per_shift=hours_per_shift,
                    monthly_shift_norm=monthly_shift_norm,
                    night_hours=night_hours,
                    night_bonus_enabled=night_enabled,
                    night_bonus_percent=night_percent,
                    salary_factor=factor_for_calc,
                )

            adj_map = {}
            if not adjustments_applied and (pos_id == adjust_position_id or adjust_position_id is None):
                adj_map = adj_map_full
                adjustments_applied = True

            total_adjustments = Decimal("0")
            total_accruals = Decimal("0")
            total_deductions = Decimal("0")
            for type_id, value in adj_map.items():
                total_adjustments += value
                if value >= 0:
                    total_accruals += value
                else:
                    total_deductions += -value
            if payment_mode == "fixed":
                total_to_pay = (hours_total * salary_factor) + total_accruals - total_deductions
            else:
                total_to_pay = hours_total + total_adjustments
            total_to_pay = total_to_pay.quantize(Decimal("0.01"))

            subdivision_name = getattr(position.restaurant_subdivision, "name", None) if position else None
            results.append(
                UserPayrollRow(
                    user=user,
                    company=company,
                    restaurant=restaurant_obj,
                    subdivision_name=subdivision_name,
                    position=position,
                    rate=rate,
                    fact_hours=fact_hours,
                    fact_shifts=fact_shifts,
                    night_hours=night_hours,
                    base_amount=base_amount,
                    night_bonus=night_bonus,
                    hours_total=hours_total,
                    adjustments_by_type=adj_map,
                    total_adjustments=total_adjustments,
                    total_accruals=total_accruals,
                    total_deductions=total_deductions,
                    total_to_pay=total_to_pay,
                    adjustments_only=adjustments_only,
                )
            )

    results.sort(key=_row_sort_key)
    return AdvanceCalcResult(
        rows=results,
        used_accrual_type_ids=used_accrual_type_ids,
        used_deduction_type_ids=used_deduction_type_ids,
        adjustments_snapshot=adjustments_snapshot,
    )


def payroll_row_to_item_payload(row: UserPayrollRow) -> dict:
    full_name = f"{row.user.last_name or ''} {row.user.first_name or ''}".strip() or row.user.username
    restaurant_id = getattr(row.restaurant, "id", None)
    position_id = getattr(row.position, "id", None)
    position_name = getattr(row.position, "name", None)
    payment_format = getattr(row.position, "payment_format", None) if row.position else None
    adjustments_by_type = {
        str(type_id): float(amount)
        for type_id, amount in (row.adjustments_by_type or {}).items()
    }
    return {
        "user_id": row.user.id,
        "restaurant_id": restaurant_id,
        "position_id": position_id,
        "staff_code": getattr(row.user, "staff_code", None),
        "full_name": full_name,
        "position_name": position_name,
        "fact_hours": float(row.fact_hours),
        "night_hours": float(row.night_hours),
        "rate": float(row.rate) if row.rate is not None else None,
        "accrual_amount": float(row.total_accruals),
        "deduction_amount": float(row.total_deductions),
        "calculated_amount": float(row.total_to_pay),
        "final_amount": float(row.total_to_pay),
        "manual": False,
        "comment": _merge_fire_comment(None, row.user.fire_date) if getattr(row.user, "fired", False) else None,
        "calc_snapshot": {
            "base_amount": float(row.base_amount),
            "night_bonus": float(row.night_bonus),
            "hours_total": float(row.hours_total),
            "fact_shifts": float(row.fact_shifts) if row.fact_shifts is not None else None,
            "payment_mode": getattr(payment_format, "calculation_mode", None),
            "payment_format_name": getattr(payment_format, "name", None),
            "adjustments_by_type": adjustments_by_type,
        },
    }
