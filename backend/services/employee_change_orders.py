"""Scheduled employee change order application helpers."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.bd.models import EmployeeChangeOrder, Position, Restaurant, User
from backend.services.employee_attendance_updates import apply_employee_updates_to_attendances
from backend.services.employee_changes import format_ref, log_employee_changes
from backend.utils import now_local


def _normalize_decimal(value) -> Optional[str]:
    if value is None:
        return None
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01")))
    except Exception:
        return str(value)


def apply_employee_change_order(db: Session, order: EmployeeChangeOrder) -> None:
    if order.status != "pending":
        raise ValueError("Only pending employee change orders can be applied")

    user = (
        db.query(User)
        .options(
            joinedload(User.position).joinedload(Position.payment_format),
            joinedload(User.workplace_restaurant),
        )
        .filter(User.id == order.user_id)
        .first()
    )
    if not user:
        raise ValueError("Employee not found")

    original_position = user.position
    original_workplace = user.workplace_restaurant
    original_rate = user.rate
    original_individual_rate = user.individual_rate

    next_position = original_position
    if order.change_position:
        if order.position_id_new:
            next_position = (
                db.query(Position)
                .options(joinedload(Position.payment_format))
                .filter(Position.id == order.position_id_new)
                .first()
            )
            if not next_position:
                raise ValueError("Target position not found")
        else:
            next_position = None
        user.position = next_position
        user.role = next_position.role if next_position else None

    next_workplace = original_workplace
    if order.change_workplace_restaurant:
        if order.workplace_restaurant_id_new:
            next_workplace = (
                db.query(Restaurant)
                .filter(Restaurant.id == order.workplace_restaurant_id_new)
                .first()
            )
            if not next_workplace:
                raise ValueError("Target workplace restaurant not found")
        else:
            next_workplace = None
        user.workplace_restaurant = next_workplace

    if order.change_rate:
        user.rate = order.rate_new

    if order.change_individual_rate:
        if order.individual_rate_new is None:
            user.individual_rate = None
            if order.change_rate:
                user.rate = order.rate_new
            elif order.change_position:
                user.rate = next_position.rate if next_position and next_position.rate is not None else None
            else:
                current_position = user.position
                user.rate = current_position.rate if current_position and current_position.rate is not None else None
        else:
            user.individual_rate = order.individual_rate_new
            user.rate = order.individual_rate_new
    elif order.change_position and not order.change_rate:
        if user.individual_rate is not None:
            user.rate = user.individual_rate
        else:
            user.rate = next_position.rate if next_position and next_position.rate is not None else None

    position_changed = getattr(original_position, "id", None) != getattr(user.position, "id", None)
    restaurant_changed = getattr(original_workplace, "id", None) != getattr(user.workplace_restaurant, "id", None)
    rate_changed = _normalize_decimal(original_rate) != _normalize_decimal(user.rate)
    individual_rate_changed = _normalize_decimal(original_individual_rate) != _normalize_decimal(user.individual_rate)

    if order.apply_to_attendances and (position_changed or restaurant_changed or rate_changed):
        apply_employee_updates_to_attendances(
            db=db,
            user_id=user.id,
            date_from=order.effective_date,
            position_changed=position_changed,
            restaurant_changed=restaurant_changed,
            rate_changed=rate_changed,
            position=user.position,
            restaurant=user.workplace_restaurant,
            rate=user.rate,
        )

    changes: list[dict] = []
    if position_changed:
        changes.append(
            {
                "field": "position",
                "old_value": format_ref(original_position),
                "new_value": format_ref(user.position),
            }
        )
    if restaurant_changed:
        changes.append(
            {
                "field": "workplace_restaurant",
                "old_value": format_ref(original_workplace),
                "new_value": format_ref(user.workplace_restaurant),
            }
        )
    if rate_changed:
        changes.append({"field": "rate", "old_value": original_rate, "new_value": user.rate})
    if individual_rate_changed:
        changes.append(
            {
                "field": "individual_rate",
                "old_value": original_individual_rate,
                "new_value": user.individual_rate,
            }
        )

    log_employee_changes(
        db,
        user_id=user.id,
        changed_by_id=order.created_by_id,
        changes=changes,
        source="employee_change_order",
        entity_type="employee_change_order",
        entity_id=order.id,
    )

    order.status = "applied"
    order.applied_at = now_local()
    order.error_message = None


def mark_employee_change_order_failed(order: EmployeeChangeOrder, exc: Exception) -> None:
    order.status = "failed"
    order.error_message = str(exc)[:2000]
