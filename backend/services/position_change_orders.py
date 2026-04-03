"""Scheduled position change order application helpers."""
from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from backend.bd.models import Position, PositionChangeOrder, User
from backend.services.employee_attendance_updates import apply_employee_updates_to_attendances
from backend.utils import now_local


def apply_position_change_order(db: Session, order: PositionChangeOrder) -> None:
    if order.status != "pending":
        raise ValueError("Only pending position change orders can be applied")

    position = (
        db.query(Position)
        .options(joinedload(Position.payment_format))
        .filter(Position.id == order.position_id)
        .first()
    )
    if not position:
        raise ValueError("Position not found")

    position.rate = order.rate_new

    affected_users = (
        db.query(User)
        .options(
            joinedload(User.position).joinedload(Position.payment_format),
            joinedload(User.workplace_restaurant),
        )
        .filter(
            User.position_id == position.id,
            User.individual_rate.is_(None),
        )
        .all()
    )

    for user in affected_users:
        user.rate = position.rate

        if order.apply_to_attendances:
            apply_employee_updates_to_attendances(
                db=db,
                user_id=user.id,
                date_from=order.effective_date,
                position_changed=False,
                restaurant_changed=False,
                rate_changed=True,
                position=user.position,
                restaurant=user.workplace_restaurant,
                rate=user.rate,
            )

    order.status = "applied"
    order.applied_at = now_local()
    order.error_message = None


def mark_position_change_order_failed(order: PositionChangeOrder, exc: Exception) -> None:
    order.status = "failed"
    order.error_message = str(exc)[:2000]
