from __future__ import annotations

import hashlib
import json
import os
import time
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException
import requests
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError, DisconnectionError, OperationalError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.bd.iiko_catalog import IikoProduct
from backend.bd.iiko_sales import (
    IikoSaleItem,
    IikoSaleOrder,
    IikoSalesHallTable,
    IikoSalesLocationMapping,
)
from backend.bd.models import Restaurant, User
from backend.services.iiko_sales_finance_refs import (
    non_cash_limits_query,
    non_cash_types_query,
    payment_methods_query,
    upsert_non_cash_types,
    upsert_payment_methods,
)
from backend.services.iiko_api import get_olap_columns, get_token, post_olap_report, to_iso_date
from backend.services.iiko_sales_layouts import normalize_location_token
from backend.services.iiko_sales_payloads import (
    DISH_WAITER_GROUP_FIELDS,
    extract_dish_waiter_fields,
    extract_non_cash_fields,
    extract_order_guid,
    extract_payment_method_fields,
    select_payment_group_fields,
)
from backend.services.iiko_sales_scope import ensure_user_access_to_restaurant, list_accessible_restaurants
from backend.utils import now_local

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


def _source_scope_filter(model: Any, source_restaurant_id: int):
    return sa.or_(
        model.source_restaurant_id == source_restaurant_id,
        sa.and_(
            model.source_restaurant_id.is_(None),
            model.restaurant_id == source_restaurant_id,
        ),
    )


def replace_sales_window_for_source(
    db: Session,
    *,
    source_restaurant_id: int,
    start_date: Any,
    end_exclusive: Any,
) -> Dict[str, int]:
    item_scope = _source_scope_filter(IikoSaleItem, source_restaurant_id)
    order_scope = _source_scope_filter(IikoSaleOrder, source_restaurant_id)

    deleted_items = (
        db.query(IikoSaleItem)
        .filter(item_scope)
        .filter(IikoSaleItem.open_date >= start_date)
        .filter(IikoSaleItem.open_date < end_exclusive)
        .delete(synchronize_session=False)
    )
    deleted_orders = (
        db.query(IikoSaleOrder)
        .filter(order_scope)
        .filter(IikoSaleOrder.open_date >= start_date)
        .filter(IikoSaleOrder.open_date < end_exclusive)
        .delete(synchronize_session=False)
    )
    return {
        "deleted_orders": int(deleted_orders or 0),
        "deleted_items": int(deleted_items or 0),
    }


def delete_sales_by_source_order_ids(
    db: Session,
    *,
    source_restaurant_id: int,
    iiko_order_ids: List[str],
) -> Dict[str, int]:
    clean_order_ids = sorted({str(value).strip() for value in iiko_order_ids if value is not None and str(value).strip()})
    if not clean_order_ids:
        return {"deleted_orders": 0, "deleted_items": 0}

    order_scope = _source_scope_filter(IikoSaleOrder, source_restaurant_id)
    order_ids_subq = (
        db.query(IikoSaleOrder.id)
        .filter(order_scope)
        .filter(IikoSaleOrder.iiko_order_id.in_(clean_order_ids))
        .subquery()
    )

    deleted_items = (
        db.query(IikoSaleItem)
        .filter(IikoSaleItem.order_id.in_(sa.select(order_ids_subq.c.id)))
        .delete(synchronize_session=False)
    )
    deleted_orders = (
        db.query(IikoSaleOrder)
        .filter(IikoSaleOrder.id.in_(sa.select(order_ids_subq.c.id)))
        .delete(synchronize_session=False)
    )
    return {
        "deleted_orders": int(deleted_orders or 0),
        "deleted_items": int(deleted_items or 0),
    }


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _sum_nullable_numbers(current: Any, incoming: Any) -> Optional[Decimal]:
    left = _to_decimal(current)
    right = _to_decimal(incoming)
    if left is None and right is None:
        return None
    if left is None:
        return right
    if right is None:
        return left
    return left + right


def _resolve_date_field(cols: Dict[str, Any]) -> str:
    return "OpenDate.Typed" if "OpenDate.Typed" in cols else "OpenDate"


def _pick_fields(cols: Dict[str, Any], desired: List[str]) -> List[str]:
    return [field for field in desired if cols.get(field, {}).get("groupingAllowed")]


def _pick_aggs(cols: Dict[str, Any], desired: List[str]) -> List[str]:
    return [field for field in desired if cols.get(field, {}).get("aggregationAllowed")]


def _all_group_fields(cols: Dict[str, Any]) -> List[str]:
    return [field for field, meta in cols.items() if meta.get("groupingAllowed")]


def _all_agg_fields(cols: Dict[str, Any]) -> List[str]:
    return [field for field, meta in cols.items() if meta.get("aggregationAllowed")]


def _load_user_maps(db: Session, *, iiko_ids: set[str], iiko_codes: set[str]) -> tuple[dict[str, int], dict[str, int]]:
    id_map: dict[str, int] = {}
    code_map: dict[str, int] = {}

    if iiko_ids:
        rows = db.query(User.id, User.iiko_id).filter(User.iiko_id.in_(list(iiko_ids))).all()
        for user_id, iiko_id in rows:
            if iiko_id:
                id_map[str(iiko_id)] = int(user_id)

    if iiko_codes:
        rows = db.query(User.id, User.iiko_code).filter(User.iiko_code.in_(list(iiko_codes))).all()
        for user_id, code in rows:
            if code:
                code_map[str(code)] = int(user_id)

    return id_map, code_map


def _load_product_num_map(db: Session, nums: set[str]) -> dict[str, str]:
    if not nums:
        return {}
    rows = db.query(IikoProduct.num, IikoProduct.id).filter(IikoProduct.num.in_(list(nums))).all()
    mapping: dict[str, str] = {}
    for num, product_id in rows:
        if num and product_id:
            mapping[str(num)] = str(product_id)
    return mapping


def _build_department_code_restaurant_map(
    db: Session,
    *,
    company_id: Optional[int],
) -> Dict[str, int]:
    q = db.query(Restaurant.id, Restaurant.department_code).filter(
        Restaurant.department_code.isnot(None)
    )
    if company_id is not None:
        q = q.filter(Restaurant.company_id == company_id)
    else:
        q = q.filter(sa.literal(False))

    by_code: Dict[str, int] = {}
    ambiguous: set[str] = set()

    for restaurant_id, department_code in q.all():
        code_norm = normalize_location_token(department_code)
        if not code_norm:
            continue
        restaurant_id_int = int(restaurant_id)
        current = by_code.get(code_norm)
        if current is None:
            by_code[code_norm] = restaurant_id_int
            continue
        if current != restaurant_id_int:
            ambiguous.add(code_norm)

    for code_norm in ambiguous:
        by_code.pop(code_norm, None)

    return by_code


def sync_payment_methods(
    db: Session,
    restaurant: Restaurant,
    from_date: str,
    to_date: str,
    cols: Dict[str, Any],
    token: str,
) -> int:
    date_field = _resolve_date_field(cols)
    group_fields = select_payment_group_fields(cols)

    if not group_fields:
        return 0

    agg_fields = _pick_aggs(cols, ["DishSumInt", "PayableAmountInt", "fullSum", "DiscountSum"])
    if not agg_fields:
        agg_fields = [name for name, meta in cols.items() if meta.get("aggregationAllowed")]
    if not agg_fields:
        return 0

    resp = post_olap_report(
        restaurant.server,
        token,
        report_type="SALES",
        groups=group_fields,
        aggregates=agg_fields[:1],
        date_field=date_field,
        from_date=from_date,
        to_date=to_date,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:400])

    items = resp.json().get("data", []) or []
    methods: dict[str, str] = {}
    for row in items:
        guid, name = extract_payment_method_fields(row)
        if guid:
            methods[guid] = name or methods.get(guid) or guid

    if not methods:
        return 0

    return upsert_payment_methods(
        db,
        company_id=restaurant.company_id,
        methods=methods,
        updated_at=now_local(),
    )


def sync_sales_orders_and_items(
    db: Session,
    restaurant: Restaurant,
    from_date: str,
    to_date: str,
    *,
    strict_source_routing: bool = False,
    token: Optional[str] = None,
    cols: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not token:
        token = get_token(restaurant.server, restaurant.iiko_login, restaurant.iiko_password_sha1)
    if cols is None:
        cols = get_olap_columns(restaurant.server, token, report_type="SALES")
    date_field = _resolve_date_field(cols)
    payment_group_fields = select_payment_group_fields(cols)
    dish_waiter_group_fields = _pick_fields(cols, DISH_WAITER_GROUP_FIELDS)
    start_date, end_exclusive = sync_sales_window_bounds(from_date, to_date)
    source_restaurant_id = int(restaurant.id)

    required_groups = [
        date_field,
        "UniqOrderId.Id",
        "UniqOrderId",
        "OrderId.Id",
        "OrderId",
        "Order.Id",
        "OrderGUID",
        "OrderGuid",
        "UniqOrderItem.Id",
        "UniqOrderItem",
        "UniqDishId.Id",
        "UniqDishId",
        "OrderNum",
        "OpenTime",
        "CloseTime",
        "Department",
        "TableNum",
        "GuestNum",
        "OrderWaiter.Id",
        "OrderWaiter.Name",
        "Cashier.Id",
        "Cashier.Name",
        "Cashier.Code",
        "AuthUser.Id",
        "AuthUser.Name",
        "DishCode",
        "DishName",
        "DishGroup",
        "DishMeasureUnit",
        "CookingPlace",
        "DishCategory.Id",
        "OrderDeleted",
        "DeletedWithWriteoff",
        "NonCashPaymentType.Id",
        "NonCashPaymentType",
    ]
    group_fields: List[str] = []
    seen_group_fields: set[str] = set()
    for field in required_groups + dish_waiter_group_fields + payment_group_fields + _all_group_fields(cols):
        if field in seen_group_fields:
            continue
        if not cols.get(field, {}).get("groupingAllowed"):
            continue
        seen_group_fields.add(field)
        group_fields.append(field)

    agg_fields = _all_agg_fields(cols)
    if not agg_fields:
        raise HTTPException(status_code=400, detail="No suitable OLAP aggregation fields available for sales sync")

    resp = post_olap_report(
        restaurant.server,
        token,
        report_type="SALES",
        groups=group_fields,
        aggregates=agg_fields,
        date_field=date_field,
        from_date=from_date,
        to_date=to_date,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:400])

    data: List[Dict[str, Any]] = resp.json().get("data", []) or []
    replaced_scope = replace_sales_window_for_source(
        db,
        source_restaurant_id=source_restaurant_id,
        start_date=start_date,
        end_exclusive=end_exclusive,
    )
    if not data:
        return {
            "status": "ok",
            "orders": 0,
            "items": 0,
            "payment_methods": 0,
            "non_cash_types": 0,
            "mapped_orders": 0,
            "unmapped_orders": 0,
            "routing_conflicts": 0,
            "strict_source_routing": bool(strict_source_routing),
            "cleanup": replaced_scope,
        }

    now = now_local()
    company_id = restaurant.company_id

    mappings_q = db.query(IikoSalesLocationMapping).filter(IikoSalesLocationMapping.is_active.is_(True))
    mappings_q = mappings_q.filter(IikoSalesLocationMapping.company_id == company_id)
    mappings_q = mappings_q.filter(
        sa.or_(
            IikoSalesLocationMapping.source_restaurant_id == source_restaurant_id,
            IikoSalesLocationMapping.source_restaurant_id.is_(None),
        )
    )
    mapping_rows = mappings_q.all()
    mapping_rows.sort(
        key=lambda row: (
            row.company_id is None,
            row.source_restaurant_id is None,
        )
    )

    mapping_exact: Dict[tuple[Optional[int], str, str], int] = {}
    mapping_department: Dict[tuple[Optional[int], str], int] = {}
    mapping_exact_ambiguous: set[tuple[Optional[int], str, str]] = set()
    mapping_department_ambiguous: set[tuple[Optional[int], str]] = set()

    def _set_or_mark_ambiguous(store: Dict[Any, int], ambiguous: set[Any], key: Any, value: int) -> None:
        current = store.get(key)
        if current is None:
            store[key] = int(value)
            return
        if int(current) != int(value):
            ambiguous.add(key)

    for mapping in mapping_rows:
        dep_norm = (mapping.department_norm or normalize_location_token(mapping.department)).strip()
        table_norm = (mapping.table_num_norm or normalize_location_token(mapping.table_num)).strip()
        if not dep_norm:
            continue
        source_key = int(mapping.source_restaurant_id) if mapping.source_restaurant_id is not None else None
        target_restaurant_id = int(mapping.target_restaurant_id)
        if table_norm:
            _set_or_mark_ambiguous(
                mapping_exact,
                mapping_exact_ambiguous,
                (source_key, dep_norm, table_norm),
                target_restaurant_id,
            )
        else:
            _set_or_mark_ambiguous(
                mapping_department,
                mapping_department_ambiguous,
                (source_key, dep_norm),
                target_restaurant_id,
            )

    for key in mapping_exact_ambiguous:
        mapping_exact.pop(key, None)
    for key in mapping_department_ambiguous:
        mapping_department.pop(key, None)

    hall_rows_q = db.query(IikoSalesHallTable).filter(IikoSalesHallTable.is_active.is_(True))
    hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.company_id == company_id)
    hall_rows_q = hall_rows_q.filter(
        sa.or_(
            IikoSalesHallTable.source_restaurant_id == source_restaurant_id,
            IikoSalesHallTable.source_restaurant_id.is_(None),
        )
    )
    hall_rows = hall_rows_q.all()
    hall_rows.sort(
        key=lambda row: (
            row.company_id is None,
            row.source_restaurant_id is None,
        )
    )

    hall_exact: Dict[tuple[Optional[int], str, str], int] = {}
    hall_department: Dict[tuple[Optional[int], str], int] = {}
    hall_exact_ambiguous: set[tuple[Optional[int], str, str]] = set()
    hall_department_ambiguous: set[tuple[Optional[int], str]] = set()
    for hall_row in hall_rows:
        dep_norm = (hall_row.department_norm or normalize_location_token(hall_row.department)).strip()
        table_norm = (hall_row.table_num_norm or normalize_location_token(hall_row.table_num)).strip()
        if not dep_norm:
            continue
        source_key = int(hall_row.source_restaurant_id) if hall_row.source_restaurant_id is not None else None
        target_restaurant_id = int(hall_row.restaurant_id)
        if table_norm:
            _set_or_mark_ambiguous(
                hall_exact,
                hall_exact_ambiguous,
                (source_key, dep_norm, table_norm),
                target_restaurant_id,
            )
        else:
            _set_or_mark_ambiguous(
                hall_department,
                hall_department_ambiguous,
                (source_key, dep_norm),
                target_restaurant_id,
            )

    for key in hall_exact_ambiguous:
        hall_exact.pop(key, None)
    for key in hall_department_ambiguous:
        hall_department.pop(key, None)

    department_code_map = _build_department_code_restaurant_map(
        db,
        company_id=company_id,
    )

    mapped_orders = 0
    unmapped_orders = 0
    routing_conflicts = 0
    routing_conflict_samples: List[Dict[str, Optional[str]]] = []

    def resolve_target_restaurant_id(*, department: Any, table_num: Any) -> tuple[int, str]:
        dep_norm = normalize_location_token(department)
        table_norm = normalize_location_token(table_num)
        if dep_norm and table_norm:
            for source_key in (source_restaurant_id, None):
                target = mapping_exact.get((source_key, dep_norm, table_norm))
                if target is not None:
                    return int(target), "mapping_exact"
            for source_key in (source_restaurant_id, None):
                target = hall_exact.get((source_key, dep_norm, table_norm))
                if target is not None:
                    return int(target), "hall_table_exact"
        if dep_norm:
            for source_key in (source_restaurant_id, None):
                target = mapping_department.get((source_key, dep_norm))
                if target is not None:
                    return int(target), "mapping_department"
            for source_key in (source_restaurant_id, None):
                target = hall_department.get((source_key, dep_norm))
                if target is not None:
                    return int(target), "hall_table_department"
            target = department_code_map.get(dep_norm)
            if target is not None:
                return int(target), "department_code"
        return source_restaurant_id, "fallback_source"

    method_names_by_guid: dict[str, str] = {}
    non_cash_names_by_id: dict[str, str] = {}
    dish_nums: set[str] = set()
    waiter_iiko_ids: set[str] = set()
    cashier_iiko_ids: set[str] = set()
    auth_iiko_ids: set[str] = set()
    dish_waiter_iiko_ids: set[str] = set()
    cashier_codes: set[str] = set()
    dish_waiter_codes: set[str] = set()

    for row in data:
        if not row:
            continue
        dish_code = row.get("DishCode")
        if dish_code:
            dish_nums.add(str(dish_code))
        w = row.get("OrderWaiter.Id")
        if w:
            waiter_iiko_ids.add(str(w))
        c = row.get("Cashier.Id")
        if c:
            cashier_iiko_ids.add(str(c))
        a = row.get("AuthUser.Id")
        if a:
            auth_iiko_ids.add(str(a))
        cc = row.get("Cashier.Code")
        if cc:
            cashier_codes.add(str(cc))
        dish_waiter_iiko_id, _dish_waiter_name, dish_waiter_code, _dish_waiter_source = extract_dish_waiter_fields(row)
        if dish_waiter_iiko_id:
            dish_waiter_iiko_ids.add(str(dish_waiter_iiko_id))
        if dish_waiter_code:
            dish_waiter_codes.add(str(dish_waiter_code))
        pay_guid, pay_name = extract_payment_method_fields(row)
        if pay_guid:
            method_names_by_guid[pay_guid] = pay_name or method_names_by_guid.get(pay_guid) or pay_guid
        non_cash_id, non_cash_name = extract_non_cash_fields(row)
        if non_cash_id:
            non_cash_names_by_id[non_cash_id] = non_cash_name or non_cash_names_by_id.get(non_cash_id) or non_cash_id

    iiko_id_map, iiko_code_map = _load_user_maps(
        db,
        iiko_ids=waiter_iiko_ids.union(cashier_iiko_ids).union(auth_iiko_ids).union(dish_waiter_iiko_ids),
        iiko_codes=cashier_codes.union(dish_waiter_codes),
    )
    product_id_by_num = _load_product_num_map(db, dish_nums)

    payment_methods_count = upsert_payment_methods(
        db,
        company_id=company_id,
        methods=method_names_by_guid,
        updated_at=now,
    )
    non_cash_types_count = upsert_non_cash_types(
        db,
        company_id=company_id,
        types_map=non_cash_names_by_id,
        updated_at=now,
    )
    if payment_methods_count == 0:
        payment_methods_count = sync_payment_methods(db, restaurant, from_date, to_date, cols, token)

    orders_by_key: dict[str, Dict[str, Any]] = {}
    for row in data:
        order_guid = extract_order_guid(row)
        if not order_guid:
            continue
        order_guid = str(order_guid)
        if order_guid in orders_by_key:
            continue

        open_date = parse_iso_date((row or {}).get(date_field))
        opened_at = parse_iso_datetime((row or {}).get("OpenTime"))
        closed_at = parse_iso_datetime((row or {}).get("CloseTime"))

        order_waiter_iiko_id = (row or {}).get("OrderWaiter.Id")
        cashier_iiko_id = (row or {}).get("Cashier.Id")
        auth_user_iiko_id = (row or {}).get("AuthUser.Id")
        cashier_code = (row or {}).get("Cashier.Code")

        order_waiter_user_id = iiko_id_map.get(str(order_waiter_iiko_id)) if order_waiter_iiko_id else None
        cashier_user_id = iiko_id_map.get(str(cashier_iiko_id)) if cashier_iiko_id else None
        if cashier_user_id is None and cashier_code:
            cashier_user_id = iiko_code_map.get(str(cashier_code))
        auth_user_id = iiko_id_map.get(str(auth_user_iiko_id)) if auth_user_iiko_id else None
        department_value = (row or {}).get("Department")
        table_num_value = (row or {}).get("TableNum")
        resolved_restaurant_id, routing_strategy = resolve_target_restaurant_id(
            department=department_value,
            table_num=table_num_value,
        )
        if strict_source_routing and routing_strategy == "fallback_source":
            routing_conflicts += 1
            if len(routing_conflict_samples) < 30:
                routing_conflict_samples.append(
                    {
                        "iiko_order_id": order_guid,
                        "department": str(department_value).strip() if department_value is not None else None,
                        "table_num": str(table_num_value).strip() if table_num_value is not None else None,
                    }
                )
            continue

        if routing_strategy != "fallback_source":
            mapped_orders += 1
        else:
            unmapped_orders += 1

        orders_by_key[order_guid] = {
            "company_id": company_id,
            "restaurant_id": resolved_restaurant_id,
            "source_restaurant_id": source_restaurant_id,
            "iiko_order_id": order_guid,
            "order_num": (row or {}).get("OrderNum"),
            "open_date": open_date,
            "opened_at": opened_at,
            "closed_at": closed_at,
            "department": department_value,
            "table_num": table_num_value,
            "guest_num": (row or {}).get("GuestNum"),
            "order_waiter_iiko_id": order_waiter_iiko_id,
            "order_waiter_name": (row or {}).get("OrderWaiter.Name"),
            "cashier_iiko_id": cashier_iiko_id,
            "cashier_code": cashier_code,
            "auth_user_iiko_id": auth_user_iiko_id,
            "order_waiter_user_id": order_waiter_user_id,
            "cashier_user_id": cashier_user_id,
            "auth_user_id": auth_user_id,
            "raw_payload": row,
            "updated_at": now,
        }

    order_payload = list(orders_by_key.values())
    if not order_payload:
        return {
            "status": "ok",
            "orders": 0,
            "items": 0,
            "payment_methods": payment_methods_count,
            "non_cash_types": non_cash_types_count,
            "mapped_orders": int(mapped_orders),
            "unmapped_orders": int(unmapped_orders),
            "routing_conflicts": int(routing_conflicts),
            "routing_conflict_samples": routing_conflict_samples,
            "strict_source_routing": bool(strict_source_routing),
            "location_mappings": len(mapping_rows),
            "cleanup": replaced_scope,
        }

    legacy_cleanup = delete_sales_by_source_order_ids(
        db,
        source_restaurant_id=source_restaurant_id,
        iiko_order_ids=list(orders_by_key.keys()),
    )

    stmt = insert(IikoSaleOrder).values(order_payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["restaurant_id", "iiko_order_id"],
        set_={
            "company_id": stmt.excluded.company_id,
            "source_restaurant_id": stmt.excluded.source_restaurant_id,
            "order_num": stmt.excluded.order_num,
            "open_date": stmt.excluded.open_date,
            "opened_at": stmt.excluded.opened_at,
            "closed_at": stmt.excluded.closed_at,
            "department": stmt.excluded.department,
            "table_num": stmt.excluded.table_num,
            "guest_num": stmt.excluded.guest_num,
            "order_waiter_iiko_id": stmt.excluded.order_waiter_iiko_id,
            "order_waiter_name": stmt.excluded.order_waiter_name,
            "cashier_iiko_id": stmt.excluded.cashier_iiko_id,
            "cashier_code": stmt.excluded.cashier_code,
            "auth_user_iiko_id": stmt.excluded.auth_user_iiko_id,
            "order_waiter_user_id": stmt.excluded.order_waiter_user_id,
            "cashier_user_id": stmt.excluded.cashier_user_id,
            "auth_user_id": stmt.excluded.auth_user_id,
            "raw_payload": stmt.excluded.raw_payload,
            "updated_at": stmt.excluded.updated_at,
        },
    ).returning(IikoSaleOrder.id, IikoSaleOrder.iiko_order_id)
    result = db.execute(stmt)
    order_id_by_guid: dict[str, str] = {str(guid): str(order_id) for order_id, guid in result.fetchall()}

    items_payload_by_key: dict[tuple[str, str], Dict[str, Any]] = {}
    for row in data:
        if not row:
            continue
        order_guid = extract_order_guid(row)
        if not order_guid:
            continue
        order_guid = str(order_guid)
        order_uuid = order_id_by_guid.get(order_guid)
        if not order_uuid:
            continue

        dish_code = row.get("DishCode")
        auth_user_iiko_id = row.get("AuthUser.Id")
        order_restaurant_id = int(orders_by_key.get(order_guid, {}).get("restaurant_id") or source_restaurant_id)

        open_date = parse_iso_date((row or {}).get(date_field))
        line_key = hash_payload(row)
        auth_user_id = iiko_id_map.get(str(auth_user_iiko_id)) if auth_user_iiko_id else None
        product_id = product_id_by_num.get(str(dish_code)) if dish_code else None

        payload_row: Dict[str, Any] = {
            "order_id": order_uuid,
            "company_id": company_id,
            "restaurant_id": order_restaurant_id,
            "source_restaurant_id": source_restaurant_id,
            "open_date": open_date,
            "line_key": line_key,
            "dish_code": dish_code,
            "dish_name": row.get("DishName") or row.get("DishFullName"),
            "dish_group": row.get("DishGroup"),
            "dish_category_id": row.get("DishCategory.Id"),
            "dish_measure_unit": row.get("DishMeasureUnit"),
            "cooking_place": row.get("CookingPlace"),
            "qty": row.get("DishAmountInt"),
            "sum": row.get("DishSumInt"),
            "discount_sum": row.get("DiscountSum"),
            "iiko_product_id": product_id,
            "auth_user_iiko_id": auth_user_iiko_id,
            "auth_user_id": auth_user_id,
            "order_waiter_iiko_id": row.get("OrderWaiter.Id"),
            "cashier_code": row.get("Cashier.Code"),
            "raw_payload": row,
            "updated_at": now,
        }

        dedupe_key = (order_uuid, line_key)
        existing = items_payload_by_key.get(dedupe_key)
        if existing is None:
            items_payload_by_key[dedupe_key] = payload_row
            continue

        existing["qty"] = _sum_nullable_numbers(existing.get("qty"), payload_row.get("qty"))
        existing["sum"] = _sum_nullable_numbers(existing.get("sum"), payload_row.get("sum"))
        existing["discount_sum"] = _sum_nullable_numbers(existing.get("discount_sum"), payload_row.get("discount_sum"))

        for field in (
            "dish_code",
            "dish_name",
            "dish_group",
            "dish_category_id",
            "dish_measure_unit",
            "cooking_place",
            "iiko_product_id",
            "auth_user_iiko_id",
            "auth_user_id",
            "order_waiter_iiko_id",
            "cashier_code",
            "open_date",
        ):
            if existing.get(field) is None and payload_row.get(field) is not None:
                existing[field] = payload_row[field]

        existing["raw_payload"] = payload_row["raw_payload"]
        existing["updated_at"] = payload_row["updated_at"]

    items_payload: List[Dict[str, Any]] = list(items_payload_by_key.values())

    if items_payload:
        it = insert(IikoSaleItem).values(items_payload)
        it = it.on_conflict_do_update(
            index_elements=["order_id", "line_key"],
            set_={
                "dish_code": sa.func.coalesce(IikoSaleItem.dish_code, it.excluded.dish_code),
                "dish_name": sa.func.coalesce(IikoSaleItem.dish_name, it.excluded.dish_name),
                "dish_group": sa.func.coalesce(IikoSaleItem.dish_group, it.excluded.dish_group),
                "dish_category_id": sa.func.coalesce(IikoSaleItem.dish_category_id, it.excluded.dish_category_id),
                "dish_measure_unit": sa.func.coalesce(IikoSaleItem.dish_measure_unit, it.excluded.dish_measure_unit),
                "cooking_place": sa.func.coalesce(IikoSaleItem.cooking_place, it.excluded.cooking_place),
                "open_date": sa.func.coalesce(IikoSaleItem.open_date, it.excluded.open_date),
                "company_id": it.excluded.company_id,
                "restaurant_id": it.excluded.restaurant_id,
                "source_restaurant_id": it.excluded.source_restaurant_id,
                "qty": it.excluded.qty,
                "sum": it.excluded.sum,
                "discount_sum": it.excluded.discount_sum,
                "iiko_product_id": sa.func.coalesce(IikoSaleItem.iiko_product_id, it.excluded.iiko_product_id),
                "auth_user_iiko_id": it.excluded.auth_user_iiko_id,
                "auth_user_id": sa.func.coalesce(IikoSaleItem.auth_user_id, it.excluded.auth_user_id),
                "order_waiter_iiko_id": it.excluded.order_waiter_iiko_id,
                "cashier_code": it.excluded.cashier_code,
                "raw_payload": it.excluded.raw_payload,
                "updated_at": it.excluded.updated_at,
            },
        )
        db.execute(it)

    return {
        "status": "ok",
        "orders": len(order_payload),
        "items": len(items_payload),
        "payment_methods": payment_methods_count,
        "non_cash_types": non_cash_types_count,
        "mapped_orders": int(mapped_orders),
        "unmapped_orders": int(unmapped_orders),
        "routing_conflicts": int(routing_conflicts),
        "routing_conflict_samples": routing_conflict_samples,
        "strict_source_routing": bool(strict_source_routing),
        "location_mappings": len(mapping_rows),
        "cleanup": {
            "deleted_orders": int(replaced_scope.get("deleted_orders", 0)) + int(legacy_cleanup.get("deleted_orders", 0)),
            "deleted_items": int(replaced_scope.get("deleted_items", 0)) + int(legacy_cleanup.get("deleted_items", 0)),
        },
    }


def sync_sales_orders_and_items_resilient(
    db: Session,
    restaurant: Restaurant,
    from_date: str,
    to_date: str,
    *,
    strict_source_routing: bool = False,
    sync_actor: Optional[str] = None,
) -> Dict[str, Any]:
    lock_key: Optional[int] = None
    try:
        set_sales_sync_application_name(db, restaurant, sync_actor=sync_actor)
        lock_wait_seconds = read_positive_float_env(
            "IIKO_SALES_SYNC_LOCK_WAIT_SECONDS",
            DEFAULT_SALES_SYNC_LOCK_WAIT_SECONDS,
        )
        lock_acquired, lock_key, _lock_source, waited_seconds = acquire_sales_sync_lock(
            db,
            restaurant,
            wait_seconds=lock_wait_seconds,
        )
        if not lock_acquired:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Синхронизация уже выполняется для этого iiko-источника. "
                    f"Ожидание в очереди: {waited_seconds:.1f}с."
                ),
            )

        windows = build_sales_sync_windows(from_date, to_date)
        chunk_days = read_positive_int_env("IIKO_SALES_SYNC_CHUNK_DAYS", DEFAULT_SALES_SYNC_CHUNK_DAYS)
        retry_count = read_positive_int_env("IIKO_SALES_SYNC_RETRY_COUNT", DEFAULT_SALES_SYNC_RETRY_COUNT)
        retry_base_seconds = read_positive_float_env(
            "IIKO_SALES_SYNC_RETRY_BASE_SECONDS",
            DEFAULT_SALES_SYNC_RETRY_BASE_SECONDS,
        )
        retry_max_seconds = read_positive_float_env(
            "IIKO_SALES_SYNC_RETRY_MAX_SECONDS",
            DEFAULT_SALES_SYNC_RETRY_MAX_SECONDS,
        )
        token = get_token(restaurant.server, restaurant.iiko_login, restaurant.iiko_password_sha1)
        cols = get_olap_columns(restaurant.server, token, report_type="SALES")

        totals: Dict[str, Any] = {
            "status": "ok",
            "orders": 0,
            "items": 0,
            "payment_methods": 0,
            "non_cash_types": 0,
            "mapped_orders": 0,
            "unmapped_orders": 0,
            "routing_conflicts": 0,
            "routing_conflict_samples": [],
            "strict_source_routing": bool(strict_source_routing),
            "location_mappings": 0,
            "cleanup": {
                "deleted_orders": 0,
                "deleted_items": 0,
            },
            "window_chunk_days": int(chunk_days),
            "windows_total": len(windows),
            "windows_done": 0,
            "lock_waited_seconds": round(float(waited_seconds), 3),
        }

        for window_from, window_to in windows:
            attempt = 0
            token_refresh_attempted = False
            while True:
                try:
                    chunk_result = sync_sales_orders_and_items(
                        db,
                        restaurant,
                        window_from,
                        window_to,
                        strict_source_routing=strict_source_routing,
                        token=token,
                        cols=cols,
                    )
                    db.commit()
                    merge_sales_sync_chunk_result(totals, chunk_result)
                    totals["windows_done"] += 1
                    break
                except Exception as exc:
                    db.rollback()
                    should_refresh_auth = (
                        not token_refresh_attempted
                        and (
                            (
                                isinstance(exc, HTTPException)
                                and int(exc.status_code) in {401, 403}
                            )
                            or (
                                isinstance(exc, requests.exceptions.HTTPError)
                                and int(getattr(getattr(exc, "response", None), "status_code", 0)) in {401, 403}
                            )
                        )
                    )
                    if should_refresh_auth:
                        token = get_token(restaurant.server, restaurant.iiko_login, restaurant.iiko_password_sha1)
                        cols = get_olap_columns(restaurant.server, token, report_type="SALES")
                        token_refresh_attempted = True
                        continue
                    if attempt >= retry_count or not is_retriable_sales_sync_error(exc):
                        detail = build_sales_sync_window_error_detail(
                            exc,
                            window_from=window_from,
                            window_to=window_to,
                            windows_done=int(totals.get("windows_done") or 0),
                            windows_total=len(windows),
                        )
                        if isinstance(exc, HTTPException):
                            raise HTTPException(status_code=exc.status_code, detail=detail)
                        if isinstance(exc, requests.exceptions.HTTPError):
                            response = getattr(exc, "response", None)
                            response_status = int(getattr(response, "status_code", 0) or 500)
                            raise HTTPException(status_code=response_status, detail=detail)
                        raise HTTPException(status_code=500, detail=detail)
                    wait_seconds = min(
                        retry_base_seconds * (2 ** attempt),
                        retry_max_seconds,
                    )
                    time.sleep(wait_seconds)
                    attempt += 1

        return totals
    finally:
        if lock_key is not None:
            release_sales_sync_lock(db, lock_key)
        reset_sales_sync_application_name(db)

def clear_iiko_sales_payload(
    db: Session,
    current_user: Any,
    *,
    restaurant_id: Optional[int] = None,
) -> Dict[str, Any]:
    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = [restaurant.id for restaurant in accessible_restaurants]
    if not accessible_ids:
        return {
            "status": "ok",
            "restaurants": 0,
            "deleted_orders": 0,
            "deleted_items": 0,
            "scope": "none",
        }

    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
        target_ids = [restaurant_id]
        scope = "restaurant"
    else:
        target_ids = accessible_ids
        scope = "network"

    try:
        deleted_items = (
            db.query(IikoSaleItem)
            .filter(IikoSaleItem.restaurant_id.in_(target_ids))
            .delete(synchronize_session=False)
        )
        deleted_orders = (
            db.query(IikoSaleOrder)
            .filter(IikoSaleOrder.restaurant_id.in_(target_ids))
            .delete(synchronize_session=False)
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    payment_methods_count = payment_methods_query(db, current_user).count()
    non_cash_types_count = non_cash_types_query(db, current_user).count()
    non_cash_limits_count = non_cash_limits_query(db, current_user).count()

    return {
        "status": "ok",
        "restaurants": len(target_ids),
        "deleted_orders": int(deleted_orders or 0),
        "deleted_items": int(deleted_items or 0),
        "scope": scope,
        "preserved": {
            "payment_methods": int(payment_methods_count or 0),
            "non_cash_types": int(non_cash_types_count or 0),
            "non_cash_employee_limits": int(non_cash_limits_count or 0),
        },
    }


def sync_iiko_sales_payload(
    db: Session,
    current_user: Any,
    *,
    restaurant_id: int,
    from_date: str,
    to_date: str,
    sync_runner: Callable[..., Dict[str, Any]],
    sync_actor: Optional[str] = None,
) -> Dict[str, Any]:
    restaurant = ensure_user_access_to_restaurant(db, current_user, restaurant_id)
    accessible_restaurants = list_accessible_restaurants(db, current_user)
    source_groups = build_sync_source_groups(accessible_restaurants)
    source_conflicts = build_sync_source_conflict_map(accessible_restaurants)
    conflict = source_conflicts.get(int(restaurant.id))
    if conflict:
        related = ", ".join(conflict.get("related") or [])
        raise HTTPException(
            status_code=409,
            detail=(
                f"Обнаружен общий iiko-источник для нескольких ресторанов: {related}. "
                f"Чтобы избежать дублей продаж, синхронизируйте ресторан "
                f"#{conflict.get('primary_id')} ({conflict.get('primary_name')}) и распределяйте продажи "
                "через маршрутизацию подразделений/столов."
            ),
        )

    source_key = restaurant_iiko_source_key(restaurant)
    strict_source_routing = bool(source_key and len(source_groups.get(source_key, [])) > 1)
    try:
        result = sync_runner(
            db,
            restaurant,
            from_date,
            to_date,
            strict_source_routing=strict_source_routing,
            sync_actor=sync_actor,
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def sync_iiko_sales_network_payload(
    db: Session,
    current_user: Any,
    *,
    from_date: str,
    to_date: str,
    restaurant_ids: Optional[List[int]],
    stop_on_error: bool,
    sync_runner: Callable[..., Dict[str, Any]],
    sync_actor: Optional[str] = None,
) -> Dict[str, Any]:
    accessible_restaurants = list_accessible_restaurants(db, current_user)
    source_groups = build_sync_source_groups(accessible_restaurants)
    source_conflicts = build_sync_source_conflict_map(accessible_restaurants)

    if restaurant_ids:
        restaurants = [
            ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
            for restaurant_id in restaurant_ids
        ]
    else:
        restaurants = accessible_restaurants

    totals = {
        "restaurants": len(restaurants),
        "synced": 0,
        "orders": 0,
        "items": 0,
        "payment_methods": 0,
        "non_cash_types": 0,
        "mapped_orders": 0,
        "unmapped_orders": 0,
        "routing_conflicts": 0,
        "skipped": 0,
        "errors": 0,
        "source_conflicts": 0,
    }
    results: List[Dict[str, Any]] = []

    for restaurant in restaurants:
        conflict = source_conflicts.get(int(restaurant.id))
        if conflict:
            totals["errors"] += 1
            totals["source_conflicts"] += 1
            related = ", ".join(conflict.get("related") or [])
            results.append(
                {
                    "restaurant_id": restaurant.id,
                    "restaurant": restaurant.name,
                    "status": "error",
                    "detail": (
                        f"Общий iiko-источник с ресторанами: {related}. "
                        f"Для предотвращения дублей синхронизация разрешена только через "
                        f"#{conflict.get('primary_id')} ({conflict.get('primary_name')})."
                    ),
                }
            )
            continue

        if not restaurant.server or not restaurant.iiko_login or not restaurant.iiko_password_sha1:
            totals["skipped"] += 1
            results.append(
                {
                    "restaurant_id": restaurant.id,
                    "restaurant": restaurant.name,
                    "status": "skipped",
                    "detail": "No iiko credentials configured",
                }
            )
            continue

        try:
            source_key = restaurant_iiko_source_key(restaurant)
            strict_source_routing = bool(source_key and len(source_groups.get(source_key, [])) > 1)
            row = sync_runner(
                db,
                restaurant,
                from_date,
                to_date,
                strict_source_routing=strict_source_routing,
                sync_actor=sync_actor,
            )
            db.commit()

            orders_count = int(row.get("orders") or 0)
            items_count = int(row.get("items") or 0)
            pm_count = int(row.get("payment_methods") or 0)
            non_cash_count = int(row.get("non_cash_types") or 0)
            mapped_orders = int(row.get("mapped_orders") or 0)
            unmapped_orders = int(row.get("unmapped_orders") or 0)
            routing_conflicts = int(row.get("routing_conflicts") or 0)

            totals["synced"] += 1
            totals["orders"] += orders_count
            totals["items"] += items_count
            totals["payment_methods"] += pm_count
            totals["non_cash_types"] += non_cash_count
            totals["mapped_orders"] += mapped_orders
            totals["unmapped_orders"] += unmapped_orders
            totals["routing_conflicts"] += routing_conflicts

            results.append(
                {
                    "restaurant_id": restaurant.id,
                    "restaurant": restaurant.name,
                    "status": "ok",
                    "orders": orders_count,
                    "items": items_count,
                    "payment_methods": pm_count,
                    "non_cash_types": non_cash_count,
                    "mapped_orders": mapped_orders,
                    "unmapped_orders": unmapped_orders,
                    "routing_conflicts": routing_conflicts,
                    "routing_conflict_samples": row.get("routing_conflict_samples") or [],
                    "strict_source_routing": bool(row.get("strict_source_routing")),
                    "location_mappings": int(row.get("location_mappings") or 0),
                }
            )
        except HTTPException as exc:
            db.rollback()
            totals["errors"] += 1
            results.append(
                {
                    "restaurant_id": restaurant.id,
                    "restaurant": restaurant.name,
                    "status": "error",
                    "detail": exc.detail,
                }
            )
            if stop_on_error:
                raise
        except Exception as exc:
            db.rollback()
            totals["errors"] += 1
            results.append(
                {
                    "restaurant_id": restaurant.id,
                    "restaurant": restaurant.name,
                    "status": "error",
                    "detail": str(exc)[:400],
                }
            )
            if stop_on_error:
                raise HTTPException(status_code=500, detail=str(exc)[:400])

    return {"status": "ok", "totals": totals, "results": results}
