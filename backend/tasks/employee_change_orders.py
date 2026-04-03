from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy.orm import Session, joinedload

from backend.bd.database import SessionLocal
from backend.bd.models import EmployeeChangeOrder, Position
from backend.services.employee_change_orders import (
    apply_employee_change_order,
    mark_employee_change_order_failed,
)
from backend.tasks.task_locks import try_task_lock
from backend.utils import today_local

logger = logging.getLogger(__name__)

EMPLOYEE_CHANGE_ORDERS_ENABLED = os.getenv("EMPLOYEE_CHANGE_ORDERS_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
EMPLOYEE_CHANGE_ORDERS_POLL_SECONDS = max(
    60, int(os.getenv("EMPLOYEE_CHANGE_ORDERS_POLL_SECONDS", "300"))
)
EMPLOYEE_CHANGE_ORDERS_LOCK_KEY = 810004


def _load_due_order_ids(db: Session, *, limit: int = 100) -> list[int]:
    today = today_local()
    rows = (
        db.query(EmployeeChangeOrder.id)
        .filter(
            EmployeeChangeOrder.status == "pending",
            EmployeeChangeOrder.effective_date <= today,
        )
        .order_by(EmployeeChangeOrder.effective_date.asc(), EmployeeChangeOrder.id.asc())
        .limit(limit)
        .all()
    )
    return [int(row.id) for row in rows]


def _process_due_employee_change_orders(db: Session) -> tuple[int, int]:
    applied = 0
    failed = 0
    order_ids = _load_due_order_ids(db)
    for order_id in order_ids:
        order = (
            db.query(EmployeeChangeOrder)
            .options(
                joinedload(EmployeeChangeOrder.position_new).joinedload(Position.payment_format),
                joinedload(EmployeeChangeOrder.workplace_restaurant_new),
            )
            .filter(EmployeeChangeOrder.id == order_id)
            .first()
        )
        if not order or order.status != "pending":
            continue
        try:
            apply_employee_change_order(db, order)
            db.commit()
            applied += 1
        except Exception as exc:
            db.rollback()
            retry_order = db.query(EmployeeChangeOrder).filter(EmployeeChangeOrder.id == order_id).first()
            if retry_order and retry_order.status == "pending":
                mark_employee_change_order_failed(retry_order, exc)
                db.commit()
                failed += 1
            else:
                db.rollback()
            logger.exception("Failed to apply employee change order %s", order_id)
    return applied, failed


async def employee_change_orders_loop() -> None:
    while True:
        if not EMPLOYEE_CHANGE_ORDERS_ENABLED:
            await asyncio.sleep(3600)
            continue

        try:
            with SessionLocal() as db:
                with try_task_lock(db, EMPLOYEE_CHANGE_ORDERS_LOCK_KEY) as acquired:
                    if not acquired:
                        logger.debug("Skipping employee change order loop: task lock is already held")
                    else:
                        applied, failed = _process_due_employee_change_orders(db)
                        if applied or failed:
                            logger.info(
                                "Employee change orders processed: applied=%s failed=%s",
                                applied,
                                failed,
                            )
        except Exception:
            logger.exception("Employee change orders loop failed")
        await asyncio.sleep(EMPLOYEE_CHANGE_ORDERS_POLL_SECONDS)
