from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from backend.bd.models import Restaurant

SYNC_APPLICATION_NAME_PREFIX = "zion_sync"


def normalize_iiko_source_token(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().rstrip("/").casefold()


def restaurant_iiko_source_key(restaurant: Restaurant) -> Optional[str]:
    server = normalize_iiko_source_token(getattr(restaurant, "server", None))
    login = normalize_iiko_source_token(getattr(restaurant, "iiko_login", None))
    password_sha1 = normalize_iiko_source_token(getattr(restaurant, "iiko_password_sha1", None))
    if not server or not login or not password_sha1:
        return None
    return f"{server}|{login}|{password_sha1}"


def sales_sync_lock_key(restaurant: Restaurant) -> tuple[int, str]:
    source_key = restaurant_iiko_source_key(restaurant) or f"restaurant:{int(restaurant.id)}"
    digest = hashlib.sha1(source_key.encode("utf-8")).digest()
    lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
    return lock_key, source_key


def normalize_sync_actor(value: Optional[str]) -> str:
    raw = str(value or "system").strip()
    if not raw:
        return "system"
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in (":", "-", "_"))
    if not cleaned:
        return "system"
    return cleaned[:20]


def build_sales_sync_application_name(restaurant: Restaurant, *, sync_actor: Optional[str] = None) -> str:
    source_key = restaurant_iiko_source_key(restaurant) or f"restaurant:{int(restaurant.id)}"
    source_hash = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:10]
    actor = normalize_sync_actor(sync_actor)
    value = f"{SYNC_APPLICATION_NAME_PREFIX} r={int(restaurant.id)} a={actor} s={source_hash}"
    return value[:63]


def parse_sales_sync_application_name(value: Any) -> Optional[Dict[str, Any]]:
    text = str(value or "").strip()
    prefix = f"{SYNC_APPLICATION_NAME_PREFIX} "
    if not text.startswith(prefix):
        return None
    payload = text[len(prefix):]
    parts = [chunk for chunk in payload.split(" ") if chunk]
    parsed: Dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        parsed[key.strip()] = val.strip()
    restaurant_id_raw = parsed.get("r")
    try:
        restaurant_id = int(restaurant_id_raw) if restaurant_id_raw is not None else None
    except Exception:
        restaurant_id = None
    return {
        "restaurant_id": restaurant_id,
        "actor": parsed.get("a"),
        "source_hash": parsed.get("s"),
        "raw": text,
    }


def set_sales_sync_application_name(
    db: Session,
    restaurant: Restaurant,
    *,
    sync_actor: Optional[str] = None,
) -> str:
    app_name = build_sales_sync_application_name(restaurant, sync_actor=sync_actor)
    db.execute(sa.text("SET application_name = :app_name"), {"app_name": app_name})
    return app_name


def reset_sales_sync_application_name(db: Session) -> None:
    try:
        db.execute(sa.text("SET application_name = DEFAULT"))
        db.commit()
    except Exception:
        db.rollback()


def acquire_sales_sync_lock(
    db: Session,
    restaurant: Restaurant,
    *,
    wait_seconds: float = 0.0,
) -> tuple[bool, int, str, float]:
    lock_key, source_key = sales_sync_lock_key(restaurant)
    wait_limit = max(0.0, float(wait_seconds or 0.0))
    started_at = time.monotonic()
    if wait_limit <= 0:
        acquired = db.execute(
            sa.text("SELECT pg_try_advisory_lock(:lock_key)"),
            {"lock_key": int(lock_key)},
        ).scalar()
        return bool(acquired), int(lock_key), source_key, max(0.0, time.monotonic() - started_at)

    timeout_ms = max(100, int(wait_limit * 1000))
    try:
        db.execute(sa.text("SET LOCAL lock_timeout = :timeout"), {"timeout": f"{timeout_ms}ms"})
        db.execute(
            sa.text("SELECT pg_advisory_lock(:lock_key)"),
            {"lock_key": int(lock_key)},
        )
        return True, int(lock_key), source_key, max(0.0, time.monotonic() - started_at)
    except DBAPIError as exc:
        db.rollback()
        text = str(getattr(exc, "orig", exc) or exc).casefold()
        if "lock timeout" in text:
            return False, int(lock_key), source_key, max(0.0, time.monotonic() - started_at)
        raise


def release_sales_sync_lock(db: Session, lock_key: int) -> None:
    try:
        db.execute(
            sa.text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": int(lock_key)},
        )
        db.commit()
    except Exception:
        db.rollback()


def build_sync_source_groups(restaurants: List[Restaurant]) -> Dict[str, List[Restaurant]]:
    grouped: Dict[str, List[Restaurant]] = {}
    for restaurant in restaurants:
        key = restaurant_iiko_source_key(restaurant)
        if not key:
            continue
        grouped.setdefault(key, []).append(restaurant)
    for key, rows in grouped.items():
        grouped[key] = sorted(rows, key=lambda row: int(row.id))
    return grouped


def build_sync_source_conflict_map(restaurants: List[Restaurant]) -> Dict[int, Dict[str, Any]]:
    grouped = build_sync_source_groups(restaurants)

    conflicts: Dict[int, Dict[str, Any]] = {}
    for group in grouped.values():
        if len(group) <= 1:
            continue
        primary = group[0]
        related = [
            f"#{int(row.id)} {row.name}"
            for row in group
        ]
        for row in group[1:]:
            conflicts[int(row.id)] = {
                "primary_id": int(primary.id),
                "primary_name": primary.name,
                "related": related,
            }
    return conflicts
