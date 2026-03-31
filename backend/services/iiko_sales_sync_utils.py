from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.exc import DBAPIError, DisconnectionError, OperationalError
from sqlalchemy.orm import Session

from backend.bd.models import Restaurant
from backend.services.iiko_api import to_iso_date

SYNC_APPLICATION_NAME_PREFIX = "zion_sync"
DEFAULT_SALES_SYNC_CHUNK_DAYS = 3
DEFAULT_SALES_SYNC_RETRY_COUNT = 4
DEFAULT_SALES_SYNC_RETRY_BASE_SECONDS = 2.0
DEFAULT_SALES_SYNC_RETRY_MAX_SECONDS = 20.0
DEFAULT_SALES_SYNC_LOCK_WAIT_SECONDS = 300.0


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


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))


def hash_payload(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def parse_iso_date(value: Optional[str]) -> Optional[datetime.date]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def sync_sales_window_bounds(from_date: str, to_date: str) -> tuple[Any, Any]:
    start_date = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_date = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date()
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    return start_date, end_date + timedelta(days=1)


def read_positive_int_env(name: str, default: int) -> int:
    raw = str(os.getenv(name, str(default))).strip()
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default


def read_positive_float_env(name: str, default: float) -> float:
    raw = str(os.getenv(name, str(default))).strip()
    try:
        value = float(raw)
    except Exception:
        return default
    return value if value > 0 else default


def build_sales_sync_windows(from_date: str, to_date: str) -> List[tuple[str, str]]:
    start_date, end_exclusive = sync_sales_window_bounds(from_date, to_date)
    end_date = end_exclusive - timedelta(days=1)
    chunk_days = read_positive_int_env("IIKO_SALES_SYNC_CHUNK_DAYS", DEFAULT_SALES_SYNC_CHUNK_DAYS)

    windows: List[tuple[str, str]] = []
    cursor = start_date
    while cursor <= end_date:
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), end_date)
        windows.append((cursor.isoformat(), chunk_end.isoformat()))
        cursor = chunk_end + timedelta(days=1)
    return windows


def is_retriable_sales_sync_error(exc: Exception) -> bool:
    if isinstance(exc, HTTPException):
        return int(exc.status_code) in {408, 425, 429, 500, 502, 503, 504}
    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    if isinstance(exc, (OperationalError, DisconnectionError)):
        return True
    if isinstance(exc, DBAPIError):
        if bool(getattr(exc, "connection_invalidated", False)):
            return True
        text = str(getattr(exc, "orig", exc) or exc).casefold()
        retry_markers = (
            "server closed the connection unexpectedly",
            "terminating connection due administrator command",
            "could not connect to server",
            "connection reset by peer",
            "connection refused",
            "ssl syserror",
            "deadlock detected",
        )
        return any(marker in text for marker in retry_markers)
    return False


def compact_error_text(value: Any, *, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def extract_sync_error_text(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, str):
            return compact_error_text(detail)
        try:
            return compact_error_text(json.dumps(detail, ensure_ascii=False))
        except Exception:
            return compact_error_text(detail)

    if isinstance(exc, requests.exceptions.HTTPError):
        response = getattr(exc, "response", None)
        status_code = int(getattr(response, "status_code", 0) or 0)
        body_text = compact_error_text(getattr(response, "text", "") or "")
        if status_code and body_text:
            return f"HTTP {status_code}: {body_text}"
        if status_code:
            return f"HTTP {status_code}"
        return compact_error_text(exc)

    if isinstance(exc, DBAPIError):
        return compact_error_text(getattr(exc, "orig", exc) or exc)

    return compact_error_text(exc)


def build_sales_sync_window_error_detail(
    exc: Exception,
    *,
    window_from: str,
    window_to: str,
    windows_done: int,
    windows_total: int,
) -> str:
    if window_from == window_to:
        window_text = f"в дате {window_from}"
    else:
        window_text = f"в периоде {window_from}..{window_to}"
    progress_text = f"Успешно обработано окон: {windows_done} из {windows_total}."
    reason_text = extract_sync_error_text(exc) or "неизвестная ошибка"
    return f"Ошибка синхронизации {window_text}: {reason_text}. {progress_text}"


def merge_sales_sync_chunk_result(target: Dict[str, Any], chunk: Dict[str, Any]) -> None:
    target["orders"] += int(chunk.get("orders") or 0)
    target["items"] += int(chunk.get("items") or 0)
    target["payment_methods"] += int(chunk.get("payment_methods") or 0)
    target["non_cash_types"] += int(chunk.get("non_cash_types") or 0)
    target["mapped_orders"] += int(chunk.get("mapped_orders") or 0)
    target["unmapped_orders"] += int(chunk.get("unmapped_orders") or 0)
    target["routing_conflicts"] += int(chunk.get("routing_conflicts") or 0)

    samples = chunk.get("routing_conflict_samples") or []
    if isinstance(samples, list):
        remain = max(0, 30 - len(target["routing_conflict_samples"]))
        if remain:
            target["routing_conflict_samples"].extend(samples[:remain])

    target["location_mappings"] = max(
        int(target.get("location_mappings") or 0),
        int(chunk.get("location_mappings") or 0),
    )
    target["cleanup"]["deleted_orders"] += int(
        (chunk.get("cleanup") or {}).get("deleted_orders") or 0
    )
    target["cleanup"]["deleted_items"] += int(
        (chunk.get("cleanup") or {}).get("deleted_items") or 0
    )
