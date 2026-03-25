from __future__ import annotations

import asyncio
import logging
import os
from datetime import date as date_cls
from datetime import timedelta
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.bd.database import SessionLocal
from backend.bd.iiko_sales import IikoSalesSyncSetting
from backend.bd.models import Restaurant
from backend.routers.iiko_sales import (
    _sync_sales_orders_and_items_resilient,
)
from backend.services.iiko_sales_sync_runtime import (
    build_sync_source_conflict_map as _build_sync_source_conflict_map,
    build_sync_source_groups as _build_sync_source_groups,
    restaurant_iiko_source_key as _restaurant_iiko_source_key,
)
from backend.tasks.task_locks import try_task_lock
from backend.utils import now_local

logger = logging.getLogger(__name__)

SYNC_ENABLED = os.getenv("IIKO_SALES_AUTO_SYNC_ENABLED", "true").lower() in ("1", "true", "yes", "on")
POLL_SECONDS = max(15, int(os.getenv("IIKO_SALES_AUTO_SYNC_POLL_SECONDS", "60")))
IIKO_SALES_AUTO_SYNC_LOCK_KEY = 810003


def _parse_time_to_minutes(value: Optional[str], fallback: str) -> int:
    text = str(value or "").strip() or fallback
    if len(text) != 5 or text[2] != ":":
        text = fallback
    try:
        hours = int(text[:2])
        minutes = int(text[3:5])
    except Exception:
        text = fallback
        hours = int(text[:2])
        minutes = int(text[3:5])

    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        hours = int(fallback[:2])
        minutes = int(fallback[3:5])
    return hours * 60 + minutes


def _resolve_due_scope(now_value, settings: IikoSalesSyncSetting) -> Optional[Tuple[str, int]]:
    now_minutes = now_value.hour * 60 + now_value.minute
    today = now_value.date()

    weekly_enabled = bool(settings.weekly_sync_enabled)
    weekly_weekday = int(settings.weekly_sync_weekday or 0)
    weekly_time_minutes = _parse_time_to_minutes(settings.weekly_sync_time, "08:00")
    weekly_due = (
        weekly_enabled
        and today.weekday() == weekly_weekday
        and now_minutes >= weekly_time_minutes
        and settings.last_weekly_run_on != today
    )
    if weekly_due:
        return "weekly", int(settings.weekly_lookback_days or 0)

    daily_time_minutes = _parse_time_to_minutes(settings.daily_sync_time, "07:00")
    daily_due = now_minutes >= daily_time_minutes and settings.last_daily_run_on != today
    if daily_due:
        return "daily", int(settings.daily_lookback_days or 0)
    return None


def _build_sync_window(today: date_cls, lookback_days: int) -> tuple[str, str]:
    safe_lookback = max(0, int(lookback_days))
    from_date = (today - timedelta(days=safe_lookback)).isoformat()
    to_date = today.isoformat()
    return from_date, to_date


def _apply_sync_mark(
    settings: IikoSalesSyncSetting,
    *,
    scope: str,
    is_success: bool,
    error_text: Optional[str],
) -> None:
    now_value = now_local()
    today = now_value.date()

    settings.last_sync_at = now_value
    settings.last_sync_scope = scope
    settings.last_sync_status = "ok" if is_success else "error"
    settings.last_sync_error = None if is_success else str(error_text or "")[:1000]

    if scope == "daily":
        settings.last_daily_run_on = today
    elif scope == "weekly":
        settings.last_weekly_run_on = today

    if is_success:
        settings.last_successful_sync_at = now_value


def _run_due_sales_syncs(db: Session) -> None:
    rows = (
        db.query(IikoSalesSyncSetting, Restaurant)
        .join(Restaurant, Restaurant.id == IikoSalesSyncSetting.restaurant_id)
        .filter(
            IikoSalesSyncSetting.auto_sync_enabled.is_(True),
            Restaurant.server.isnot(None),
            Restaurant.iiko_login.isnot(None),
            Restaurant.iiko_password_sha1.isnot(None),
        )
        .order_by(Restaurant.id.asc())
        .all()
    )
    if not rows:
        return

    restaurants = [restaurant for _settings, restaurant in rows]
    source_groups = _build_sync_source_groups(restaurants)
    source_conflicts = _build_sync_source_conflict_map(restaurants)
    now_value = now_local()
    today = now_value.date()

    for settings, restaurant in rows:
        due = _resolve_due_scope(now_value, settings)
        if not due:
            continue

        scope, lookback_days = due
        conflict = source_conflicts.get(int(restaurant.id))
        if conflict:
            _apply_sync_mark(
                settings,
                scope=scope,
                is_success=False,
                error_text=(
                    f"Source conflict: sync allowed via "
                    f"#{conflict.get('primary_id')} ({conflict.get('primary_name')})"
                ),
            )
            db.commit()
            continue

        from_date, to_date = _build_sync_window(today, lookback_days)
        source_key = _restaurant_iiko_source_key(restaurant)
        strict_source_routing = bool(source_key and len(source_groups.get(source_key, [])) > 1)

        try:
            result = _sync_sales_orders_and_items_resilient(
                db,
                restaurant,
                from_date,
                to_date,
                strict_source_routing=strict_source_routing,
                sync_actor="auto",
            )
            _apply_sync_mark(settings, scope=scope, is_success=True, error_text=None)
            db.commit()
            logger.info(
                "Auto sales sync (%s) done for restaurant %s: orders=%s, items=%s",
                scope,
                restaurant.id,
                result.get("orders"),
                result.get("items"),
            )
        except Exception as exc:
            db.rollback()
            if isinstance(exc, HTTPException) and int(getattr(exc, "status_code", 0)) == 409:
                # Source is busy right now. Keep task due and retry on next poll cycle.
                logger.info(
                    "Auto sales sync (%s) deferred for restaurant %s: source busy",
                    scope,
                    restaurant.id,
                )
                continue
            retry_settings = (
                db.query(IikoSalesSyncSetting)
                .filter(IikoSalesSyncSetting.restaurant_id == restaurant.id)
                .first()
            )
            if retry_settings:
                _apply_sync_mark(
                    retry_settings,
                    scope=scope,
                    is_success=False,
                    error_text=str(exc),
                )
                db.commit()
            logger.exception(
                "Auto sales sync (%s) failed for restaurant %s",
                scope,
                restaurant.id,
            )


async def iiko_sales_auto_sync_loop() -> None:
    while True:
        if not SYNC_ENABLED:
            await asyncio.sleep(3600)
            continue

        try:
            with SessionLocal() as db:
                with try_task_lock(db, IIKO_SALES_AUTO_SYNC_LOCK_KEY) as acquired:
                    if not acquired:
                        logger.debug("Skipping sales auto sync loop: task lock is already held")
                    else:
                        _run_due_sales_syncs(db)
        except Exception:
            logger.exception("Sales auto sync loop failed")
        await asyncio.sleep(POLL_SECONDS)
