from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy.orm import Session, joinedload

from backend.bd.database import SessionLocal
from backend.bd.models import Position, PositionChangeOrder
from backend.services.position_change_orders import (
    apply_position_change_order,
    mark_position_change_order_failed,
)
from backend.tasks.task_locks import try_task_lock
from backend.utils import today_local

logger = logging.getLogger(__name__)

POSITION_CHANGE_ORDERS_ENABLED = os.getenv("POSITION_CHANGE_ORDERS_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
POSITION_CHANGE_ORDERS_POLL_SECONDS = max(
    60, int(os.getenv("POSITION_CHANGE_ORDERS_POLL_SECONDS", "300"))
)
POSITION_CHANGE_ORDERS_LOCK_KEY = 810005


def _load_due_order_ids(db: Session, *, limit: int = 100) -> list[int]:
    today = today_local()
    rows = (
        db.query(PositionChangeOrder.id)
        .filter(
            PositionChangeOrder.status == "pending",
            PositionChangeOrder.effective_date <= today,
        )
        .order_by(PositionChangeOrder.effective_date.asc(), PositionChangeOrder.id.asc())
        .limit(limit)
        .all()
    )
    return [int(row.id) for row in rows]


def _process_due_position_change_orders(db: Session) -> tuple[int, int]:
    applied = 0
    failed = 0
    order_ids = _load_due_order_ids(db)
    for order_id in order_ids:
        order = (
            db.query(PositionChangeOrder)
            .options(joinedload(PositionChangeOrder.position).joinedload(Position.payment_format))
            .filter(PositionChangeOrder.id == order_id)
            .first()
        )
        if not order or order.status != "pending":
            continue
        try:
            apply_position_change_order(db, order)
            db.commit()
            applied += 1
        except Exception as exc:
            db.rollback()
            retry_order = db.query(PositionChangeOrder).filter(PositionChangeOrder.id == order_id).first()
            if retry_order and retry_order.status == "pending":
                mark_position_change_order_failed(retry_order, exc)
                db.commit()
                failed += 1
            else:
                db.rollback()
            logger.exception("Failed to apply position change order %s", order_id)
    return applied, failed


async def position_change_orders_loop() -> None:
    while True:
        if not POSITION_CHANGE_ORDERS_ENABLED:
            await asyncio.sleep(3600)
            continue

        try:
            with SessionLocal() as db:
                with try_task_lock(db, POSITION_CHANGE_ORDERS_LOCK_KEY) as acquired:
                    if not acquired:
                        logger.debug("Skipping position change order loop: task lock is already held")
                    else:
                        applied, failed = _process_due_position_change_orders(db)
                        if applied or failed:
                            logger.info(
                                "Position change orders processed: applied=%s failed=%s",
                                applied,
                                failed,
                            )
        except Exception:
            logger.exception("Position change orders loop failed")
        await asyncio.sleep(POSITION_CHANGE_ORDERS_POLL_SECONDS)
