from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session, joinedload

from backend.bd.models import User, Position

logger = logging.getLogger(__name__)


def _month_bounds(day: date) -> tuple[date, date]:
    start = date(day.year, day.month, 1)
    if day.month == 12:
        end = date(day.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(day.year, day.month + 1, 1) - timedelta(days=1)
    return start, end


def recalc_salary_for_user_month(
    db: Session,
    user_id: int,
    ref_date: date,
    *,
    calculated_by_id: int | None = None,
) -> None:
    """
    Recalculate salary results for the month of ref_date for a specific user.
    Silently logs and returns on errors to avoid breaking attendance edits.
    """
    try:
        from backend.routers.payroll import _recalculate_salary_for_user
    except Exception:  # pragma: no cover - defensive import
        logger.exception("Payroll module unavailable, skip salary recalculation")
        return

    start, end = _month_bounds(ref_date)
    user = (
        db.query(User)
        .options(
            joinedload(User.position).joinedload(Position.payment_format),
            joinedload(User.position).joinedload(Position.restaurant_subdivision),
            joinedload(User.company),
            joinedload(User.restaurants),
        )
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        logger.warning("User %s not found for salary recalculation", user_id)
        return

    try:
        _recalculate_salary_for_user(db, user, start, end, calculated_by_id)
        db.commit()
    except Exception:
        logger.exception(
            "Failed to recalculate salary for user %s period %s - %s", user_id, start, end
        )
