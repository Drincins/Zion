from __future__ import annotations

import hashlib
import json
import os
import time
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import requests
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError, DisconnectionError, OperationalError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import Position, Restaurant, User
from backend.bd.iiko_catalog import (
    IikoNonCashEmployeeLimit,
    IikoNonCashPaymentType,
    IikoPaymentMethod,
    IikoProduct,
    IikoProductRestaurant,
    IikoProductSetting,
    IikoWaiterTurnoverSetting,
)
from backend.bd.iiko_sales import (
    IikoSaleItem,
    IikoSaleOrder,
    IikoSalesHall,
    IikoSalesHallTable,
    IikoSalesHallZone,
    IikoSalesLocationMapping,
)
from backend.services.iiko_api import get_olap_columns, get_token, post_olap_report, to_iso_date
from backend.services.permissions import PermissionCode, ensure_permissions, has_global_access, has_permission
from backend.services.reference_cache import cached_reference_data
from backend.utils import get_current_user, now_local

router = APIRouter(prefix="/iiko-sales", tags=["iiko-sales"])

SALES_REPORT_VIEW_PERMISSIONS = (
    PermissionCode.SALES_REPORT_VIEW_QTY,
    PermissionCode.SALES_REPORT_VIEW_MONEY,
    PermissionCode.IIKO_VIEW,
    PermissionCode.IIKO_MANAGE,
)
SALES_REPORT_MONEY_PERMISSIONS = (
    PermissionCode.SALES_REPORT_VIEW_MONEY,
    PermissionCode.IIKO_VIEW,
    PermissionCode.IIKO_MANAGE,
)
SALES_TABLES_VIEW_PERMISSIONS = (
    PermissionCode.SALES_TABLES_VIEW,
    PermissionCode.SALES_TABLES_MANAGE,
    PermissionCode.IIKO_VIEW,
    PermissionCode.IIKO_MANAGE,
)
SALES_TABLES_MANAGE_PERMISSIONS = (
    PermissionCode.SALES_TABLES_MANAGE,
    PermissionCode.IIKO_MANAGE,
)

DEFAULT_SALES_SYNC_CHUNK_DAYS = 3
DEFAULT_SALES_SYNC_RETRY_COUNT = 4
DEFAULT_SALES_SYNC_RETRY_BASE_SECONDS = 2.0
DEFAULT_SALES_SYNC_RETRY_MAX_SECONDS = 20.0
DEFAULT_SALES_SYNC_LOCK_WAIT_SECONDS = 300.0
SYNC_APPLICATION_NAME_PREFIX = "zion_sync"
WAITER_SALES_OPTIONS_CACHE_SCOPE = "iiko-sales:waiter-sales-options"
WAITER_SALES_OPTIONS_CACHE_TTL_SECONDS = 45


def _can_view_sales_money(current_user: User) -> bool:
    return any(has_permission(current_user, code) for code in SALES_REPORT_MONEY_PERMISSIONS)


def _zero_money_metrics(target: Optional[Dict[str, Any]]) -> None:
    if not isinstance(target, dict):
        return
    if "sum" in target:
        target["sum"] = 0.0
    if "discount_sum" in target:
        target["discount_sum"] = 0.0



class SyncIikoSalesRequest(BaseModel):
    restaurant_id: int
    from_date: str  # 'DD.MM.YYYY' or 'YYYY-MM-DD'
    to_date: str    # 'DD.MM.YYYY' or 'YYYY-MM-DD'


class SyncIikoSalesNetworkRequest(BaseModel):
    from_date: str  # 'DD.MM.YYYY' or 'YYYY-MM-DD'
    to_date: str    # 'DD.MM.YYYY' or 'YYYY-MM-DD'
    restaurant_ids: Optional[List[int]] = None
    stop_on_error: bool = False


class ClearIikoSalesRequest(BaseModel):
    restaurant_id: Optional[int] = None


class UpdateIikoPaymentMethodRequest(BaseModel):
    category: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class UpdateIikoNonCashTypeRequest(BaseModel):
    category: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class CreateIikoNonCashTypeRequest(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    comment: Optional[str] = None
    is_active: bool = True


class UpsertIikoNonCashEmployeeLimitRequest(BaseModel):
    non_cash_type_id: str
    user_id: int
    period_type: str = "month"
    limit_amount: Optional[float] = None
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoNonCashEmployeeLimitRequest(BaseModel):
    period_type: Optional[str] = None
    limit_amount: Optional[float] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class UpsertIikoSalesLocationMappingRequest(BaseModel):
    source_restaurant_id: Optional[int] = None
    target_restaurant_id: int
    department: Optional[str] = None
    table_num: Optional[str] = None
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoSalesLocationMappingRequest(BaseModel):
    source_restaurant_id: Optional[int] = None
    target_restaurant_id: Optional[int] = None
    department: Optional[str] = None
    table_num: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class UpsertIikoSalesHallTableRequest(BaseModel):
    restaurant_id: int
    source_restaurant_id: Optional[int] = None
    department: Optional[str] = None
    table_num: Optional[str] = None
    hall_name: str
    table_name: Optional[str] = None
    capacity: Optional[int] = None
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoSalesHallTableRequest(BaseModel):
    restaurant_id: Optional[int] = None
    source_restaurant_id: Optional[int] = None
    department: Optional[str] = None
    table_num: Optional[str] = None
    hall_name: Optional[str] = None
    table_name: Optional[str] = None
    capacity: Optional[int] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class CreateIikoSalesHallRequest(BaseModel):
    name: str
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoSalesHallRequest(BaseModel):
    name: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class CreateIikoSalesHallZoneRequest(BaseModel):
    hall_id: UUID
    restaurant_id: int
    name: str
    comment: Optional[str] = None
    is_active: bool = True


class UpdateIikoSalesHallZoneRequest(BaseModel):
    name: Optional[str] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class AssignIikoSalesZoneTableItemRequest(BaseModel):
    source_restaurant_id: Optional[int] = None
    department: str
    table_num: Optional[str] = None
    table_name: Optional[str] = None
    capacity: Optional[int] = None
    comment: Optional[str] = None
    is_active: bool = True


class AssignIikoSalesZoneTablesRequest(BaseModel):
    items: List[AssignIikoSalesZoneTableItemRequest]
    replace_zone_tables: bool = False


class UpdateIikoWaiterTurnoverSettingsRequest(BaseModel):
    rule_name: Optional[str] = None
    is_active: Optional[bool] = None
    real_money_only: Optional[bool] = None
    amount_mode: Optional[str] = None
    deleted_mode: Optional[str] = None
    waiter_mode: Optional[str] = None
    position_ids: Optional[List[int]] = None
    include_groups: Optional[List[str]] = None
    exclude_groups: Optional[List[str]] = None
    include_categories: Optional[List[str]] = None
    exclude_categories: Optional[List[str]] = None
    include_positions: Optional[List[str]] = None
    exclude_positions: Optional[List[str]] = None
    include_payment_method_guids: Optional[List[str]] = None
    comment: Optional[str] = None


def _ensure_user_access_to_restaurant(
    db: Session,
    current_user: User,
    restaurant_id: int,
    *,
    require_credentials: bool = True,
) -> Restaurant:
    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    else:
        restaurant = (
            db.query(Restaurant)
            .filter(Restaurant.id == restaurant_id, Restaurant.users.contains(current_user))
            .first()
        )
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or unavailable")
    if require_credentials and (not restaurant.server or not restaurant.iiko_login or not restaurant.iiko_password_sha1):
        raise HTTPException(status_code=400, detail="Restaurant has no iiko credentials configured")
    return restaurant


def _list_accessible_restaurants(db: Session, current_user: User) -> List[Restaurant]:
    q = db.query(Restaurant)
    if not (has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE)):
        q = q.filter(Restaurant.users.contains(current_user))
    if getattr(current_user, "company_id", None) is not None:
        q = q.filter(Restaurant.company_id == current_user.company_id)
    q = q.filter(Restaurant.participates_in_sales.is_(True))
    return q.order_by(Restaurant.id.asc()).all()


def _normalize_iiko_source_token(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().rstrip("/").casefold()


def _restaurant_iiko_source_key(restaurant: Restaurant) -> Optional[str]:
    server = _normalize_iiko_source_token(getattr(restaurant, "server", None))
    login = _normalize_iiko_source_token(getattr(restaurant, "iiko_login", None))
    password_sha1 = _normalize_iiko_source_token(getattr(restaurant, "iiko_password_sha1", None))
    if not server or not login or not password_sha1:
        return None
    return f"{server}|{login}|{password_sha1}"


def _sales_sync_lock_key(restaurant: Restaurant) -> tuple[int, str]:
    source_key = _restaurant_iiko_source_key(restaurant) or f"restaurant:{int(restaurant.id)}"
    digest = hashlib.sha1(source_key.encode("utf-8")).digest()
    # Use signed 64-bit key for pg advisory lock.
    lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
    return lock_key, source_key


def _normalize_sync_actor(value: Optional[str]) -> str:
    raw = str(value or "system").strip()
    if not raw:
        return "system"
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in (":", "-", "_"))
    if not cleaned:
        return "system"
    return cleaned[:20]


def _build_sales_sync_application_name(restaurant: Restaurant, *, sync_actor: Optional[str] = None) -> str:
    source_key = _restaurant_iiko_source_key(restaurant) or f"restaurant:{int(restaurant.id)}"
    source_hash = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:10]
    actor = _normalize_sync_actor(sync_actor)
    value = f"{SYNC_APPLICATION_NAME_PREFIX} r={int(restaurant.id)} a={actor} s={source_hash}"
    return value[:63]


def _parse_sales_sync_application_name(value: Any) -> Optional[Dict[str, Any]]:
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


def _set_sales_sync_application_name(
    db: Session,
    restaurant: Restaurant,
    *,
    sync_actor: Optional[str] = None,
) -> str:
    app_name = _build_sales_sync_application_name(restaurant, sync_actor=sync_actor)
    db.execute(sa.text("SET application_name = :app_name"), {"app_name": app_name})
    return app_name


def _reset_sales_sync_application_name(db: Session) -> None:
    try:
        db.execute(sa.text("SET application_name = DEFAULT"))
        db.commit()
    except Exception:
        db.rollback()


def _acquire_sales_sync_lock(
    db: Session,
    restaurant: Restaurant,
    *,
    wait_seconds: float = 0.0,
) -> tuple[bool, int, str, float]:
    lock_key, source_key = _sales_sync_lock_key(restaurant)
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
        # Queue on advisory lock up to lock_timeout to avoid immediate 409 under parallel runs.
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


def _release_sales_sync_lock(db: Session, lock_key: int) -> None:
    try:
        db.execute(
            sa.text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": int(lock_key)},
        )
        db.commit()
    except Exception:
        db.rollback()


def _payment_methods_query(db: Session, current_user: User):
    q = db.query(IikoPaymentMethod)
    company_id = getattr(current_user, "company_id", None)
    if company_id is not None:
        return q.filter(
            sa.or_(
                IikoPaymentMethod.company_id == company_id,
                IikoPaymentMethod.company_id.is_(None),
            )
        )

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    company_ids = sorted(
        {
            restaurant.company_id
            for restaurant in accessible_restaurants
            if restaurant.company_id is not None
        }
    )

    if company_ids:
        return q.filter(
            sa.or_(
                IikoPaymentMethod.company_id.in_(company_ids),
                IikoPaymentMethod.company_id.is_(None),
            )
        )

    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        return q

    return q.filter(sa.literal(False))


def _non_cash_types_query(db: Session, current_user: User):
    q = db.query(IikoNonCashPaymentType)
    company_id = getattr(current_user, "company_id", None)
    if company_id is not None:
        return q.filter(
            sa.or_(
                IikoNonCashPaymentType.company_id == company_id,
                IikoNonCashPaymentType.company_id.is_(None),
            )
        )

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    company_ids = sorted(
        {
            restaurant.company_id
            for restaurant in accessible_restaurants
            if restaurant.company_id is not None
        }
    )
    if company_ids:
        return q.filter(
            sa.or_(
                IikoNonCashPaymentType.company_id.in_(company_ids),
                IikoNonCashPaymentType.company_id.is_(None),
            )
        )

    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        return q

    return q.filter(sa.literal(False))


def _non_cash_limits_query(db: Session, current_user: User):
    q = db.query(IikoNonCashEmployeeLimit)
    company_id = getattr(current_user, "company_id", None)
    if company_id is not None:
        return q.filter(
            sa.or_(
                IikoNonCashEmployeeLimit.company_id == company_id,
                IikoNonCashEmployeeLimit.company_id.is_(None),
            )
        )

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    company_ids = sorted(
        {
            restaurant.company_id
            for restaurant in accessible_restaurants
            if restaurant.company_id is not None
        }
    )
    if company_ids:
        return q.filter(
            sa.or_(
                IikoNonCashEmployeeLimit.company_id.in_(company_ids),
                IikoNonCashEmployeeLimit.company_id.is_(None),
            )
        )

    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        return q

    return q.filter(sa.literal(False))


def _serialize_payment_method(row: IikoPaymentMethod) -> Dict[str, Any]:
    return {
        "guid": row.guid,
        "company_id": row.company_id,
        "name": row.name,
        "category": row.category,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _serialize_non_cash_type(row: IikoNonCashPaymentType) -> Dict[str, Any]:
    return {
        "id": row.id,
        "company_id": row.company_id,
        "name": row.name,
        "category": row.category,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _serialize_non_cash_limit(
    row: IikoNonCashEmployeeLimit,
    *,
    non_cash_name: Optional[str],
    user_name: Optional[str],
) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "non_cash_type_id": row.non_cash_type_id,
        "non_cash_type_name": non_cash_name,
        "user_id": row.user_id,
        "user_name": user_name,
        "period_type": row.period_type,
        "limit_amount": float(row.limit_amount) if row.limit_amount is not None else None,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


PAYMENT_ID_NAME_FIELDS: List[tuple[str, str]] = [
    ("PayTypes.GUID", "PayTypes"),
    ("NonCashPaymentType.Id", "NonCashPaymentType"),
    ("PaymentType.Id", "PaymentType"),
]

PAYMENT_NAME_ONLY_FIELDS: List[str] = [
    "PayTypes",
    "NonCashPaymentType",
    "PaymentType",
]

DISH_WAITER_GROUP_FIELDS: List[str] = [
    "DishWaiter.Id",
    "DishWaiter.Name",
    "DishWaiter",
    "DishWaiter.Code",
    "DishSeller.Id",
    "DishSeller.Name",
    "DishSeller",
    "DishSeller.Code",
    "DishEmployee.Id",
    "DishEmployee.Name",
    "DishEmployee",
    "DishEmployee.Code",
    "Waiter.Id",
    "Waiter.Name",
    "Waiter",
    "Waiter.Code",
    "WaiterName",
]

HALL_TABLE_DEPARTMENT_FIELDS: List[str] = [
    "Department",
    "Department.Name",
    "DepartmentCode",
    "Department.Code",
]

HALL_TABLE_TABLE_FIELDS: List[str] = [
    "TableNum",
    "Table",
    "Table.Name",
    "TableNum.Name",
]

HALL_TABLE_AGG_FIELDS: List[str] = [
    "DishSumInt",
    "PayableAmountInt",
    "fullSum",
    "GuestNum",
]

HALL_TABLE_DEFAULT_LOOKBACK_DAYS = 365

DISH_WAITER_FIELD_SETS: List[Dict[str, Any]] = [
    {
        "source": "DishWaiter",
        "id_keys": ["DishWaiter.Id"],
        "name_keys": ["DishWaiter.Name", "DishWaiter"],
        "code_keys": ["DishWaiter.Code"],
    },
    {
        "source": "DishSeller",
        "id_keys": ["DishSeller.Id"],
        "name_keys": ["DishSeller.Name", "DishSeller"],
        "code_keys": ["DishSeller.Code"],
    },
    {
        "source": "DishEmployee",
        "id_keys": ["DishEmployee.Id"],
        "name_keys": ["DishEmployee.Name", "DishEmployee"],
        "code_keys": ["DishEmployee.Code"],
    },
    {
        "source": "Waiter",
        "id_keys": ["Waiter.Id"],
        "name_keys": ["Waiter.Name", "Waiter"],
        "code_keys": ["Waiter.Code"],
    },
    {
        "source": "WaiterName",
        "id_keys": [],
        "name_keys": ["WaiterName"],
        "code_keys": [],
    },
]

ORDER_ID_FIELD_CANDIDATES: List[str] = [
    "UniqOrderId.Id",
    "UniqOrderId",
    "OrderId.Id",
    "OrderId",
    "Order.Id",
    "OrderGUID",
    "OrderGuid",
]


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def _build_synthetic_payment_guid(name: str) -> str:
    digest = hashlib.sha1(name.casefold().encode("utf-8")).hexdigest()
    return f"name::{digest}"


def _build_synthetic_non_cash_id(name: str) -> str:
    digest = hashlib.sha1(name.casefold().encode("utf-8")).hexdigest()
    return f"non_cash_name::{digest}"


def _normalize_payment_method(raw_guid: Any, raw_name: Any) -> tuple[Optional[str], Optional[str]]:
    guid = _clean_optional_text(raw_guid)
    name = _clean_optional_text(raw_name)

    if guid and name:
        return guid, name
    if guid and not name:
        return guid, guid
    if name:
        return _build_synthetic_payment_guid(name), name
    return None, None


def _normalize_non_cash_type(raw_id: Any, raw_name: Any) -> tuple[Optional[str], Optional[str]]:
    non_cash_id = _clean_optional_text(raw_id)
    non_cash_name = _clean_optional_text(raw_name)

    if non_cash_id and non_cash_name:
        return non_cash_id, non_cash_name
    if non_cash_id and not non_cash_name:
        return non_cash_id, non_cash_id
    if non_cash_name:
        return _build_synthetic_non_cash_id(non_cash_name), non_cash_name
    return None, None


def _extract_non_cash_fields(payload: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(payload, dict):
        return None, None

    return _normalize_non_cash_type(
        payload.get("NonCashPaymentType.Id"),
        payload.get("NonCashPaymentType"),
    )


def _select_payment_group_fields(cols: Dict[str, Any]) -> List[str]:
    for guid_field, name_field in PAYMENT_ID_NAME_FIELDS:
        if cols.get(guid_field, {}).get("groupingAllowed") and cols.get(name_field, {}).get("groupingAllowed"):
            return [guid_field, name_field]

    for name_field in PAYMENT_NAME_ONLY_FIELDS:
        if cols.get(name_field, {}).get("groupingAllowed"):
            return [name_field]

    for guid_field, _name_field in PAYMENT_ID_NAME_FIELDS:
        if cols.get(guid_field, {}).get("groupingAllowed"):
            return [guid_field]

    return []


def _extract_payment_method_fields(payload: Any) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(payload, dict):
        return None, None

    for guid_field, name_field in PAYMENT_ID_NAME_FIELDS:
        guid, name = _normalize_payment_method(payload.get(guid_field), payload.get(name_field))
        if guid or name:
            return guid, name

    for name_field in PAYMENT_NAME_ONLY_FIELDS:
        guid, name = _normalize_payment_method(None, payload.get(name_field))
        if guid or name:
            return guid, name

    for guid_field, _name_field in PAYMENT_ID_NAME_FIELDS:
        guid, name = _normalize_payment_method(payload.get(guid_field), None)
        if guid or name:
            return guid, name

    return None, None


def _extract_payload_text_any(payload: Any, keys: List[str]) -> Optional[str]:
    for key in keys:
        value = _extract_payload_text(payload, key)
        if value:
            return value
    return None


def _looks_like_uuid(value: Optional[str]) -> bool:
    text = _clean_optional_text(value)
    if not text:
        return False
    try:
        UUID(text)
        return True
    except Exception:
        return False


def _extract_dish_category_name(payload: Any) -> Optional[str]:
    category_value = _extract_payload_text_any(
        payload,
        [
            "DishCategory.Name",
            "DishCategory",
            "DishCategoryFullName",
            "DishCategory.Title",
            "DishCategory.Text",
        ],
    )
    if category_value and not _looks_like_uuid(category_value):
        return category_value
    return None


_UUID_REGEX_SQL = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


def _non_uuid_text_sql(expr: Any):
    text_expr = sa.func.nullif(sa.func.trim(sa.cast(expr, sa.String)), "")
    return sa.case((text_expr.op("~*")(_UUID_REGEX_SQL), sa.null()), else_=text_expr)


def _dish_group_sql_expr():
    return sa.func.coalesce(
        sa.func.nullif(IikoProductSetting.custom_product_group_type, ""),
        sa.func.nullif(IikoSaleItem.dish_group, ""),
    )


def _dish_category_sql_expr(*, with_fallback: bool = False):
    payload_category_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["DishCategory.Name"].astext,
        IikoSaleItem.raw_payload["DishCategory"].astext,
        IikoSaleItem.raw_payload["DishCategoryFullName"].astext,
        IikoSaleItem.raw_payload["DishCategory.Title"].astext,
        IikoSaleItem.raw_payload["DishCategory.Text"].astext,
    )
    category_id_expr = sa.func.nullif(sa.func.trim(sa.cast(IikoSaleItem.dish_category_id, sa.String)), "")
    safe_category_id_expr = sa.case((category_id_expr.op("~*")(_UUID_REGEX_SQL), sa.null()), else_=category_id_expr)
    category_expr = sa.func.coalesce(
        _non_uuid_text_sql(IikoProductSetting.custom_product_category),
        _non_uuid_text_sql(
            sa.func.jsonb_extract_path_text(IikoProduct.raw_payload, "product", "product_category")
        ),
        _non_uuid_text_sql(IikoProduct.product_category),
        _non_uuid_text_sql(payload_category_expr),
        safe_category_id_expr,
    )
    if with_fallback:
        return sa.func.coalesce(category_expr, sa.literal("Uncategorized"))
    return category_expr


def _extract_dish_waiter_fields(payload: Any) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    if not isinstance(payload, dict):
        return None, None, None, None

    for field_set in DISH_WAITER_FIELD_SETS:
        iiko_id = _extract_payload_text_any(payload, field_set.get("id_keys", []))
        name = _extract_payload_text_any(payload, field_set.get("name_keys", []))
        code = _extract_payload_text_any(payload, field_set.get("code_keys", []))
        if iiko_id or name or code:
            return iiko_id, name, code, str(field_set.get("source") or "")

    auth_iiko_id = _extract_payload_text(payload, "AuthUser.Id")
    auth_name = _extract_payload_text(payload, "AuthUser.Name")
    auth_code = _extract_payload_text(payload, "AuthUser.Code")
    if auth_iiko_id or auth_name or auth_code:
        return auth_iiko_id, auth_name, auth_code, "AuthUser"

    return None, None, None, None


def _extract_order_guid(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None

    for key in ORDER_ID_FIELD_CANDIDATES:
        value = _clean_optional_text(payload.get(key))
        if value:
            return value

    # Fallback for iiko instances that do not expose unique order GUID in OLAP.
    # We build a stable key from order-level attributes that should be identical
    # for all item rows of the same order.
    parts = [
        _clean_optional_text(payload.get("OrderNum")) or "",
        _clean_optional_text(payload.get("OpenTime")) or "",
        _clean_optional_text(payload.get("CloseTime")) or "",
        _normalize_location_token(payload.get("Department")) or "",
        _normalize_location_token(payload.get("TableNum")) or "",
        _clean_optional_text(payload.get("OrderWaiter.Id")) or "",
        _clean_optional_text(payload.get("OrderWaiter.Name")) or "",
        _clean_optional_text(payload.get("GuestNum")) or "",
    ]
    signature = "|".join(parts)
    if not signature.strip("|"):
        return None
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()
    return f"synthetic::{digest}"


def _upsert_payment_methods(
    db: Session,
    *,
    company_id: Optional[int],
    methods: Dict[str, str],
    updated_at: datetime,
) -> int:
    payload = []
    for guid, name in (methods or {}).items():
        clean_guid = str(guid).strip() if guid is not None else ""
        if not clean_guid:
            continue
        clean_name = str(name).strip() if name is not None else ""
        payload.append(
            {
                "guid": clean_guid,
                "company_id": company_id,
                "name": clean_name or clean_guid,
                "updated_at": updated_at,
            }
        )

    if not payload:
        return 0

    # Keep deterministic key order to reduce deadlock probability on concurrent UPSERTs.
    payload.sort(key=lambda row: str(row.get("guid") or ""))

    stmt = insert(IikoPaymentMethod).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["guid"],
        set_={
            "name": stmt.excluded.name,
            "company_id": stmt.excluded.company_id,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    db.execute(stmt)
    return len(payload)


def _upsert_non_cash_types(
    db: Session,
    *,
    company_id: Optional[int],
    types_map: Dict[str, str],
    updated_at: datetime,
) -> int:
    payload = []
    for non_cash_id, name in (types_map or {}).items():
        clean_id = str(non_cash_id).strip() if non_cash_id is not None else ""
        if not clean_id:
            continue
        clean_name = str(name).strip() if name is not None else ""
        payload.append(
            {
                "id": clean_id,
                "company_id": company_id,
                "name": clean_name or clean_id,
                "updated_at": updated_at,
            }
        )

    if not payload:
        return 0

    # Keep deterministic key order to reduce deadlock probability on concurrent UPSERTs.
    payload.sort(key=lambda row: str(row.get("id") or ""))

    stmt = insert(IikoNonCashPaymentType).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "name": stmt.excluded.name,
            "company_id": stmt.excluded.company_id,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    db.execute(stmt)
    return len(payload)


def _payment_method_lookup_by_guid(
    db: Session,
    current_user: User,
    guids: set[str],
) -> Dict[str, Dict[str, Any]]:
    if not guids:
        return {}

    rows = (
        _payment_methods_query(db, current_user)
        .filter(IikoPaymentMethod.guid.in_(sorted(guids)))
        .all()
    )
    return {
        str(row.guid): {
            "name": row.name,
            "category": row.category,
            "is_active": bool(row.is_active),
        }
        for row in rows
    }


def _non_cash_lookup_by_id(
    db: Session,
    current_user: User,
    ids: set[str],
) -> Dict[str, Dict[str, Any]]:
    if not ids:
        return {}
    rows = (
        _non_cash_types_query(db, current_user)
        .filter(IikoNonCashPaymentType.id.in_(sorted(ids)))
        .all()
    )
    return {
        str(row.id): {
            "name": row.name,
            "category": row.category,
            "is_active": bool(row.is_active),
        }
        for row in rows
    }


def _user_display_name(
    first_name: Optional[str],
    last_name: Optional[str],
    middle_name: Optional[str],
    username: Optional[str],
) -> str:
    parts = [
        (last_name or "").strip(),
        (first_name or "").strip(),
        (middle_name or "").strip(),
    ]
    full_name = " ".join(part for part in parts if part)
    return full_name or (username or "").strip() or "-"


def _user_names_by_ids(db: Session, user_ids: set[int]) -> Dict[int, str]:
    if not user_ids:
        return {}
    rows = (
        db.query(User.id, User.first_name, User.last_name, User.middle_name, User.username)
        .filter(User.id.in_(sorted(user_ids)))
        .all()
    )
    mapping: Dict[int, str] = {}
    for user_id, first_name, last_name, middle_name, username in rows:
        mapping[int(user_id)] = _user_display_name(first_name, last_name, middle_name, username)
    return mapping


def _user_meta_by_iiko_ids(db: Session, iiko_ids: set[str]) -> Dict[str, Dict[str, Any]]:
    clean_ids = sorted({str(value).strip() for value in iiko_ids if value})
    if not clean_ids:
        return {}
    rows = (
        db.query(User.id, User.iiko_id, User.first_name, User.last_name, User.middle_name, User.username)
        .filter(User.iiko_id.in_(clean_ids))
        .all()
    )
    mapping: Dict[str, Dict[str, Any]] = {}
    for user_id, iiko_id, first_name, last_name, middle_name, username in rows:
        if not iiko_id:
            continue
        key = str(iiko_id).strip()
        if not key:
            continue
        mapping[key] = {
            "id": int(user_id),
            "name": _user_display_name(first_name, last_name, middle_name, username),
        }
    return mapping


def _user_meta_by_iiko_codes(db: Session, iiko_codes: set[str]) -> Dict[str, Dict[str, Any]]:
    clean_codes = sorted({str(value).strip() for value in iiko_codes if value})
    if not clean_codes:
        return {}
    rows = (
        db.query(User.id, User.iiko_code, User.first_name, User.last_name, User.middle_name, User.username)
        .filter(User.iiko_code.in_(clean_codes))
        .all()
    )
    mapping: Dict[str, Dict[str, Any]] = {}
    for user_id, iiko_code, first_name, last_name, middle_name, username in rows:
        if not iiko_code:
            continue
        key = str(iiko_code).strip()
        if not key:
            continue
        mapping[key] = {
            "id": int(user_id),
            "name": _user_display_name(first_name, last_name, middle_name, username),
        }
    return mapping


def _extract_payload_text(payload: Any, key: str) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    value = payload.get(key)
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        # iiko returns "YYYY-MM-DDTHH:MM:SS" or with fractional seconds.
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_iso_date(value: Optional[str]) -> Optional[datetime.date]:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _sync_sales_window_bounds(from_date: str, to_date: str) -> tuple[Any, Any]:
    start_date = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_date = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date()
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    return start_date, end_date + timedelta(days=1)


def _read_positive_int_env(name: str, default: int) -> int:
    raw = str(os.getenv(name, str(default))).strip()
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default


def _read_positive_float_env(name: str, default: float) -> float:
    raw = str(os.getenv(name, str(default))).strip()
    try:
        value = float(raw)
    except Exception:
        return default
    return value if value > 0 else default


def _build_sales_sync_windows(from_date: str, to_date: str) -> List[tuple[str, str]]:
    start_date, end_exclusive = _sync_sales_window_bounds(from_date, to_date)
    end_date = end_exclusive - timedelta(days=1)
    chunk_days = _read_positive_int_env("IIKO_SALES_SYNC_CHUNK_DAYS", DEFAULT_SALES_SYNC_CHUNK_DAYS)

    windows: List[tuple[str, str]] = []
    cursor = start_date
    while cursor <= end_date:
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), end_date)
        windows.append((cursor.isoformat(), chunk_end.isoformat()))
        cursor = chunk_end + timedelta(days=1)
    return windows


def _is_retriable_sales_sync_error(exc: Exception) -> bool:
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


def _compact_error_text(value: Any, *, limit: int = 320) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _extract_sync_error_text(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, str):
            return _compact_error_text(detail)
        try:
            return _compact_error_text(json.dumps(detail, ensure_ascii=False))
        except Exception:
            return _compact_error_text(detail)

    if isinstance(exc, requests.exceptions.HTTPError):
        response = getattr(exc, "response", None)
        status_code = int(getattr(response, "status_code", 0) or 0)
        body_text = _compact_error_text(getattr(response, "text", "") or "")
        if status_code and body_text:
            return f"HTTP {status_code}: {body_text}"
        if status_code:
            return f"HTTP {status_code}"
        return _compact_error_text(exc)

    if isinstance(exc, DBAPIError):
        return _compact_error_text(getattr(exc, "orig", exc) or exc)

    return _compact_error_text(exc)


def _build_sales_sync_window_error_detail(
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
    reason_text = _extract_sync_error_text(exc) or "неизвестная ошибка"
    return f"Ошибка синхронизации {window_text}: {reason_text}. {progress_text}"


def _source_scope_filter(model: Any, source_restaurant_id: int):
    return sa.or_(
        model.source_restaurant_id == source_restaurant_id,
        sa.and_(
            model.source_restaurant_id.is_(None),
            model.restaurant_id == source_restaurant_id,
        ),
    )


def _replace_sales_window_for_source(
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


def _delete_sales_by_source_order_ids(
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


def _normalize_period_type(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    if not clean:
        return "month"
    allowed = {"day", "week", "month", "custom"}
    return clean if clean in allowed else "month"


def _split_filter_values(values: Optional[List[str]]) -> List[str]:
    parts: List[str] = []
    for value in values or []:
        if value is None:
            continue
        text = str(value).replace("\n", ",").replace(";", ",")
        for chunk in text.split(","):
            clean = chunk.strip()
            if clean:
                parts.append(clean)
    # Stable unique order
    unique: List[str] = []
    seen = set()
    for value in parts:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def _lower_values(values: List[str]) -> List[str]:
    return [value.casefold() for value in values if value]


TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT = "sum_without_discount"
TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT = "sum_with_discount"
TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY = "discount_only"

TURNOVER_AMOUNT_MODES = {
    TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
    TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT,
    TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY,
}

WAITER_MODE_ORDER_CLOSE = "order_close"
WAITER_MODE_ITEM_PUNCH = "item_punch"


def _normalize_turnover_amount_mode(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    aliases = {
        "": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "sum": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "gross": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "sum_without_discount": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "sum_with_discount": TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT,
        "net": TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT,
        "discount": TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY,
        "discount_only": TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY,
    }
    return aliases.get(clean, TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT)


def _normalize_waiter_mode(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    aliases = {
        "": WAITER_MODE_ORDER_CLOSE,
        "order_close": WAITER_MODE_ORDER_CLOSE,
        "order_closed": WAITER_MODE_ORDER_CLOSE,
        "close_order": WAITER_MODE_ORDER_CLOSE,
        "order_waiter": WAITER_MODE_ORDER_CLOSE,
        "close": WAITER_MODE_ORDER_CLOSE,
        "closed": WAITER_MODE_ORDER_CLOSE,
        "item_punch": WAITER_MODE_ITEM_PUNCH,
        "punch": WAITER_MODE_ITEM_PUNCH,
        "item_waiter": WAITER_MODE_ITEM_PUNCH,
        "dish_waiter": WAITER_MODE_ITEM_PUNCH,
        "dish_seller": WAITER_MODE_ITEM_PUNCH,
    }
    return aliases.get(clean, WAITER_MODE_ORDER_CLOSE)


def _waiter_dimension_exprs(waiter_mode: Optional[str]) -> Dict[str, Any]:
    resolved_waiter_mode = _normalize_waiter_mode(waiter_mode)
    if resolved_waiter_mode == WAITER_MODE_ITEM_PUNCH:
        waiter_iiko_id_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["DishWaiter.Id"].astext,
            IikoSaleItem.raw_payload["DishSeller.Id"].astext,
            IikoSaleItem.raw_payload["DishEmployee.Id"].astext,
            IikoSaleItem.raw_payload["Waiter.Id"].astext,
            IikoSaleItem.raw_payload["AuthUser.Id"].astext,
            IikoSaleItem.auth_user_iiko_id,
        )
        waiter_iiko_code_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["DishWaiter.Code"].astext,
            IikoSaleItem.raw_payload["DishSeller.Code"].astext,
            IikoSaleItem.raw_payload["DishEmployee.Code"].astext,
            IikoSaleItem.raw_payload["Waiter.Code"].astext,
            IikoSaleItem.raw_payload["AuthUser.Code"].astext,
        )
        waiter_name_iiko_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["DishWaiter.Name"].astext,
            IikoSaleItem.raw_payload["DishWaiter"].astext,
            IikoSaleItem.raw_payload["DishSeller.Name"].astext,
            IikoSaleItem.raw_payload["DishSeller"].astext,
            IikoSaleItem.raw_payload["DishEmployee.Name"].astext,
            IikoSaleItem.raw_payload["DishEmployee"].astext,
            IikoSaleItem.raw_payload["Waiter.Name"].astext,
            IikoSaleItem.raw_payload["Waiter"].astext,
            IikoSaleItem.raw_payload["WaiterName"].astext,
            IikoSaleItem.raw_payload["AuthUser.Name"].astext,
            IikoSaleOrder.order_waiter_name,
        )
        return {
            "waiter_user_id": IikoSaleItem.auth_user_id,
            "waiter_iiko_id": waiter_iiko_id_expr,
            "waiter_iiko_code": waiter_iiko_code_expr,
            "waiter_name_iiko": waiter_name_iiko_expr,
        }

    return {
        "waiter_user_id": IikoSaleOrder.order_waiter_user_id,
        "waiter_iiko_id": IikoSaleOrder.order_waiter_iiko_id,
        "waiter_iiko_code": sa.cast(sa.literal(None), sa.String),
        "waiter_name_iiko": IikoSaleOrder.order_waiter_name,
    }


def _resolve_waiter_identity(
    *,
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
    waiter_name_iiko: Optional[str],
    user_name_by_id: Dict[int, str],
    user_meta_by_iiko_id: Dict[str, Dict[str, Any]],
    user_meta_by_iiko_code: Dict[str, Dict[str, Any]],
) -> tuple[Optional[int], str]:
    clean_waiter_iiko_id = _clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = _clean_optional_text(waiter_iiko_code)
    clean_waiter_name_iiko = _clean_optional_text(waiter_name_iiko)

    resolved_user_id = int(waiter_user_id) if waiter_user_id is not None else None
    if resolved_user_id is None and clean_waiter_iiko_id:
        maybe_user_id = user_meta_by_iiko_id.get(clean_waiter_iiko_id, {}).get("id")
        if maybe_user_id is not None:
            resolved_user_id = int(maybe_user_id)
    if resolved_user_id is None and clean_waiter_iiko_code:
        maybe_user_id = user_meta_by_iiko_code.get(clean_waiter_iiko_code, {}).get("id")
        if maybe_user_id is not None:
            resolved_user_id = int(maybe_user_id)

    resolved_name = (
        user_name_by_id.get(resolved_user_id)
        if resolved_user_id is not None
        else user_meta_by_iiko_id.get(clean_waiter_iiko_id or "", {}).get("name")
        if clean_waiter_iiko_id
        else user_meta_by_iiko_code.get(clean_waiter_iiko_code or "", {}).get("name")
        if clean_waiter_iiko_code
        else None
    ) or clean_waiter_name_iiko or clean_waiter_iiko_code or clean_waiter_iiko_id or "Без привязки"

    return resolved_user_id, resolved_name


def _apply_waiter_filter_to_items_query(
    db: Session,
    query,
    *,
    waiter_mode: Optional[str],
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
):
    resolved_waiter_mode = _normalize_waiter_mode(waiter_mode)
    clean_waiter_iiko_id = _clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = _clean_optional_text(waiter_iiko_code)

    if resolved_waiter_mode == WAITER_MODE_ORDER_CLOSE:
        if waiter_user_id is not None:
            query = query.filter(IikoSaleOrder.order_waiter_user_id == int(waiter_user_id))
        if clean_waiter_iiko_id:
            query = query.filter(IikoSaleOrder.order_waiter_iiko_id == clean_waiter_iiko_id)
        return query

    waiter_exprs = _waiter_dimension_exprs(resolved_waiter_mode)
    waiter_iiko_id_norm_expr = sa.func.trim(sa.func.coalesce(waiter_exprs["waiter_iiko_id"], ""))
    waiter_iiko_code_norm_expr = sa.func.trim(sa.func.coalesce(waiter_exprs["waiter_iiko_code"], ""))

    if waiter_user_id is not None:
        conditions = [IikoSaleItem.auth_user_id == int(waiter_user_id)]
        user_row = (
            db.query(User.iiko_id, User.iiko_code)
            .filter(User.id == int(waiter_user_id))
            .first()
        )
        if user_row:
            user_iiko_id = _clean_optional_text(getattr(user_row, "iiko_id", None))
            user_iiko_code = _clean_optional_text(getattr(user_row, "iiko_code", None))
            if user_iiko_id:
                conditions.append(waiter_iiko_id_norm_expr == user_iiko_id)
            if user_iiko_code:
                conditions.append(waiter_iiko_code_norm_expr == user_iiko_code)
        query = query.filter(sa.or_(*conditions))

    if clean_waiter_iiko_id:
        query = query.filter(waiter_iiko_id_norm_expr == clean_waiter_iiko_id)
    if clean_waiter_iiko_code:
        query = query.filter(waiter_iiko_code_norm_expr == clean_waiter_iiko_code)

    return query


def _normalize_text_list(values: Optional[List[str]]) -> List[str]:
    return _split_filter_values(values)


def _normalize_int_list(values: Optional[List[int]]) -> List[int]:
    unique: List[int] = []
    seen = set()
    for value in values or []:
        try:
            parsed = int(value)
        except Exception:
            continue
        if parsed <= 0 or parsed in seen:
            continue
        seen.add(parsed)
        unique.append(parsed)
    return unique


def _waiter_turnover_settings_query(db: Session, current_user: User):
    q = db.query(IikoWaiterTurnoverSetting)
    company_id = getattr(current_user, "company_id", None)
    if company_id is not None:
        return q.filter(
            sa.or_(
                IikoWaiterTurnoverSetting.company_id == company_id,
                IikoWaiterTurnoverSetting.company_id.is_(None),
            )
        )

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    company_ids = sorted(
        {
            restaurant.company_id
            for restaurant in accessible_restaurants
            if restaurant.company_id is not None
        }
    )
    if company_ids:
        return q.filter(
            sa.or_(
                IikoWaiterTurnoverSetting.company_id.in_(company_ids),
                IikoWaiterTurnoverSetting.company_id.is_(None),
            )
        )

    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        return q

    return q.filter(sa.literal(False))


def _resolve_settings_company_id(
    db: Session,
    current_user: User,
    requested_company_id: Optional[int] = None,
) -> Optional[int]:
    if requested_company_id is not None:
        return int(requested_company_id)

    direct_company_id = getattr(current_user, "company_id", None)
    if direct_company_id is not None:
        return int(direct_company_id)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    company_ids = sorted(
        {
            int(restaurant.company_id)
            for restaurant in accessible_restaurants
            if restaurant.company_id is not None
        }
    )
    if not company_ids:
        return None
    if len(company_ids) == 1:
        return company_ids[0]
    raise HTTPException(
        status_code=400,
        detail="Multiple companies available; pass company_id explicitly.",
    )


def _waiter_turnover_settings_company_query(
    db: Session,
    current_user: User,
    company_id: Optional[int],
):
    q = _waiter_turnover_settings_query(db, current_user)
    if company_id is None:
        return q.filter(IikoWaiterTurnoverSetting.company_id.is_(None))
    return q.filter(IikoWaiterTurnoverSetting.company_id == company_id)


def _normalize_rule_name(value: Optional[str], fallback: str = "Правило") -> str:
    clean = _clean_optional_text(value)
    return clean or fallback


def _default_waiter_turnover_rule_name(existing_count: int) -> str:
    if existing_count <= 0:
        return "Основное правило"
    return f"Правило {existing_count + 1}"


def _waiter_turnover_rules_list_payload(rows: List[IikoWaiterTurnoverSetting]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "id": str(row.id) if row.id is not None else None,
                "rule_name": _normalize_rule_name(row.rule_name, "Без названия"),
                "is_active": bool(row.is_active),
                "real_money_only": bool(row.real_money_only),
                "amount_mode": _normalize_turnover_amount_mode(row.amount_mode),
                "deleted_mode": _normalize_deleted_mode(row.deleted_mode),
                "waiter_mode": _normalize_waiter_mode(row.waiter_mode),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        )
    return items


def _find_waiter_turnover_rule(
    db: Session,
    current_user: User,
    company_id: Optional[int],
    rule_id: UUID,
) -> Optional[IikoWaiterTurnoverSetting]:
    return (
        _waiter_turnover_settings_company_query(db, current_user, company_id)
        .filter(IikoWaiterTurnoverSetting.id == rule_id)
        .first()
    )


def _apply_waiter_turnover_settings_payload(
    db: Session,
    row: IikoWaiterTurnoverSetting,
    payload: UpdateIikoWaiterTurnoverSettingsRequest,
) -> None:
    if payload.rule_name is not None:
        row.rule_name = _normalize_rule_name(payload.rule_name, row.rule_name or "Правило")
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)
    if payload.real_money_only is not None:
        row.real_money_only = bool(payload.real_money_only)
    if payload.amount_mode is not None:
        row.amount_mode = _normalize_turnover_amount_mode(payload.amount_mode)
    if payload.deleted_mode is not None:
        row.deleted_mode = _normalize_deleted_mode(payload.deleted_mode)
    if payload.waiter_mode is not None:
        row.waiter_mode = _normalize_waiter_mode(payload.waiter_mode)
    if payload.comment is not None:
        row.comment = _clean_optional_text(payload.comment)

    if payload.position_ids is not None:
        candidate_ids = _normalize_int_list(payload.position_ids)
        if candidate_ids:
            existing_ids = {
                int(pos_id)
                for (pos_id,) in db.query(Position.id).filter(Position.id.in_(candidate_ids)).all()
                if pos_id is not None
            }
            row.position_ids = [pos_id for pos_id in candidate_ids if pos_id in existing_ids]
        else:
            row.position_ids = []

    if payload.include_groups is not None:
        row.include_groups = _normalize_text_list(payload.include_groups)
    if payload.exclude_groups is not None:
        row.exclude_groups = _normalize_text_list(payload.exclude_groups)
    if payload.include_categories is not None:
        row.include_categories = _normalize_text_list(payload.include_categories)
    if payload.exclude_categories is not None:
        row.exclude_categories = _normalize_text_list(payload.exclude_categories)
    if payload.include_positions is not None:
        row.include_positions = _normalize_text_list(payload.include_positions)
    if payload.exclude_positions is not None:
        row.exclude_positions = _normalize_text_list(payload.exclude_positions)
    if payload.include_payment_method_guids is not None:
        row.include_payment_method_guids = _normalize_text_list(payload.include_payment_method_guids)


def _deactivate_other_waiter_turnover_rules(
    db: Session,
    company_id: Optional[int],
    keep_rule_id: UUID,
) -> None:
    q = db.query(IikoWaiterTurnoverSetting).filter(IikoWaiterTurnoverSetting.id != keep_rule_id)
    if company_id is None:
        q = q.filter(IikoWaiterTurnoverSetting.company_id.is_(None))
    else:
        q = q.filter(IikoWaiterTurnoverSetting.company_id == company_id)
    q.update({IikoWaiterTurnoverSetting.is_active: False}, synchronize_session=False)


def _position_options_for_settings(db: Session) -> List[Dict[str, Any]]:
    rows = db.query(Position.id, Position.name).order_by(Position.name.asc(), Position.id.asc()).all()
    result: List[Dict[str, Any]] = []
    for pos_id, pos_name in rows:
        if pos_id is None:
            continue
        result.append(
            {
                "id": int(pos_id),
                "name": str(pos_name or f"Position #{pos_id}"),
            }
        )
    return result


def _default_waiter_turnover_settings(company_id: Optional[int]) -> Dict[str, Any]:
    return {
        "id": None,
        "company_id": company_id,
        "rule_name": "Основное правило",
        "is_active": False,
        "real_money_only": True,
        "amount_mode": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "deleted_mode": DELETED_MODE_WITHOUT,
        "waiter_mode": WAITER_MODE_ORDER_CLOSE,
        "position_ids": [],
        "include_groups": [],
        "exclude_groups": [],
        "include_categories": [],
        "exclude_categories": [],
        "include_positions": [],
        "exclude_positions": [],
        "include_payment_method_guids": [],
        "comment": None,
        "created_at": None,
        "updated_at": None,
    }


def _serialize_waiter_turnover_settings(row: Optional[IikoWaiterTurnoverSetting], company_id: Optional[int]) -> Dict[str, Any]:
    if not row:
        return _default_waiter_turnover_settings(company_id)
    return {
        "id": str(row.id) if row.id is not None else None,
        "company_id": row.company_id,
        "rule_name": _normalize_rule_name(row.rule_name, "Основное правило"),
        "is_active": bool(row.is_active),
        "real_money_only": bool(row.real_money_only),
        "amount_mode": _normalize_turnover_amount_mode(row.amount_mode),
        "deleted_mode": _normalize_deleted_mode(row.deleted_mode),
        "waiter_mode": _normalize_waiter_mode(row.waiter_mode),
        "position_ids": _normalize_int_list(row.position_ids if isinstance(row.position_ids, list) else []),
        "include_groups": _normalize_text_list(row.include_groups if isinstance(row.include_groups, list) else []),
        "exclude_groups": _normalize_text_list(row.exclude_groups if isinstance(row.exclude_groups, list) else []),
        "include_categories": _normalize_text_list(
            row.include_categories if isinstance(row.include_categories, list) else []
        ),
        "exclude_categories": _normalize_text_list(
            row.exclude_categories if isinstance(row.exclude_categories, list) else []
        ),
        "include_positions": _normalize_text_list(
            row.include_positions if isinstance(row.include_positions, list) else []
        ),
        "exclude_positions": _normalize_text_list(
            row.exclude_positions if isinstance(row.exclude_positions, list) else []
        ),
        "include_payment_method_guids": _normalize_text_list(
            row.include_payment_method_guids if isinstance(row.include_payment_method_guids, list) else []
        ),
        "comment": _clean_optional_text(row.comment),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }

DELETED_MODE_ALL = "all"
DELETED_MODE_ONLY = "only_deleted"
DELETED_MODE_WITHOUT = "without_deleted"


def _normalize_deleted_mode(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    aliases = {
        "": DELETED_MODE_ALL,
        "all": DELETED_MODE_ALL,
        "only_deleted": DELETED_MODE_ONLY,
        "deleted_only": DELETED_MODE_ONLY,
        "only": DELETED_MODE_ONLY,
        "deleted": DELETED_MODE_ONLY,
        "without_deleted": DELETED_MODE_WITHOUT,
        "exclude_deleted": DELETED_MODE_WITHOUT,
        "without": DELETED_MODE_WITHOUT,
        "active_only": DELETED_MODE_WITHOUT,
    }
    return aliases.get(clean, DELETED_MODE_ALL)


def _is_not_deleted_state(value: Optional[str]) -> bool:
    clean = (value or "").strip()
    if not clean:
        return True
    return clean.upper() == "NOT_DELETED"


def _states_indicate_deleted(
    order_deleted_state: Optional[str],
    deleted_with_writeoff_state: Optional[str],
) -> bool:
    return not (
        _is_not_deleted_state(order_deleted_state)
        and _is_not_deleted_state(deleted_with_writeoff_state)
    )


def _payload_deleted_states(payload: Any) -> tuple[Optional[str], Optional[str]]:
    return (
        _extract_payload_text(payload, "OrderDeleted"),
        _extract_payload_text(payload, "DeletedWithWriteoff"),
    )


def _serialize_deleted_payload(payload: Any) -> Dict[str, Any]:
    order_deleted_state, deleted_with_writeoff_state = _payload_deleted_states(payload)
    return {
        "order_deleted_state": order_deleted_state,
        "deleted_with_writeoff_state": deleted_with_writeoff_state,
        "is_deleted": _states_indicate_deleted(order_deleted_state, deleted_with_writeoff_state),
    }


def _is_not_deleted_expr(field_expr: Any):
    normalized = sa.func.upper(sa.func.trim(sa.func.coalesce(field_expr, "")))
    return sa.or_(normalized == "", normalized == "NOT_DELETED")


def _apply_deleted_mode_filter(
    query,
    *,
    deleted_mode: str,
    order_deleted_expr: Any,
    deleted_with_writeoff_expr: Any,
):
    mode = _normalize_deleted_mode(deleted_mode)
    is_not_deleted = sa.and_(
        _is_not_deleted_expr(order_deleted_expr),
        _is_not_deleted_expr(deleted_with_writeoff_expr),
    )
    if mode == DELETED_MODE_ONLY:
        return query.filter(sa.not_(is_not_deleted))
    if mode == DELETED_MODE_WITHOUT:
        return query.filter(is_not_deleted)
    return query


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


def _first_grouping_field(cols: Dict[str, Any], desired: List[str]) -> Optional[str]:
    for field in desired:
        if cols.get(field, {}).get("groupingAllowed"):
            return field
    return None


def _first_aggregate_field(cols: Dict[str, Any], desired: List[str]) -> Optional[str]:
    preferred = _pick_aggs(cols, desired)
    if preferred:
        return preferred[0]
    all_fields = _all_agg_fields(cols)
    return all_fields[0] if all_fields else None


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


def _normalize_location_token(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _build_department_code_restaurant_map(
    db: Session,
    *,
    company_id: Optional[int],
) -> Dict[str, int]:
    """
    Build map: iiko Department code -> local restaurant id.

    If the same normalized code is configured on multiple restaurants, the code is skipped
    to avoid ambiguous automatic routing.
    """
    q = db.query(Restaurant.id, Restaurant.department_code).filter(
        Restaurant.department_code.isnot(None)
    )
    if company_id is not None:
        q = q.filter(Restaurant.company_id == company_id)
    else:
        q = q.filter(Restaurant.company_id.is_(None))

    by_code: Dict[str, int] = {}
    ambiguous: set[str] = set()

    for restaurant_id, department_code in q.all():
        code_norm = _normalize_location_token(department_code)
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


def _resolve_hall_table_candidates_window(
    from_date: Optional[str],
    to_date: Optional[str],
) -> tuple[str, str]:
    today = now_local().date()
    if from_date:
        start_date = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    elif to_date:
        end_hint = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date()
        start_date = end_hint - timedelta(days=HALL_TABLE_DEFAULT_LOOKBACK_DAYS)
    else:
        start_date = today - timedelta(days=HALL_TABLE_DEFAULT_LOOKBACK_DAYS)

    end_date = (
        datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date()
        if to_date
        else today
    )
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    return start_date.isoformat(), end_date.isoformat()


def _build_sales_target_restaurant_resolver(
    db: Session,
    *,
    company_id: Optional[int],
    source_restaurant_id: int,
):
    mappings_q = db.query(IikoSalesLocationMapping).filter(IikoSalesLocationMapping.is_active.is_(True))
    mappings_q = mappings_q.filter(
        sa.or_(
            IikoSalesLocationMapping.company_id == company_id,
            IikoSalesLocationMapping.company_id.is_(None),
        )
    )
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
        dep_norm = (mapping.department_norm or _normalize_location_token(mapping.department)).strip()
        table_norm = (mapping.table_num_norm or _normalize_location_token(mapping.table_num)).strip()
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
    hall_rows_q = hall_rows_q.filter(
        sa.or_(
            IikoSalesHallTable.company_id == company_id,
            IikoSalesHallTable.company_id.is_(None),
        )
    )
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
        dep_norm = (hall_row.department_norm or _normalize_location_token(hall_row.department)).strip()
        table_norm = (hall_row.table_num_norm or _normalize_location_token(hall_row.table_num)).strip()
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

    def resolve_target_restaurant_id(*, department: Any, table_num: Any) -> int:
        dep_norm = _normalize_location_token(department)
        table_norm = _normalize_location_token(table_num)
        if dep_norm and table_norm:
            for source_key in (source_restaurant_id, None):
                target = mapping_exact.get((source_key, dep_norm, table_norm))
                if target is not None:
                    return int(target)
            for source_key in (source_restaurant_id, None):
                target = hall_exact.get((source_key, dep_norm, table_norm))
                if target is not None:
                    return int(target)
        if dep_norm:
            for source_key in (source_restaurant_id, None):
                target = mapping_department.get((source_key, dep_norm))
                if target is not None:
                    return int(target)
            for source_key in (source_restaurant_id, None):
                target = hall_department.get((source_key, dep_norm))
                if target is not None:
                    return int(target)
            target = department_code_map.get(dep_norm)
            if target is not None:
                return int(target)
        return source_restaurant_id

    return resolve_target_restaurant_id


def _sales_location_mappings_query(db: Session, current_user: User):
    q = db.query(IikoSalesLocationMapping)
    company_id = getattr(current_user, "company_id", None)
    if company_id is not None:
        return q.filter(
            sa.or_(
                IikoSalesLocationMapping.company_id == company_id,
                IikoSalesLocationMapping.company_id.is_(None),
            )
        )

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    company_ids = sorted(
        {
            restaurant.company_id
            for restaurant in accessible_restaurants
            if restaurant.company_id is not None
        }
    )
    if company_ids:
        return q.filter(
            sa.or_(
                IikoSalesLocationMapping.company_id.in_(company_ids),
                IikoSalesLocationMapping.company_id.is_(None),
            )
        )

    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        return q

    return q.filter(sa.literal(False))


def _serialize_sales_location_mapping(
    row: IikoSalesLocationMapping,
    *,
    source_restaurant_name: Optional[str] = None,
    target_restaurant_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "source_restaurant_id": row.source_restaurant_id,
        "source_restaurant_name": source_restaurant_name,
        "target_restaurant_id": row.target_restaurant_id,
        "target_restaurant_name": target_restaurant_name,
        "department": row.department,
        "table_num": row.table_num,
        "department_norm": row.department_norm,
        "table_num_norm": row.table_num_norm,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _sales_halls_query(db: Session, current_user: User):
    q = db.query(IikoSalesHall)
    company_id = getattr(current_user, "company_id", None)
    if company_id is not None:
        return q.filter(
            sa.or_(
                IikoSalesHall.company_id == company_id,
                IikoSalesHall.company_id.is_(None),
            )
        )

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    company_ids = sorted(
        {
            restaurant.company_id
            for restaurant in accessible_restaurants
            if restaurant.company_id is not None
        }
    )
    if company_ids:
        return q.filter(
            sa.or_(
                IikoSalesHall.company_id.in_(company_ids),
                IikoSalesHall.company_id.is_(None),
            )
        )

    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        return q

    return q.filter(sa.literal(False))


def _sales_hall_zones_query(db: Session, current_user: User):
    q = db.query(IikoSalesHallZone)
    company_id = getattr(current_user, "company_id", None)
    if company_id is not None:
        return q.filter(
            sa.or_(
                IikoSalesHallZone.company_id == company_id,
                IikoSalesHallZone.company_id.is_(None),
            )
        )

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    company_ids = sorted(
        {
            restaurant.company_id
            for restaurant in accessible_restaurants
            if restaurant.company_id is not None
        }
    )
    if company_ids:
        return q.filter(
            sa.or_(
                IikoSalesHallZone.company_id.in_(company_ids),
                IikoSalesHallZone.company_id.is_(None),
            )
        )

    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        return q

    return q.filter(sa.literal(False))


def _serialize_sales_hall(row: IikoSalesHall) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "name": row.name,
        "name_norm": row.name_norm,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _serialize_sales_hall_zone(
    row: IikoSalesHallZone,
    *,
    hall_name: Optional[str] = None,
    restaurant_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "hall_id": str(row.hall_id) if row.hall_id is not None else None,
        "hall_name": hall_name,
        "restaurant_id": row.restaurant_id,
        "restaurant_name": restaurant_name,
        "name": row.name,
        "name_norm": row.name_norm,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _sales_hall_tables_query(db: Session, current_user: User):
    q = db.query(IikoSalesHallTable)
    company_id = getattr(current_user, "company_id", None)
    if company_id is not None:
        return q.filter(
            sa.or_(
                IikoSalesHallTable.company_id == company_id,
                IikoSalesHallTable.company_id.is_(None),
            )
        )

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    company_ids = sorted(
        {
            restaurant.company_id
            for restaurant in accessible_restaurants
            if restaurant.company_id is not None
        }
    )
    if company_ids:
        return q.filter(
            sa.or_(
                IikoSalesHallTable.company_id.in_(company_ids),
                IikoSalesHallTable.company_id.is_(None),
            )
        )

    if has_global_access(current_user) or has_permission(current_user, PermissionCode.IIKO_MANAGE):
        return q

    return q.filter(sa.literal(False))


def _serialize_sales_hall_table(
    row: IikoSalesHallTable,
    *,
    restaurant_name: Optional[str] = None,
    source_restaurant_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "restaurant_id": row.restaurant_id,
        "restaurant_name": restaurant_name,
        "hall_id": str(row.hall_id) if getattr(row, "hall_id", None) is not None else None,
        "zone_id": str(row.zone_id) if getattr(row, "zone_id", None) is not None else None,
        "source_restaurant_id": row.source_restaurant_id,
        "source_restaurant_name": source_restaurant_name,
        "department": row.department,
        "table_num": row.table_num,
        "department_norm": row.department_norm,
        "table_num_norm": row.table_num_norm,
        "hall_name": row.hall_name,
        "hall_name_norm": row.hall_name_norm,
        "zone_name": getattr(row, "zone_name", None),
        "zone_name_norm": getattr(row, "zone_name_norm", None),
        "table_name": row.table_name,
        "capacity": row.capacity,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _build_sales_hall_table_resolver(rows: List[IikoSalesHallTable]):
    sorted_rows = sorted(
        rows or [],
        key=lambda row: (
            row.company_id is None,  # prefer company-specific rows
            row.source_restaurant_id is None,  # prefer source-specific rows
        ),
    )

    by_exact: Dict[tuple[int, Optional[int], str, str], IikoSalesHallTable] = {}
    by_department: Dict[tuple[int, Optional[int], str], IikoSalesHallTable] = {}

    for row in sorted_rows:
        rest_id = int(row.restaurant_id) if row.restaurant_id is not None else None
        if rest_id is None:
            continue
        dep_norm = (row.department_norm or _normalize_location_token(row.department)).strip()
        table_norm = (row.table_num_norm or _normalize_location_token(row.table_num)).strip()
        if not dep_norm:
            continue
        source_key = int(row.source_restaurant_id) if row.source_restaurant_id is not None else None
        if table_norm:
            by_exact.setdefault((rest_id, source_key, dep_norm, table_norm), row)
        else:
            by_department.setdefault((rest_id, source_key, dep_norm), row)

    def _resolve(
        *,
        restaurant_id: Optional[int],
        source_restaurant_id: Optional[int],
        department: Any,
        table_num: Any,
    ) -> Dict[str, Any]:
        rest_id = int(restaurant_id) if restaurant_id is not None else None
        dep_norm = _normalize_location_token(department)
        table_norm = _normalize_location_token(table_num)
        source_key = (
            int(source_restaurant_id)
            if source_restaurant_id is not None
            else (rest_id if rest_id is not None else None)
        )

        if rest_id is not None and dep_norm:
            if table_norm:
                for maybe_source in (source_key, None):
                    row = by_exact.get((rest_id, maybe_source, dep_norm, table_norm))
                    if row is not None:
                        hall_name = (row.hall_name or "").strip() or (department or "Без зала")
                        return {
                            "hall_name": hall_name,
                            "hall_name_norm": _normalize_location_token(hall_name),
                            "zone_name": (row.zone_name or "").strip() or None,
                            "zone_name_norm": _normalize_location_token(row.zone_name),
                            "table_name": (row.table_name or "").strip() or (table_num or None),
                            "capacity": int(row.capacity) if row.capacity is not None else None,
                        }
            for maybe_source in (source_key, None):
                row = by_department.get((rest_id, maybe_source, dep_norm))
                if row is not None:
                    hall_name = (row.hall_name or "").strip() or (department or "Без зала")
                    return {
                        "hall_name": hall_name,
                        "hall_name_norm": _normalize_location_token(hall_name),
                        "zone_name": (row.zone_name or "").strip() or None,
                        "zone_name_norm": _normalize_location_token(row.zone_name),
                        "table_name": (row.table_name or "").strip() or (table_num or None),
                        "capacity": int(row.capacity) if row.capacity is not None else None,
                    }

        fallback_hall = str(department).strip() if department is not None and str(department).strip() else "Без зала"
        fallback_table = str(table_num).strip() if table_num is not None and str(table_num).strip() else None
        return {
            "hall_name": fallback_hall,
            "hall_name_norm": _normalize_location_token(fallback_hall),
            "zone_name": None,
            "zone_name_norm": "",
            "table_name": fallback_table,
            "capacity": None,
        }

    return _resolve


def _collect_halls_from_order_rows(
    db: Session,
    current_user: User,
    order_rows: List[Any],
) -> List[str]:
    if not order_rows:
        return []

    restaurant_ids = {
        int(row.restaurant_id)
        for row in order_rows
        if getattr(row, "restaurant_id", None) is not None
    }
    hall_rows_q = _sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.is_active.is_(True))
    if restaurant_ids:
        hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.restaurant_id.in_(sorted(restaurant_ids)))
    resolve_hall = _build_sales_hall_table_resolver(hall_rows_q.all())

    by_norm: Dict[str, str] = {}
    for row in order_rows:
        resolved = resolve_hall(
            restaurant_id=getattr(row, "restaurant_id", None),
            source_restaurant_id=getattr(row, "source_restaurant_id", None),
            department=getattr(row, "department", None),
            table_num=getattr(row, "table_num", None),
        )
        hall_name = str(resolved.get("hall_name") or "").strip()
        hall_norm = str(resolved.get("hall_name_norm") or "").strip()
        if not hall_name or not hall_norm or hall_norm in by_norm:
            continue
        by_norm[hall_norm] = hall_name

    return sorted(by_norm.values(), key=lambda value: str(value).casefold())


def _apply_hall_filter_to_base_query(
    db: Session,
    current_user: User,
    base_q,
    include_halls_lower: List[str],
):
    include_set = {str(value or "").strip().casefold() for value in include_halls_lower if str(value or "").strip()}
    if not include_set:
        return base_q

    order_rows = (
        base_q.with_entities(
            IikoSaleOrder.id.label("order_id"),
            IikoSaleOrder.restaurant_id.label("restaurant_id"),
            IikoSaleOrder.source_restaurant_id.label("source_restaurant_id"),
            IikoSaleOrder.department.label("department"),
            IikoSaleOrder.table_num.label("table_num"),
        )
        .distinct()
        .all()
    )
    if not order_rows:
        return base_q.filter(sa.literal(False))

    restaurant_ids = {
        int(row.restaurant_id)
        for row in order_rows
        if row.restaurant_id is not None
    }
    hall_rows_q = _sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.is_active.is_(True))
    if restaurant_ids:
        hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.restaurant_id.in_(sorted(restaurant_ids)))
    resolve_hall = _build_sales_hall_table_resolver(hall_rows_q.all())

    selected_order_ids = []
    for row in order_rows:
        resolved = resolve_hall(
            restaurant_id=row.restaurant_id,
            source_restaurant_id=row.source_restaurant_id,
            department=row.department,
            table_num=row.table_num,
        )
        if str(resolved.get("hall_name_norm") or "").strip().casefold() in include_set:
            selected_order_ids.append(row.order_id)

    if not selected_order_ids:
        return base_q.filter(sa.literal(False))

    return base_q.filter(IikoSaleOrder.id.in_(selected_order_ids))


def _sync_payment_methods(
    db: Session,
    restaurant: Restaurant,
    from_date: str,
    to_date: str,
    cols: Dict[str, Any],
    token: str,
) -> int:
    date_field = _resolve_date_field(cols)
    group_fields = _select_payment_group_fields(cols)

    if not group_fields:
        return 0

    # OLAP requires at least one aggregate. Prefer DishSumInt, fallback to any allowed aggregate.
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
        guid, name = _extract_payment_method_fields(row)
        if guid:
            methods[guid] = name or methods.get(guid) or guid

    if not methods:
        return 0

    return _upsert_payment_methods(
        db,
        company_id=restaurant.company_id,
        methods=methods,
        updated_at=now_local(),
    )


def _sync_sales_orders_and_items(
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
    payment_group_fields = _select_payment_group_fields(cols)
    dish_waiter_group_fields = _pick_fields(cols, DISH_WAITER_GROUP_FIELDS)
    start_date, end_exclusive = _sync_sales_window_bounds(from_date, to_date)
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
    # Keep required fields first, then append all remaining groupable fields from OLAP.
    group_fields: List[str] = []
    seen_group_fields: set[str] = set()
    for field in required_groups + dish_waiter_group_fields + payment_group_fields + _all_group_fields(cols):
        if field in seen_group_fields:
            continue
        if not cols.get(field, {}).get("groupingAllowed"):
            continue
        seen_group_fields.add(field)
        group_fields.append(field)

    # Pull every aggregate iiko allows for SALES to preserve full snapshot in raw_payload.
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
    replaced_scope = _replace_sales_window_for_source(
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

    # Optional location mapping: source restaurant + department (+table) -> target restaurant.
    mappings_q = db.query(IikoSalesLocationMapping).filter(IikoSalesLocationMapping.is_active.is_(True))
    mappings_q = mappings_q.filter(
        sa.or_(
            IikoSalesLocationMapping.company_id == company_id,
            IikoSalesLocationMapping.company_id.is_(None),
        )
    )
    mappings_q = mappings_q.filter(
        sa.or_(
            IikoSalesLocationMapping.source_restaurant_id == source_restaurant_id,
            IikoSalesLocationMapping.source_restaurant_id.is_(None),
        )
    )
    mapping_rows = mappings_q.all()
    mapping_rows.sort(
        key=lambda row: (
            row.company_id is None,  # company-specific first
            row.source_restaurant_id is None,  # source-specific first
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
        dep_norm = (mapping.department_norm or _normalize_location_token(mapping.department)).strip()
        table_norm = (mapping.table_num_norm or _normalize_location_token(mapping.table_num)).strip()
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
    hall_rows_q = hall_rows_q.filter(
        sa.or_(
            IikoSalesHallTable.company_id == company_id,
            IikoSalesHallTable.company_id.is_(None),
        )
    )
    hall_rows_q = hall_rows_q.filter(
        sa.or_(
            IikoSalesHallTable.source_restaurant_id == source_restaurant_id,
            IikoSalesHallTable.source_restaurant_id.is_(None),
        )
    )
    hall_rows = hall_rows_q.all()
    hall_rows.sort(
        key=lambda row: (
            row.company_id is None,  # company-specific first
            row.source_restaurant_id is None,  # source-specific first
        )
    )

    hall_exact: Dict[tuple[Optional[int], str, str], int] = {}
    hall_department: Dict[tuple[Optional[int], str], int] = {}
    hall_exact_ambiguous: set[tuple[Optional[int], str, str]] = set()
    hall_department_ambiguous: set[tuple[Optional[int], str]] = set()
    for hall_row in hall_rows:
        dep_norm = (hall_row.department_norm or _normalize_location_token(hall_row.department)).strip()
        table_norm = (hall_row.table_num_norm or _normalize_location_token(hall_row.table_num)).strip()
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
        dep_norm = _normalize_location_token(department)
        table_norm = _normalize_location_token(table_num)
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

    # Prepare lookup sets for joins.
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
        dish_waiter_iiko_id, _dish_waiter_name, dish_waiter_code, _dish_waiter_source = _extract_dish_waiter_fields(row)
        if dish_waiter_iiko_id:
            dish_waiter_iiko_ids.add(str(dish_waiter_iiko_id))
        if dish_waiter_code:
            dish_waiter_codes.add(str(dish_waiter_code))
        pay_guid, pay_name = _extract_payment_method_fields(row)
        if pay_guid:
            method_names_by_guid[pay_guid] = pay_name or method_names_by_guid.get(pay_guid) or pay_guid
        non_cash_id, non_cash_name = _extract_non_cash_fields(row)
        if non_cash_id:
            non_cash_names_by_id[non_cash_id] = non_cash_name or non_cash_names_by_id.get(non_cash_id) or non_cash_id

    iiko_id_map, iiko_code_map = _load_user_maps(
        db,
        iiko_ids=waiter_iiko_ids.union(cashier_iiko_ids).union(auth_iiko_ids).union(dish_waiter_iiko_ids),
        iiko_codes=cashier_codes.union(dish_waiter_codes),
    )
    product_id_by_num = _load_product_num_map(db, dish_nums)

    payment_methods_count = _upsert_payment_methods(
        db,
        company_id=company_id,
        methods=method_names_by_guid,
        updated_at=now,
    )
    non_cash_types_count = _upsert_non_cash_types(
        db,
        company_id=company_id,
        types_map=non_cash_names_by_id,
        updated_at=now,
    )
    if payment_methods_count == 0:
        # Fallback for environments where payment fields are not available in main OLAP payload.
        payment_methods_count = _sync_payment_methods(db, restaurant, from_date, to_date, cols, token)

    # Orders are repeated for each item row; dedupe by iiko_order_id.
    orders_by_key: dict[str, Dict[str, Any]] = {}

    for row in data:
        order_guid = _extract_order_guid(row)
        if not order_guid:
            continue
        order_guid = str(order_guid)
        if order_guid in orders_by_key:
            continue

        open_date = _parse_iso_date((row or {}).get(date_field))
        opened_at = _parse_iso_datetime((row or {}).get("OpenTime"))
        closed_at = _parse_iso_datetime((row or {}).get("CloseTime"))

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
                        "department": _clean_optional_text(department_value),
                        "table_num": _clean_optional_text(table_num_value),
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

    # UPSERT orders and get UUID ids for item FK.
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

    legacy_cleanup = _delete_sales_by_source_order_ids(
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

    # Build items and protect against duplicate keys inside a single INSERT batch.
    items_payload_by_key: dict[tuple[str, str], Dict[str, Any]] = {}
    for row in data:
        if not row:
            continue
        order_guid = _extract_order_guid(row)
        if not order_guid:
            continue
        order_guid = str(order_guid)
        order_uuid = order_id_by_guid.get(order_guid)
        if not order_uuid:
            continue

        dish_code = row.get("DishCode")
        auth_user_iiko_id = row.get("AuthUser.Id")
        order_restaurant_id = int(orders_by_key.get(order_guid, {}).get("restaurant_id") or source_restaurant_id)

        open_date = _parse_iso_date((row or {}).get(date_field))
        payment_method_guid, payment_method_name = _extract_payment_method_fields(row)
        dish_waiter_iiko_id, dish_waiter_name, dish_waiter_code, _dish_waiter_source = _extract_dish_waiter_fields(row)

        # Full OLAP row hash keeps distinct lines when iiko adds dimensions we do not model explicitly.
        line_key = _hash_payload(row)

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

        # Fill missing snapshots if they were null in the first row.
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

        # Keep the latest raw payload and timestamp.
        existing["raw_payload"] = payload_row["raw_payload"]
        existing["updated_at"] = payload_row["updated_at"]

    items_payload: List[Dict[str, Any]] = list(items_payload_by_key.values())

    if items_payload:
        it = insert(IikoSaleItem).values(items_payload)
        it = it.on_conflict_do_update(
            index_elements=["order_id", "line_key"],
            set_={
                # Preserve snapshots once set, but allow filling missing values.
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


def _merge_sales_sync_chunk_result(target: Dict[str, Any], chunk: Dict[str, Any]) -> None:
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


def _sync_sales_orders_and_items_resilient(
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
        _set_sales_sync_application_name(db, restaurant, sync_actor=sync_actor)
        lock_wait_seconds = _read_positive_float_env(
            "IIKO_SALES_SYNC_LOCK_WAIT_SECONDS",
            DEFAULT_SALES_SYNC_LOCK_WAIT_SECONDS,
        )
        lock_acquired, lock_key, _lock_source, waited_seconds = _acquire_sales_sync_lock(
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

        windows = _build_sales_sync_windows(from_date, to_date)
        chunk_days = _read_positive_int_env("IIKO_SALES_SYNC_CHUNK_DAYS", DEFAULT_SALES_SYNC_CHUNK_DAYS)
        retry_count = _read_positive_int_env("IIKO_SALES_SYNC_RETRY_COUNT", DEFAULT_SALES_SYNC_RETRY_COUNT)
        retry_base_seconds = _read_positive_float_env(
            "IIKO_SALES_SYNC_RETRY_BASE_SECONDS",
            DEFAULT_SALES_SYNC_RETRY_BASE_SECONDS,
        )
        retry_max_seconds = _read_positive_float_env(
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
                    chunk_result = _sync_sales_orders_and_items(
                        db,
                        restaurant,
                        window_from,
                        window_to,
                        strict_source_routing=strict_source_routing,
                        token=token,
                        cols=cols,
                    )
                    db.commit()
                    _merge_sales_sync_chunk_result(totals, chunk_result)
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
                    if attempt >= retry_count or not _is_retriable_sales_sync_error(exc):
                        detail = _build_sales_sync_window_error_detail(
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
            _release_sales_sync_lock(db, lock_key)
        _reset_sales_sync_application_name(db)


def _build_sync_source_groups(restaurants: List[Restaurant]) -> Dict[str, List[Restaurant]]:
    grouped: Dict[str, List[Restaurant]] = {}
    for restaurant in restaurants:
        key = _restaurant_iiko_source_key(restaurant)
        if not key:
            continue
        grouped.setdefault(key, []).append(restaurant)
    for key, rows in grouped.items():
        grouped[key] = sorted(rows, key=lambda row: int(row.id))
    return grouped


def _build_sync_source_conflict_map(restaurants: List[Restaurant]) -> Dict[int, Dict[str, Any]]:
    grouped = _build_sync_source_groups(restaurants)

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


@router.post("/sync")
def sync_iiko_sales(
    payload: SyncIikoSalesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    restaurant = _ensure_user_access_to_restaurant(db, current_user, payload.restaurant_id)
    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    source_groups = _build_sync_source_groups(accessible_restaurants)
    source_conflicts = _build_sync_source_conflict_map(accessible_restaurants)
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
    source_key = _restaurant_iiko_source_key(restaurant)
    strict_source_routing = bool(source_key and len(source_groups.get(source_key, [])) > 1)
    try:
        result = _sync_sales_orders_and_items_resilient(
            db,
            restaurant,
            payload.from_date,
            payload.to_date,
            strict_source_routing=strict_source_routing,
            sync_actor=f"user:{int(current_user.id)}",
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


@router.post("/sync-network")
def sync_iiko_sales_network(
    payload: SyncIikoSalesNetworkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    source_groups = _build_sync_source_groups(accessible_restaurants)
    source_conflicts = _build_sync_source_conflict_map(accessible_restaurants)

    if payload.restaurant_ids:
        restaurants = [
            _ensure_user_access_to_restaurant(db, current_user, rid, require_credentials=False)
            for rid in payload.restaurant_ids
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
            source_key = _restaurant_iiko_source_key(restaurant)
            strict_source_routing = bool(source_key and len(source_groups.get(source_key, [])) > 1)
            row = _sync_sales_orders_and_items_resilient(
                db,
                restaurant,
                payload.from_date,
                payload.to_date,
                strict_source_routing=strict_source_routing,
                sync_actor=f"user:{int(current_user.id)}",
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
            if payload.stop_on_error:
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
            if payload.stop_on_error:
                raise HTTPException(status_code=500, detail=str(exc)[:400])

    return {"status": "ok", "totals": totals, "results": results}


@router.post("/clear")
def clear_iiko_sales(
    payload: ClearIikoSalesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    accessible_ids = [r.id for r in accessible_restaurants]
    if not accessible_ids:
        return {
            "status": "ok",
            "restaurants": 0,
            "deleted_orders": 0,
            "deleted_items": 0,
            "scope": "none",
        }

    if payload.restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, payload.restaurant_id, require_credentials=False)
        target_ids = [payload.restaurant_id]
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

    # Sales cleanup does not touch payment dictionaries or configured limits.
    payment_methods_count = _payment_methods_query(db, current_user).count()
    non_cash_types_count = _non_cash_types_query(db, current_user).count()
    non_cash_limits_count = _non_cash_limits_query(db, current_user).count()

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


@router.get("/sales-location-mappings")
def list_sales_location_mappings(
    include_inactive: bool = Query(True),
    source_restaurant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)

    if source_restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)

    q = _sales_location_mappings_query(db, current_user)
    if not include_inactive:
        q = q.filter(IikoSalesLocationMapping.is_active.is_(True))
    if source_restaurant_id is not None:
        q = q.filter(IikoSalesLocationMapping.source_restaurant_id == source_restaurant_id)

    rows = q.order_by(
        IikoSalesLocationMapping.source_restaurant_id.asc().nullsfirst(),
        IikoSalesLocationMapping.department_norm.asc(),
        IikoSalesLocationMapping.table_num_norm.asc(),
    ).all()

    restaurant_ids = {
        int(row.source_restaurant_id)
        for row in rows
        if row.source_restaurant_id is not None
    }.union(
        {
            int(row.target_restaurant_id)
            for row in rows
            if row.target_restaurant_id is not None
        }
    )
    restaurant_name_by_id: Dict[int, str] = {}
    if restaurant_ids:
        restaurant_name_rows = (
            db.query(Restaurant.id, Restaurant.name)
            .filter(Restaurant.id.in_(sorted(restaurant_ids)))
            .all()
        )
        restaurant_name_by_id = {
            int(rest_id): str(rest_name)
            for rest_id, rest_name in restaurant_name_rows
            if rest_id is not None and rest_name is not None
        }

    return [
        _serialize_sales_location_mapping(
            row,
            source_restaurant_name=restaurant_name_by_id.get(int(row.source_restaurant_id))
            if row.source_restaurant_id is not None
            else None,
            target_restaurant_name=restaurant_name_by_id.get(int(row.target_restaurant_id))
            if row.target_restaurant_id is not None
            else None,
        )
        for row in rows
    ]


@router.put("/sales-location-mappings")
def upsert_sales_location_mapping(
    payload: UpsertIikoSalesLocationMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    source_restaurant: Optional[Restaurant] = None
    if payload.source_restaurant_id is not None:
        source_restaurant = _ensure_user_access_to_restaurant(
            db,
            current_user,
            int(payload.source_restaurant_id),
            require_credentials=False,
        )

    target_restaurant = _ensure_user_access_to_restaurant(
        db,
        current_user,
        int(payload.target_restaurant_id),
        require_credentials=False,
    )

    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        company_id = source_restaurant.company_id if source_restaurant is not None else target_restaurant.company_id

    if company_id is not None:
        if source_restaurant is not None and source_restaurant.company_id not in {None, company_id}:
            raise HTTPException(status_code=400, detail="Source restaurant is outside of your company scope")
        if target_restaurant.company_id not in {None, company_id}:
            raise HTTPException(status_code=400, detail="Target restaurant is outside of your company scope")

    department = (payload.department or "").strip() or None
    table_num = (payload.table_num or "").strip() or None
    department_norm = _normalize_location_token(department)
    table_num_norm = _normalize_location_token(table_num)
    if not department_norm:
        raise HTTPException(status_code=400, detail="department is required")

    source_restaurant_id_value = int(payload.source_restaurant_id) if payload.source_restaurant_id is not None else None

    row = (
        _sales_location_mappings_query(db, current_user)
        .filter(IikoSalesLocationMapping.source_restaurant_id == source_restaurant_id_value)
        .filter(IikoSalesLocationMapping.department_norm == department_norm)
        .filter(IikoSalesLocationMapping.table_num_norm == table_num_norm)
        .first()
    )

    if row is None:
        row = IikoSalesLocationMapping(
            company_id=company_id,
            source_restaurant_id=source_restaurant_id_value,
            department=department,
            table_num=table_num,
            department_norm=department_norm,
            table_num_norm=table_num_norm,
            target_restaurant_id=int(payload.target_restaurant_id),
            comment=(payload.comment or "").strip() or None,
            is_active=bool(payload.is_active),
        )
    else:
        row.company_id = company_id
        row.source_restaurant_id = source_restaurant_id_value
        row.department = department
        row.table_num = table_num
        row.department_norm = department_norm
        row.table_num_norm = table_num_norm
        row.target_restaurant_id = int(payload.target_restaurant_id)
        row.comment = (payload.comment or "").strip() or None
        row.is_active = bool(payload.is_active)

    db.add(row)
    db.commit()
    db.refresh(row)

    return _serialize_sales_location_mapping(
        row,
        source_restaurant_name=source_restaurant.name if source_restaurant is not None else None,
        target_restaurant_name=target_restaurant.name,
    )


@router.patch("/sales-location-mappings/{mapping_id}")
def update_sales_location_mapping(
    mapping_id: str,
    payload: UpdateIikoSalesLocationMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    row = _sales_location_mappings_query(db, current_user).filter(IikoSalesLocationMapping.id == mapping_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sales location mapping not found")

    source_restaurant: Optional[Restaurant] = None
    if payload.source_restaurant_id is not None:
        source_restaurant = _ensure_user_access_to_restaurant(
            db,
            current_user,
            int(payload.source_restaurant_id),
            require_credentials=False,
        )
        row.source_restaurant_id = int(payload.source_restaurant_id)

    target_restaurant: Optional[Restaurant] = None
    if payload.target_restaurant_id is not None:
        target_restaurant = _ensure_user_access_to_restaurant(
            db,
            current_user,
            int(payload.target_restaurant_id),
            require_credentials=False,
        )
        row.target_restaurant_id = int(payload.target_restaurant_id)

    if payload.department is not None:
        row.department = (payload.department or "").strip() or None
        row.department_norm = _normalize_location_token(row.department)
    if payload.table_num is not None:
        row.table_num = (payload.table_num or "").strip() or None
        row.table_num_norm = _normalize_location_token(row.table_num)
    if not row.department_norm:
        raise HTTPException(status_code=400, detail="department is required")

    if payload.comment is not None:
        row.comment = (payload.comment or "").strip() or None
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)

    db.add(row)
    db.commit()
    db.refresh(row)

    if source_restaurant is None and row.source_restaurant_id is not None:
        source_restaurant = (
            db.query(Restaurant)
            .filter(Restaurant.id == int(row.source_restaurant_id))
            .first()
        )
    if target_restaurant is None:
        target_restaurant = (
            db.query(Restaurant)
            .filter(Restaurant.id == int(row.target_restaurant_id))
            .first()
        )

    return _serialize_sales_location_mapping(
        row,
        source_restaurant_name=source_restaurant.name if source_restaurant is not None else None,
        target_restaurant_name=target_restaurant.name if target_restaurant is not None else None,
    )


@router.delete("/sales-location-mappings/{mapping_id}")
def delete_sales_location_mapping(
    mapping_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    row = _sales_location_mappings_query(db, current_user).filter(IikoSalesLocationMapping.id == mapping_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sales location mapping not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "id": str(row.id)}


@router.get("/sales-location-candidates")
def list_sales_location_candidates(
    source_restaurant_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    if source_restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    accessible_ids = [int(r.id) for r in accessible_restaurants]
    restaurant_name_by_id = {int(r.id): r.name for r in accessible_restaurants}
    if not accessible_ids:
        return []

    q = (
        db.query(
            sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id).label("source_restaurant_id"),
            IikoSaleOrder.department.label("department"),
            IikoSaleOrder.table_num.label("table_num"),
            sa.func.count(sa.distinct(IikoSaleOrder.iiko_order_id)).label("orders_count"),
            sa.func.max(IikoSaleOrder.open_date).label("last_open_date"),
        )
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
    )

    if from_date:
        from_value = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
        q = q.filter(IikoSaleOrder.open_date >= from_value)
    if to_date:
        to_value = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)
        q = q.filter(IikoSaleOrder.open_date < to_value)
    if source_restaurant_id is not None:
        q = q.filter(
            sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id) == int(source_restaurant_id)
        )

    rows = (
        q.group_by(
            sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id),
            IikoSaleOrder.department,
            IikoSaleOrder.table_num,
        )
        .order_by(
            sa.func.count(sa.distinct(IikoSaleOrder.iiko_order_id)).desc(),
            sa.func.max(IikoSaleOrder.open_date).desc().nullslast(),
            IikoSaleOrder.department.asc().nullslast(),
            IikoSaleOrder.table_num.asc().nullslast(),
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "source_restaurant_id": int(row.source_restaurant_id) if row.source_restaurant_id is not None else None,
            "source_restaurant_name": (
                restaurant_name_by_id.get(int(row.source_restaurant_id))
                if row.source_restaurant_id is not None
                else None
            ),
            "department": row.department,
            "table_num": row.table_num,
            "department_norm": _normalize_location_token(row.department),
            "table_num_norm": _normalize_location_token(row.table_num),
            "orders_count": int(row.orders_count or 0),
            "last_open_date": row.last_open_date.isoformat() if row.last_open_date else None,
        }
        for row in rows
    ]


@router.get("/sales-halls")
def list_sales_halls(
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    q = _sales_halls_query(db, current_user)
    if not include_inactive:
        q = q.filter(IikoSalesHall.is_active.is_(True))
    rows = q.order_by(
        IikoSalesHall.is_active.desc(),
        IikoSalesHall.name_norm.asc(),
        IikoSalesHall.created_at.asc(),
    ).all()
    return [_serialize_sales_hall(row) for row in rows]


@router.post("/sales-halls")
def create_sales_hall(
    payload: CreateIikoSalesHallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    name_norm = _normalize_location_token(name)

    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        accessible_restaurants = _list_accessible_restaurants(db, current_user)
        company_ids = sorted(
            {
                int(restaurant.company_id)
                for restaurant in accessible_restaurants
                if restaurant.company_id is not None
            }
        )
        if len(company_ids) == 1:
            company_id = int(company_ids[0])

    dup_q = db.query(IikoSalesHall).filter(IikoSalesHall.name_norm == name_norm)
    if company_id is None:
        dup_q = dup_q.filter(IikoSalesHall.company_id.is_(None))
    else:
        dup_q = dup_q.filter(IikoSalesHall.company_id == company_id)
    if dup_q.first() is not None:
        raise HTTPException(status_code=400, detail="Hall with this name already exists")

    row = IikoSalesHall(
        company_id=company_id,
        name=name,
        name_norm=name_norm,
        comment=(payload.comment or "").strip() or None,
        is_active=bool(payload.is_active),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_sales_hall(row)


@router.patch("/sales-halls/{hall_id}")
def update_sales_hall(
    hall_id: UUID,
    payload: UpdateIikoSalesHallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row = _sales_halls_query(db, current_user).filter(IikoSalesHall.id == hall_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Hall not found")

    if payload.name is not None:
        name = (payload.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        name_norm = _normalize_location_token(name)
        dup_q = (
            db.query(IikoSalesHall)
            .filter(IikoSalesHall.id != row.id)
            .filter(IikoSalesHall.name_norm == name_norm)
        )
        if row.company_id is None:
            dup_q = dup_q.filter(IikoSalesHall.company_id.is_(None))
        else:
            dup_q = dup_q.filter(IikoSalesHall.company_id == row.company_id)
        if dup_q.first() is not None:
            raise HTTPException(status_code=400, detail="Hall with this name already exists")
        row.name = name
        row.name_norm = name_norm
    if payload.comment is not None:
        row.comment = (payload.comment or "").strip() or None
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)

    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_sales_hall(row)


@router.delete("/sales-halls/{hall_id}")
def delete_sales_hall(
    hall_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row = _sales_halls_query(db, current_user).filter(IikoSalesHall.id == hall_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Hall not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "id": str(row.id)}


@router.get("/sales-hall-zones")
def list_sales_hall_zones(
    include_inactive: bool = Query(True),
    hall_id: Optional[UUID] = Query(None),
    restaurant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    if restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
    if hall_id is not None:
        hall_exists = _sales_halls_query(db, current_user).filter(IikoSalesHall.id == hall_id).first()
        if hall_exists is None:
            raise HTTPException(status_code=404, detail="Hall not found")

    q = _sales_hall_zones_query(db, current_user)
    if not include_inactive:
        q = q.filter(IikoSalesHallZone.is_active.is_(True))
    if hall_id is not None:
        q = q.filter(IikoSalesHallZone.hall_id == hall_id)
    if restaurant_id is not None:
        q = q.filter(IikoSalesHallZone.restaurant_id == int(restaurant_id))
    rows = q.order_by(
        IikoSalesHallZone.restaurant_id.asc(),
        IikoSalesHallZone.name_norm.asc(),
        IikoSalesHallZone.created_at.asc(),
    ).all()
    if not rows:
        return []

    hall_ids = {
        row.hall_id
        for row in rows
        if row.hall_id is not None
    }
    hall_name_by_id: Dict[str, str] = {}
    if hall_ids:
        hall_rows = (
            db.query(IikoSalesHall.id, IikoSalesHall.name)
            .filter(IikoSalesHall.id.in_(list(hall_ids)))
            .all()
        )
        hall_name_by_id = {
            str(hall_row_id): str(hall_name)
            for hall_row_id, hall_name in hall_rows
            if hall_row_id is not None and hall_name is not None
        }

    restaurant_ids = {
        int(row.restaurant_id)
        for row in rows
        if row.restaurant_id is not None
    }
    restaurant_name_by_id: Dict[int, str] = {}
    if restaurant_ids:
        restaurant_rows = (
            db.query(Restaurant.id, Restaurant.name)
            .filter(Restaurant.id.in_(sorted(restaurant_ids)))
            .all()
        )
        restaurant_name_by_id = {
            int(rest_id): str(rest_name)
            for rest_id, rest_name in restaurant_rows
            if rest_id is not None and rest_name is not None
        }

    return [
        _serialize_sales_hall_zone(
            row,
            hall_name=hall_name_by_id.get(str(row.hall_id)) if row.hall_id is not None else None,
            restaurant_name=restaurant_name_by_id.get(int(row.restaurant_id))
            if row.restaurant_id is not None
            else None,
        )
        for row in rows
    ]


@router.post("/sales-hall-zones")
def create_sales_hall_zone(
    payload: CreateIikoSalesHallZoneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    hall = _sales_halls_query(db, current_user).filter(IikoSalesHall.id == payload.hall_id).first()
    if hall is None:
        raise HTTPException(status_code=404, detail="Hall not found")

    restaurant = _ensure_user_access_to_restaurant(
        db,
        current_user,
        int(payload.restaurant_id),
        require_credentials=False,
    )

    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    name_norm = _normalize_location_token(name)

    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        company_id = restaurant.company_id if restaurant.company_id is not None else hall.company_id
    if company_id is not None:
        if restaurant.company_id not in {None, company_id}:
            raise HTTPException(status_code=400, detail="Restaurant is outside of your company scope")
        if hall.company_id not in {None, company_id}:
            raise HTTPException(status_code=400, detail="Hall is outside of your company scope")
    if hall.company_id is None and company_id is not None:
        hall.company_id = company_id

    dup_q = (
        db.query(IikoSalesHallZone)
        .filter(IikoSalesHallZone.hall_id == hall.id)
        .filter(IikoSalesHallZone.restaurant_id == int(restaurant.id))
        .filter(IikoSalesHallZone.name_norm == name_norm)
    )
    if company_id is None:
        dup_q = dup_q.filter(IikoSalesHallZone.company_id.is_(None))
    else:
        dup_q = dup_q.filter(IikoSalesHallZone.company_id == company_id)
    if dup_q.first() is not None:
        raise HTTPException(status_code=400, detail="Zone with this name already exists for this hall and restaurant")

    row = IikoSalesHallZone(
        company_id=company_id,
        hall_id=hall.id,
        restaurant_id=int(restaurant.id),
        name=name,
        name_norm=name_norm,
        comment=(payload.comment or "").strip() or None,
        is_active=bool(payload.is_active),
    )
    db.add(hall)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_sales_hall_zone(
        row,
        hall_name=hall.name,
        restaurant_name=restaurant.name,
    )


@router.patch("/sales-hall-zones/{zone_id}")
def update_sales_hall_zone(
    zone_id: UUID,
    payload: UpdateIikoSalesHallZoneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    row = _sales_hall_zones_query(db, current_user).filter(IikoSalesHallZone.id == zone_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    if payload.name is not None:
        name = (payload.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        name_norm = _normalize_location_token(name)
        dup_q = (
            db.query(IikoSalesHallZone)
            .filter(IikoSalesHallZone.id != row.id)
            .filter(IikoSalesHallZone.hall_id == row.hall_id)
            .filter(IikoSalesHallZone.restaurant_id == row.restaurant_id)
            .filter(IikoSalesHallZone.name_norm == name_norm)
        )
        if row.company_id is None:
            dup_q = dup_q.filter(IikoSalesHallZone.company_id.is_(None))
        else:
            dup_q = dup_q.filter(IikoSalesHallZone.company_id == row.company_id)
        if dup_q.first() is not None:
            raise HTTPException(status_code=400, detail="Zone with this name already exists for this hall and restaurant")
        row.name = name
        row.name_norm = name_norm
    if payload.comment is not None:
        row.comment = (payload.comment or "").strip() or None
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)

    db.add(row)
    db.commit()
    db.refresh(row)

    hall_row = db.query(IikoSalesHall.id, IikoSalesHall.name).filter(IikoSalesHall.id == row.hall_id).first()
    restaurant_row = db.query(Restaurant.id, Restaurant.name).filter(Restaurant.id == row.restaurant_id).first()
    return _serialize_sales_hall_zone(
        row,
        hall_name=str(hall_row.name) if hall_row is not None and hall_row.name is not None else None,
        restaurant_name=str(restaurant_row.name)
        if restaurant_row is not None and restaurant_row.name is not None
        else None,
    )


@router.delete("/sales-hall-zones/{zone_id}")
def delete_sales_hall_zone(
    zone_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row = _sales_hall_zones_query(db, current_user).filter(IikoSalesHallZone.id == zone_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "id": str(row.id)}


@router.post("/sales-hall-zones/{zone_id}/assign-tables")
def assign_tables_to_sales_hall_zone(
    zone_id: UUID,
    payload: AssignIikoSalesZoneTablesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    zone = _sales_hall_zones_query(db, current_user).filter(IikoSalesHallZone.id == zone_id).first()
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    hall = _sales_halls_query(db, current_user).filter(IikoSalesHall.id == zone.hall_id).first()
    if hall is None:
        raise HTTPException(status_code=404, detail="Hall not found")
    restaurant = _ensure_user_access_to_restaurant(
        db,
        current_user,
        int(zone.restaurant_id),
        require_credentials=False,
    )

    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        company_id = zone.company_id if zone.company_id is not None else restaurant.company_id
    if company_id is None:
        company_id = hall.company_id

    if payload.replace_zone_tables:
        old_rows = (
            _sales_hall_tables_query(db, current_user)
            .filter(IikoSalesHallTable.restaurant_id == int(zone.restaurant_id))
            .filter(IikoSalesHallTable.zone_id == zone.id)
            .all()
        )
        for old_row in old_rows:
            db.delete(old_row)

    source_restaurant_ids = sorted(
        {
            int(item.source_restaurant_id)
            for item in (payload.items or [])
            if item.source_restaurant_id is not None
        }
    )
    for source_restaurant_id in source_restaurant_ids:
        _ensure_user_access_to_restaurant(
            db,
            current_user,
            source_restaurant_id,
            require_credentials=False,
        )

    upserted = 0
    for index, item in enumerate(payload.items or []):
        department = (item.department or "").strip()
        if not department:
            raise HTTPException(status_code=400, detail=f"items[{index}].department is required")
        table_num = (item.table_num or "").strip() or None
        table_name = (item.table_name or "").strip() or table_num
        comment = (item.comment or "").strip() or None
        if item.capacity is not None and int(item.capacity) < 0:
            raise HTTPException(status_code=400, detail=f"items[{index}].capacity cannot be negative")
        capacity = int(item.capacity) if item.capacity is not None else None
        source_restaurant_id_value = int(item.source_restaurant_id) if item.source_restaurant_id is not None else None

        department_norm = _normalize_location_token(department)
        table_num_norm = _normalize_location_token(table_num)
        row = (
            _sales_hall_tables_query(db, current_user)
            .filter(IikoSalesHallTable.restaurant_id == int(zone.restaurant_id))
            .filter(IikoSalesHallTable.source_restaurant_id == source_restaurant_id_value)
            .filter(IikoSalesHallTable.department_norm == department_norm)
            .filter(IikoSalesHallTable.table_num_norm == table_num_norm)
            .first()
        )

        if row is None:
            row = IikoSalesHallTable(
                company_id=company_id,
                restaurant_id=int(zone.restaurant_id),
                hall_id=hall.id,
                zone_id=zone.id,
                source_restaurant_id=source_restaurant_id_value,
                department=department,
                table_num=table_num,
                department_norm=department_norm,
                table_num_norm=table_num_norm,
                hall_name=hall.name,
                hall_name_norm=_normalize_location_token(hall.name),
                zone_name=zone.name,
                zone_name_norm=_normalize_location_token(zone.name),
                table_name=table_name,
                capacity=capacity,
                comment=comment,
                is_active=bool(item.is_active),
            )
        else:
            row.company_id = company_id
            row.restaurant_id = int(zone.restaurant_id)
            row.hall_id = hall.id
            row.zone_id = zone.id
            row.source_restaurant_id = source_restaurant_id_value
            row.department = department
            row.table_num = table_num
            row.department_norm = department_norm
            row.table_num_norm = table_num_norm
            row.hall_name = hall.name
            row.hall_name_norm = _normalize_location_token(hall.name)
            row.zone_name = zone.name
            row.zone_name_norm = _normalize_location_token(zone.name)
            row.table_name = table_name
            row.capacity = capacity
            row.comment = comment
            row.is_active = bool(item.is_active)
        db.add(row)
        upserted += 1

    db.commit()
    return {"status": "ok", "zone_id": str(zone.id), "upserted": upserted}


@router.get("/sales-hall-tables")
def list_sales_hall_tables(
    include_inactive: bool = Query(True),
    restaurant_id: Optional[int] = Query(None),
    source_restaurant_id: Optional[int] = Query(None),
    hall_id: Optional[UUID] = Query(None),
    zone_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    if restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
    if source_restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)
    if hall_id is not None:
        hall_exists = _sales_halls_query(db, current_user).filter(IikoSalesHall.id == hall_id).first()
        if hall_exists is None:
            raise HTTPException(status_code=404, detail="Hall not found")
    if zone_id is not None:
        zone_exists = _sales_hall_zones_query(db, current_user).filter(IikoSalesHallZone.id == zone_id).first()
        if zone_exists is None:
            raise HTTPException(status_code=404, detail="Zone not found")

    q = _sales_hall_tables_query(db, current_user)
    if not include_inactive:
        q = q.filter(IikoSalesHallTable.is_active.is_(True))
    if restaurant_id is not None:
        q = q.filter(IikoSalesHallTable.restaurant_id == int(restaurant_id))
    if source_restaurant_id is not None:
        q = q.filter(IikoSalesHallTable.source_restaurant_id == int(source_restaurant_id))
    if hall_id is not None:
        q = q.filter(IikoSalesHallTable.hall_id == hall_id)
    if zone_id is not None:
        q = q.filter(IikoSalesHallTable.zone_id == zone_id)

    rows = q.order_by(
        IikoSalesHallTable.restaurant_id.asc(),
        IikoSalesHallTable.hall_name_norm.asc(),
        IikoSalesHallTable.department_norm.asc(),
        IikoSalesHallTable.table_num_norm.asc(),
    ).all()

    restaurant_ids = {
        int(row.restaurant_id)
        for row in rows
        if row.restaurant_id is not None
    }.union(
        {
            int(row.source_restaurant_id)
            for row in rows
            if row.source_restaurant_id is not None
        }
    )
    restaurant_name_by_id: Dict[int, str] = {}
    if restaurant_ids:
        name_rows = (
            db.query(Restaurant.id, Restaurant.name)
            .filter(Restaurant.id.in_(sorted(restaurant_ids)))
            .all()
        )
        restaurant_name_by_id = {
            int(rest_id): str(rest_name)
            for rest_id, rest_name in name_rows
            if rest_id is not None and rest_name is not None
        }

    return [
        _serialize_sales_hall_table(
            row,
            restaurant_name=restaurant_name_by_id.get(int(row.restaurant_id))
            if row.restaurant_id is not None
            else None,
            source_restaurant_name=restaurant_name_by_id.get(int(row.source_restaurant_id))
            if row.source_restaurant_id is not None
            else None,
        )
        for row in rows
    ]


@router.put("/sales-hall-tables")
def upsert_sales_hall_table(
    payload: UpsertIikoSalesHallTableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    restaurant = _ensure_user_access_to_restaurant(
        db,
        current_user,
        int(payload.restaurant_id),
        require_credentials=False,
    )
    source_restaurant: Optional[Restaurant] = None
    if payload.source_restaurant_id is not None:
        source_restaurant = _ensure_user_access_to_restaurant(
            db,
            current_user,
            int(payload.source_restaurant_id),
            require_credentials=False,
        )

    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        company_id = restaurant.company_id
    if company_id is not None:
        if restaurant.company_id not in {None, company_id}:
            raise HTTPException(status_code=400, detail="Restaurant is outside of your company scope")
        if source_restaurant is not None and source_restaurant.company_id not in {None, company_id}:
            raise HTTPException(status_code=400, detail="Source restaurant is outside of your company scope")

    department = (payload.department or "").strip() or None
    table_num = (payload.table_num or "").strip() or None
    hall_name = (payload.hall_name or "").strip()
    table_name = (payload.table_name or "").strip() or None
    comment = (payload.comment or "").strip() or None
    if not department:
        raise HTTPException(status_code=400, detail="department is required")
    if not hall_name:
        raise HTTPException(status_code=400, detail="hall_name is required")
    capacity = payload.capacity
    if capacity is not None and int(capacity) < 0:
        raise HTTPException(status_code=400, detail="capacity cannot be negative")

    department_norm = _normalize_location_token(department)
    table_num_norm = _normalize_location_token(table_num)
    hall_name_norm = _normalize_location_token(hall_name)
    source_restaurant_id_value = int(payload.source_restaurant_id) if payload.source_restaurant_id is not None else None

    row = (
        _sales_hall_tables_query(db, current_user)
        .filter(IikoSalesHallTable.restaurant_id == int(payload.restaurant_id))
        .filter(IikoSalesHallTable.source_restaurant_id == source_restaurant_id_value)
        .filter(IikoSalesHallTable.department_norm == department_norm)
        .filter(IikoSalesHallTable.table_num_norm == table_num_norm)
        .first()
    )

    if row is None:
        row = IikoSalesHallTable(
            company_id=company_id,
            restaurant_id=int(payload.restaurant_id),
            source_restaurant_id=source_restaurant_id_value,
            department=department,
            table_num=table_num,
            department_norm=department_norm,
            table_num_norm=table_num_norm,
            hall_name=hall_name,
            hall_name_norm=hall_name_norm,
            table_name=table_name,
            capacity=int(capacity) if capacity is not None else None,
            comment=comment,
            is_active=bool(payload.is_active),
        )
    else:
        row.company_id = company_id
        row.restaurant_id = int(payload.restaurant_id)
        row.source_restaurant_id = source_restaurant_id_value
        row.department = department
        row.table_num = table_num
        row.department_norm = department_norm
        row.table_num_norm = table_num_norm
        row.hall_name = hall_name
        row.hall_name_norm = hall_name_norm
        row.table_name = table_name
        row.capacity = int(capacity) if capacity is not None else None
        row.comment = comment
        row.is_active = bool(payload.is_active)

    db.add(row)
    db.commit()
    db.refresh(row)

    return _serialize_sales_hall_table(
        row,
        restaurant_name=restaurant.name,
        source_restaurant_name=source_restaurant.name if source_restaurant is not None else None,
    )


@router.patch("/sales-hall-tables/{row_id}")
def update_sales_hall_table(
    row_id: str,
    payload: UpdateIikoSalesHallTableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    row = _sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Hall table mapping not found")

    restaurant: Optional[Restaurant] = None
    source_restaurant: Optional[Restaurant] = None
    if payload.restaurant_id is not None:
        restaurant = _ensure_user_access_to_restaurant(
            db,
            current_user,
            int(payload.restaurant_id),
            require_credentials=False,
        )
        row.restaurant_id = int(payload.restaurant_id)
    if payload.source_restaurant_id is not None:
        source_restaurant = _ensure_user_access_to_restaurant(
            db,
            current_user,
            int(payload.source_restaurant_id),
            require_credentials=False,
        )
        row.source_restaurant_id = int(payload.source_restaurant_id)

    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        if restaurant is not None:
            company_id = restaurant.company_id
        else:
            company_id = row.company_id
    row.company_id = company_id

    if payload.department is not None:
        row.department = (payload.department or "").strip() or None
        row.department_norm = _normalize_location_token(row.department)
    if payload.table_num is not None:
        row.table_num = (payload.table_num or "").strip() or None
        row.table_num_norm = _normalize_location_token(row.table_num)
    if payload.hall_name is not None:
        row.hall_name = (payload.hall_name or "").strip()
        row.hall_name_norm = _normalize_location_token(row.hall_name)
    if payload.table_name is not None:
        row.table_name = (payload.table_name or "").strip() or None
    if payload.capacity is not None:
        if int(payload.capacity) < 0:
            raise HTTPException(status_code=400, detail="capacity cannot be negative")
        row.capacity = int(payload.capacity)
    if payload.comment is not None:
        row.comment = (payload.comment or "").strip() or None
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)

    if not row.department_norm:
        raise HTTPException(status_code=400, detail="department is required")
    if not (row.hall_name or "").strip():
        raise HTTPException(status_code=400, detail="hall_name is required")
    row.hall_name_norm = _normalize_location_token(row.hall_name)

    db.add(row)
    db.commit()
    db.refresh(row)

    if restaurant is None:
        restaurant = db.query(Restaurant).filter(Restaurant.id == int(row.restaurant_id)).first()
    if source_restaurant is None and row.source_restaurant_id is not None:
        source_restaurant = db.query(Restaurant).filter(Restaurant.id == int(row.source_restaurant_id)).first()

    return _serialize_sales_hall_table(
        row,
        restaurant_name=restaurant.name if restaurant is not None else None,
        source_restaurant_name=source_restaurant.name if source_restaurant is not None else None,
    )


@router.delete("/sales-hall-tables/{row_id}")
def delete_sales_hall_table(
    row_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)

    row = _sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Hall table mapping not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "id": str(row.id)}


@router.get("/sales-hall-table-candidates")
def list_sales_hall_table_candidates(
    restaurant_id: Optional[int] = Query(None),
    source_restaurant_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    if restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
    if source_restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    restaurant_name_by_id = {int(row.id): row.name for row in accessible_restaurants if row.id is not None}
    if not accessible_restaurants:
        return []
    accessible_ids = [int(row.id) for row in accessible_restaurants if row.id is not None]
    if not accessible_ids:
        return []

    hall_rows_q = _sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.is_active.is_(True))
    if restaurant_id is not None:
        hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.restaurant_id == int(restaurant_id))
    resolve_hall = _build_sales_hall_table_resolver(hall_rows_q.all())

    from_date_value, to_date_value = _resolve_hall_table_candidates_window(from_date, to_date)
    start_date = datetime.strptime(from_date_value, "%Y-%m-%d").date()
    end_date = datetime.strptime(to_date_value, "%Y-%m-%d").date()
    source_restaurant_expr = sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id)

    sales_rows_q = (
        db.query(
            IikoSaleOrder.restaurant_id.label("restaurant_id"),
            source_restaurant_expr.label("source_restaurant_id"),
            IikoSaleOrder.department.label("department"),
            IikoSaleOrder.table_num.label("table_num"),
            sa.func.count(IikoSaleOrder.id).label("orders_count"),
            sa.func.coalesce(sa.func.sum(sa.func.coalesce(IikoSaleOrder.guest_num, 0)), 0).label("guests_count"),
            sa.func.max(IikoSaleOrder.open_date).label("last_open_date"),
        )
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date.isnot(None))
        .filter(IikoSaleOrder.open_date >= start_date)
        .filter(IikoSaleOrder.open_date <= end_date)
    )
    if restaurant_id is not None:
        sales_rows_q = sales_rows_q.filter(IikoSaleOrder.restaurant_id == int(restaurant_id))
    if source_restaurant_id is not None:
        sales_rows_q = sales_rows_q.filter(source_restaurant_expr == int(source_restaurant_id))
    sales_rows = (
        sales_rows_q.group_by(
            IikoSaleOrder.restaurant_id,
            source_restaurant_expr,
            IikoSaleOrder.department,
            IikoSaleOrder.table_num,
        ).all()
    )

    items_by_scope: Dict[tuple[int, Optional[int], str, str], Dict[str, Any]] = {}
    for row in sales_rows:
        resolved_restaurant_id = int(row.restaurant_id) if row.restaurant_id is not None else None
        source_restaurant_id_value = int(row.source_restaurant_id) if row.source_restaurant_id is not None else None
        if resolved_restaurant_id is None:
            continue

        department = str(row.department or "").strip()
        table_num = str(row.table_num or "").strip()
        department_norm = _normalize_location_token(department)
        table_num_norm = _normalize_location_token(table_num)
        if not department_norm and not table_num_norm:
            continue

        scope_key = (
            resolved_restaurant_id,
            source_restaurant_id_value,
            department_norm,
            table_num_norm,
        )
        resolved = resolve_hall(
            restaurant_id=resolved_restaurant_id,
            source_restaurant_id=source_restaurant_id_value,
            department=department,
            table_num=table_num,
        )
        last_open_date = row.last_open_date.isoformat() if row.last_open_date is not None else None
        items_by_scope[scope_key] = {
            "restaurant_id": resolved_restaurant_id,
            "restaurant_name": restaurant_name_by_id.get(resolved_restaurant_id),
            "source_restaurant_id": source_restaurant_id_value,
            "source_restaurant_name": (
                restaurant_name_by_id.get(source_restaurant_id_value)
                if source_restaurant_id_value is not None
                else None
            ),
            "department": department,
            "table_num": table_num,
            "department_norm": department_norm,
            "table_num_norm": table_num_norm,
            "orders_count": int(row.orders_count or 0),
            "guests_count": int(row.guests_count or 0),
            "last_open_date": last_open_date,
            "hall_name": resolved.get("hall_name"),
            "zone_name": resolved.get("zone_name"),
            "table_name": resolved.get("table_name"),
            "capacity": resolved.get("capacity"),
        }

    if not items_by_scope:
        return []

    missing_restaurant_ids = {
        int(item.get("restaurant_id"))
        for item in items_by_scope.values()
        if item.get("restaurant_id") is not None and int(item.get("restaurant_id")) not in restaurant_name_by_id
    }
    if missing_restaurant_ids:
        name_rows = (
            db.query(Restaurant.id, Restaurant.name)
            .filter(Restaurant.id.in_(sorted(missing_restaurant_ids)))
            .all()
        )
        for rest_id, rest_name in name_rows:
            if rest_id is None or rest_name is None:
                continue
            restaurant_name_by_id[int(rest_id)] = str(rest_name)

    items = list(items_by_scope.values())
    for item in items:
        restaurant_id_value = item.get("restaurant_id")
        source_id_value = item.get("source_restaurant_id")
        if restaurant_id_value is not None and not item.get("restaurant_name"):
            item["restaurant_name"] = restaurant_name_by_id.get(int(restaurant_id_value))
        if source_id_value is not None and not item.get("source_restaurant_name"):
            item["source_restaurant_name"] = restaurant_name_by_id.get(int(source_id_value))

    items.sort(
        key=lambda item: (
            _normalize_location_token(item.get("restaurant_name") or item.get("restaurant_id")),
            _normalize_location_token(item.get("source_restaurant_name") or item.get("source_restaurant_id")),
            _normalize_location_token(item.get("department")),
            _normalize_location_token(item.get("table_num")),
        )
    )
    return items[:limit]


@router.get("/waiter-turnover-rules")
def list_waiter_turnover_rules(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    resolved_company_id = _resolve_settings_company_id(db, current_user, company_id)
    rows = (
        _waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
        .order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
            IikoWaiterTurnoverSetting.created_at.desc().nullslast(),
        )
        .all()
    )
    return {
        "company_id": resolved_company_id,
        "items": _waiter_turnover_rules_list_payload(rows),
        "position_options": _position_options_for_settings(db),
    }


@router.get("/waiter-turnover-rules/{rule_id}")
def get_waiter_turnover_rule(
    rule_id: UUID,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    resolved_company_id = _resolve_settings_company_id(db, current_user, company_id)
    row = _find_waiter_turnover_rule(db, current_user, resolved_company_id, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    payload = _serialize_waiter_turnover_settings(row, resolved_company_id)
    payload["position_options"] = _position_options_for_settings(db)
    return payload


@router.post("/waiter-turnover-rules")
def create_waiter_turnover_rule(
    payload: UpdateIikoWaiterTurnoverSettingsRequest,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    resolved_company_id = _resolve_settings_company_id(db, current_user, company_id)
    company_q = _waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
    existing_count = company_q.count()

    row = IikoWaiterTurnoverSetting(company_id=resolved_company_id)
    row.rule_name = _normalize_rule_name(
        payload.rule_name,
        _default_waiter_turnover_rule_name(existing_count),
    )
    row.is_active = bool(payload.is_active) if payload.is_active is not None else existing_count == 0
    db.add(row)
    _apply_waiter_turnover_settings_payload(db, row, payload)
    db.flush()
    if row.is_active:
        _deactivate_other_waiter_turnover_rules(db, resolved_company_id, row.id)
    db.commit()
    db.refresh(row)

    result = _serialize_waiter_turnover_settings(row, resolved_company_id)
    result["position_options"] = _position_options_for_settings(db)
    return result


@router.patch("/waiter-turnover-rules/{rule_id}")
def update_waiter_turnover_rule(
    rule_id: UUID,
    payload: UpdateIikoWaiterTurnoverSettingsRequest,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    resolved_company_id = _resolve_settings_company_id(db, current_user, company_id)
    row = _find_waiter_turnover_rule(db, current_user, resolved_company_id, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")

    _apply_waiter_turnover_settings_payload(db, row, payload)
    db.add(row)
    db.flush()
    if row.is_active:
        _deactivate_other_waiter_turnover_rules(db, resolved_company_id, row.id)
    db.commit()
    db.refresh(row)

    result = _serialize_waiter_turnover_settings(row, resolved_company_id)
    result["position_options"] = _position_options_for_settings(db)
    return result


@router.delete("/waiter-turnover-rules/{rule_id}", status_code=204)
def delete_waiter_turnover_rule(
    rule_id: UUID,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    resolved_company_id = _resolve_settings_company_id(db, current_user, company_id)
    row = _find_waiter_turnover_rule(db, current_user, resolved_company_id, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")

    was_active = bool(row.is_active)
    db.delete(row)
    db.flush()
    if was_active:
        fallback = (
            _waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
            .order_by(IikoWaiterTurnoverSetting.updated_at.desc().nullslast())
            .first()
        )
        if fallback:
            fallback.is_active = True
            db.add(fallback)
    db.commit()
    return None


@router.get("/waiter-turnover-settings")
def get_waiter_turnover_settings(
    company_id: Optional[int] = Query(None),
    rule_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)

    resolved_company_id = _resolve_settings_company_id(db, current_user, company_id)
    q = _waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
    if rule_id is not None:
        row = q.filter(IikoWaiterTurnoverSetting.id == rule_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Rule not found")
    else:
        row = q.order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
        ).first()
    payload = _serialize_waiter_turnover_settings(row, resolved_company_id)
    payload["position_options"] = _position_options_for_settings(db)
    payload["rules"] = _waiter_turnover_rules_list_payload(
        q.order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
        ).all()
    )
    return payload


@router.put("/waiter-turnover-settings")
def upsert_waiter_turnover_settings(
    payload: UpdateIikoWaiterTurnoverSettingsRequest,
    company_id: Optional[int] = Query(None),
    rule_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)

    resolved_company_id = _resolve_settings_company_id(db, current_user, company_id)
    q = _waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
    row = None
    if rule_id is not None:
        row = q.filter(IikoWaiterTurnoverSetting.id == rule_id).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Rule not found")
    else:
        row = q.order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
        ).first()

    if row is None:
        row = IikoWaiterTurnoverSetting(
            company_id=resolved_company_id,
            rule_name=_normalize_rule_name(payload.rule_name, "Основное правило"),
        )
        db.add(row)

    _apply_waiter_turnover_settings_payload(db, row, payload)
    db.add(row)
    db.flush()
    if row.is_active:
        _deactivate_other_waiter_turnover_rules(db, resolved_company_id, row.id)
    db.commit()
    db.refresh(row)

    result = _serialize_waiter_turnover_settings(row, resolved_company_id)
    result["position_options"] = _position_options_for_settings(db)
    result["rules"] = _waiter_turnover_rules_list_payload(
        q.order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
        ).all()
    )
    return result


@router.get("/payment-methods")
def list_payment_methods(
    include_inactive: bool = Query(True),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)

    q = _payment_methods_query(db, current_user)
    if not include_inactive:
        q = q.filter(IikoPaymentMethod.is_active.is_(True))

    if category:
        clean_category = category.strip()
        if clean_category.lower() in {"null", "none", "-"}:
            q = q.filter(IikoPaymentMethod.category.is_(None))
        else:
            q = q.filter(IikoPaymentMethod.category == clean_category)

    rows = q.order_by(
        IikoPaymentMethod.name.asc(),
        IikoPaymentMethod.guid.asc(),
    ).all()

    return [_serialize_payment_method(row) for row in rows]


@router.patch("/payment-methods/{guid}")
def update_payment_method(
    guid: str,
    payload: UpdateIikoPaymentMethodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)

    row = _payment_methods_query(db, current_user).filter(IikoPaymentMethod.guid == guid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Payment method not found")

    if payload.category is not None:
        clean_category = payload.category.strip()
        row.category = clean_category or None

    if payload.comment is not None:
        clean_comment = payload.comment.strip()
        row.comment = clean_comment or None

    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)

    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_payment_method(row)


@router.get("/non-cash-types")
def list_non_cash_types(
    include_inactive: bool = Query(True),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)

    q = _non_cash_types_query(db, current_user)
    if not include_inactive:
        q = q.filter(IikoNonCashPaymentType.is_active.is_(True))

    if category:
        clean_category = category.strip()
        if clean_category.lower() in {"null", "none", "-"}:
            q = q.filter(IikoNonCashPaymentType.category.is_(None))
        else:
            q = q.filter(IikoNonCashPaymentType.category == clean_category)

    rows = q.order_by(IikoNonCashPaymentType.name.asc(), IikoNonCashPaymentType.id.asc()).all()
    return [_serialize_non_cash_type(row) for row in rows]


@router.post("/non-cash-types")
def create_non_cash_type(
    payload: CreateIikoNonCashTypeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)

    clean_id = (payload.id or "").strip()
    clean_name = (payload.name or "").strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="id is required")
    if not clean_name:
        raise HTTPException(status_code=400, detail="name is required")

    existing = _non_cash_types_query(db, current_user).filter(IikoNonCashPaymentType.id == clean_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Non-cash type already exists")

    row = IikoNonCashPaymentType(
        id=clean_id,
        company_id=getattr(current_user, "company_id", None),
        name=clean_name,
        category=(payload.category or "").strip() or None,
        comment=(payload.comment or "").strip() or None,
        is_active=bool(payload.is_active),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_non_cash_type(row)


@router.patch("/non-cash-types/{non_cash_type_id}")
def update_non_cash_type(
    non_cash_type_id: str,
    payload: UpdateIikoNonCashTypeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)

    row = _non_cash_types_query(db, current_user).filter(IikoNonCashPaymentType.id == non_cash_type_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Non-cash type not found")

    if payload.category is not None:
        clean_category = payload.category.strip()
        row.category = clean_category or None

    if payload.comment is not None:
        clean_comment = payload.comment.strip()
        row.comment = clean_comment or None

    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)

    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_non_cash_type(row)


@router.get("/non-cash-employee-limits")
def list_non_cash_employee_limits(
    include_inactive: bool = Query(True),
    non_cash_type_id: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)

    q = _non_cash_limits_query(db, current_user)
    if not include_inactive:
        q = q.filter(IikoNonCashEmployeeLimit.is_active.is_(True))

    clean_non_cash_type_id = (non_cash_type_id or "").strip() or None
    if clean_non_cash_type_id:
        q = q.filter(IikoNonCashEmployeeLimit.non_cash_type_id == clean_non_cash_type_id)
    if user_id is not None:
        q = q.filter(IikoNonCashEmployeeLimit.user_id == user_id)

    rows = q.order_by(
        IikoNonCashEmployeeLimit.non_cash_type_id.asc(),
        IikoNonCashEmployeeLimit.user_id.asc(),
        IikoNonCashEmployeeLimit.period_type.asc(),
    ).all()

    non_cash_ids = {row.non_cash_type_id for row in rows if row.non_cash_type_id}
    user_ids = {int(row.user_id) for row in rows if row.user_id is not None}
    non_cash_lookup = _non_cash_lookup_by_id(db, current_user, non_cash_ids)
    user_name_by_id = _user_names_by_ids(db, user_ids)

    return [
        _serialize_non_cash_limit(
            row,
            non_cash_name=non_cash_lookup.get(str(row.non_cash_type_id), {}).get("name"),
            user_name=user_name_by_id.get(int(row.user_id)) if row.user_id is not None else None,
        )
        for row in rows
    ]


@router.put("/non-cash-employee-limits")
def upsert_non_cash_employee_limit(
    payload: UpsertIikoNonCashEmployeeLimitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)

    clean_non_cash_type_id = (payload.non_cash_type_id or "").strip()
    if not clean_non_cash_type_id:
        raise HTTPException(status_code=400, detail="non_cash_type_id is required")

    period_type = _normalize_period_type(payload.period_type)
    limit_amount = _to_decimal(payload.limit_amount)
    if payload.limit_amount is not None and limit_amount is None:
        raise HTTPException(status_code=400, detail="limit_amount must be a number")

    non_cash_row = (
        _non_cash_types_query(db, current_user)
        .filter(IikoNonCashPaymentType.id == clean_non_cash_type_id)
        .first()
    )
    if not non_cash_row:
        raise HTTPException(status_code=404, detail="Non-cash type not found")

    user_row = db.query(User).filter(User.id == payload.user_id).first()
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
    if getattr(current_user, "company_id", None) is not None and user_row.company_id != current_user.company_id:
        raise HTTPException(status_code=400, detail="User is outside of your company scope")

    row = (
        _non_cash_limits_query(db, current_user)
        .filter(IikoNonCashEmployeeLimit.non_cash_type_id == clean_non_cash_type_id)
        .filter(IikoNonCashEmployeeLimit.user_id == payload.user_id)
        .filter(IikoNonCashEmployeeLimit.period_type == period_type)
        .first()
    )
    if row is None:
        row = IikoNonCashEmployeeLimit(
            company_id=non_cash_row.company_id or getattr(current_user, "company_id", None),
            non_cash_type_id=clean_non_cash_type_id,
            user_id=payload.user_id,
            period_type=period_type,
        )

    row.limit_amount = limit_amount
    row.comment = (payload.comment or "").strip() or None
    row.is_active = bool(payload.is_active)

    db.add(row)
    db.commit()
    db.refresh(row)

    return _serialize_non_cash_limit(
        row,
        non_cash_name=non_cash_row.name,
        user_name=_user_display_name(
            user_row.first_name,
            user_row.last_name,
            user_row.middle_name,
            user_row.username,
        ),
    )


@router.patch("/non-cash-employee-limits/{limit_id}")
def update_non_cash_employee_limit(
    limit_id: str,
    payload: UpdateIikoNonCashEmployeeLimitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)

    row = _non_cash_limits_query(db, current_user).filter(IikoNonCashEmployeeLimit.id == limit_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Non-cash employee limit not found")

    if payload.period_type is not None:
        row.period_type = _normalize_period_type(payload.period_type)
    if payload.limit_amount is not None:
        parsed_amount = _to_decimal(payload.limit_amount)
        if parsed_amount is None:
            raise HTTPException(status_code=400, detail="limit_amount must be a number")
        row.limit_amount = parsed_amount
    if payload.comment is not None:
        row.comment = (payload.comment or "").strip() or None
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)

    db.add(row)
    db.commit()
    db.refresh(row)

    non_cash_name = (
        _non_cash_types_query(db, current_user)
        .filter(IikoNonCashPaymentType.id == row.non_cash_type_id)
        .with_entities(IikoNonCashPaymentType.name)
        .scalar()
    )
    user_name = _user_names_by_ids(db, {int(row.user_id)}).get(int(row.user_id)) if row.user_id is not None else None
    return _serialize_non_cash_limit(row, non_cash_name=non_cash_name, user_name=user_name)


@router.delete("/non-cash-employee-limits/{limit_id}")
def delete_non_cash_employee_limit(
    limit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)

    row = _non_cash_limits_query(db, current_user).filter(IikoNonCashEmployeeLimit.id == limit_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Non-cash employee limit not found")

    db.delete(row)
    db.commit()
    return {"status": "ok", "id": str(row.id)}


@router.get("/non-cash-consumption")
def list_non_cash_consumption(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_id: Optional[int] = Query(None),
    non_cash_type_id: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    include_inactive_limits: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    if restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    accessible_ids = [r.id for r in accessible_restaurants]
    restaurant_name_by_id = {r.id: r.name for r in accessible_restaurants}
    if not accessible_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "items": [],
            "unmapped": [],
            "types": [],
            "totals_by_restaurant": [],
            "totals": {"mapped_consumed": 0.0, "unmapped_consumed": 0.0, "total_consumed": 0.0},
        }

    clean_non_cash_type_id = (non_cash_type_id or "").strip() or None
    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)

    known_non_cash_rows = (
        _non_cash_types_query(db, current_user)
        .with_entities(IikoNonCashPaymentType.id, IikoNonCashPaymentType.name)
        .all()
    )
    non_cash_id_by_name: Dict[str, str] = {}
    for known_id, known_name in known_non_cash_rows:
        clean_name = (known_name or "").strip()
        clean_id = (known_id or "").strip()
        if not clean_name or not clean_id:
            continue
        key = clean_name.casefold()
        if key not in non_cash_id_by_name:
            non_cash_id_by_name[key] = clean_id

    non_cash_id_expr = IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext
    non_cash_name_expr = IikoSaleItem.raw_payload["NonCashPaymentType"].astext
    base_items_q = (
        db.query(IikoSaleItem)
        .filter(IikoSaleItem.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleItem.open_date >= start)
        .filter(IikoSaleItem.open_date < end_excl)
        .filter(sa.or_(non_cash_id_expr.isnot(None), non_cash_name_expr.isnot(None)))
    )
    if restaurant_id is not None:
        base_items_q = base_items_q.filter(IikoSaleItem.restaurant_id == restaurant_id)

    consumption_rows = (
        base_items_q.with_entities(
            non_cash_id_expr.label("non_cash_type_id"),
            non_cash_name_expr.label("non_cash_type_name"),
            IikoSaleItem.restaurant_id.label("restaurant_id"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("consumed_amount"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("consumed_qty"),
            sa.func.count(sa.distinct(IikoSaleItem.order_id)).label("orders_count"),
            sa.func.count(IikoSaleItem.id).label("items_count"),
        )
        .group_by(non_cash_id_expr, non_cash_name_expr, IikoSaleItem.restaurant_id)
        .all()
    )
    consumption_by_type: Dict[str, Dict[str, Any]] = {}
    for row in consumption_rows:
        type_id, type_name = _normalize_non_cash_type(row.non_cash_type_id, row.non_cash_type_name)
        if not type_id:
            continue
        if type_name and str(type_id).startswith("non_cash_name::"):
            mapped_id = non_cash_id_by_name.get(type_name.casefold())
            if mapped_id:
                type_id = mapped_id
        if clean_non_cash_type_id and str(type_id) != clean_non_cash_type_id:
            continue

        key = str(type_id)
        existing = consumption_by_type.get(key)
        if not existing:
            consumption_by_type[key] = {
                "name": type_name,
                "consumed_amount": 0.0,
                "consumed_qty": 0.0,
                "orders_count": 0,
                "items_count": 0,
                "restaurants": {},
            }
            existing = consumption_by_type[key]

        amount = float(row.consumed_amount or 0)
        qty = float(row.consumed_qty or 0)
        orders_count = int(row.orders_count or 0)
        items_count = int(row.items_count or 0)

        existing["consumed_amount"] = float(existing.get("consumed_amount") or 0) + amount
        existing["consumed_qty"] = float(existing.get("consumed_qty") or 0) + qty
        existing["orders_count"] = int(existing.get("orders_count") or 0) + orders_count
        existing["items_count"] = int(existing.get("items_count") or 0) + items_count
        if not existing.get("name") and type_name:
            existing["name"] = type_name

        rest_id = int(row.restaurant_id) if row.restaurant_id is not None else None
        if rest_id is not None:
            rest_stats = existing["restaurants"].setdefault(
                rest_id,
                {
                    "consumed_amount": 0.0,
                    "consumed_qty": 0.0,
                    "orders_count": 0,
                    "items_count": 0,
                },
            )
            rest_stats["consumed_amount"] = float(rest_stats.get("consumed_amount") or 0) + amount
            rest_stats["consumed_qty"] = float(rest_stats.get("consumed_qty") or 0) + qty
            rest_stats["orders_count"] = int(rest_stats.get("orders_count") or 0) + orders_count
            rest_stats["items_count"] = int(rest_stats.get("items_count") or 0) + items_count

    def _serialize_category_stats(categories_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for category_name, stats in categories_map.items():
            rows.append(
                {
                    "category_name": category_name or "Uncategorized",
                    "consumed_amount": float(stats.get("consumed_amount") or 0),
                    "consumed_qty": float(stats.get("consumed_qty") or 0),
                    "orders_count": int(stats.get("orders_count") or 0),
                    "items_count": int(stats.get("items_count") or 0),
                }
            )
        rows.sort(
            key=lambda item: (
                -float(item.get("consumed_amount") or 0),
                str(item.get("category_name") or ""),
            )
        )
        return rows

    def _serialize_restaurant_stats(restaurants_map: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for rest_id in sorted(restaurants_map.keys()):
            rest_stats = restaurants_map.get(rest_id) or {}
            rows.append(
                {
                    "restaurant_id": int(rest_id),
                    "restaurant_name": restaurant_name_by_id.get(int(rest_id)),
                    "consumed_amount": float(rest_stats.get("consumed_amount") or 0),
                    "consumed_qty": float(rest_stats.get("consumed_qty") or 0),
                    "orders_count": int(rest_stats.get("orders_count") or 0),
                    "items_count": int(rest_stats.get("items_count") or 0),
                }
            )
        return rows

    category_expr = _dish_category_sql_expr(with_fallback=True)
    category_rows = (
        base_items_q
        .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .with_entities(
            non_cash_id_expr.label("non_cash_type_id"),
            non_cash_name_expr.label("non_cash_type_name"),
            IikoSaleItem.restaurant_id.label("restaurant_id"),
            category_expr.label("category_name"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("consumed_amount"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("consumed_qty"),
            sa.func.count(sa.distinct(IikoSaleItem.order_id)).label("orders_count"),
            sa.func.count(IikoSaleItem.id).label("items_count"),
        )
        .group_by(non_cash_id_expr, non_cash_name_expr, IikoSaleItem.restaurant_id, category_expr)
        .all()
    )
    categories_by_type_by_restaurant: Dict[str, Dict[int, Dict[str, Dict[str, Any]]]] = {}
    for row in category_rows:
        type_id, type_name = _normalize_non_cash_type(row.non_cash_type_id, row.non_cash_type_name)
        if not type_id:
            continue
        if type_name and str(type_id).startswith("non_cash_name::"):
            mapped_id = non_cash_id_by_name.get(type_name.casefold())
            if mapped_id:
                type_id = mapped_id
        if clean_non_cash_type_id and str(type_id) != clean_non_cash_type_id:
            continue
        rest_id = int(row.restaurant_id) if row.restaurant_id is not None else None
        if rest_id is None:
            continue
        category_name = str(row.category_name or "").strip() or "Uncategorized"
        amount = float(row.consumed_amount or 0)
        qty = float(row.consumed_qty or 0)
        orders_count = int(row.orders_count or 0)
        items_count = int(row.items_count or 0)

        category_bucket = (
            categories_by_type_by_restaurant
            .setdefault(str(type_id), {})
            .setdefault(rest_id, {})
            .setdefault(
                category_name,
                {
                    "consumed_amount": 0.0,
                    "consumed_qty": 0.0,
                    "orders_count": 0,
                    "items_count": 0,
                },
            )
        )
        category_bucket["consumed_amount"] = float(category_bucket.get("consumed_amount") or 0) + amount
        category_bucket["consumed_qty"] = float(category_bucket.get("consumed_qty") or 0) + qty
        category_bucket["orders_count"] = int(category_bucket.get("orders_count") or 0) + orders_count
        category_bucket["items_count"] = int(category_bucket.get("items_count") or 0) + items_count

    limits_q = _non_cash_limits_query(db, current_user)
    if not include_inactive_limits:
        limits_q = limits_q.filter(IikoNonCashEmployeeLimit.is_active.is_(True))
    if clean_non_cash_type_id:
        limits_q = limits_q.filter(IikoNonCashEmployeeLimit.non_cash_type_id == clean_non_cash_type_id)
    if user_id is not None:
        limits_q = limits_q.filter(IikoNonCashEmployeeLimit.user_id == user_id)

    limit_rows = limits_q.order_by(
        IikoNonCashEmployeeLimit.non_cash_type_id.asc(),
        IikoNonCashEmployeeLimit.user_id.asc(),
        IikoNonCashEmployeeLimit.period_type.asc(),
    ).all()

    non_cash_ids = {
        *(str(row.non_cash_type_id) for row in limit_rows if row.non_cash_type_id),
        *consumption_by_type.keys(),
    }
    user_ids = {int(row.user_id) for row in limit_rows if row.user_id is not None}
    non_cash_lookup = _non_cash_lookup_by_id(db, current_user, set(non_cash_ids))
    user_name_by_id = _user_names_by_ids(db, user_ids)
    user_workplace_restaurant_by_id: Dict[int, Optional[int]] = {}
    if user_ids:
        workplace_rows = (
            db.query(User.id, User.workplace_restaurant_id)
            .filter(User.id.in_(sorted(user_ids)))
            .all()
        )
        user_workplace_restaurant_by_id = {
            int(user_id): int(restaurant_id) if restaurant_id is not None else None
            for user_id, restaurant_id in workplace_rows
        }
    limits_count_by_type: Dict[str, int] = {}
    for row in limit_rows:
        key = str(row.non_cash_type_id)
        limits_count_by_type[key] = int(limits_count_by_type.get(key) or 0) + 1

    items: List[Dict[str, Any]] = []
    mapped_non_cash_ids: set[str] = set()
    for row in limit_rows:
        type_id = str(row.non_cash_type_id)
        mapped_non_cash_ids.add(type_id)
        consumed_total = consumption_by_type.get(type_id, {})
        consumed = consumed_total
        categories_by_restaurant = categories_by_type_by_restaurant.get(type_id, {})
        assigned_restaurant_id = None
        if limits_count_by_type.get(type_id, 0) > 1 and row.user_id is not None:
            assigned_restaurant_id = user_workplace_restaurant_by_id.get(int(row.user_id))
            if assigned_restaurant_id is not None:
                consumed = (consumed_total.get("restaurants") or {}).get(int(assigned_restaurant_id), {})
        limit_categories: Dict[str, Dict[str, Any]] = {}
        if assigned_restaurant_id is not None:
            source_categories = categories_by_restaurant.get(int(assigned_restaurant_id), {})
            for category_name, stats in source_categories.items():
                limit_categories[category_name] = {
                    "consumed_amount": float(stats.get("consumed_amount") or 0),
                    "consumed_qty": float(stats.get("consumed_qty") or 0),
                    "orders_count": int(stats.get("orders_count") or 0),
                    "items_count": int(stats.get("items_count") or 0),
                }
        else:
            for source_categories in categories_by_restaurant.values():
                for category_name, stats in source_categories.items():
                    bucket = limit_categories.setdefault(
                        category_name,
                        {
                            "consumed_amount": 0.0,
                            "consumed_qty": 0.0,
                            "orders_count": 0,
                            "items_count": 0,
                        },
                    )
                    bucket["consumed_amount"] = float(bucket.get("consumed_amount") or 0) + float(
                        stats.get("consumed_amount") or 0
                    )
                    bucket["consumed_qty"] = float(bucket.get("consumed_qty") or 0) + float(stats.get("consumed_qty") or 0)
                    bucket["orders_count"] = int(bucket.get("orders_count") or 0) + int(stats.get("orders_count") or 0)
                    bucket["items_count"] = int(bucket.get("items_count") or 0) + int(stats.get("items_count") or 0)
        limit_amount = float(row.limit_amount) if row.limit_amount is not None else None
        consumed_amount = float(consumed.get("consumed_amount") or 0)
        balance_amount = None
        if limit_amount is not None:
            balance_amount = limit_amount - consumed_amount
        items.append(
            {
                **_serialize_non_cash_limit(
                    row,
                    non_cash_name=non_cash_lookup.get(type_id, {}).get("name"),
                    user_name=user_name_by_id.get(int(row.user_id)) if row.user_id is not None else None,
                ),
                "consumed_amount": consumed_amount,
                "consumed_qty": float(consumed.get("consumed_qty") or 0),
                "orders_count": int(consumed.get("orders_count") or 0),
                "items_count": int(consumed.get("items_count") or 0),
                "balance_amount": balance_amount,
                "assigned_restaurant_id": assigned_restaurant_id,
                "assigned_restaurant_name": (
                    restaurant_name_by_id.get(int(assigned_restaurant_id))
                    if assigned_restaurant_id is not None
                    else None
                ),
                "by_restaurant": _serialize_restaurant_stats(consumed_total.get("restaurants") or {}),
                "by_category": _serialize_category_stats(limit_categories),
            }
        )

    unmapped = []
    for type_id, consumed in consumption_by_type.items():
        if type_id in mapped_non_cash_ids:
            continue
        unmapped.append(
            {
                "non_cash_type_id": type_id,
                "non_cash_type_name": (
                    non_cash_lookup.get(type_id, {}).get("name")
                    or consumed.get("name")
                    or type_id
                ),
                "consumed_amount": float(consumed.get("consumed_amount") or 0),
                "consumed_qty": float(consumed.get("consumed_qty") or 0),
                "orders_count": int(consumed.get("orders_count") or 0),
                "items_count": int(consumed.get("items_count") or 0),
                "by_restaurant": _serialize_restaurant_stats(consumed.get("restaurants") or {}),
            }
        )

    types = []
    type_keys = sorted(set(consumption_by_type.keys()) | set(mapped_non_cash_ids))
    for type_id in type_keys:
        consumed = consumption_by_type.get(type_id, {})
        lookup = non_cash_lookup.get(type_id, {})
        types.append(
            {
                "non_cash_type_id": type_id,
                "non_cash_type_name": lookup.get("name") or consumed.get("name") or type_id,
                "category": lookup.get("category"),
                "is_active": lookup.get("is_active"),
                "employees_count": int(limits_count_by_type.get(type_id) or 0),
                "consumed_amount": float(consumed.get("consumed_amount") or 0),
                "consumed_qty": float(consumed.get("consumed_qty") or 0),
                "orders_count": int(consumed.get("orders_count") or 0),
                "items_count": int(consumed.get("items_count") or 0),
                "by_restaurant": _serialize_restaurant_stats(consumed.get("restaurants") or {}),
            }
        )

    totals_by_restaurant_map: Dict[int, Dict[str, Any]] = {}
    for consumed in consumption_by_type.values():
        for rest_id, rest_stats in (consumed.get("restaurants") or {}).items():
            bucket = totals_by_restaurant_map.setdefault(
                int(rest_id),
                {
                    "consumed_amount": 0.0,
                    "consumed_qty": 0.0,
                    "orders_count": 0,
                    "items_count": 0,
                },
            )
            bucket["consumed_amount"] = float(bucket.get("consumed_amount") or 0) + float(
                rest_stats.get("consumed_amount") or 0
            )
            bucket["consumed_qty"] = float(bucket.get("consumed_qty") or 0) + float(rest_stats.get("consumed_qty") or 0)
            bucket["orders_count"] = int(bucket.get("orders_count") or 0) + int(rest_stats.get("orders_count") or 0)
            bucket["items_count"] = int(bucket.get("items_count") or 0) + int(rest_stats.get("items_count") or 0)

    totals_by_restaurant = _serialize_restaurant_stats(totals_by_restaurant_map)
    mapped_consumed = round(
        sum(float(consumption_by_type.get(type_id, {}).get("consumed_amount") or 0) for type_id in mapped_non_cash_ids),
        2,
    )
    unmapped_consumed = round(
        sum(
            float(consumed.get("consumed_amount") or 0)
            for type_id, consumed in consumption_by_type.items()
            if type_id not in mapped_non_cash_ids
        ),
        2,
    )
    total_consumed = round(mapped_consumed + unmapped_consumed, 2)

    return {
        "from_date": start.isoformat(),
        "to_date": (end_excl - timedelta(days=1)).isoformat(),
        "restaurant_id": restaurant_id,
        "items": items,
        "unmapped": unmapped,
        "types": types,
        "totals_by_restaurant": totals_by_restaurant,
        "totals": {
            "mapped_consumed": mapped_consumed,
            "unmapped_consumed": unmapped_consumed,
            "total_consumed": total_consumed,
        },
    }


@router.get("/revenue-by-payment-methods")
def get_revenue_by_payment_methods(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_ids: Optional[List[int]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_MONEY_PERMISSIONS)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    accessible_ids = {int(row.id) for row in accessible_restaurants}
    restaurant_name_by_id = {int(row.id): row.name for row in accessible_restaurants}
    if not accessible_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "restaurants": [],
            "selected_restaurant_ids": [],
            "dates": [],
            "methods": [],
            "totals_by_date": {},
            "total_amount": 0.0,
        }

    selected_restaurant_ids: List[int]
    if restaurant_ids:
        unique_requested_ids = sorted({int(value) for value in restaurant_ids if value is not None})
        unavailable_ids = [rest_id for rest_id in unique_requested_ids if rest_id not in accessible_ids]
        if unavailable_ids:
            raise HTTPException(status_code=404, detail=f"Restaurant not found or unavailable: {unavailable_ids[0]}")
        selected_restaurant_ids = unique_requested_ids
    else:
        selected_restaurant_ids = sorted(accessible_ids)

    if not selected_restaurant_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "restaurants": [],
            "selected_restaurant_ids": [],
            "dates": [],
            "methods": [],
            "totals_by_date": {},
            "total_amount": 0.0,
        }

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date()
    if start > end:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    end_excl = end + timedelta(days=1)

    payment_methods_rows = (
        _payment_methods_query(db, current_user)
        .with_entities(IikoPaymentMethod.guid, IikoPaymentMethod.name, IikoPaymentMethod.category)
        .all()
    )
    payment_methods_by_guid: Dict[str, Dict[str, Any]] = {}
    payment_guid_by_name: Dict[str, str] = {}
    for guid, name, category in payment_methods_rows:
        clean_guid = _clean_optional_text(guid)
        if not clean_guid:
            continue
        clean_name = _clean_optional_text(name) or clean_guid
        payment_methods_by_guid[clean_guid] = {
            "guid": clean_guid,
            "name": clean_name,
            "category": _clean_optional_text(category),
        }
        payment_guid_by_name.setdefault(clean_name.casefold(), clean_guid)

    payment_guid_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
        IikoSaleItem.raw_payload["PaymentType.Id"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
    )
    payment_name_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["PayTypes"].astext,
        IikoSaleItem.raw_payload["PaymentType"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType"].astext,
    )

    base_q = (
        db.query(IikoSaleItem)
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .filter(IikoSaleOrder.restaurant_id.in_(selected_restaurant_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_excl)
    )
    base_q = _apply_deleted_mode_filter(
        base_q,
        deleted_mode=DELETED_MODE_WITHOUT,
        order_deleted_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["OrderDeleted"].astext,
            IikoSaleOrder.raw_payload["OrderDeleted"].astext,
        ),
        deleted_with_writeoff_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
            IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
        ),
    )
    non_cash_id_expr = sa.func.trim(sa.func.coalesce(IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext, ""))
    non_cash_name_expr = sa.func.trim(sa.func.coalesce(IikoSaleItem.raw_payload["NonCashPaymentType"].astext, ""))
    base_q = base_q.filter(non_cash_id_expr == "").filter(non_cash_name_expr == "")

    gross_sum_expr = (
        sa.func.coalesce(IikoSaleItem.sum, 0)
        - sa.func.abs(sa.func.coalesce(IikoSaleItem.discount_sum, 0))
    )

    rows = (
        base_q.with_entities(
            IikoSaleOrder.open_date.label("open_date"),
            payment_guid_expr.label("payment_guid"),
            payment_name_expr.label("payment_name"),
            sa.func.coalesce(sa.func.sum(gross_sum_expr), 0).label("amount"),
        )
        .group_by(IikoSaleOrder.open_date, payment_guid_expr, payment_name_expr)
        .all()
    )

    methods_by_guid: Dict[str, Dict[str, Any]] = {}
    totals_by_date: Dict[str, float] = {}
    total_amount = 0.0

    current = start
    dates: List[str] = []
    while current <= end:
        date_key = current.isoformat()
        dates.append(date_key)
        totals_by_date[date_key] = 0.0
        current += timedelta(days=1)

    for row in rows:
        open_date = row.open_date
        if open_date is None:
            continue
        date_key = open_date.isoformat()
        if date_key not in totals_by_date:
            continue

        raw_guid, raw_name = _normalize_payment_method(row.payment_guid, row.payment_name)
        if not raw_guid and not raw_name:
            continue
        resolved_guid = raw_guid
        method_meta = payment_methods_by_guid.get(resolved_guid) if resolved_guid else None
        if method_meta is None and raw_name:
            mapped_guid = payment_guid_by_name.get(raw_name.casefold())
            if mapped_guid:
                resolved_guid = mapped_guid
                method_meta = payment_methods_by_guid.get(mapped_guid)

        # Explicitly exclude non real-money methods when category is configured in dictionary.
        if method_meta and method_meta.get("category") and method_meta.get("category") != "real_money":
            continue

        if not resolved_guid:
            resolved_guid = _build_synthetic_payment_guid(raw_name or "unknown")

        amount = float(row.amount or 0)
        if not amount:
            continue

        method_bucket = methods_by_guid.setdefault(
            resolved_guid,
            {
                "method_guid": resolved_guid,
                "method_name": (method_meta or {}).get("name") or raw_name or resolved_guid,
                "by_date": {date: 0.0 for date in dates},
                "total_amount": 0.0,
            },
        )
        method_bucket["by_date"][date_key] = float(method_bucket["by_date"].get(date_key) or 0) + amount
        method_bucket["total_amount"] = float(method_bucket.get("total_amount") or 0) + amount
        totals_by_date[date_key] = float(totals_by_date.get(date_key) or 0) + amount
        total_amount += amount

    methods = list(methods_by_guid.values())
    methods.sort(key=lambda item: str(item.get("method_name") or "").casefold())

    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "restaurants": [
            {"id": rest_id, "name": restaurant_name_by_id.get(rest_id)}
            for rest_id in selected_restaurant_ids
        ],
        "selected_restaurant_ids": selected_restaurant_ids,
        "dates": dates,
        "methods": methods,
        "totals_by_date": totals_by_date,
        "total_amount": total_amount,
    }


@router.get("/waiter-sales-report/options")
def list_waiter_sales_report_options(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_id: Optional[int] = Query(None),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    positions_limit: int = Query(500, ge=50, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    resolved_deleted_mode = _normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = _normalize_waiter_mode(waiter_mode)
    if restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    accessible_ids = [r.id for r in accessible_restaurants]
    restaurant_name_by_id = {r.id: r.name for r in accessible_restaurants}
    if not accessible_ids:
        return {
            "deleted_mode": resolved_deleted_mode,
            "waiter_mode": resolved_waiter_mode,
            "restaurants": [],
            "waiters": [],
            "halls": [],
            "departments": [],
            "tables": [],
            "groups": [],
            "categories": [],
            "positions": [],
            "payment_types": [],
        }

    normalized_from_date = to_iso_date(from_date)
    normalized_to_date = to_iso_date(to_date)
    accessible_ids_set = set(accessible_ids)
    cache_key = (
        int(getattr(current_user, "id", 0) or 0),
        tuple(sorted(accessible_ids)),
        normalized_from_date,
        normalized_to_date,
        int(restaurant_id) if restaurant_id is not None else None,
        resolved_waiter_mode,
        resolved_deleted_mode,
        int(positions_limit),
    )

    def _load_waiter_sales_options() -> dict[str, Any]:
        start = datetime.strptime(normalized_from_date, "%Y-%m-%d").date()
        end_excl = datetime.strptime(normalized_to_date, "%Y-%m-%d").date() + timedelta(days=1)

        base_items_q = (
            db.query(IikoSaleItem)
            .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
            .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
            .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
            .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
            .filter(IikoSaleOrder.open_date >= start)
            .filter(IikoSaleOrder.open_date < end_excl)
        )
        base_items_q = _apply_deleted_mode_filter(
            base_items_q,
            deleted_mode=resolved_deleted_mode,
            order_deleted_expr=sa.func.coalesce(
                IikoSaleItem.raw_payload["OrderDeleted"].astext,
                IikoSaleOrder.raw_payload["OrderDeleted"].astext,
            ),
            deleted_with_writeoff_expr=sa.func.coalesce(
                IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
                IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
            ),
        )
        if restaurant_id is not None:
            base_items_q = base_items_q.filter(IikoSaleOrder.restaurant_id == restaurant_id)

        group_expr = _dish_group_sql_expr()
        category_expr = _dish_category_sql_expr()
        position_expr = sa.func.coalesce(IikoSaleItem.dish_name, IikoProduct.name, IikoSaleItem.dish_code)
        payment_type_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["PayTypes"].astext,
            IikoSaleItem.raw_payload["NonCashPaymentType"].astext,
            IikoSaleItem.raw_payload["PaymentType"].astext,
            IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
            IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
            IikoSaleItem.raw_payload["PaymentType.Id"].astext,
        )

        # Categories stay catalog-based; groups stay sales-based for selected period.
        catalog_restaurant_ids = accessible_ids
        if restaurant_id is not None:
            catalog_restaurant_ids = [restaurant_id] if restaurant_id in accessible_ids_set else []

        # Groups should reflect only sold items for the selected period.
        groups = [
            value
            for (value,) in (
                base_items_q.with_entities(group_expr)
                .filter(group_expr.isnot(None))
                .distinct()
                .order_by(group_expr.asc())
                .all()
            )
            if value
        ]

        catalog_category_expr = sa.func.coalesce(
            _non_uuid_text_sql(IikoProductSetting.custom_product_category),
            _non_uuid_text_sql(
                sa.func.jsonb_extract_path_text(IikoProduct.raw_payload, "product", "product_category")
            ),
            _non_uuid_text_sql(IikoProduct.product_category),
        )

        categories: List[str] = []
        if catalog_restaurant_ids:
            catalog_q = (
                db.query(IikoProduct.id)
                .select_from(IikoProduct)
                .join(IikoProductRestaurant, IikoProductRestaurant.product_id == IikoProduct.id)
                .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
                .filter(IikoProductRestaurant.restaurant_id.in_(catalog_restaurant_ids))
            )
            if getattr(current_user, "company_id", None) is not None:
                catalog_q = catalog_q.filter(IikoProduct.company_id == current_user.company_id)

            categories = [
                value
                for (value,) in (
                    catalog_q.with_entities(catalog_category_expr)
                    .filter(catalog_category_expr.isnot(None))
                    .distinct()
                    .order_by(catalog_category_expr.asc())
                    .all()
                )
                if value
            ]
        positions = [
            value
            for (value,) in (
                base_items_q.with_entities(position_expr)
                .filter(position_expr.isnot(None))
                .distinct()
                .order_by(position_expr.asc())
                .limit(positions_limit)
                .all()
            )
            if value
        ]
        payment_types = [
            value
            for (value,) in (
                base_items_q.with_entities(payment_type_expr)
                .filter(payment_type_expr.isnot(None))
                .distinct()
                .order_by(payment_type_expr.asc())
                .all()
            )
            if value
        ]
        hall_order_rows = (
            base_items_q.with_entities(
                IikoSaleOrder.restaurant_id.label("restaurant_id"),
                IikoSaleOrder.source_restaurant_id.label("source_restaurant_id"),
                IikoSaleOrder.department.label("department"),
                IikoSaleOrder.table_num.label("table_num"),
            )
            .distinct()
            .all()
        )
        halls = _collect_halls_from_order_rows(db, current_user, hall_order_rows)
        departments = sorted(
            {
                str(getattr(row, "department", "")).strip()
                for row in hall_order_rows
                if getattr(row, "department", None) is not None and str(getattr(row, "department", "")).strip()
            },
            key=lambda value: str(value).casefold(),
        )
        tables = sorted(
            {
                str(getattr(row, "table_num", "")).strip()
                for row in hall_order_rows
                if getattr(row, "table_num", None) is not None and str(getattr(row, "table_num", "")).strip()
            },
            key=lambda value: str(value).casefold(),
        )

        waiter_exprs = _waiter_dimension_exprs(resolved_waiter_mode)
        waiter_rows = (
            base_items_q.with_entities(
                waiter_exprs["waiter_user_id"].label("waiter_user_id"),
                waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
                waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
                waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
            )
            .distinct()
            .all()
        )
        user_ids = {int(row.waiter_user_id) for row in waiter_rows if row.waiter_user_id is not None}
        iiko_ids = {str(row.waiter_iiko_id) for row in waiter_rows if row.waiter_iiko_id}
        iiko_codes = {str(row.waiter_iiko_code) for row in waiter_rows if row.waiter_iiko_code}
        user_name_by_id = _user_names_by_ids(db, user_ids)
        user_meta_by_iiko_id = _user_meta_by_iiko_ids(db, iiko_ids)
        user_meta_by_iiko_code = _user_meta_by_iiko_codes(db, iiko_codes)

        waiters = []
        seen_waiters: set[tuple[Optional[int], Optional[str], Optional[str]]] = set()
        for row in waiter_rows:
            waiter_user_id_value = int(row.waiter_user_id) if row.waiter_user_id is not None else None
            waiter_iiko_id_value = _clean_optional_text(row.waiter_iiko_id)
            waiter_iiko_code_value = _clean_optional_text(row.waiter_iiko_code)
            resolved_user_id, resolved_name = _resolve_waiter_identity(
                waiter_user_id=waiter_user_id_value,
                waiter_iiko_id=waiter_iiko_id_value,
                waiter_iiko_code=waiter_iiko_code_value,
                waiter_name_iiko=_clean_optional_text(row.waiter_name_iiko),
                user_name_by_id=user_name_by_id,
                user_meta_by_iiko_id=user_meta_by_iiko_id,
                user_meta_by_iiko_code=user_meta_by_iiko_code,
            )
            dedupe_key = (resolved_user_id, waiter_iiko_id_value, waiter_iiko_code_value)
            if dedupe_key in seen_waiters:
                continue
            seen_waiters.add(dedupe_key)
            waiters.append(
                {
                    "user_id": resolved_user_id,
                    "iiko_id": waiter_iiko_id_value,
                    "iiko_code": waiter_iiko_code_value,
                    "name": resolved_name,
                }
            )
        waiters.sort(key=lambda item: str(item.get("name") or "").casefold())

        restaurants = [
            {"id": r.id, "name": restaurant_name_by_id.get(r.id) or r.name}
            for r in accessible_restaurants
        ]

        return {
            "deleted_mode": resolved_deleted_mode,
            "waiter_mode": resolved_waiter_mode,
            "restaurants": restaurants,
            "waiters": waiters,
            "halls": halls,
            "departments": departments,
            "tables": tables,
            "groups": groups,
            "categories": categories,
            "positions": positions,
            "payment_types": payment_types,
        }

    return cached_reference_data(
        WAITER_SALES_OPTIONS_CACHE_SCOPE,
        cache_key,
        _load_waiter_sales_options,
        ttl_seconds=WAITER_SALES_OPTIONS_CACHE_TTL_SECONDS,
    )


@router.get("/waiter-sales-report")
def list_waiter_sales_report(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_id: Optional[int] = Query(None),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    waiter_user_id: Optional[int] = Query(None),
    waiter_iiko_id: Optional[str] = Query(None),
    waiter_iiko_code: Optional[str] = Query(None),
    include_payment_types: Optional[List[str]] = Query(None),
    include_groups: Optional[List[str]] = Query(None),
    exclude_groups: Optional[List[str]] = Query(None),
    include_categories: Optional[List[str]] = Query(None),
    exclude_categories: Optional[List[str]] = Query(None),
    include_positions: Optional[List[str]] = Query(None),
    exclude_positions: Optional[List[str]] = Query(None),
    include_halls: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    can_view_money = _can_view_sales_money(current_user)
    resolved_deleted_mode = _normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = _normalize_waiter_mode(waiter_mode)
    if restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    accessible_ids = [r.id for r in accessible_restaurants]
    restaurant_name_by_id = {r.id: r.name for r in accessible_restaurants}
    if not accessible_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "deleted_mode": resolved_deleted_mode,
            "waiter_mode": resolved_waiter_mode,
            "items": [],
            "totals": {
                "orders_count": 0,
                "guests_count": 0,
                "items_count": 0,
                "qty": 0.0,
                "kitchen_load_qty": 0.0,
                "hall_load_qty": 0.0,
                "sum": 0.0,
                "discount_sum": 0.0,
            },
            "totals_by_restaurant": [],
            "totals_by_waiter": [],
        }

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)

    include_groups_list = _split_filter_values(include_groups)
    exclude_groups_list = _split_filter_values(exclude_groups)
    include_categories_list = _split_filter_values(include_categories)
    exclude_categories_list = _split_filter_values(exclude_categories)
    include_positions_list = _split_filter_values(include_positions)
    exclude_positions_list = _split_filter_values(exclude_positions)
    include_payment_types_list = _split_filter_values(include_payment_types)
    include_halls_list = _split_filter_values(include_halls)

    include_groups_lower = _lower_values(include_groups_list)
    exclude_groups_lower = _lower_values(exclude_groups_list)
    include_categories_lower = _lower_values(include_categories_list)
    exclude_categories_lower = _lower_values(exclude_categories_list)
    include_positions_lower = _lower_values(include_positions_list)
    exclude_positions_lower = _lower_values(exclude_positions_list)
    include_payment_types_lower = _lower_values(include_payment_types_list)
    include_halls_lower = _lower_values(include_halls_list)

    group_expr = _dish_group_sql_expr()
    category_expr = _dish_category_sql_expr()
    position_expr = sa.func.coalesce(IikoSaleItem.dish_name, IikoProduct.name, IikoSaleItem.dish_code)
    payment_type_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["PayTypes"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType"].astext,
        IikoSaleItem.raw_payload["PaymentType"].astext,
        IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
        IikoSaleItem.raw_payload["PaymentType.Id"].astext,
    )
    order_number_expr = sa.func.coalesce(
        IikoSaleOrder.order_num,
        IikoSaleOrder.iiko_order_id,
        sa.cast(IikoSaleOrder.id, sa.String),
    )
    portion_coef_kitchen_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_kitchen, 1.0), sa.Float)
    portion_coef_hall_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_hall, 1.0), sa.Float)
    kitchen_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_kitchen_expr
    hall_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_hall_expr

    base_q = (
        db.query(IikoSaleItem)
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_excl)
    )
    base_q = _apply_deleted_mode_filter(
        base_q,
        deleted_mode=resolved_deleted_mode,
        order_deleted_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["OrderDeleted"].astext,
            IikoSaleOrder.raw_payload["OrderDeleted"].astext,
        ),
        deleted_with_writeoff_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
            IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
        ),
    )

    if restaurant_id is not None:
        base_q = base_q.filter(IikoSaleOrder.restaurant_id == restaurant_id)
    base_q = _apply_waiter_filter_to_items_query(
        db,
        base_q,
        waiter_mode=resolved_waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=waiter_iiko_id,
        waiter_iiko_code=waiter_iiko_code,
    )

    group_expr_lower = sa.func.lower(sa.func.coalesce(group_expr, ""))
    category_expr_lower = sa.func.lower(sa.func.coalesce(category_expr, ""))
    position_expr_lower = sa.func.lower(sa.func.coalesce(position_expr, ""))
    payment_type_expr_lower = sa.func.lower(sa.func.coalesce(payment_type_expr, ""))

    if include_groups_lower:
        base_q = base_q.filter(group_expr_lower.in_(include_groups_lower))
    if exclude_groups_lower:
        base_q = base_q.filter(~group_expr_lower.in_(exclude_groups_lower))
    if include_categories_lower:
        base_q = base_q.filter(category_expr_lower.in_(include_categories_lower))
    if exclude_categories_lower:
        base_q = base_q.filter(~category_expr_lower.in_(exclude_categories_lower))
    if include_positions_lower:
        base_q = base_q.filter(position_expr_lower.in_(include_positions_lower))
    if exclude_positions_lower:
        base_q = base_q.filter(~position_expr_lower.in_(exclude_positions_lower))
    if include_payment_types_lower:
        base_q = base_q.filter(payment_type_expr_lower.in_(include_payment_types_lower))
    if include_halls_lower:
        base_q = _apply_hall_filter_to_base_query(db, current_user, base_q, include_halls_lower)

    waiter_exprs = _waiter_dimension_exprs(resolved_waiter_mode)

    if resolved_waiter_mode == WAITER_MODE_ITEM_PUNCH:
        waiter_orders_subq = (
            base_q.with_entities(
                IikoSaleOrder.id.label("order_id"),
                IikoSaleOrder.restaurant_id.label("restaurant_id"),
                waiter_exprs["waiter_user_id"].label("waiter_user_id"),
                waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
                waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
                waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
            )
            .distinct()
            .subquery(name="waiter_filtered_orders")
        )
        order_metrics_rows = (
            db.query(
                waiter_orders_subq.c.restaurant_id.label("restaurant_id"),
                waiter_orders_subq.c.waiter_user_id.label("waiter_user_id"),
                waiter_orders_subq.c.waiter_iiko_id.label("waiter_iiko_id"),
                waiter_orders_subq.c.waiter_iiko_code.label("waiter_iiko_code"),
                waiter_orders_subq.c.waiter_name_iiko.label("waiter_name_iiko"),
                sa.func.count(waiter_orders_subq.c.order_id).label("orders_count"),
                sa.func.coalesce(sa.func.sum(IikoSaleOrder.guest_num), 0).label("guests_count"),
            )
            .join(IikoSaleOrder, IikoSaleOrder.id == waiter_orders_subq.c.order_id)
            .group_by(
                waiter_orders_subq.c.restaurant_id,
                waiter_orders_subq.c.waiter_user_id,
                waiter_orders_subq.c.waiter_iiko_id,
                waiter_orders_subq.c.waiter_iiko_code,
                waiter_orders_subq.c.waiter_name_iiko,
            )
            .all()
        )
    else:
        filtered_order_ids_subq = base_q.with_entities(
            IikoSaleOrder.id.label("order_id")
        ).distinct().subquery(name="waiter_filtered_orders")

        order_metrics_rows = (
            db.query(
                IikoSaleOrder.restaurant_id.label("restaurant_id"),
                waiter_exprs["waiter_user_id"].label("waiter_user_id"),
                waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
                waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
                waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
                sa.func.count(sa.distinct(order_number_expr)).label("orders_count"),
                sa.func.coalesce(sa.func.sum(IikoSaleOrder.guest_num), 0).label("guests_count"),
            )
            .join(filtered_order_ids_subq, filtered_order_ids_subq.c.order_id == IikoSaleOrder.id)
            .group_by(
                IikoSaleOrder.restaurant_id,
                waiter_exprs["waiter_user_id"],
                waiter_exprs["waiter_iiko_id"],
                waiter_exprs["waiter_iiko_code"],
                waiter_exprs["waiter_name_iiko"],
            )
            .all()
        )
    order_metrics_by_key: Dict[
        tuple[Optional[int], Optional[int], Optional[str], Optional[str], Optional[str]],
        Dict[str, Any],
    ] = {}
    for row in order_metrics_rows:
        key = (
            int(row.restaurant_id) if row.restaurant_id is not None else None,
            int(row.waiter_user_id) if row.waiter_user_id is not None else None,
            str(row.waiter_iiko_id) if row.waiter_iiko_id else None,
            str(row.waiter_iiko_code) if row.waiter_iiko_code else None,
            str(row.waiter_name_iiko) if row.waiter_name_iiko else None,
        )
        order_metrics_by_key[key] = {
            "orders_count": int(row.orders_count or 0),
            "guests_count": int(row.guests_count or 0),
        }

    rows = (
        base_q.with_entities(
            IikoSaleOrder.restaurant_id.label("restaurant_id"),
            waiter_exprs["waiter_user_id"].label("waiter_user_id"),
            waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
            waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
            waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
            sa.func.count(sa.distinct(order_number_expr)).label("orders_count"),
            sa.func.count(IikoSaleItem.id).label("items_count"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("qty"),
            sa.func.coalesce(sa.func.sum(kitchen_load_expr), 0).label("kitchen_load_qty"),
            sa.func.coalesce(sa.func.sum(hall_load_expr), 0).label("hall_load_qty"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("sum"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.discount_sum), 0).label("discount_sum"),
        )
        .group_by(
            IikoSaleOrder.restaurant_id,
            waiter_exprs["waiter_user_id"],
            waiter_exprs["waiter_iiko_id"],
            waiter_exprs["waiter_iiko_code"],
            waiter_exprs["waiter_name_iiko"],
        )
        .order_by(
            IikoSaleOrder.restaurant_id.asc(),
            waiter_exprs["waiter_name_iiko"].asc().nullslast(),
            waiter_exprs["waiter_iiko_id"].asc().nullslast(),
            waiter_exprs["waiter_iiko_code"].asc().nullslast(),
        )
        .all()
    )

    user_ids = {int(row.waiter_user_id) for row in rows if row.waiter_user_id is not None}
    iiko_ids = {str(row.waiter_iiko_id) for row in rows if row.waiter_iiko_id}
    iiko_codes = {str(row.waiter_iiko_code) for row in rows if row.waiter_iiko_code}
    user_name_by_id = _user_names_by_ids(db, user_ids)
    user_meta_by_iiko_id = _user_meta_by_iiko_ids(db, iiko_ids)
    user_meta_by_iiko_code = _user_meta_by_iiko_codes(db, iiko_codes)

    items: List[Dict[str, Any]] = []
    totals = {
        "orders_count": 0,
        "guests_count": 0,
        "items_count": 0,
        "qty": 0.0,
        "kitchen_load_qty": 0.0,
        "hall_load_qty": 0.0,
        "sum": 0.0,
        "discount_sum": 0.0,
    }
    totals_by_restaurant_map: Dict[int, Dict[str, Any]] = {}
    totals_by_waiter_map: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        waiter_user_id_value = int(row.waiter_user_id) if row.waiter_user_id is not None else None
        waiter_iiko_id_value = _clean_optional_text(row.waiter_iiko_id)
        waiter_iiko_code_value = _clean_optional_text(row.waiter_iiko_code)
        resolved_user_id, waiter_name = _resolve_waiter_identity(
            waiter_user_id=waiter_user_id_value,
            waiter_iiko_id=waiter_iiko_id_value,
            waiter_iiko_code=waiter_iiko_code_value,
            waiter_name_iiko=_clean_optional_text(row.waiter_name_iiko),
            user_name_by_id=user_name_by_id,
            user_meta_by_iiko_id=user_meta_by_iiko_id,
            user_meta_by_iiko_code=user_meta_by_iiko_code,
        )

        metrics_key = (
            int(row.restaurant_id) if row.restaurant_id is not None else None,
            waiter_user_id_value,
            waiter_iiko_id_value,
            waiter_iiko_code_value,
            str(row.waiter_name_iiko) if row.waiter_name_iiko else None,
        )
        order_metrics = order_metrics_by_key.get(metrics_key, {})

        orders_count = int(order_metrics.get("orders_count") or row.orders_count or 0)
        guests_count = int(order_metrics.get("guests_count") or 0)
        items_count = int(row.items_count or 0)
        qty_value = float(row.qty or 0)
        kitchen_load_value = float(row.kitchen_load_qty or 0)
        hall_load_value = float(row.hall_load_qty or 0)
        sum_value = float(row.sum or 0)
        discount_value = float(row.discount_sum or 0)

        payload_row = {
            "restaurant_id": int(row.restaurant_id) if row.restaurant_id is not None else None,
            "restaurant_name": restaurant_name_by_id.get(int(row.restaurant_id))
            if row.restaurant_id is not None
            else None,
            "waiter_user_id": resolved_user_id,
            "waiter_iiko_id": waiter_iiko_id_value,
            "waiter_iiko_code": waiter_iiko_code_value,
            "waiter_name": waiter_name,
            "waiter_name_iiko": row.waiter_name_iiko,
            "orders_count": orders_count,
            "guests_count": guests_count,
            "items_count": items_count,
            "qty": qty_value,
            "kitchen_load_qty": kitchen_load_value,
            "hall_load_qty": hall_load_value,
            "sum": sum_value,
            "discount_sum": discount_value,
        }
        items.append(payload_row)

        totals["orders_count"] += orders_count
        totals["guests_count"] += guests_count
        totals["items_count"] += items_count
        totals["qty"] += qty_value
        totals["kitchen_load_qty"] += kitchen_load_value
        totals["hall_load_qty"] += hall_load_value
        totals["sum"] += sum_value
        totals["discount_sum"] += discount_value

        if row.restaurant_id is not None:
            rest_id = int(row.restaurant_id)
            rest_bucket = totals_by_restaurant_map.setdefault(
                rest_id,
                {
                    "restaurant_id": rest_id,
                    "restaurant_name": restaurant_name_by_id.get(rest_id),
                    "orders_count": 0,
                    "guests_count": 0,
                    "items_count": 0,
                    "qty": 0.0,
                    "kitchen_load_qty": 0.0,
                    "hall_load_qty": 0.0,
                    "sum": 0.0,
                    "discount_sum": 0.0,
                },
            )
            rest_bucket["orders_count"] += orders_count
            rest_bucket["guests_count"] += guests_count
            rest_bucket["items_count"] += items_count
            rest_bucket["qty"] += qty_value
            rest_bucket["kitchen_load_qty"] += kitchen_load_value
            rest_bucket["hall_load_qty"] += hall_load_value
            rest_bucket["sum"] += sum_value
            rest_bucket["discount_sum"] += discount_value

        waiter_key = (
            f"user:{resolved_user_id}"
            if resolved_user_id is not None
            else f"iiko:{waiter_iiko_id_value or 'none'}:code:{waiter_iiko_code_value or 'none'}"
        )
        waiter_bucket = totals_by_waiter_map.setdefault(
            waiter_key,
            {
                "waiter_user_id": resolved_user_id,
                "waiter_iiko_id": waiter_iiko_id_value,
                "waiter_iiko_code": waiter_iiko_code_value,
                "waiter_name": waiter_name,
                "orders_count": 0,
                "guests_count": 0,
                "items_count": 0,
                "qty": 0.0,
                "kitchen_load_qty": 0.0,
                "hall_load_qty": 0.0,
                "sum": 0.0,
                "discount_sum": 0.0,
            },
        )
        waiter_bucket["orders_count"] += orders_count
        waiter_bucket["guests_count"] += guests_count
        waiter_bucket["items_count"] += items_count
        waiter_bucket["qty"] += qty_value
        waiter_bucket["kitchen_load_qty"] += kitchen_load_value
        waiter_bucket["hall_load_qty"] += hall_load_value
        waiter_bucket["sum"] += sum_value
        waiter_bucket["discount_sum"] += discount_value

    totals_by_restaurant = sorted(totals_by_restaurant_map.values(), key=lambda row: (row.get("restaurant_name") or ""))
    totals_by_waiter = sorted(totals_by_waiter_map.values(), key=lambda row: (row.get("waiter_name") or ""))

    if not can_view_money:
        _zero_money_metrics(totals)
        for row in items:
            _zero_money_metrics(row)
        for row in totals_by_restaurant:
            _zero_money_metrics(row)
        for row in totals_by_waiter:
            _zero_money_metrics(row)

    return {
        "from_date": start.isoformat(),
        "to_date": (end_excl - timedelta(days=1)).isoformat(),
        "deleted_mode": resolved_deleted_mode,
        "waiter_mode": resolved_waiter_mode,
        "items": items,
        "totals": {
            "orders_count": int(totals["orders_count"]),
            "guests_count": int(totals["guests_count"]),
            "items_count": int(totals["items_count"]),
            "qty": round(float(totals["qty"]), 3),
            "kitchen_load_qty": round(float(totals["kitchen_load_qty"]), 3),
            "hall_load_qty": round(float(totals["hall_load_qty"]), 3),
            "sum": round(float(totals["sum"]), 2),
            "discount_sum": round(float(totals["discount_sum"]), 2),
        },
        "totals_by_restaurant": totals_by_restaurant,
        "totals_by_waiter": totals_by_waiter,
    }


@router.get("/waiter-sales-report/positions")
def list_waiter_sales_report_positions(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_id: Optional[int] = Query(None),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    waiter_user_id: Optional[int] = Query(None),
    waiter_iiko_id: Optional[str] = Query(None),
    waiter_iiko_code: Optional[str] = Query(None),
    include_payment_types: Optional[List[str]] = Query(None),
    include_groups: Optional[List[str]] = Query(None),
    exclude_groups: Optional[List[str]] = Query(None),
    include_categories: Optional[List[str]] = Query(None),
    exclude_categories: Optional[List[str]] = Query(None),
    include_positions: Optional[List[str]] = Query(None),
    exclude_positions: Optional[List[str]] = Query(None),
    include_halls: Optional[List[str]] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    can_view_money = _can_view_sales_money(current_user)
    resolved_deleted_mode = _normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = _normalize_waiter_mode(waiter_mode)

    clean_waiter_iiko_id = _clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = _clean_optional_text(waiter_iiko_code)
    if waiter_user_id is None and clean_waiter_iiko_id is None and clean_waiter_iiko_code is None:
        raise HTTPException(status_code=400, detail="waiter_user_id, waiter_iiko_id or waiter_iiko_code is required")

    if restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    accessible_ids = [r.id for r in accessible_restaurants]
    restaurant_name_by_id = {r.id: r.name for r in accessible_restaurants}
    if not accessible_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "deleted_mode": resolved_deleted_mode,
            "waiter_mode": resolved_waiter_mode,
            "waiter": None,
            "items": [],
            "totals": {
                "orders_count": 0,
                "guests_count": 0,
                "items_count": 0,
                "qty": 0.0,
                "kitchen_load_qty": 0.0,
                "hall_load_qty": 0.0,
                "sum": 0.0,
                "discount_sum": 0.0,
            },
        }

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)

    include_groups_list = _split_filter_values(include_groups)
    exclude_groups_list = _split_filter_values(exclude_groups)
    include_categories_list = _split_filter_values(include_categories)
    exclude_categories_list = _split_filter_values(exclude_categories)
    include_positions_list = _split_filter_values(include_positions)
    exclude_positions_list = _split_filter_values(exclude_positions)
    include_payment_types_list = _split_filter_values(include_payment_types)
    include_halls_list = _split_filter_values(include_halls)

    include_groups_lower = _lower_values(include_groups_list)
    exclude_groups_lower = _lower_values(exclude_groups_list)
    include_categories_lower = _lower_values(include_categories_list)
    exclude_categories_lower = _lower_values(exclude_categories_list)
    include_positions_lower = _lower_values(include_positions_list)
    exclude_positions_lower = _lower_values(exclude_positions_list)
    include_payment_types_lower = _lower_values(include_payment_types_list)
    include_halls_lower = _lower_values(include_halls_list)

    group_expr = _dish_group_sql_expr()
    category_expr = _dish_category_sql_expr()
    position_expr = sa.func.coalesce(IikoSaleItem.dish_name, IikoProduct.name, IikoSaleItem.dish_code)
    payment_type_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["PayTypes"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType"].astext,
        IikoSaleItem.raw_payload["PaymentType"].astext,
        IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
        IikoSaleItem.raw_payload["PaymentType.Id"].astext,
    )
    order_number_expr = sa.func.coalesce(
        IikoSaleOrder.order_num,
        IikoSaleOrder.iiko_order_id,
        sa.cast(IikoSaleOrder.id, sa.String),
    )
    portion_coef_kitchen_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_kitchen, 1.0), sa.Float)
    portion_coef_hall_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_hall, 1.0), sa.Float)
    kitchen_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_kitchen_expr
    hall_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_hall_expr

    base_q = (
        db.query(IikoSaleItem)
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_excl)
    )
    base_q = _apply_deleted_mode_filter(
        base_q,
        deleted_mode=resolved_deleted_mode,
        order_deleted_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["OrderDeleted"].astext,
            IikoSaleOrder.raw_payload["OrderDeleted"].astext,
        ),
        deleted_with_writeoff_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
            IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
        ),
    )

    if restaurant_id is not None:
        base_q = base_q.filter(IikoSaleOrder.restaurant_id == restaurant_id)
    base_q = _apply_waiter_filter_to_items_query(
        db,
        base_q,
        waiter_mode=resolved_waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=clean_waiter_iiko_id,
        waiter_iiko_code=clean_waiter_iiko_code,
    )

    group_expr_lower = sa.func.lower(sa.func.coalesce(group_expr, ""))
    category_expr_lower = sa.func.lower(sa.func.coalesce(category_expr, ""))
    position_expr_lower = sa.func.lower(sa.func.coalesce(position_expr, ""))
    payment_type_expr_lower = sa.func.lower(sa.func.coalesce(payment_type_expr, ""))

    if include_groups_lower:
        base_q = base_q.filter(group_expr_lower.in_(include_groups_lower))
    if exclude_groups_lower:
        base_q = base_q.filter(~group_expr_lower.in_(exclude_groups_lower))
    if include_categories_lower:
        base_q = base_q.filter(category_expr_lower.in_(include_categories_lower))
    if exclude_categories_lower:
        base_q = base_q.filter(~category_expr_lower.in_(exclude_categories_lower))
    if include_positions_lower:
        base_q = base_q.filter(position_expr_lower.in_(include_positions_lower))
    if exclude_positions_lower:
        base_q = base_q.filter(~position_expr_lower.in_(exclude_positions_lower))
    if include_payment_types_lower:
        base_q = base_q.filter(payment_type_expr_lower.in_(include_payment_types_lower))
    if include_halls_lower:
        base_q = _apply_hall_filter_to_base_query(db, current_user, base_q, include_halls_lower)

    waiter_exprs = _waiter_dimension_exprs(resolved_waiter_mode)

    rows = (
        base_q.with_entities(
            IikoSaleOrder.restaurant_id.label("restaurant_id"),
            waiter_exprs["waiter_user_id"].label("waiter_user_id"),
            waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
            waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
            waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
            IikoSaleItem.dish_code.label("dish_code"),
            position_expr.label("dish_name"),
            group_expr.label("dish_group"),
            category_expr.label("dish_category"),
            IikoSaleItem.dish_measure_unit.label("dish_measure_unit"),
            payment_type_expr.label("payment_type"),
            sa.func.count(sa.distinct(order_number_expr)).label("orders_count"),
            sa.func.count(IikoSaleItem.id).label("items_count"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("qty"),
            sa.func.coalesce(sa.func.sum(kitchen_load_expr), 0).label("kitchen_load_qty"),
            sa.func.coalesce(sa.func.sum(hall_load_expr), 0).label("hall_load_qty"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("sum"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.discount_sum), 0).label("discount_sum"),
        )
        .group_by(
            IikoSaleOrder.restaurant_id,
            waiter_exprs["waiter_user_id"],
            waiter_exprs["waiter_iiko_id"],
            waiter_exprs["waiter_iiko_code"],
            waiter_exprs["waiter_name_iiko"],
            IikoSaleItem.dish_code,
            position_expr,
            group_expr,
            category_expr,
            IikoSaleItem.dish_measure_unit,
            payment_type_expr,
        )
        .order_by(
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).desc(),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).desc(),
            position_expr.asc().nullslast(),
        )
        .limit(limit)
        .all()
    )

    totals_row = base_q.with_entities(
        sa.func.count(sa.distinct(order_number_expr)).label("orders_count"),
        sa.func.count(IikoSaleItem.id).label("items_count"),
        sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("qty"),
        sa.func.coalesce(sa.func.sum(kitchen_load_expr), 0).label("kitchen_load_qty"),
        sa.func.coalesce(sa.func.sum(hall_load_expr), 0).label("hall_load_qty"),
        sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("sum"),
        sa.func.coalesce(sa.func.sum(IikoSaleItem.discount_sum), 0).label("discount_sum"),
    ).one()
    filtered_order_ids_subq = base_q.with_entities(
        IikoSaleOrder.id.label("order_id")
    ).distinct().subquery(name="waiter_positions_filtered_orders")
    guests_total_row = (
        db.query(
            sa.func.coalesce(sa.func.sum(IikoSaleOrder.guest_num), 0).label("guests_count"),
        )
        .join(filtered_order_ids_subq, filtered_order_ids_subq.c.order_id == IikoSaleOrder.id)
        .one()
    )

    user_ids = {int(row.waiter_user_id) for row in rows if row.waiter_user_id is not None}
    iiko_ids = {str(row.waiter_iiko_id) for row in rows if row.waiter_iiko_id}
    iiko_codes = {str(row.waiter_iiko_code) for row in rows if row.waiter_iiko_code}
    if waiter_user_id is not None:
        user_ids.add(int(waiter_user_id))
    if clean_waiter_iiko_id:
        iiko_ids.add(clean_waiter_iiko_id)
    if clean_waiter_iiko_code:
        iiko_codes.add(clean_waiter_iiko_code)
    user_name_by_id = _user_names_by_ids(db, user_ids)
    user_meta_by_iiko_id = _user_meta_by_iiko_ids(db, iiko_ids)
    user_meta_by_iiko_code = _user_meta_by_iiko_codes(db, iiko_codes)

    items: List[Dict[str, Any]] = []
    totals = {
        "orders_count": int(totals_row.orders_count or 0),
        "guests_count": int(guests_total_row.guests_count or 0),
        "items_count": int(totals_row.items_count or 0),
        "qty": float(totals_row.qty or 0),
        "kitchen_load_qty": float(totals_row.kitchen_load_qty or 0),
        "hall_load_qty": float(totals_row.hall_load_qty or 0),
        "sum": float(totals_row.sum or 0),
        "discount_sum": float(totals_row.discount_sum or 0),
    }
    waiter_payload: Optional[Dict[str, Any]] = None

    for row in rows:
        waiter_user_id_value = int(row.waiter_user_id) if row.waiter_user_id is not None else None
        waiter_iiko_id_value = _clean_optional_text(row.waiter_iiko_id)
        waiter_iiko_code_value = _clean_optional_text(row.waiter_iiko_code)
        resolved_user_id, waiter_name = _resolve_waiter_identity(
            waiter_user_id=waiter_user_id_value,
            waiter_iiko_id=waiter_iiko_id_value,
            waiter_iiko_code=waiter_iiko_code_value,
            waiter_name_iiko=_clean_optional_text(row.waiter_name_iiko),
            user_name_by_id=user_name_by_id,
            user_meta_by_iiko_id=user_meta_by_iiko_id,
            user_meta_by_iiko_code=user_meta_by_iiko_code,
        )

        if waiter_payload is None:
            waiter_payload = {
                "waiter_user_id": resolved_user_id,
                "waiter_iiko_id": waiter_iiko_id_value,
                "waiter_iiko_code": waiter_iiko_code_value,
                "waiter_name": waiter_name,
                "waiter_name_iiko": row.waiter_name_iiko,
            }

        orders_count = int(row.orders_count or 0)
        items_count = int(row.items_count or 0)
        qty_value = float(row.qty or 0)
        kitchen_load_value = float(row.kitchen_load_qty or 0)
        hall_load_value = float(row.hall_load_qty or 0)
        sum_value = float(row.sum or 0)
        discount_value = float(row.discount_sum or 0)

        items.append(
            {
                "restaurant_id": int(row.restaurant_id) if row.restaurant_id is not None else None,
                "restaurant_name": restaurant_name_by_id.get(int(row.restaurant_id))
                if row.restaurant_id is not None
                else None,
                "dish_code": row.dish_code,
                "dish_name": row.dish_name,
                "dish_group": row.dish_group,
                "dish_category": row.dish_category,
                "dish_measure_unit": row.dish_measure_unit,
                "payment_type": row.payment_type,
                "orders_count": orders_count,
                "items_count": items_count,
                "qty": qty_value,
                "kitchen_load_qty": kitchen_load_value,
                "hall_load_qty": hall_load_value,
                "sum": sum_value,
                "discount_sum": discount_value,
            }
        )

    if waiter_payload is None:
        resolved_user_id, resolved_waiter_name = _resolve_waiter_identity(
            waiter_user_id=waiter_user_id,
            waiter_iiko_id=clean_waiter_iiko_id,
            waiter_iiko_code=clean_waiter_iiko_code,
            waiter_name_iiko=None,
            user_name_by_id=user_name_by_id,
            user_meta_by_iiko_id=user_meta_by_iiko_id,
            user_meta_by_iiko_code=user_meta_by_iiko_code,
        )
        waiter_payload = {
            "waiter_user_id": resolved_user_id,
            "waiter_iiko_id": clean_waiter_iiko_id,
            "waiter_iiko_code": clean_waiter_iiko_code,
            "waiter_name": resolved_waiter_name,
            "waiter_name_iiko": None,
        }

    if not can_view_money:
        _zero_money_metrics(totals)
        for row in items:
            _zero_money_metrics(row)

    return {
        "from_date": start.isoformat(),
        "to_date": (end_excl - timedelta(days=1)).isoformat(),
        "deleted_mode": resolved_deleted_mode,
        "waiter_mode": resolved_waiter_mode,
        "restaurant_id": restaurant_id,
        "waiter": waiter_payload,
        "items": items,
        "totals": {
            "orders_count": int(totals["orders_count"]),
            "guests_count": int(totals["guests_count"]),
            "items_count": int(totals["items_count"]),
            "qty": round(float(totals["qty"]), 3),
            "kitchen_load_qty": round(float(totals["kitchen_load_qty"]), 3),
            "hall_load_qty": round(float(totals["hall_load_qty"]), 3),
            "sum": round(float(totals["sum"]), 2),
            "discount_sum": round(float(totals["discount_sum"]), 2),
        },
    }


@router.get("/orders")
def list_orders(
    restaurant_id: Optional[int] = Query(None),
    source_restaurant_id: Optional[int] = Query(None),
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    waiter_user_id: Optional[int] = Query(None),
    waiter_iiko_id: Optional[str] = Query(None),
    waiter_iiko_code: Optional[str] = Query(None),
    dish_code: Optional[str] = Query(None),
    include_payment_types: Optional[List[str]] = Query(None),
    include_groups: Optional[List[str]] = Query(None),
    include_categories: Optional[List[str]] = Query(None),
    include_positions: Optional[List[str]] = Query(None),
    include_halls: Optional[List[str]] = Query(None),
    include_departments: Optional[List[str]] = Query(None),
    include_tables: Optional[List[str]] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    with_meta: bool = Query(False, description="Return object {items,total,limit,offset} instead of plain list"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    if restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
    if source_restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    accessible_ids = [r.id for r in accessible_restaurants]
    restaurant_name_by_id = {r.id: r.name for r in accessible_restaurants}
    if not accessible_ids:
        if with_meta:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        return []

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)
    resolved_deleted_mode = _normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = _normalize_waiter_mode(waiter_mode)
    clean_waiter_iiko_id = _clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = _clean_optional_text(waiter_iiko_code)
    clean_dish_code = _clean_optional_text(dish_code)

    include_groups_lower = _lower_values(_split_filter_values(include_groups))
    include_categories_lower = _lower_values(_split_filter_values(include_categories))
    include_positions_lower = _lower_values(_split_filter_values(include_positions))
    include_payment_types_lower = _lower_values(_split_filter_values(include_payment_types))
    include_halls_lower = _lower_values(_split_filter_values(include_halls))
    include_departments_lower = _lower_values(_split_filter_values(include_departments))
    include_tables_lower = _lower_values(_split_filter_values(include_tables))

    q = (
        db.query(IikoSaleOrder)
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_excl)
        .order_by(IikoSaleOrder.open_date.desc(), IikoSaleOrder.opened_at.desc().nullslast(), IikoSaleOrder.id.desc())
    )
    q = _apply_deleted_mode_filter(
        q,
        deleted_mode=resolved_deleted_mode,
        order_deleted_expr=IikoSaleOrder.raw_payload["OrderDeleted"].astext,
        deleted_with_writeoff_expr=IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
    )
    if restaurant_id is not None:
        q = q.filter(IikoSaleOrder.restaurant_id == restaurant_id)
    if source_restaurant_id is not None:
        q = q.filter(sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id) == source_restaurant_id)
    if include_departments_lower:
        q = q.filter(
            sa.func.lower(sa.func.coalesce(IikoSaleOrder.department, "")).in_(include_departments_lower)
        )
    if include_tables_lower:
        q = q.filter(
            sa.func.lower(sa.func.coalesce(IikoSaleOrder.table_num, "")).in_(include_tables_lower)
        )
    if include_halls_lower:
        q = _apply_hall_filter_to_base_query(db, current_user, q, include_halls_lower)

    has_item_scope_filters = bool(
        include_groups_lower
        or include_categories_lower
        or include_positions_lower
        or include_payment_types_lower
        or clean_dish_code
        or waiter_user_id is not None
        or clean_waiter_iiko_id
        or clean_waiter_iiko_code
    )
    if has_item_scope_filters:
        group_expr = _dish_group_sql_expr()
        category_expr = _dish_category_sql_expr()
        position_expr = sa.func.coalesce(IikoSaleItem.dish_name, IikoProduct.name, IikoSaleItem.dish_code)
        payment_type_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["PayTypes"].astext,
            IikoSaleItem.raw_payload["NonCashPaymentType"].astext,
            IikoSaleItem.raw_payload["PaymentType"].astext,
            IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
            IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
            IikoSaleItem.raw_payload["PaymentType.Id"].astext,
        )

        group_expr_lower = sa.func.lower(sa.func.coalesce(group_expr, ""))
        category_expr_lower = sa.func.lower(sa.func.coalesce(category_expr, ""))
        position_expr_lower = sa.func.lower(sa.func.coalesce(position_expr, ""))
        payment_type_expr_lower = sa.func.lower(sa.func.coalesce(payment_type_expr, ""))

        scoped_items_q = (
            db.query(IikoSaleItem.order_id.label("order_id"))
            .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
            .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
            .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
            .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
            .filter(IikoSaleOrder.open_date >= start)
            .filter(IikoSaleOrder.open_date < end_excl)
        )
        scoped_items_q = _apply_deleted_mode_filter(
            scoped_items_q,
            deleted_mode=resolved_deleted_mode,
            order_deleted_expr=sa.func.coalesce(
                IikoSaleItem.raw_payload["OrderDeleted"].astext,
                IikoSaleOrder.raw_payload["OrderDeleted"].astext,
            ),
            deleted_with_writeoff_expr=sa.func.coalesce(
                IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
                IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
            ),
        )
        if restaurant_id is not None:
            scoped_items_q = scoped_items_q.filter(IikoSaleOrder.restaurant_id == restaurant_id)
        if source_restaurant_id is not None:
            scoped_items_q = scoped_items_q.filter(
                sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id) == source_restaurant_id
            )
        if include_departments_lower:
            scoped_items_q = scoped_items_q.filter(
                sa.func.lower(sa.func.coalesce(IikoSaleOrder.department, "")).in_(include_departments_lower)
            )
        if include_tables_lower:
            scoped_items_q = scoped_items_q.filter(
                sa.func.lower(sa.func.coalesce(IikoSaleOrder.table_num, "")).in_(include_tables_lower)
            )
        if include_halls_lower:
            scoped_items_q = _apply_hall_filter_to_base_query(db, current_user, scoped_items_q, include_halls_lower)

        scoped_items_q = _apply_waiter_filter_to_items_query(
            db,
            scoped_items_q,
            waiter_mode=resolved_waiter_mode,
            waiter_user_id=waiter_user_id,
            waiter_iiko_id=clean_waiter_iiko_id,
            waiter_iiko_code=clean_waiter_iiko_code,
        )

        if clean_dish_code:
            scoped_items_q = scoped_items_q.filter(IikoSaleItem.dish_code == clean_dish_code)
        if include_groups_lower:
            scoped_items_q = scoped_items_q.filter(group_expr_lower.in_(include_groups_lower))
        if include_categories_lower:
            scoped_items_q = scoped_items_q.filter(category_expr_lower.in_(include_categories_lower))
        if include_positions_lower:
            scoped_items_q = scoped_items_q.filter(position_expr_lower.in_(include_positions_lower))
        if include_payment_types_lower:
            scoped_items_q = scoped_items_q.filter(payment_type_expr_lower.in_(include_payment_types_lower))

        scoped_items_subq = scoped_items_q.distinct().subquery(name="sales_orders_items_scope")
        q = q.filter(IikoSaleOrder.id.in_(sa.select(scoped_items_subq.c.order_id)))

    total = q.count() if with_meta else None
    rows = q.offset(offset).limit(limit).all()

    order_hall_meta_by_id: Dict[str, Dict[str, Any]] = {}
    if rows:
        hall_rows_q = _sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.is_active.is_(True))
        row_restaurant_ids = {int(row.restaurant_id) for row in rows if row.restaurant_id is not None}
        if row_restaurant_ids:
            hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.restaurant_id.in_(sorted(row_restaurant_ids)))
        resolve_hall = _build_sales_hall_table_resolver(hall_rows_q.all())
        for row in rows:
            resolved = resolve_hall(
                restaurant_id=row.restaurant_id,
                source_restaurant_id=row.source_restaurant_id,
                department=row.department,
                table_num=row.table_num,
            )
            order_hall_meta_by_id[str(row.id)] = resolved

    payment_by_order_id: Dict[str, tuple[Optional[str], Optional[str]]] = {}
    non_cash_by_order_id: Dict[str, tuple[Optional[str], Optional[str]]] = {}
    cashier_name_iiko_by_order_id: Dict[str, Optional[str]] = {}
    auth_user_name_iiko_by_order_id: Dict[str, Optional[str]] = {}
    order_waiter_name_iiko_by_order_id: Dict[str, Optional[str]] = {}
    payment_guids: set[str] = set()
    non_cash_ids: set[str] = set()
    user_ids: set[int] = set()
    for row in rows:
        pay_guid, pay_name = _extract_payment_method_fields(row.raw_payload)
        non_cash_id, non_cash_name = _extract_non_cash_fields(row.raw_payload)
        row_id = str(row.id)
        payment_by_order_id[row_id] = (pay_guid, pay_name)
        non_cash_by_order_id[row_id] = (non_cash_id, non_cash_name)
        cashier_name_iiko_by_order_id[row_id] = _extract_payload_text(row.raw_payload, "Cashier.Name")
        auth_user_name_iiko_by_order_id[row_id] = _extract_payload_text(row.raw_payload, "AuthUser.Name")
        order_waiter_name_iiko_by_order_id[row_id] = _extract_payload_text(row.raw_payload, "OrderWaiter.Name")
        if pay_guid:
            payment_guids.add(pay_guid)
        if non_cash_id:
            non_cash_ids.add(non_cash_id)
        if row.order_waiter_user_id is not None:
            user_ids.add(int(row.order_waiter_user_id))
        if row.cashier_user_id is not None:
            user_ids.add(int(row.cashier_user_id))
        if row.auth_user_id is not None:
            user_ids.add(int(row.auth_user_id))

    payment_lookup = _payment_method_lookup_by_guid(db, current_user, payment_guids)
    non_cash_lookup = _non_cash_lookup_by_id(db, current_user, non_cash_ids)
    user_name_by_id = _user_names_by_ids(db, user_ids)

    items = [
        {
            "id": str(row.id),
            "company_id": row.company_id,
            "restaurant_id": row.restaurant_id,
            "restaurant_name": restaurant_name_by_id.get(row.restaurant_id),
            "source_restaurant_id": row.source_restaurant_id,
            "source_restaurant_name": (
                restaurant_name_by_id.get(row.source_restaurant_id)
                if row.source_restaurant_id is not None
                else restaurant_name_by_id.get(row.restaurant_id)
            ),
            "iiko_order_id": row.iiko_order_id,
            "order_num": row.order_num,
            "open_date": row.open_date.isoformat() if row.open_date else None,
            "opened_at": row.opened_at.isoformat() if row.opened_at else None,
            "closed_at": row.closed_at.isoformat() if row.closed_at else None,
            "department": row.department,
            "hall_name": (order_hall_meta_by_id.get(str(row.id)) or {}).get("hall_name"),
            "hall_name_norm": (order_hall_meta_by_id.get(str(row.id)) or {}).get("hall_name_norm"),
            "zone_name": (order_hall_meta_by_id.get(str(row.id)) or {}).get("zone_name"),
            "zone_name_norm": (order_hall_meta_by_id.get(str(row.id)) or {}).get("zone_name_norm"),
            "table_num": row.table_num,
            "table_name": (order_hall_meta_by_id.get(str(row.id)) or {}).get("table_name"),
            "table_capacity": (order_hall_meta_by_id.get(str(row.id)) or {}).get("capacity"),
            "guest_num": row.guest_num,
            "order_waiter_iiko_id": row.order_waiter_iiko_id,
            "order_waiter_name": row.order_waiter_name,
            "order_waiter_name_iiko": (
                order_waiter_name_iiko_by_order_id.get(str(row.id))
                or row.order_waiter_name
            ),
            "cashier_iiko_id": row.cashier_iiko_id,
            "cashier_code": row.cashier_code,
            "cashier_name_iiko": cashier_name_iiko_by_order_id.get(str(row.id)),
            "auth_user_iiko_id": row.auth_user_iiko_id,
            "auth_user_name_iiko": auth_user_name_iiko_by_order_id.get(str(row.id)),
            "order_waiter_user_id": row.order_waiter_user_id,
            "order_waiter_user_name": user_name_by_id.get(int(row.order_waiter_user_id))
            if row.order_waiter_user_id is not None
            else None,
            "cashier_user_id": row.cashier_user_id,
            "cashier_user_name": user_name_by_id.get(int(row.cashier_user_id))
            if row.cashier_user_id is not None
            else None,
            "auth_user_id": row.auth_user_id,
            "auth_user_name": user_name_by_id.get(int(row.auth_user_id))
            if row.auth_user_id is not None
            else None,
            "payment_method_guid": payment_by_order_id.get(str(row.id), (None, None))[0],
            "payment_method_name": (
                payment_lookup.get(payment_by_order_id.get(str(row.id), (None, None))[0], {}).get("name")
                or payment_by_order_id.get(str(row.id), (None, None))[1]
            ),
            "non_cash_payment_type_id": non_cash_by_order_id.get(str(row.id), (None, None))[0],
            "non_cash_payment_type_name": (
                non_cash_lookup.get(non_cash_by_order_id.get(str(row.id), (None, None))[0], {}).get("name")
                or non_cash_by_order_id.get(str(row.id), (None, None))[1]
            ),
            "non_cash_payment_type_category": non_cash_lookup.get(
                non_cash_by_order_id.get(str(row.id), (None, None))[0],
                {},
            ).get("category"),
            "non_cash_payment_type_is_active": non_cash_lookup.get(
                non_cash_by_order_id.get(str(row.id), (None, None))[0],
                {},
            ).get("is_active"),
            "payment_method_category": payment_lookup.get(
                payment_by_order_id.get(str(row.id), (None, None))[0],
                {},
            ).get("category"),
            "payment_method_is_active": payment_lookup.get(
                payment_by_order_id.get(str(row.id), (None, None))[0],
                {},
            ).get("is_active"),
            **_serialize_deleted_payload(row.raw_payload),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]
    if with_meta:
        return {"items": items, "total": total, "limit": limit, "offset": offset}
    return items


@router.get("/items")
def list_items(
    restaurant_id: Optional[int] = Query(None),
    source_restaurant_id: Optional[int] = Query(None),
    order_id: Optional[UUID] = Query(None, description="Local order UUID"),
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    dish_code: Optional[str] = Query(None),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    waiter_user_id: Optional[int] = Query(None),
    waiter_iiko_id: Optional[str] = Query(None),
    waiter_iiko_code: Optional[str] = Query(None),
    include_payment_types: Optional[List[str]] = Query(None),
    include_groups: Optional[List[str]] = Query(None),
    include_categories: Optional[List[str]] = Query(None),
    include_positions: Optional[List[str]] = Query(None),
    include_halls: Optional[List[str]] = Query(None),
    include_departments: Optional[List[str]] = Query(None),
    include_tables: Optional[List[str]] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    with_meta: bool = Query(False, description="Return object {items,total,limit,offset} instead of plain list"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    can_view_money = _can_view_sales_money(current_user)
    if restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
    if source_restaurant_id is not None:
        _ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)

    accessible_restaurants = _list_accessible_restaurants(db, current_user)
    accessible_ids = [r.id for r in accessible_restaurants]
    restaurant_name_by_id = {r.id: r.name for r in accessible_restaurants}
    if not accessible_ids:
        if with_meta:
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "totals": {
                    "qty": 0.0,
                    "kitchen_load_qty": 0.0,
                    "hall_load_qty": 0.0,
                    "sum": 0.0,
                    "discount_sum": 0.0,
                },
            }
        return []

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)
    resolved_deleted_mode = _normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = _normalize_waiter_mode(waiter_mode)
    clean_waiter_iiko_id = _clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = _clean_optional_text(waiter_iiko_code)
    clean_dish_code = _clean_optional_text(dish_code)

    include_groups_lower = _lower_values(_split_filter_values(include_groups))
    include_categories_lower = _lower_values(_split_filter_values(include_categories))
    include_positions_lower = _lower_values(_split_filter_values(include_positions))
    include_payment_types_lower = _lower_values(_split_filter_values(include_payment_types))
    include_halls_lower = _lower_values(_split_filter_values(include_halls))
    include_departments_lower = _lower_values(_split_filter_values(include_departments))
    include_tables_lower = _lower_values(_split_filter_values(include_tables))

    base_q = (
        db.query(IikoSaleItem)
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_excl)
    )

    group_expr = _dish_group_sql_expr()
    category_expr = _dish_category_sql_expr()
    position_expr = sa.func.coalesce(IikoSaleItem.dish_name, IikoProduct.name, IikoSaleItem.dish_code)
    payment_type_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["PayTypes"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType"].astext,
        IikoSaleItem.raw_payload["PaymentType"].astext,
        IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
        IikoSaleItem.raw_payload["PaymentType.Id"].astext,
    )
    group_expr_lower = sa.func.lower(sa.func.coalesce(group_expr, ""))
    category_expr_lower = sa.func.lower(sa.func.coalesce(category_expr, ""))
    position_expr_lower = sa.func.lower(sa.func.coalesce(position_expr, ""))
    payment_type_expr_lower = sa.func.lower(sa.func.coalesce(payment_type_expr, ""))

    portion_coef_kitchen_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_kitchen, 1.0), sa.Float)
    portion_coef_hall_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_hall, 1.0), sa.Float)
    kitchen_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_kitchen_expr
    hall_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_hall_expr
    base_q = _apply_deleted_mode_filter(
        base_q,
        deleted_mode=resolved_deleted_mode,
        order_deleted_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["OrderDeleted"].astext,
            IikoSaleOrder.raw_payload["OrderDeleted"].astext,
        ),
        deleted_with_writeoff_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
            IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
        ),
    )
    if restaurant_id is not None:
        base_q = base_q.filter(IikoSaleOrder.restaurant_id == restaurant_id)
    if source_restaurant_id is not None:
        base_q = base_q.filter(
            sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id) == source_restaurant_id
        )
    if order_id is not None:
        base_q = base_q.filter(IikoSaleItem.order_id == order_id)
    if include_departments_lower:
        base_q = base_q.filter(sa.func.lower(sa.func.coalesce(IikoSaleOrder.department, "")).in_(include_departments_lower))
    if include_tables_lower:
        base_q = base_q.filter(sa.func.lower(sa.func.coalesce(IikoSaleOrder.table_num, "")).in_(include_tables_lower))
    if include_halls_lower:
        base_q = _apply_hall_filter_to_base_query(db, current_user, base_q, include_halls_lower)

    base_q = _apply_waiter_filter_to_items_query(
        db,
        base_q,
        waiter_mode=resolved_waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=clean_waiter_iiko_id,
        waiter_iiko_code=clean_waiter_iiko_code,
    )

    if clean_dish_code:
        base_q = base_q.filter(IikoSaleItem.dish_code == clean_dish_code)
    if include_groups_lower:
        base_q = base_q.filter(group_expr_lower.in_(include_groups_lower))
    if include_categories_lower:
        base_q = base_q.filter(category_expr_lower.in_(include_categories_lower))
    if include_positions_lower:
        base_q = base_q.filter(position_expr_lower.in_(include_positions_lower))
    if include_payment_types_lower:
        base_q = base_q.filter(payment_type_expr_lower.in_(include_payment_types_lower))

    total = base_q.count() if with_meta else None
    totals = None
    if with_meta:
        qty_total, kitchen_load_total, hall_load_total, sum_total, discount_total = (
            base_q.with_entities(
                sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0),
                sa.func.coalesce(sa.func.sum(kitchen_load_expr), 0),
                sa.func.coalesce(sa.func.sum(hall_load_expr), 0),
                sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0),
                sa.func.coalesce(sa.func.sum(IikoSaleItem.discount_sum), 0),
            ).one()
        )
        totals = {
            "qty": float(qty_total or 0),
            "kitchen_load_qty": float(kitchen_load_total or 0),
            "hall_load_qty": float(hall_load_total or 0),
            "sum": float(sum_total or 0),
            "discount_sum": float(discount_total or 0),
        }

    rows = (
        base_q.order_by(IikoSaleItem.open_date.desc(), IikoSaleItem.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    order_meta_by_id: Dict[str, Dict[str, Any]] = {}
    order_ids_for_rows = {row.order_id for row in rows if getattr(row, "order_id", None) is not None}
    if order_ids_for_rows:
        order_rows = (
            db.query(
                IikoSaleOrder.id.label("id"),
                IikoSaleOrder.restaurant_id.label("restaurant_id"),
                IikoSaleOrder.source_restaurant_id.label("source_restaurant_id"),
                IikoSaleOrder.department.label("department"),
                IikoSaleOrder.table_num.label("table_num"),
            )
            .filter(IikoSaleOrder.id.in_(sorted(order_ids_for_rows, key=lambda value: str(value))))
            .all()
        )
        hall_rows_q = _sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.is_active.is_(True))
        order_restaurant_ids = {
            int(order_row.restaurant_id)
            for order_row in order_rows
            if order_row.restaurant_id is not None
        }
        if order_restaurant_ids:
            hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.restaurant_id.in_(sorted(order_restaurant_ids)))
        resolve_hall = _build_sales_hall_table_resolver(hall_rows_q.all())
        for order_row in order_rows:
            resolved = resolve_hall(
                restaurant_id=order_row.restaurant_id,
                source_restaurant_id=order_row.source_restaurant_id,
                department=order_row.department,
                table_num=order_row.table_num,
            )
            order_meta_by_id[str(order_row.id)] = {
                "department": order_row.department,
                "table_num": order_row.table_num,
                "hall_name": resolved.get("hall_name"),
                "hall_name_norm": resolved.get("hall_name_norm"),
                "zone_name": resolved.get("zone_name"),
                "zone_name_norm": resolved.get("zone_name_norm"),
                "table_name": resolved.get("table_name"),
                "table_capacity": resolved.get("capacity"),
            }

    payment_by_item_id: Dict[str, tuple[Optional[str], Optional[str]]] = {}
    non_cash_by_item_id: Dict[str, tuple[Optional[str], Optional[str]]] = {}
    cashier_name_iiko_by_item_id: Dict[str, Optional[str]] = {}
    auth_user_name_iiko_by_item_id: Dict[str, Optional[str]] = {}
    order_waiter_name_iiko_by_item_id: Dict[str, Optional[str]] = {}
    dish_waiter_iiko_id_by_item_id: Dict[str, Optional[str]] = {}
    dish_waiter_name_iiko_by_item_id: Dict[str, Optional[str]] = {}
    dish_waiter_code_by_item_id: Dict[str, Optional[str]] = {}
    dish_waiter_source_by_item_id: Dict[str, Optional[str]] = {}
    payment_guids: set[str] = set()
    non_cash_ids: set[str] = set()
    user_ids: set[int] = set()
    iiko_ids: set[str] = set()
    iiko_codes: set[str] = set()
    for row in rows:
        pay_guid, pay_name = _extract_payment_method_fields(row.raw_payload)
        non_cash_id, non_cash_name = _extract_non_cash_fields(row.raw_payload)
        dish_waiter_iiko_id, dish_waiter_name_iiko, dish_waiter_code, dish_waiter_source = _extract_dish_waiter_fields(
            row.raw_payload
        )
        row_id = str(row.id)
        payment_by_item_id[row_id] = (pay_guid, pay_name)
        non_cash_by_item_id[row_id] = (non_cash_id, non_cash_name)
        cashier_name_iiko_by_item_id[row_id] = _extract_payload_text(row.raw_payload, "Cashier.Name")
        auth_user_name_iiko_by_item_id[row_id] = _extract_payload_text(row.raw_payload, "AuthUser.Name")
        order_waiter_name_iiko_by_item_id[row_id] = _extract_payload_text(row.raw_payload, "OrderWaiter.Name")
        dish_waiter_iiko_id_by_item_id[row_id] = dish_waiter_iiko_id
        dish_waiter_name_iiko_by_item_id[row_id] = dish_waiter_name_iiko
        dish_waiter_code_by_item_id[row_id] = dish_waiter_code
        dish_waiter_source_by_item_id[row_id] = dish_waiter_source
        if pay_guid:
            payment_guids.add(pay_guid)
        if non_cash_id:
            non_cash_ids.add(non_cash_id)
        if row.auth_user_id is not None:
            user_ids.add(int(row.auth_user_id))
        if row.auth_user_iiko_id:
            iiko_ids.add(str(row.auth_user_iiko_id))
        if row.order_waiter_iiko_id:
            iiko_ids.add(str(row.order_waiter_iiko_id))
        if dish_waiter_iiko_id:
            iiko_ids.add(str(dish_waiter_iiko_id))
        if dish_waiter_code:
            iiko_codes.add(str(dish_waiter_code))

    payment_lookup = _payment_method_lookup_by_guid(db, current_user, payment_guids)
    non_cash_lookup = _non_cash_lookup_by_id(db, current_user, non_cash_ids)
    user_name_by_id = _user_names_by_ids(db, user_ids)
    user_meta_by_iiko_id = _user_meta_by_iiko_ids(db, iiko_ids)
    user_meta_by_iiko_code = _user_meta_by_iiko_codes(db, iiko_codes)

    product_ids = {str(row.iiko_product_id) for row in rows if row.iiko_product_id}
    product_meta_by_id: Dict[str, Dict[str, Any]] = {}
    if product_ids:
        coef_rows = (
            db.query(
                IikoProduct.id.label("product_id"),
                IikoProductSetting.portion_coef_kitchen.label("portion_coef_kitchen"),
                IikoProductSetting.portion_coef_hall.label("portion_coef_hall"),
                IikoProduct.product_category.label("product_category"),
                sa.func.jsonb_extract_path_text(
                    IikoProduct.raw_payload,
                    "product",
                    "product_category",
                ).label("legacy_product_category"),
                IikoProductSetting.custom_product_category.label("custom_product_category"),
            )
            .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
            .filter(IikoProduct.id.in_(product_ids))
            .all()
        )
        for coef_row in coef_rows:
            custom_category = _clean_optional_text(getattr(coef_row, "custom_product_category", None))
            base_category = _clean_optional_text(getattr(coef_row, "product_category", None))
            legacy_category = _clean_optional_text(getattr(coef_row, "legacy_product_category", None))
            product_meta_by_id[str(coef_row.product_id)] = {
                "portion_coef_kitchen": float(coef_row.portion_coef_kitchen)
                if coef_row.portion_coef_kitchen is not None
                else None,
                "portion_coef_hall": float(coef_row.portion_coef_hall)
                if coef_row.portion_coef_hall is not None
                else None,
                "dish_category": custom_category or legacy_category or base_category,
            }

    items: List[Dict[str, Any]] = []
    for row in rows:
        qty_value = float(row.qty) if row.qty is not None else None
        sum_value = float(row.sum) if row.sum is not None else None
        discount_value = float(row.discount_sum) if row.discount_sum is not None else None
        row_id = str(row.id)

        dish_waiter_iiko_id = dish_waiter_iiko_id_by_item_id.get(row_id)
        dish_waiter_name_iiko = dish_waiter_name_iiko_by_item_id.get(row_id)
        dish_waiter_code = dish_waiter_code_by_item_id.get(row_id)
        dish_waiter_source = dish_waiter_source_by_item_id.get(row_id)
        dish_waiter_meta: Dict[str, Any] = {}
        if dish_waiter_iiko_id:
            dish_waiter_meta = user_meta_by_iiko_id.get(str(dish_waiter_iiko_id), {})
        if not dish_waiter_meta and dish_waiter_code:
            dish_waiter_meta = user_meta_by_iiko_code.get(str(dish_waiter_code), {})
        dish_waiter_user_id = dish_waiter_meta.get("id")
        dish_waiter_user_name = dish_waiter_meta.get("name")

        product_meta = product_meta_by_id.get(str(row.iiko_product_id), {})
        coef_values = product_meta
        kitchen_coef = coef_values.get("portion_coef_kitchen")
        hall_coef = coef_values.get("portion_coef_hall")
        dish_category_from_product = _clean_optional_text(product_meta.get("dish_category"))
        if _looks_like_uuid(dish_category_from_product):
            dish_category_from_product = None
        dish_category_from_payload = _extract_dish_category_name(row.raw_payload)
        dish_category_id = _clean_optional_text(row.dish_category_id)
        dish_category_from_id = dish_category_id if dish_category_id and not _looks_like_uuid(dish_category_id) else None
        dish_category_resolved = (
            dish_category_from_payload
            or dish_category_from_product
            or dish_category_from_id
        )

        kitchen_load_value = (
            qty_value * (kitchen_coef if kitchen_coef is not None else 1.0)
            if qty_value is not None
            else None
        )
        hall_load_value = (
            qty_value * (hall_coef if hall_coef is not None else 1.0)
            if qty_value is not None
            else None
        )

        items.append(
            {
                "id": str(row.id),
                "order_id": str(row.order_id),
                "company_id": row.company_id,
                "restaurant_id": row.restaurant_id,
                "restaurant_name": restaurant_name_by_id.get(row.restaurant_id),
                "source_restaurant_id": row.source_restaurant_id,
                "source_restaurant_name": (
                    restaurant_name_by_id.get(row.source_restaurant_id)
                    if row.source_restaurant_id is not None
                    else restaurant_name_by_id.get(row.restaurant_id)
                ),
                "department": (order_meta_by_id.get(str(row.order_id)) or {}).get("department"),
                "hall_name": (order_meta_by_id.get(str(row.order_id)) or {}).get("hall_name"),
                "hall_name_norm": (order_meta_by_id.get(str(row.order_id)) or {}).get("hall_name_norm"),
                "zone_name": (order_meta_by_id.get(str(row.order_id)) or {}).get("zone_name"),
                "zone_name_norm": (order_meta_by_id.get(str(row.order_id)) or {}).get("zone_name_norm"),
                "table_num": (order_meta_by_id.get(str(row.order_id)) or {}).get("table_num"),
                "table_name": (order_meta_by_id.get(str(row.order_id)) or {}).get("table_name"),
                "table_capacity": (order_meta_by_id.get(str(row.order_id)) or {}).get("table_capacity"),
                "open_date": row.open_date.isoformat() if row.open_date else None,
                "line_key": row.line_key,
                "dish_code": row.dish_code,
                "dish_name": row.dish_name,
                "dish_group": row.dish_group,
                "dish_category_id": row.dish_category_id,
                "dish_category": dish_category_resolved,
                "dish_measure_unit": row.dish_measure_unit,
                "cooking_place": row.cooking_place,
                "qty": qty_value,
                "portion_coef_kitchen": kitchen_coef,
                "portion_coef_hall": hall_coef,
                "kitchen_load_qty": kitchen_load_value,
                "hall_load_qty": hall_load_value,
                "sum": sum_value,
                "discount_sum": discount_value,
                "cashier_code": row.cashier_code,
                "cashier_name_iiko": cashier_name_iiko_by_item_id.get(row_id),
                "order_waiter_iiko_id": row.order_waiter_iiko_id,
                "order_waiter_name_iiko": order_waiter_name_iiko_by_item_id.get(row_id),
                "order_waiter_user_name": (
                    user_meta_by_iiko_id.get(str(row.order_waiter_iiko_id), {}).get("name")
                    if row.order_waiter_iiko_id
                    else None
                ),
                "dish_waiter_iiko_id": dish_waiter_iiko_id,
                "dish_waiter_code": dish_waiter_code,
                "dish_waiter_name_iiko": dish_waiter_name_iiko,
                "dish_waiter_source": dish_waiter_source,
                "dish_waiter_user_id": dish_waiter_user_id,
                "dish_waiter_user_name": dish_waiter_user_name
                or dish_waiter_name_iiko
                or dish_waiter_code
                or dish_waiter_iiko_id,
                "auth_user_iiko_id": row.auth_user_iiko_id,
                "auth_user_name_iiko": auth_user_name_iiko_by_item_id.get(row_id),
                "auth_user_id": row.auth_user_id,
                "auth_user_name": (
                    user_name_by_id.get(int(row.auth_user_id))
                    if row.auth_user_id is not None
                    else user_meta_by_iiko_id.get(str(row.auth_user_iiko_id), {}).get("name")
                    if row.auth_user_iiko_id
                    else None
                ),
                "iiko_product_id": row.iiko_product_id,
                "payment_method_guid": payment_by_item_id.get(str(row.id), (None, None))[0],
                "payment_method_name": (
                    payment_lookup.get(payment_by_item_id.get(str(row.id), (None, None))[0], {}).get("name")
                    or payment_by_item_id.get(str(row.id), (None, None))[1]
                ),
                "non_cash_payment_type_id": non_cash_by_item_id.get(str(row.id), (None, None))[0],
                "non_cash_payment_type_name": (
                    non_cash_lookup.get(non_cash_by_item_id.get(str(row.id), (None, None))[0], {}).get("name")
                    or non_cash_by_item_id.get(str(row.id), (None, None))[1]
                ),
                "non_cash_payment_type_category": non_cash_lookup.get(
                    non_cash_by_item_id.get(str(row.id), (None, None))[0],
                    {},
                ).get("category"),
                "non_cash_payment_type_is_active": non_cash_lookup.get(
                    non_cash_by_item_id.get(str(row.id), (None, None))[0],
                    {},
                ).get("is_active"),
                "payment_method_category": payment_lookup.get(
                    payment_by_item_id.get(str(row.id), (None, None))[0],
                    {},
                ).get("category"),
                "payment_method_is_active": payment_lookup.get(
                    payment_by_item_id.get(str(row.id), (None, None))[0],
                    {},
                ).get("is_active"),
                **_serialize_deleted_payload(row.raw_payload),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        )
    if not can_view_money:
        if totals is not None:
            _zero_money_metrics(totals)
        for row in items:
            _zero_money_metrics(row)
    if with_meta:
        return {"items": items, "total": total, "limit": limit, "offset": offset, "totals": totals}
    return items
