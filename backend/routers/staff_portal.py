# backend/routers/staff_portal.py
from __future__ import annotations

import os
from datetime import datetime, timedelta, date, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
import sqlalchemy as sa

from backend.bd.database import get_db
from backend.bd.models import User, Attendance, Position, Restaurant
from backend.bd.iiko_catalog import (
    IikoPaymentMethod,
    IikoProduct,
    IikoProductSetting,
    IikoWaiterTurnoverSetting,
)
from backend.bd.iiko_sales import IikoSaleItem, IikoSaleOrder
from backend.schemas import (
    StaffLoginRequest, StaffLoginResponse, StaffUserPublic,
    AttendancePublic, AttendanceListResponse,
    AttendanceOpenRequest, AttendanceCloseRequest, AttendanceManualUpdate, StaffPositionOption,
)
from backend.services.iiko_api import to_iso_date
from backend.services.attendance_calculations import (
    combine_date_time,
    calc_night_minutes,
    calc_duration_minutes,
    calc_attendance_pay,
)
from backend.services.payroll_recalc import recalc_salary_for_user_month
from backend.services.fingerprint_events import log_fingerprint_event
from backend.services.employee_changes import log_employee_changes

try:
    from backend.utils import get_current_user, create_access_token, now_local
    from backend.services.permissions import (
        PermissionCode,
        ensure_permissions,
        has_permission,
        can_manage_user,
        ensure_can_manage_user,
    )
except Exception:
    from fastapi.security import OAuth2PasswordBearer
    from jose import jwt, JWTError

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")
    SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "CHANGE_ME"
    ALGORITHM = "HS256"

    def create_access_token(sub: str, expires_minutes: int = 60 * 24) -> str:
        exp = datetime.utcnow() + timedelta(minutes=expires_minutes)
        return jwt.encode({"sub": sub, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

    def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            sub = payload.get("sub")
            if not sub:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            user = db.query(User).get(int(sub))
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            if user.fired:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")
            return user
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    class PermissionCode:
        STAFF_MANAGE_ALL = "staff.manage_all"
        STAFF_MANAGE_SUBORDINATES = "staff.manage_subordinates"

    def ensure_permissions(user: User, *codes: str) -> None:
        return

    def has_permission(user: User, code: str) -> bool:
        return True

    def can_manage_user(viewer: User, target: User) -> bool:
        return True

    def ensure_can_manage_user(viewer: User, target: User) -> None:
        return

    def now_local() -> datetime:
        return datetime.now().replace(microsecond=0)


router = APIRouter(prefix="/staff", tags=["Staff portal"])

AUTO_CLOSE_THRESHOLD = timedelta(hours=24)


def _now_dt() -> datetime:
    return now_local().replace(tzinfo=None)


def _ensure_close_after_open(opened_dt: datetime, closed_dt: datetime) -> None:
    if closed_dt < opened_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="время закрытия должно быть позже времени открытия")


def _apply_close_stats(a: Attendance, opened_dt: datetime, closed_dt: datetime) -> None:
    _ensure_close_after_open(opened_dt, closed_dt)
    a.duration_minutes = calc_duration_minutes(opened_dt, closed_dt)
    a.night_minutes = calc_night_minutes(opened_dt, closed_dt)

def _format_value(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

def _attendance_summary(attendance: Attendance) -> dict:
    return {
        "attendance_id": attendance.id,
        "open_date": _format_value(attendance.open_date),
        "open_time": _format_value(attendance.open_time),
        "close_date": _format_value(attendance.close_date),
        "close_time": _format_value(attendance.close_time),
        "restaurant_id": attendance.restaurant_id,
        "position_id": attendance.position_id,
        "rate": _format_value(attendance.rate),
        "pay_amount": _format_value(attendance.pay_amount),
        "duration_minutes": attendance.duration_minutes,
        "night_minutes": attendance.night_minutes,
    }


TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT = "sum_without_discount"
TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT = "sum_with_discount"
TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY = "discount_only"

TURNOVER_DELETED_MODE_ALL = "all"
TURNOVER_DELETED_MODE_ONLY = "only_deleted"
TURNOVER_DELETED_MODE_WITHOUT = "without_deleted"
TURNOVER_WAITER_MODE_ORDER_CLOSE = "order_close"
TURNOVER_WAITER_MODE_ITEM_PUNCH = "item_punch"


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


def _normalize_deleted_mode(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    aliases = {
        "": TURNOVER_DELETED_MODE_ALL,
        "all": TURNOVER_DELETED_MODE_ALL,
        "only_deleted": TURNOVER_DELETED_MODE_ONLY,
        "deleted_only": TURNOVER_DELETED_MODE_ONLY,
        "only": TURNOVER_DELETED_MODE_ONLY,
        "deleted": TURNOVER_DELETED_MODE_ONLY,
        "without_deleted": TURNOVER_DELETED_MODE_WITHOUT,
        "without": TURNOVER_DELETED_MODE_WITHOUT,
        "exclude_deleted": TURNOVER_DELETED_MODE_WITHOUT,
    }
    return aliases.get(clean, TURNOVER_DELETED_MODE_ALL)


def _normalize_waiter_mode(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    aliases = {
        "": TURNOVER_WAITER_MODE_ORDER_CLOSE,
        "order_close": TURNOVER_WAITER_MODE_ORDER_CLOSE,
        "order_closed": TURNOVER_WAITER_MODE_ORDER_CLOSE,
        "close_order": TURNOVER_WAITER_MODE_ORDER_CLOSE,
        "order_waiter": TURNOVER_WAITER_MODE_ORDER_CLOSE,
        "close": TURNOVER_WAITER_MODE_ORDER_CLOSE,
        "closed": TURNOVER_WAITER_MODE_ORDER_CLOSE,
        "item_punch": TURNOVER_WAITER_MODE_ITEM_PUNCH,
        "punch": TURNOVER_WAITER_MODE_ITEM_PUNCH,
        "item_waiter": TURNOVER_WAITER_MODE_ITEM_PUNCH,
        "dish_waiter": TURNOVER_WAITER_MODE_ITEM_PUNCH,
        "dish_seller": TURNOVER_WAITER_MODE_ITEM_PUNCH,
    }
    return aliases.get(clean, TURNOVER_WAITER_MODE_ORDER_CLOSE)


def _is_not_deleted_expr(field_expr):
    normalized = sa.func.upper(sa.func.trim(sa.func.coalesce(field_expr, "")))
    return sa.or_(normalized == "", normalized == "NOT_DELETED")


def _apply_deleted_mode_filter(
    query,
    *,
    deleted_mode: str,
    order_deleted_expr,
    deleted_with_writeoff_expr,
):
    mode = _normalize_deleted_mode(deleted_mode)
    condition = sa.and_(
        _is_not_deleted_expr(order_deleted_expr),
        _is_not_deleted_expr(deleted_with_writeoff_expr),
    )
    if mode == TURNOVER_DELETED_MODE_ONLY:
        return query.filter(sa.not_(condition))
    if mode == TURNOVER_DELETED_MODE_WITHOUT:
        return query.filter(condition)
    return query


def _split_filter_values(values: Optional[list[str]]) -> list[str]:
    parts: list[str] = []
    for value in values or []:
        if value is None:
            continue
        text = str(value).replace("\n", ",").replace(";", ",")
        for chunk in text.split(","):
            clean = chunk.strip()
            if clean:
                parts.append(clean)
    unique: list[str] = []
    seen = set()
    for value in parts:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def _lower_values(values: list[str]) -> list[str]:
    return [value.casefold() for value in values if value]


def _normalize_int_list(values: Optional[list[int]]) -> list[int]:
    unique: list[int] = []
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


def _default_waiter_turnover_settings(company_id: Optional[int]) -> dict:
    return {
        "company_id": company_id,
        "is_active": False,
        "real_money_only": True,
        "amount_mode": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "deleted_mode": TURNOVER_DELETED_MODE_WITHOUT,
        "waiter_mode": TURNOVER_WAITER_MODE_ORDER_CLOSE,
        "position_ids": [],
        "include_groups": [],
        "exclude_groups": [],
        "include_categories": [],
        "exclude_categories": [],
        "include_positions": [],
        "exclude_positions": [],
        "include_payment_method_guids": [],
    }


def _serialize_waiter_turnover_settings(row: Optional[IikoWaiterTurnoverSetting], company_id: Optional[int]) -> dict:
    if not row:
        return _default_waiter_turnover_settings(company_id)
    return {
        "company_id": row.company_id,
        "is_active": bool(row.is_active),
        "real_money_only": bool(row.real_money_only),
        "amount_mode": _normalize_turnover_amount_mode(row.amount_mode),
        "deleted_mode": _normalize_deleted_mode(row.deleted_mode),
        "waiter_mode": _normalize_waiter_mode(getattr(row, "waiter_mode", None)),
        "position_ids": _normalize_int_list(row.position_ids if isinstance(row.position_ids, list) else []),
        "include_groups": _split_filter_values(row.include_groups if isinstance(row.include_groups, list) else []),
        "exclude_groups": _split_filter_values(row.exclude_groups if isinstance(row.exclude_groups, list) else []),
        "include_categories": _split_filter_values(
            row.include_categories if isinstance(row.include_categories, list) else []
        ),
        "exclude_categories": _split_filter_values(
            row.exclude_categories if isinstance(row.exclude_categories, list) else []
        ),
        "include_positions": _split_filter_values(
            row.include_positions if isinstance(row.include_positions, list) else []
        ),
        "exclude_positions": _split_filter_values(
            row.exclude_positions if isinstance(row.exclude_positions, list) else []
        ),
        "include_payment_method_guids": _split_filter_values(
            row.include_payment_method_guids if isinstance(row.include_payment_method_guids, list) else []
        ),
    }


def _resolve_company_id_for_staff(user: User) -> Optional[int]:
    direct_company = getattr(user, "company_id", None)
    if direct_company is not None:
        return int(direct_company)
    company_ids = sorted(
        {
            int(rest.company_id)
            for rest in (user.restaurants or [])
            if rest and getattr(rest, "company_id", None) is not None
        }
    )
    if len(company_ids) == 1:
        return company_ids[0]
    return company_ids[0] if company_ids else None


def _resolve_staff_restaurant_ids(db: Session, user: User) -> list[int]:
    ids = sorted({int(item.id) for item in (user.restaurants or []) if item and item.id is not None})
    if ids:
        return ids
    workplace_id = getattr(user, "workplace_restaurant_id", None)
    if workplace_id is not None:
        return [int(workplace_id)]
    company_id = _resolve_company_id_for_staff(user)
    if company_id is None:
        return []
    return [
        int(rest_id)
        for (rest_id,) in db.query(Restaurant.id).filter(Restaurant.company_id == company_id).all()
        if rest_id is not None
    ]

def _attendance_intervals_overlap(
    start_a: datetime,
    end_a: Optional[datetime],
    start_b: datetime,
    end_b: Optional[datetime],
) -> bool:
    end_a_cmp = end_a if end_a is not None else datetime.max
    end_b_cmp = end_b if end_b is not None else datetime.max
    return start_a <= end_b_cmp and start_b <= end_a_cmp

def _find_attendance_overlap(
    db: Session,
    user_id: int,
    start_dt: datetime,
    end_dt: Optional[datetime],
    exclude_attendance_id: Optional[int] = None,
) -> Optional[Attendance]:
    start_date = start_dt.date()
    end_date = end_dt.date() if end_dt else start_dt.date()
    query = (
        db.query(Attendance)
          .filter(
              Attendance.user_id == user_id,
              Attendance.open_date <= end_date,
              or_(Attendance.close_date.is_(None), Attendance.close_date >= start_date),
          )
    )
    if exclude_attendance_id is not None:
        query = query.filter(Attendance.id != exclude_attendance_id)
    candidates = query.all()
    for attendance in candidates:
        a_start = combine_date_time(attendance.open_date, attendance.open_time)
        a_end = None
        if attendance.close_date and attendance.close_time:
            a_end = combine_date_time(attendance.close_date, attendance.close_time)
        if _attendance_intervals_overlap(start_dt, end_dt, a_start, a_end):
            return attendance
    return None


def _calculate_and_set_pay(db: Session, a: Attendance) -> None:
    position = a.position or (db.query(Position).get(a.position_id) if a.position_id else None)
    payment_format = getattr(position, "payment_format", None)
    calc_mode = getattr(payment_format, "calculation_mode", None) if payment_format else None
    hours_per_shift = getattr(position, "hours_per_shift", None) if position else None
    monthly_shift_norm = getattr(position, "monthly_shift_norm", None) if position else None
    night_bonus_enabled = bool(getattr(position, "night_bonus_enabled", False)) if position else False
    night_bonus_percent = getattr(position, "night_bonus_percent", None) if position else None

    a.pay_amount = calc_attendance_pay(
        rate=a.rate,
        calculation_mode=calc_mode,
        duration_minutes=a.duration_minutes,
        night_minutes=a.night_minutes,
        hours_per_shift=hours_per_shift,
        monthly_shift_norm=monthly_shift_norm,
        night_bonus_enabled=night_bonus_enabled,
        night_bonus_percent=night_bonus_percent,
    )


def _auto_close_if_over_24h(db: Session, a: Attendance, now: datetime) -> Optional[Attendance]:
    if a.close_date is not None or a.close_time is not None:
        return None
    opened_dt = combine_date_time(a.open_date, a.open_time)
    if now - opened_dt >= AUTO_CLOSE_THRESHOLD:
        closed_dt = opened_dt + AUTO_CLOSE_THRESHOLD
        a.close_date = closed_dt.date()
        a.close_time = closed_dt.time()
        _apply_close_stats(a, opened_dt, closed_dt)
        _calculate_and_set_pay(db, a)
        db.commit()
        db.refresh(a)
        return a
    return None


def _current_open_attendance(db: Session, user_id: int) -> Optional[Attendance]:
    a = (
        db.query(Attendance)
          .filter(Attendance.user_id == user_id,
                  Attendance.close_date.is_(None),
                  Attendance.close_time.is_(None))
          .order_by(Attendance.open_date.asc(), Attendance.open_time.asc())
          .first()
    )
    if not a:
        return None
    closed = _auto_close_if_over_24h(db, a, _now_dt())
    return None if closed is not None else a


def _to_public(a: Attendance) -> AttendancePublic:
    return AttendancePublic(
        id=a.id,
        user_id=a.user_id,
        position_id=a.position_id,
        position_name=(a.position.name if a.position else None),
        restaurant_id=a.restaurant_id,
        restaurant_name=(a.restaurant.name if a.restaurant else None),
        rate=float(a.rate) if a.rate is not None else None,
        pay_amount=float(a.pay_amount) if a.pay_amount is not None else None,
        open_date=a.open_date,
        open_time=a.open_time,
        close_date=a.close_date,
        close_time=a.close_time,
        duration_minutes=a.duration_minutes,
        night_minutes=a.night_minutes or 0,
    )


@router.post("/login", response_model=StaffLoginResponse)
def staff_login(payload: StaffLoginRequest, db: Session = Depends(get_db)):
    code = (payload.staff_code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="staff_code is required")

    user = (
        db.query(User)
        .options(
            joinedload(User.role),
            joinedload(User.position).joinedload(Position.restaurant_subdivision),
            joinedload(User.restaurants),
        )
        .filter(User.staff_code == code)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid staff_code")
    if user.fired:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")
    # Требуем право на доступ в портал учёта времени.
    ensure_permissions(user, PermissionCode.STAFF_PORTAL_ACCESS)

    token = create_access_token(str(user.id), expires_minutes=60 * 24)

    restaurants = [
        {"id": r.id, "name": (r.name or f"Restaurant #{r.id}")}  # type: ignore[arg-type]
        for r in (user.restaurants or [])
        if r and r.id is not None
    ]

    user_pub = StaffUserPublic(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        staff_code=user.staff_code,
        role_id=user.role_id,
        role_name=(user.role.name if user.role else None),
        position_id=user.position_id,
        position_name=(user.position.name if user.position else None),
        gender=user.gender,
        rate=float(user.rate) if user.rate is not None else None,
        fired=bool(user.fired),
        restaurants=restaurants,
        restaurant_ids=[item["id"] for item in restaurants],
        individual_rate=float(user.individual_rate) if user.individual_rate is not None else None,
        workplace_restaurant_id=getattr(user, "workplace_restaurant_id", None),
        has_full_restaurant_access=bool(getattr(user, "has_full_restaurant_access", False)),
        has_fingerprint=bool(getattr(user, "has_fingerprint", False)),
        rate_hidden=False,
        restaurant_subdivision_id=getattr(getattr(user, "position", None), "restaurant_subdivision_id", None),
        restaurant_subdivision_name=getattr(getattr(getattr(user, "position", None), "restaurant_subdivision", None), "name", None),
        restaurant_subdivision_is_multi=bool(
            getattr(getattr(getattr(user, "position", None), "restaurant_subdivision", None), "is_multi", False)
        ),
    )

    if payload.auth_method == "fingerprint":
        log_fingerprint_event(
            db,
            staff_code=code,
            action="login",
            ok=True,
            source="web",
            slot=payload.fingerprint_slot,
            score=payload.fingerprint_score,
        )
    return StaffLoginResponse(access_token=token, user=user_pub)


@router.get("/attendances/month", response_model=AttendanceListResponse)
def my_attendances_month(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.STAFF_PORTAL_ACCESS)
    if current_user.fired:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")

    today = _now_dt().date()
    y = year or today.year
    m = month or today.month

    _ = _current_open_attendance(db, current_user.id)

    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(y, m + 1, 1) - timedelta(days=1)

    cond = or_(
        and_(Attendance.open_date >= start, Attendance.open_date <= end),
        and_(Attendance.close_date != None, Attendance.close_date >= start, Attendance.close_date <= end),
        and_(Attendance.open_date < start, or_(Attendance.close_date == None, Attendance.close_date >= start)),
    )

    rows = (
        db.query(Attendance)
          .options(
              joinedload(Attendance.position),
              joinedload(Attendance.restaurant),
          )
          .filter(Attendance.user_id == current_user.id)
          .filter(cond)
          .order_by(Attendance.open_date.asc(), Attendance.open_time.asc())
          .all()
    )

    items = [_to_public(a) for a in rows]
    return AttendanceListResponse(items=items, year=y, month=m)


@router.get("/metrics/waiter-turnover")
def my_waiter_turnover_metric(
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    restaurant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.STAFF_PORTAL_ACCESS)
    if current_user.fired:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")

    company_id = _resolve_company_id_for_staff(current_user)
    settings_row = (
        db.query(IikoWaiterTurnoverSetting)
        .filter(IikoWaiterTurnoverSetting.company_id == company_id)
        .order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
        )
        .first()
    )
    settings = _serialize_waiter_turnover_settings(settings_row, company_id)
    if not settings.get("is_active"):
        return {
            "enabled": False,
            "reason": "settings_inactive",
            "from_date": None,
            "to_date": None,
            "turnover_amount": 0.0,
            "orders_count": 0,
            "items_count": 0,
            "qty": 0.0,
            "sum_without_discount": 0.0,
            "sum_with_discount": 0.0,
            "discount_amount": 0.0,
            "amount_mode": settings.get("amount_mode"),
            "waiter_mode": _normalize_waiter_mode(settings.get("waiter_mode")),
        }

    scoped_position_ids = _normalize_int_list(settings.get("position_ids"))
    if scoped_position_ids and int(getattr(current_user, "position_id", 0) or 0) not in set(scoped_position_ids):
        return {
            "enabled": False,
            "reason": "position_not_in_scope",
            "from_date": None,
            "to_date": None,
            "turnover_amount": 0.0,
            "orders_count": 0,
            "items_count": 0,
            "qty": 0.0,
            "sum_without_discount": 0.0,
            "sum_with_discount": 0.0,
            "discount_amount": 0.0,
            "amount_mode": settings.get("amount_mode"),
            "waiter_mode": _normalize_waiter_mode(settings.get("waiter_mode")),
        }

    allowed_restaurant_ids = _resolve_staff_restaurant_ids(db, current_user)
    if restaurant_id is not None:
        if int(restaurant_id) not in set(allowed_restaurant_ids):
            raise HTTPException(status_code=403, detail="Нет доступа к выбранному ресторану")
        selected_restaurant_ids = [int(restaurant_id)]
    else:
        selected_restaurant_ids = allowed_restaurant_ids

    if not selected_restaurant_ids:
        return {
            "enabled": False,
            "reason": "no_restaurants",
            "from_date": None,
            "to_date": None,
            "turnover_amount": 0.0,
            "orders_count": 0,
            "items_count": 0,
            "qty": 0.0,
            "sum_without_discount": 0.0,
            "sum_with_discount": 0.0,
            "discount_amount": 0.0,
            "amount_mode": settings.get("amount_mode"),
            "waiter_mode": _normalize_waiter_mode(settings.get("waiter_mode")),
        }

    today = _now_dt().date()
    default_start = date(today.year, today.month, 1)
    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date() if from_date else default_start
    end = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() if to_date else today
    if start > end:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    end_excl = end + timedelta(days=1)

    waiter_mode = _normalize_waiter_mode(settings.get("waiter_mode"))
    current_user_iiko_id = str(getattr(current_user, "iiko_id", "") or "").strip()
    current_user_iiko_code = str(getattr(current_user, "iiko_code", "") or "").strip()
    waiter_filters = []
    if waiter_mode == TURNOVER_WAITER_MODE_ITEM_PUNCH:
        item_waiter_iiko_id_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["DishWaiter.Id"].astext,
            IikoSaleItem.raw_payload["DishSeller.Id"].astext,
            IikoSaleItem.raw_payload["DishEmployee.Id"].astext,
            IikoSaleItem.raw_payload["Waiter.Id"].astext,
            IikoSaleItem.raw_payload["AuthUser.Id"].astext,
            IikoSaleItem.auth_user_iiko_id,
        )
        item_waiter_iiko_code_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["DishWaiter.Code"].astext,
            IikoSaleItem.raw_payload["DishSeller.Code"].astext,
            IikoSaleItem.raw_payload["DishEmployee.Code"].astext,
            IikoSaleItem.raw_payload["Waiter.Code"].astext,
            IikoSaleItem.raw_payload["AuthUser.Code"].astext,
        )
        waiter_filters.append(IikoSaleItem.auth_user_id == int(current_user.id))
        if current_user_iiko_id:
            waiter_filters.append(sa.func.trim(sa.func.coalesce(item_waiter_iiko_id_expr, "")) == current_user_iiko_id)
        if current_user_iiko_code:
            waiter_filters.append(sa.func.trim(sa.func.coalesce(item_waiter_iiko_code_expr, "")) == current_user_iiko_code)
    else:
        waiter_filters.append(IikoSaleOrder.order_waiter_user_id == int(current_user.id))
        if current_user_iiko_id:
            waiter_filters.append(IikoSaleOrder.order_waiter_iiko_id == current_user_iiko_id)

    group_expr = sa.func.coalesce(
        IikoProductSetting.custom_product_group_type,
        IikoProduct.product_group_type,
        IikoSaleItem.dish_group,
    )
    category_expr = sa.func.coalesce(
        IikoProductSetting.custom_product_category,
        IikoProduct.product_category,
        IikoSaleItem.dish_category_id,
    )
    position_expr = sa.func.coalesce(IikoSaleItem.dish_name, IikoProduct.name, IikoSaleItem.dish_code)
    payment_guid_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
        IikoSaleItem.raw_payload["PaymentType.Id"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
    )
    payment_guid_expr_norm = sa.func.lower(sa.func.trim(sa.func.coalesce(payment_guid_expr, "")))
    order_number_expr = sa.func.coalesce(
        IikoSaleOrder.order_num,
        IikoSaleOrder.iiko_order_id,
        sa.cast(IikoSaleOrder.id, sa.String),
    )

    base_q = (
        db.query(IikoSaleItem)
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .filter(IikoSaleOrder.restaurant_id.in_(selected_restaurant_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_excl)
        .filter(sa.or_(*waiter_filters))
    )
    base_q = _apply_deleted_mode_filter(
        base_q,
        deleted_mode=str(settings.get("deleted_mode") or TURNOVER_DELETED_MODE_WITHOUT),
        order_deleted_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["OrderDeleted"].astext,
            IikoSaleOrder.raw_payload["OrderDeleted"].astext,
        ),
        deleted_with_writeoff_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
            IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
        ),
    )

    include_groups = _lower_values(_split_filter_values(settings.get("include_groups")))
    exclude_groups = _lower_values(_split_filter_values(settings.get("exclude_groups")))
    include_categories = _lower_values(_split_filter_values(settings.get("include_categories")))
    exclude_categories = _lower_values(_split_filter_values(settings.get("exclude_categories")))
    include_positions = _lower_values(_split_filter_values(settings.get("include_positions")))
    exclude_positions = _lower_values(_split_filter_values(settings.get("exclude_positions")))

    group_expr_lower = sa.func.lower(sa.func.coalesce(group_expr, ""))
    category_expr_lower = sa.func.lower(sa.func.coalesce(category_expr, ""))
    position_expr_lower = sa.func.lower(sa.func.coalesce(position_expr, ""))

    if include_groups:
        base_q = base_q.filter(group_expr_lower.in_(include_groups))
    if exclude_groups:
        base_q = base_q.filter(~group_expr_lower.in_(exclude_groups))
    if include_categories:
        base_q = base_q.filter(category_expr_lower.in_(include_categories))
    if exclude_categories:
        base_q = base_q.filter(~category_expr_lower.in_(exclude_categories))
    if include_positions:
        base_q = base_q.filter(position_expr_lower.in_(include_positions))
    if exclude_positions:
        base_q = base_q.filter(~position_expr_lower.in_(exclude_positions))

    include_payment_method_guids = _lower_values(_split_filter_values(settings.get("include_payment_method_guids")))
    if include_payment_method_guids:
        base_q = base_q.filter(payment_guid_expr_norm.in_(include_payment_method_guids))

    if bool(settings.get("real_money_only")):
        payment_methods_q = db.query(IikoPaymentMethod.guid, IikoPaymentMethod.category, IikoPaymentMethod.is_active)
        if company_id is not None:
            payment_methods_q = payment_methods_q.filter(
                sa.or_(
                    IikoPaymentMethod.company_id == company_id,
                    IikoPaymentMethod.company_id.is_(None),
                )
            )

        real_money_guids: list[str] = []
        categorized_count = 0
        for guid, category, is_active in payment_methods_q.all():
            clean_guid = str(guid or "").strip()
            if not clean_guid:
                continue
            clean_category = str(category or "").strip()
            if clean_category:
                categorized_count += 1
            if not is_active:
                continue
            if clean_category == "real_money":
                real_money_guids.append(clean_guid.casefold())

        if real_money_guids:
            base_q = base_q.filter(payment_guid_expr_norm.in_(sorted(set(real_money_guids))))
        elif categorized_count > 0:
            base_q = base_q.filter(sa.literal(False))
        else:
            non_cash_id_expr = sa.func.trim(sa.func.coalesce(IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext, ""))
            non_cash_name_expr = sa.func.trim(sa.func.coalesce(IikoSaleItem.raw_payload["NonCashPaymentType"].astext, ""))
            base_q = base_q.filter(non_cash_id_expr == "").filter(non_cash_name_expr == "")

    sum_without_discount_expr = sa.func.coalesce(IikoSaleItem.sum, 0)
    discount_amount_expr = sa.func.abs(sa.func.coalesce(IikoSaleItem.discount_sum, 0))
    sum_with_discount_expr = sum_without_discount_expr - discount_amount_expr

    totals_row = base_q.with_entities(
        sa.func.count(sa.distinct(order_number_expr)).label("orders_count"),
        sa.func.count(IikoSaleItem.id).label("items_count"),
        sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("qty"),
        sa.func.coalesce(sa.func.sum(sum_without_discount_expr), 0).label("sum_without_discount"),
        sa.func.coalesce(sa.func.sum(sum_with_discount_expr), 0).label("sum_with_discount"),
        sa.func.coalesce(sa.func.sum(discount_amount_expr), 0).label("discount_amount"),
    ).one()

    amount_mode = _normalize_turnover_amount_mode(str(settings.get("amount_mode") or ""))
    sum_without_discount_value = float(totals_row.sum_without_discount or 0)
    sum_with_discount_value = float(totals_row.sum_with_discount or 0)
    discount_amount_value = float(totals_row.discount_amount or 0)

    if amount_mode == TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY:
        turnover_amount = discount_amount_value
    elif amount_mode == TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT:
        turnover_amount = sum_with_discount_value
    else:
        turnover_amount = sum_without_discount_value

    return {
        "enabled": True,
        "reason": None,
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "amount_mode": amount_mode,
        "waiter_mode": waiter_mode,
        "turnover_amount": round(float(turnover_amount), 2),
        "orders_count": int(totals_row.orders_count or 0),
        "items_count": int(totals_row.items_count or 0),
        "qty": round(float(totals_row.qty or 0), 3),
        "sum_without_discount": round(sum_without_discount_value, 2),
        "sum_with_discount": round(sum_with_discount_value, 2),
        "discount_amount": round(discount_amount_value, 2),
        "restaurants_count": len(selected_restaurant_ids),
    }


@router.get("/positions", response_model=list[StaffPositionOption])
def list_available_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StaffPositionOption]:
    ensure_permissions(current_user, PermissionCode.STAFF_PORTAL_ACCESS)
    base_position = None
    if current_user.position_id:
        base_position = (
            db.query(Position)
            .options(joinedload(Position.restaurant_subdivision))
            .filter(Position.id == current_user.position_id)
            .first()
        )
    subdivision = getattr(base_position, "restaurant_subdivision", None)
    if not subdivision or not getattr(subdivision, "is_multi", False):
        return []

    positions = (
        db.query(Position)
        .filter(Position.restaurant_subdivision_id == subdivision.id)
        .order_by(Position.name.asc())
        .all()
    )
    return [
        StaffPositionOption(
            id=pos.id,
            name=pos.name or f"Position #{pos.id}",
            restaurant_subdivision_id=getattr(pos, "restaurant_subdivision_id", None),
        )
        for pos in positions
        if pos.id is not None
    ]


@router.post("/attendances/open", response_model=AttendancePublic)
def open_attendance(
    payload: AttendanceOpenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.STAFF_PORTAL_ACCESS)
    if current_user.fired:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")

    existing = _current_open_attendance(db, current_user.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Already have an open attendance (id={existing.id})")

    now = _now_dt()
    conflict = _find_attendance_overlap(db, current_user.id, now, None)
    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"Смена пересекается с существующей (id={conflict.id})",
        )

    # Resolve restaurant: if only one привязка — подставляем её, иначе требуем указать.
    allowed_restaurants = [r.id for r in (current_user.restaurants or []) if r and r.id is not None]
    restaurant_id = payload.restaurant_id
    if restaurant_id is None:
        if len(allowed_restaurants) == 1:
            restaurant_id = allowed_restaurants[0]
        elif len(allowed_restaurants) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple restaurants available; specify restaurant_id",
            )
    elif allowed_restaurants and restaurant_id not in allowed_restaurants:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Restaurant not allowed for this user")

    # Position and rate: allow switching within multi subdivision, otherwise use base position.
    base_position = None
    if current_user.position_id:
        base_position = (
            db.query(Position)
            .options(joinedload(Position.restaurant_subdivision), joinedload(Position.payment_format))
            .get(current_user.position_id)
        )

    selected_position = base_position
    if payload.position_id is not None:
        if not base_position or not getattr(getattr(base_position, "restaurant_subdivision", None), "is_multi", False):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position selection is not allowed")
        candidate = (
            db.query(Position)
            .options(joinedload(Position.restaurant_subdivision), joinedload(Position.payment_format))
            .get(payload.position_id)
        )
        if not candidate or getattr(candidate, "restaurant_subdivision_id", None) != getattr(base_position, "restaurant_subdivision_id", None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected position is not available")
        selected_position = candidate

    position_id = getattr(selected_position, "id", None)
    if current_user.individual_rate is not None:
        rate = current_user.individual_rate
    else:
        rate = selected_position.rate if selected_position and selected_position.rate is not None else current_user.rate

    a = Attendance(
        user_id=current_user.id,
        position_id=position_id,
        restaurant_id=restaurant_id,
        rate=rate,
        open_date=now.date(),
        open_time=now.time(),
    )
    db.add(a)
    db.flush()
    log_employee_changes(
        db,
        user_id=current_user.id,
        changed_by_id=current_user.id,
        changes=[
            {
                "field": "attendance",
                "old_value": None,
                "new_value": _attendance_summary(a),
                "source": "staff_portal",
                "comment": "Открыта смена",
                "entity_type": "attendance",
                "entity_id": a.id,
            }
        ],
    )
    db.commit()
    db.refresh(a)
    recalc_salary_for_user_month(
        db,
        a.user_id,
        a.open_date or date.today(),
        calculated_by_id=current_user.id if getattr(current_user, "id", None) else None,
    )
    return _to_public(a)


@router.post("/attendances/close", response_model=AttendancePublic)
def close_attendance(
    payload: AttendanceCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.STAFF_PORTAL_ACCESS)
    if current_user.fired:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь уволен")

    a = (
        db.query(Attendance)
          .filter(Attendance.user_id == current_user.id,
                  Attendance.close_date.is_(None),
                  Attendance.close_time.is_(None))
          .order_by(Attendance.open_date.asc(), Attendance.open_time.asc())
          .first()
    )

    now = _now_dt()

    if not a:
        last = (
            db.query(Attendance)
              .filter(Attendance.user_id == current_user.id)
              .order_by(Attendance.close_date.desc().nullslast(), Attendance.close_time.desc().nullslast())
              .first()
        )
        if last and last.close_date and last.close_time:
            opened_dt = combine_date_time(last.open_date, last.open_time)
            closed_dt = combine_date_time(last.close_date, last.close_time)
            if (closed_dt - opened_dt) >= AUTO_CLOSE_THRESHOLD:
                if last.night_minutes is None:
                    last.night_minutes = calc_night_minutes(opened_dt, closed_dt)
                    db.commit()
                    db.refresh(last)
                return _to_public(last)
        raise HTTPException(status_code=409, detail="No open attendance to close")

    before_summary = _attendance_summary(a)
    data = payload.model_dump(exclude_unset=True)
    close_date = data.get("close_date", now.date())
    close_time = data.get("close_time", now.time())

    opened_dt = combine_date_time(a.open_date, a.open_time)
    closed_dt = combine_date_time(close_date, close_time)
    _apply_close_stats(a, opened_dt, closed_dt)

    a.close_date = close_date
    a.close_time = close_time
    _calculate_and_set_pay(db, a)

    after_summary = _attendance_summary(a)
    if before_summary != after_summary:
        log_employee_changes(
            db,
            user_id=current_user.id,
            changed_by_id=current_user.id,
            changes=[
                {
                    "field": "attendance",
                    "old_value": before_summary,
                    "new_value": after_summary,
                    "source": "staff_portal",
                    "comment": "Закрыта смена",
                    "entity_type": "attendance",
                    "entity_id": a.id,
                }
            ],
        )
    db.commit()
    db.refresh(a)
    recalc_salary_for_user_month(
        db,
        current_user.id,
        a.open_date or date.today(),
        calculated_by_id=current_user.id if getattr(current_user, "id", None) else None,
    )
    return _to_public(a)


@router.patch("/attendances/{attendance_id}", response_model=AttendancePublic)
def manual_update_attendance(
    attendance_id: int,
    payload: AttendanceManualUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(
        current_user,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.STAFF_MANAGE_SUBORDINATES,
    )

    a = (
        db.query(Attendance)
        .options(
            joinedload(Attendance.user).joinedload(User.position),
            joinedload(Attendance.restaurant),
        )
        .filter(Attendance.id == attendance_id)
        .first()
    )
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance not found")

    target_user = a.user or db.query(User).options(joinedload(User.position)).filter(User.id == a.user_id).first()
    if a.user_id == current_user.id:
        if not has_permission(current_user, PermissionCode.STAFF_MANAGE_ALL):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you cannot modify your own record",
            )
    else:
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        ensure_can_manage_user(current_user, target_user)

    before_summary = _attendance_summary(a)
    data = payload.model_dump(exclude_unset=True)
    interval_changed = any(
        field in data for field in ("open_date", "open_time", "close_date", "close_time")
    )
    if interval_changed:
        new_open_date = data.get("open_date", a.open_date)
        new_open_time = data.get("open_time", a.open_time)
        close_date_provided = "close_date" in data
        close_time_provided = "close_time" in data
        new_close_date = data.get("close_date") if close_date_provided else a.close_date
        new_close_time = data.get("close_time") if close_time_provided else a.close_time
        if (close_date_provided and data.get("close_date") is None) or (close_time_provided and data.get("close_time") is None):
            new_close_date = None
            new_close_time = None

        today = now_local().date()
        if new_open_date and new_open_date > today:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя создавать смены в будущие даты")
        if new_close_date and new_close_date > today:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя создавать смены в будущие даты")

        opened_dt = combine_date_time(new_open_date, new_open_time)
        closed_dt = combine_date_time(new_close_date, new_close_time) if new_close_date and new_close_time else None
        conflict = _find_attendance_overlap(
            db,
            a.user_id,
            opened_dt,
            closed_dt,
            exclude_attendance_id=a.id,
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Смена пересекается с существующей (id={conflict.id})",
            )

    if "position_id" in data:
        pos_id = data["position_id"]
        if pos_id is not None and not db.query(Position).get(pos_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        a.position_id = pos_id
    if "restaurant_id" in data:
        a.restaurant_id = data["restaurant_id"]
    if "rate" in data:
        a.rate = data["rate"]

    open_changed = False
    if "open_date" in data:
        a.open_date = data["open_date"]
        open_changed = True
    if "open_time" in data:
        a.open_time = data["open_time"]
        open_changed = True

    close_changed = False
    if "close_date" in data:
        a.close_date = data["close_date"]
        close_changed = True
    if "close_time" in data:
        a.close_time = data["close_time"]
        close_changed = True

    explicit_duration = "duration_minutes" in data
    explicit_night = "night_minutes" in data

    if ("close_date" in data and data["close_date"] is None) or ("close_time" in data and data["close_time"] is None):
        a.close_date = None
        a.close_time = None
        a.duration_minutes = data.get("duration_minutes") if explicit_duration else None
        a.night_minutes = data.get("night_minutes") if explicit_night else 0
        a.pay_amount = None
    else:
        if explicit_duration:
            a.duration_minutes = data["duration_minutes"]
        if explicit_night:
            a.night_minutes = data["night_minutes"] or 0

        if a.close_date and a.close_time and a.open_date and a.open_time:
            opened_dt = combine_date_time(a.open_date, a.open_time)
            closed_dt = combine_date_time(a.close_date, a.close_time)
            if not explicit_duration or not explicit_night:
                _apply_close_stats(a, opened_dt, closed_dt)
            _calculate_and_set_pay(db, a)
        else:
            if open_changed or close_changed:
                if not explicit_duration:
                    a.duration_minutes = None
                if not explicit_night:
                    a.night_minutes = 0
            a.pay_amount = None

    after_summary = _attendance_summary(a)
    if before_summary != after_summary:
        log_employee_changes(
            db,
            user_id=a.user_id,
            changed_by_id=current_user.id,
            changes=[
                {
                    "field": "attendance",
                    "old_value": before_summary,
                    "new_value": after_summary,
                    "source": "staff_portal",
                    "comment": "Изменена смена",
                    "entity_type": "attendance",
                    "entity_id": a.id,
                }
            ],
        )
    db.commit()
    db.refresh(a)
    return _to_public(a)

