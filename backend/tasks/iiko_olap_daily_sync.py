from __future__ import annotations

import asyncio
import logging
import os
from datetime import date as date_cls
from datetime import timedelta

from sqlalchemy.orm import Session

from backend.bd.database import SessionLocal
from backend.bd.models import Restaurant
from backend.routers.iiko_olap_product import sync_olap_sales_full
from backend.tasks.task_locks import try_task_lock
from backend.utils import now_local

logger = logging.getLogger(__name__)

SYNC_HOUR = int(os.getenv("IIKO_OLAP_SYNC_HOUR", "7"))
SYNC_MINUTE = int(os.getenv("IIKO_OLAP_SYNC_MINUTE", "0"))
SYNC_DAYS_BACK = int(os.getenv("IIKO_OLAP_SYNC_DAYS_BACK", "1"))
SYNC_ENABLED = os.getenv("IIKO_OLAP_SYNC_ENABLED", "true").lower() in ("1", "true", "yes", "on")
IIKO_OLAP_DAILY_SYNC_LOCK_KEY = 810002


def _next_run(now):
    target = now.replace(hour=SYNC_HOUR, minute=SYNC_MINUTE, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return target


def _sync_for_date(db: Session, target_date: date_cls) -> None:
    restaurants = (
        db.query(Restaurant)
        .filter(
            Restaurant.server.isnot(None),
            Restaurant.iiko_login.isnot(None),
            Restaurant.iiko_password_sha1.isnot(None),
        )
        .all()
    )
    for restaurant in restaurants:
        try:
            res = sync_olap_sales_full(
                db,
                restaurant,
                target_date.isoformat(),
                target_date.isoformat(),
            )
            logger.info(
                "OLAP raw sync done for restaurant %s (%s): inserted=%s updated=%s skipped=%s",
                restaurant.id,
                target_date,
                res.get("inserted_raw"),
                res.get("updated_raw"),
                res.get("skipped_raw"),
            )
        except Exception:
            db.rollback()
            logger.exception(
                "OLAP full sync failed for restaurant %s (%s)",
                restaurant.id,
                target_date,
            )


async def iiko_olap_daily_sync_loop() -> None:
    while True:
        if not SYNC_ENABLED:
            await asyncio.sleep(3600)
            continue
        now = now_local()
        next_run = _next_run(now)
        sleep_seconds = max(1.0, (next_run - now).total_seconds())
        await asyncio.sleep(sleep_seconds)

        target_date = now_local().date() - timedelta(days=SYNC_DAYS_BACK)
        try:
            with SessionLocal() as db:
                with try_task_lock(db, IIKO_OLAP_DAILY_SYNC_LOCK_KEY) as acquired:
                    if not acquired:
                        logger.info("Skipping OLAP daily sync: task lock is already held")
                    else:
                        _sync_for_date(db, target_date)
        except Exception:
            logger.exception("OLAP daily sync loop failed")
