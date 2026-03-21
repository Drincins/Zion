# backend/routers/restaurants.py
from __future__ import annotations

import hashlib
import re
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.iiko_sales import IikoSalesSyncSetting
from backend.bd.models import Company, Restaurant, User
from backend.routers.iiko_sales import (
    SyncIikoSalesRequest,
    _parse_sales_sync_application_name,
    sync_iiko_sales,
)
from backend.schemas import RestaurantCreate, RestaurantRead
from backend.services.permissions import PermissionCode, require_permissions, has_permission
from backend.services.reference_cache import cached_reference_data, invalidate_reference_scope
from backend.utils import get_user_restaurant_ids, user_has_global_access, get_current_user, now_local

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])
TIME_HHMM_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
RESTAURANTS_LIST_CACHE_SCOPE = "restaurants:list"
RESTAURANTS_LIST_CACHE_TTL_SECONDS = 60

RESTAURANT_SETTINGS_VIEW_PERMISSIONS = (
    PermissionCode.RESTAURANTS_SETTINGS_VIEW,
    PermissionCode.RESTAURANTS_SETTINGS_MANAGE,
    PermissionCode.RESTAURANTS_MANAGE,
)
RESTAURANT_SETTINGS_MANAGE_PERMISSIONS = (
    PermissionCode.RESTAURANTS_SETTINGS_MANAGE,
    PermissionCode.RESTAURANTS_MANAGE,
)


class RestaurantSalesSyncSettingsRead(BaseModel):
    restaurant_id: int
    auto_sync_enabled: bool
    daily_sync_time: str
    daily_lookback_days: int
    weekly_sync_enabled: bool
    weekly_sync_weekday: int
    weekly_sync_time: str
    weekly_lookback_days: int
    manual_default_lookback_days: int
    last_daily_run_on: Optional[str] = None
    last_weekly_run_on: Optional[str] = None
    last_sync_at: Optional[str] = None
    last_successful_sync_at: Optional[str] = None
    last_manual_sync_at: Optional[str] = None
    last_sync_scope: Optional[str] = None
    last_sync_status: Optional[str] = None
    last_sync_error: Optional[str] = None


class RestaurantSalesSyncSettingsUpdate(BaseModel):
    auto_sync_enabled: Optional[bool] = None
    daily_sync_time: Optional[str] = None
    daily_lookback_days: Optional[int] = Field(default=None, ge=0, le=90)
    weekly_sync_enabled: Optional[bool] = None
    weekly_sync_weekday: Optional[int] = Field(default=None, ge=0, le=6)
    weekly_sync_time: Optional[str] = None
    weekly_lookback_days: Optional[int] = Field(default=None, ge=0, le=365)
    manual_default_lookback_days: Optional[int] = Field(default=None, ge=0, le=365)


class RestaurantSalesSyncRunRequest(BaseModel):
    from_date: str
    to_date: str


class RestaurantSalesSyncOperationRead(BaseModel):
    pid: int
    state: Optional[str] = None
    stage: str
    wait_event_type: Optional[str] = None
    wait_event: Optional[str] = None
    started_at: Optional[str] = None
    age_seconds: int
    restaurant_id: Optional[int] = None
    actor: Optional[str] = None
    source_hash: Optional[str] = None
    query: Optional[str] = None


class RestaurantSalesSyncCancelRequest(BaseModel):
    pid: int
    force: bool = False


def get_current_user_restaurant_view(current_user: User = Depends(get_current_user)) -> User:
    """Allow restaurants list/read if user has view/manage or staff_portal.access."""
    if user_has_global_access(current_user):
        return current_user
    if has_permission(current_user, PermissionCode.RESTAURANTS_SETTINGS_VIEW):
        return current_user
    if has_permission(current_user, PermissionCode.RESTAURANTS_SETTINGS_MANAGE):
        return current_user
    if has_permission(current_user, PermissionCode.RESTAURANTS_VIEW):
        return current_user
    if has_permission(current_user, PermissionCode.RESTAURANTS_MANAGE):
        return current_user
    if has_permission(current_user, PermissionCode.STAFF_PORTAL_ACCESS):
        return current_user
    raise HTTPException(status_code=403, detail="Access denied")


def ensure_user_access_to_restaurant(
    db: Session,
    current_user: User,
    restaurant_id: int,
    *,
    require_credentials: bool = False,
) -> Restaurant:
    if user_has_global_access(current_user) or has_permission(current_user, PermissionCode.RESTAURANTS_MANAGE):
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


def hash_iiko_password_sha1(password: str) -> str:
    """iiko API ожидает предрасчитанный SHA-1-хеш пароля."""
    # Важно: не заменяйте на другие алгоритмы (bcrypt/argon2). Внешний сервис принимает только SHA-1.
    return hashlib.sha1(password.encode("utf-8")).hexdigest()


def _normalize_sync_time_or_error(value: Optional[str], *, field_name: str) -> str:
    text = str(value or "").strip()
    if not TIME_HHMM_RE.match(text):
        raise HTTPException(status_code=400, detail=f"Invalid time format for {field_name}. Use HH:MM")
    return text


def _serialize_sales_sync_settings(row: IikoSalesSyncSetting) -> dict:
    return {
        "restaurant_id": int(row.restaurant_id),
        "auto_sync_enabled": bool(row.auto_sync_enabled),
        "daily_sync_time": row.daily_sync_time or "07:00",
        "daily_lookback_days": int(row.daily_lookback_days or 0),
        "weekly_sync_enabled": bool(row.weekly_sync_enabled),
        "weekly_sync_weekday": int(row.weekly_sync_weekday or 0),
        "weekly_sync_time": row.weekly_sync_time or "08:00",
        "weekly_lookback_days": int(row.weekly_lookback_days or 0),
        "manual_default_lookback_days": int(row.manual_default_lookback_days or 0),
        "last_daily_run_on": row.last_daily_run_on.isoformat() if row.last_daily_run_on else None,
        "last_weekly_run_on": row.last_weekly_run_on.isoformat() if row.last_weekly_run_on else None,
        "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
        "last_successful_sync_at": row.last_successful_sync_at.isoformat() if row.last_successful_sync_at else None,
        "last_manual_sync_at": row.last_manual_sync_at.isoformat() if row.last_manual_sync_at else None,
        "last_sync_scope": row.last_sync_scope,
        "last_sync_status": row.last_sync_status,
        "last_sync_error": row.last_sync_error,
    }


def _get_or_create_sales_sync_settings(db: Session, restaurant_id: int) -> IikoSalesSyncSetting:
    row = db.query(IikoSalesSyncSetting).filter(IikoSalesSyncSetting.restaurant_id == restaurant_id).first()
    if row:
        return row
    row = IikoSalesSyncSetting(restaurant_id=restaurant_id)
    db.add(row)
    db.flush()
    return row


def _resolve_sync_operation_stage(row: dict) -> str:
    state = str(row.get("state") or "").strip().lower()
    wait_event_type = str(row.get("wait_event_type") or "").strip().lower()
    if wait_event_type == "lock":
        return "queued"
    if state in {"active", "idle in transaction"}:
        return "running"
    if state:
        return state
    return "unknown"


def _serialize_sync_operation_row(row: dict) -> RestaurantSalesSyncOperationRead:
    app_meta = _parse_sales_sync_application_name(row.get("application_name")) or {}
    age_value = row.get("age")
    age_seconds = 0
    if hasattr(age_value, "total_seconds"):
        try:
            age_seconds = max(0, int(age_value.total_seconds()))
        except Exception:
            age_seconds = 0
    query_start = row.get("query_start")
    started_at = query_start.isoformat() if query_start is not None else None
    return RestaurantSalesSyncOperationRead(
        pid=int(row.get("pid")),
        state=row.get("state"),
        stage=_resolve_sync_operation_stage(row),
        wait_event_type=row.get("wait_event_type"),
        wait_event=row.get("wait_event"),
        started_at=started_at,
        age_seconds=age_seconds,
        restaurant_id=app_meta.get("restaurant_id"),
        actor=app_meta.get("actor"),
        source_hash=app_meta.get("source_hash"),
        query=row.get("query"),
    )


def _list_active_sales_sync_operations(db: Session) -> list[RestaurantSalesSyncOperationRead]:
    rows = db.execute(
        sa.text(
            """
            SELECT
                a.pid,
                a.application_name,
                a.state,
                a.wait_event_type,
                a.wait_event,
                a.query_start,
                now() - COALESCE(a.xact_start, a.query_start) AS age,
                left(a.query, 260) AS query
            FROM pg_stat_activity a
            WHERE a.datname = current_database()
              AND a.pid <> pg_backend_pid()
              AND a.application_name LIKE 'zion_sync %'
            ORDER BY COALESCE(a.xact_start, a.query_start) ASC NULLS LAST
            """
        )
    ).mappings().all()
    return [_serialize_sync_operation_row(dict(row)) for row in rows]


def _restaurant_cache_payload(item: Restaurant) -> dict:
    return {
        "id": int(item.id),
        "name": item.name,
        "server": item.server,
        "department_code": item.department_code,
        "participates_in_sales": bool(item.participates_in_sales),
        "iiko_login": item.iiko_login,
        "company_id": int(item.company_id),
    }


def _restaurants_scope_key(allowed_restaurants: set[int] | None) -> tuple:
    if allowed_restaurants is None:
        return ("all",)
    if not allowed_restaurants:
        return ("none",)
    return tuple(sorted(int(value) for value in allowed_restaurants))


# ---------- READ LIST ----------
@router.get("/", response_model=list[RestaurantRead])
def list_restaurants(
    db: Session = Depends(get_db),
    company_id: int | None = Query(None),
    sales_participants_only: bool = Query(False),
    current_user: User = Depends(get_current_user_restaurant_view),
):
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    cache_key = (
        _restaurants_scope_key(allowed_restaurants),
        int(company_id) if company_id is not None else None,
        bool(sales_participants_only),
    )

    def _load_restaurants() -> list[dict]:
        query = db.query(Restaurant)
        if allowed_restaurants is not None:
            if not allowed_restaurants:
                return []
            query = query.filter(Restaurant.id.in_(allowed_restaurants))
        if company_id is not None:
            query = query.filter(Restaurant.company_id == company_id)
        if sales_participants_only:
            query = query.filter(Restaurant.participates_in_sales.is_(True))
        rows = query.order_by(Restaurant.id.asc()).all()
        return [_restaurant_cache_payload(item) for item in rows]

    return cached_reference_data(
        RESTAURANTS_LIST_CACHE_SCOPE,
        cache_key,
        _load_restaurants,
        ttl_seconds=RESTAURANTS_LIST_CACHE_TTL_SECONDS,
    )


# ---------- READ ONE ----------
@router.get("/{restaurant_id}", response_model=RestaurantRead)
def get_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_restaurant_view),
):
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден")
    if allowed_restaurants is not None and restaurant.id not in allowed_restaurants:
        raise HTTPException(status_code=403, detail='Access denied')
    return restaurant


# ---------- INTERNAL CREATE UTIL ----------
def _create_restaurant(db: Session, company_id: int, payload: RestaurantCreate) -> Restaurant:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")

    restaurant = Restaurant(
        name=payload.name,
        server=payload.server,
        department_code=payload.department_code,
        participates_in_sales=bool(payload.participates_in_sales),
        iiko_login=payload.iiko_login,
        iiko_password_sha1=hash_iiko_password_sha1(payload.iiko_password),
        company_id=company_id,
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    invalidate_reference_scope(RESTAURANTS_LIST_CACHE_SCOPE)
    return restaurant


# ---------- CREATE (query ?company_id=) ----------
@router.post("/", response_model=RestaurantRead)
def create_restaurant_query(
    db: Session = Depends(get_db),
    company_id: int = Query(..., description="ID компании"),
    rest: RestaurantCreate = Body(...),
    current_user: User = Depends(require_permissions(PermissionCode.RESTAURANTS_MANAGE)),
):
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None:
        raise HTTPException(status_code=403, detail='Access denied')
    return _create_restaurant(db, company_id, rest)


# ---------- CREATE (path /{company_id}) ----------
@router.post("/{company_id}", response_model=RestaurantRead)
def create_restaurant_path(
    company_id: int,
    rest: RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(PermissionCode.RESTAURANTS_MANAGE)),
):
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None:
        raise HTTPException(status_code=403, detail='Access denied')
    return _create_restaurant(db, company_id, rest)


# ---------- UPDATE ----------
@router.put("/{restaurant_id}", response_model=RestaurantRead)
def update_restaurant(
    restaurant_id: int,
    data: RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(*RESTAURANT_SETTINGS_MANAGE_PERMISSIONS)),
):
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден")

    if allowed_restaurants is not None and restaurant.id not in allowed_restaurants:
        raise HTTPException(status_code=403, detail='Access denied')
    restaurant.name = data.name
    restaurant.server = data.server
    restaurant.department_code = data.department_code
    restaurant.participates_in_sales = bool(data.participates_in_sales)
    restaurant.iiko_login = data.iiko_login
    if data.iiko_password:
        restaurant.iiko_password_sha1 = hash_iiko_password_sha1(data.iiko_password)

    db.commit()
    db.refresh(restaurant)
    invalidate_reference_scope(RESTAURANTS_LIST_CACHE_SCOPE)
    return restaurant


@router.get("/{restaurant_id}/sales-sync-settings", response_model=RestaurantSalesSyncSettingsRead)
def get_sales_sync_settings(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(*RESTAURANT_SETTINGS_VIEW_PERMISSIONS)),
):
    ensure_user_access_to_restaurant(db, current_user, restaurant_id)
    settings = _get_or_create_sales_sync_settings(db, restaurant_id)
    db.commit()
    db.refresh(settings)
    return _serialize_sales_sync_settings(settings)


@router.put("/{restaurant_id}/sales-sync-settings", response_model=RestaurantSalesSyncSettingsRead)
def update_sales_sync_settings(
    restaurant_id: int,
    payload: RestaurantSalesSyncSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(*RESTAURANT_SETTINGS_MANAGE_PERMISSIONS)),
):
    ensure_user_access_to_restaurant(db, current_user, restaurant_id)
    settings = _get_or_create_sales_sync_settings(db, restaurant_id)
    fields_set = payload.model_fields_set

    if "auto_sync_enabled" in fields_set:
        settings.auto_sync_enabled = bool(payload.auto_sync_enabled)
    if "daily_sync_time" in fields_set and payload.daily_sync_time is not None:
        settings.daily_sync_time = _normalize_sync_time_or_error(payload.daily_sync_time, field_name="daily_sync_time")
    if "daily_lookback_days" in fields_set and payload.daily_lookback_days is not None:
        settings.daily_lookback_days = int(payload.daily_lookback_days)

    if "weekly_sync_enabled" in fields_set:
        settings.weekly_sync_enabled = bool(payload.weekly_sync_enabled)
    if "weekly_sync_weekday" in fields_set and payload.weekly_sync_weekday is not None:
        settings.weekly_sync_weekday = int(payload.weekly_sync_weekday)
    if "weekly_sync_time" in fields_set and payload.weekly_sync_time is not None:
        settings.weekly_sync_time = _normalize_sync_time_or_error(payload.weekly_sync_time, field_name="weekly_sync_time")
    if "weekly_lookback_days" in fields_set and payload.weekly_lookback_days is not None:
        settings.weekly_lookback_days = int(payload.weekly_lookback_days)

    if "manual_default_lookback_days" in fields_set and payload.manual_default_lookback_days is not None:
        settings.manual_default_lookback_days = int(payload.manual_default_lookback_days)

    db.commit()
    db.refresh(settings)
    return _serialize_sales_sync_settings(settings)


@router.post("/{restaurant_id}/sales-sync-settings/run")
def run_sales_sync_for_restaurant(
    restaurant_id: int,
    payload: RestaurantSalesSyncRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions(
            PermissionCode.RESTAURANTS_SETTINGS_MANAGE,
            PermissionCode.RESTAURANTS_MANAGE,
            PermissionCode.IIKO_MANAGE,
        )
    ),
):
    ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=True)
    settings = _get_or_create_sales_sync_settings(db, restaurant_id)

    try:
        result = sync_iiko_sales(
            payload=SyncIikoSalesRequest(
                restaurant_id=restaurant_id,
                from_date=payload.from_date,
                to_date=payload.to_date,
            ),
            db=db,
            current_user=current_user,
        )
        now_value = now_local()
        settings.last_sync_at = now_value
        settings.last_successful_sync_at = now_value
        settings.last_manual_sync_at = now_value
        settings.last_sync_scope = "manual"
        settings.last_sync_status = "ok"
        settings.last_sync_error = None
        db.commit()
        db.refresh(settings)
        return {
            "status": "ok",
            "result": result,
            "settings": _serialize_sales_sync_settings(settings),
        }
    except HTTPException as exc:
        db.rollback()
        settings = _get_or_create_sales_sync_settings(db, restaurant_id)
        settings.last_sync_at = now_local()
        settings.last_sync_scope = "manual"
        settings.last_sync_status = "error"
        settings.last_sync_error = str(exc.detail)[:1000]
        db.commit()
        raise
    except Exception as exc:
        db.rollback()
        settings = _get_or_create_sales_sync_settings(db, restaurant_id)
        settings.last_sync_at = now_local()
        settings.last_sync_scope = "manual"
        settings.last_sync_status = "error"
        settings.last_sync_error = str(exc)[:1000]
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc)[:400])


@router.get("/{restaurant_id}/sales-sync-settings/operations")
def list_sales_sync_operations(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(*RESTAURANT_SETTINGS_VIEW_PERMISSIONS)),
):
    ensure_user_access_to_restaurant(db, current_user, restaurant_id)
    operations = [
        row
        for row in _list_active_sales_sync_operations(db)
        if int(row.restaurant_id or 0) == int(restaurant_id)
    ]
    return {
        "status": "ok",
        "operations": [item.model_dump() for item in operations],
        "total": len(operations),
    }


@router.post("/{restaurant_id}/sales-sync-settings/operations/cancel")
def cancel_sales_sync_operation(
    restaurant_id: int,
    payload: RestaurantSalesSyncCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(*RESTAURANT_SETTINGS_MANAGE_PERMISSIONS, PermissionCode.IIKO_MANAGE)),
):
    ensure_user_access_to_restaurant(db, current_user, restaurant_id)
    operation = None
    for row in _list_active_sales_sync_operations(db):
        if int(row.pid) == int(payload.pid):
            operation = row
            break
    if operation is None:
        raise HTTPException(status_code=404, detail="Операция не найдена")
    if int(operation.restaurant_id or 0) != int(restaurant_id):
        raise HTTPException(status_code=403, detail="Операция относится к другому ресторану")

    action = "terminate" if payload.force else "cancel"
    sql = "SELECT pg_terminate_backend(:pid)" if payload.force else "SELECT pg_cancel_backend(:pid)"
    ok = bool(db.execute(sa.text(sql), {"pid": int(payload.pid)}).scalar())
    if not ok and not payload.force:
        # Fallback for sessions stuck in idle-in-transaction.
        ok = bool(db.execute(sa.text("SELECT pg_terminate_backend(:pid)"), {"pid": int(payload.pid)}).scalar())
        if ok:
            action = "terminate"

    if not ok:
        raise HTTPException(status_code=409, detail="Не удалось остановить операцию")

    return {
        "status": "ok",
        "pid": int(payload.pid),
        "restaurant_id": int(restaurant_id),
        "action": action,
    }


# ---------- DELETE ----------
@router.delete("/{restaurant_id}")
def delete_restaurant(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(PermissionCode.RESTAURANTS_MANAGE)),
):
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден")

    if allowed_restaurants is not None and restaurant.id not in allowed_restaurants:
        raise HTTPException(status_code=403, detail='Access denied')
    db.delete(restaurant)
    db.commit()
    invalidate_reference_scope(RESTAURANTS_LIST_CACHE_SCOPE)
    return {"ok": True}
