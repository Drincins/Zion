from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload, load_only, noload, selectinload

from backend.bd.database import get_db
from backend.bd.models import (
    Attendance,
    Company,
    EmployeeChangeEvent,
    Position,
    Restaurant,
    RestaurantSubdivision,
    Role,
    User,
)
from backend.schemas import (
    AttendancePublic,
    EmployeeCardPublic,
    EmployeeIikoSyncPreviewResponse,
    EmployeeUpdateRequest,
    IikoSyncEmployeeSnapshot,
    PhotoUploadResponse,
    StaffEmployeeDetailResponse,
    StaffEmployeeListResponse,
    StaffEmployeesBootstrapResponse,
    StaffUserPublic,
    TimesheetOptionsResponse,
)
from backend.services.employee_identity import build_employee_row_id
from backend.services.employee_changes import format_ref, log_employee_changes
from backend.services.iiko_staff import (
    IikoIntegrationError,
    add_user_to_iiko,
    fetch_iiko_employee_snapshot,
    fire_user_in_iiko,
)
from backend.services.payroll_export import _autosize_sheet, _style_sheet
from backend.services.permissions import (
    PermissionCode,
    can_manage_user,
    can_view_rate,
    ensure_can_manage_user,
    ensure_permissions,
    has_permission,
)
from backend.services.reference_cache import cached_reference_data
from backend.services.s3 import generate_presigned_url, upload_employee_photo_with_url
from backend.services.staff_employee_listing import (
    ensure_staff_view as _ensure_staff_view,
    get_allowed_workplace_ids as _get_allowed_workplace_ids,
    ids_scope_key as _ids_scope_key,
    list_staff_employee_items as _list_staff_employee_items,
    load_staff_references as _load_staff_references,
    role_level_for_rate as _role_level_for_rate,
    to_staff_public as _to_staff_public,
)
from backend.services.timesheet_export import build_timesheet_report
from backend.utils import (
    get_current_user,
    get_user_restaurant_ids,
    hash_password,
    users_share_restaurant,
)

logger = logging.getLogger(__name__)

STAFF_TIMESHEET_OPTIONS_CACHE_SCOPE = "staff_employees:timesheet_options"
STAFF_TIMESHEET_OPTIONS_CACHE_TTL_SECONDS = 45


def _month_bounds(day: date) -> tuple[date, date]:
    start = date(day.year, day.month, 1)
    if day.month == 12:
        end = date(day.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(day.year, day.month + 1, 1) - timedelta(days=1)
    return start, end


def _normalize_rate_value(value):
    if value is None:
        return None
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01")))
    except Exception:
        return str(value)


def _format_restaurant_refs(restaurants):
    if not restaurants:
        return []
    return [format_ref(item) for item in restaurants if item]


def _to_employee_card(user: User, viewer: Optional[User] = None) -> EmployeeCardPublic:
    can_see_rate = can_view_rate(viewer, user) if viewer else True
    photo_url = None
    if user.photo_key:
        try:
            photo_url = generate_presigned_url(user.photo_key)
        except Exception:
            logger.warning("Failed to build photo URL for user %s", user.id, exc_info=True)
            photo_url = None

    return EmployeeCardPublic(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        iiko_code=user.iiko_code,
        iiko_id=user.iiko_id,
        company_id=user.company.id if user.company else None,
        company_name=user.company.name if user.company else None,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        position_id=user.position_id,
        position_name=user.position.name if user.position else None,
        rate=float(user.rate) if can_see_rate and user.rate is not None else None,
        hire_date=user.hire_date,
        fire_date=user.fire_date,
        fired=bool(user.fired),
        staff_code=user.staff_code,
        gender=user.gender,
        birth_date=user.birth_date,
        phone_number=user.phone_number,
        email=user.email,
        photo_key=user.photo_key,
        photo_url=photo_url,
        is_cis_employee=bool(getattr(user, "is_cis_employee", False)),
        confidential_data_consent=bool(getattr(user, "confidential_data_consent", False)),
        is_formalized=bool(getattr(user, "is_formalized", False)),
        workplace_restaurant_id=getattr(user, "workplace_restaurant_id", None),
        individual_rate=float(user.individual_rate)
        if can_see_rate and user.individual_rate is not None
        else None,
        iiko_sync_error=getattr(user, "iiko_sync_error", None),
        rate_hidden=not can_see_rate,
        has_fingerprint=bool(getattr(user, "has_fingerprint", False)),
    )


def _get_duplicate_photo_url(user: User) -> Optional[str]:
    if not user.photo_key:
        return None
    try:
        return generate_presigned_url(user.photo_key)
    except Exception:
        logger.warning("Failed to build photo URL for duplicate employee %s", user.id, exc_info=True)
        return None


def _get_duplicate_fired_comment(db: Session, user: User) -> Optional[str]:
    if not user.fired:
        return None
    event = (
        db.query(EmployeeChangeEvent)
        .filter(
            EmployeeChangeEvent.user_id == user.id,
            EmployeeChangeEvent.field == "fired",
            EmployeeChangeEvent.new_value.in_(["True", "true", "1"]),
        )
        .order_by(EmployeeChangeEvent.created_at.desc(), EmployeeChangeEvent.id.desc())
        .first()
    )
    return event.comment if event else None


def _can_view_duplicate_employee(db: Session, viewer: User, target: User) -> bool:
    if viewer.id == target.id:
        return True
    if not users_share_restaurant(db, viewer, target.id):
        return False
    return any(
        has_permission(viewer, code)
        for code in (
            PermissionCode.STAFF_VIEW_SENSITIVE,
            PermissionCode.STAFF_MANAGE_SUBORDINATES,
            PermissionCode.STAFF_MANAGE_ALL,
            PermissionCode.STAFF_EMPLOYEES_VIEW,
            PermissionCode.EMPLOYEES_CARD_VIEW,
        )
    )


def _build_duplicate_employee_payload(db: Session, user: User, *, include_id: bool) -> dict:
    position_name = user.position.name if user.position else None
    workplace_name = user.workplace_restaurant.name if user.workplace_restaurant else None
    payload = {
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "middle_name": user.middle_name or "",
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "hire_date": user.hire_date.isoformat() if user.hire_date else None,
        "fire_date": user.fire_date.isoformat() if user.fire_date else None,
        "position": position_name,
        "workplace": workplace_name,
        "fired": bool(user.fired),
        "fired_comment": _get_duplicate_fired_comment(db, user),
        "photo_url": _get_duplicate_photo_url(user),
    }
    if include_id:
        payload["id"] = user.id
    return payload


def _attendance_to_public(
    attendance: Attendance,
    viewer: Optional[User] = None,
    target: Optional[User] = None,
) -> AttendancePublic:
    can_see_rate = True
    if viewer is not None and target is not None:
        can_see_rate = can_view_rate(viewer, target)
    return AttendancePublic(
        id=attendance.id,
        user_id=attendance.user_id,
        position_id=attendance.position_id,
        position_name=attendance.position.name if attendance.position else None,
        restaurant_id=attendance.restaurant_id,
        restaurant_name=attendance.restaurant.name if attendance.restaurant else None,
        rate=float(attendance.rate) if can_see_rate and attendance.rate is not None else None,
        pay_amount=float(attendance.pay_amount)
        if can_see_rate and attendance.pay_amount is not None
        else None,
        open_date=attendance.open_date,
        open_time=attendance.open_time,
        close_date=attendance.close_date,
        close_time=attendance.close_time,
        duration_minutes=attendance.duration_minutes,
        night_minutes=attendance.night_minutes or 0,
    )


def _attendance_range_condition(date_from: date, date_to: date):
    return and_(
        Attendance.open_date >= date_from,
        Attendance.open_date <= date_to,
    )


def _ensure_timesheet_export(user: User) -> None:
    _ensure_staff_view(user)
    ensure_permissions(user, PermissionCode.TIMESHEET_EXPORT)


def _validate_iiko_restaurant_scope(
    db: Session,
    viewer: User,
    *,
    sync_restaurant_id: Optional[int],
    department_restaurant_ids: Optional[list[int]],
) -> None:
    allowed_restaurants = get_user_restaurant_ids(db, viewer)
    if allowed_restaurants is None:
        return

    requested_ids: set[int] = set()
    if sync_restaurant_id:
        requested_ids.add(int(sync_restaurant_id))
    for raw in department_restaurant_ids or []:
        try:
            rid = int(raw)
        except Exception:
            continue
        if rid > 0:
            requested_ids.add(rid)

    invalid_ids = requested_ids.difference(allowed_restaurants)
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to the selected restaurants is not allowed",
        )


def _normalize_role_key(role: Optional[Role]) -> str:
    name = getattr(role, "name", None) or ""
    return name.strip().lower().replace(" ", "").replace("-", "")


def _can_edit_iiko_id(viewer: User) -> bool:
    if has_permission(viewer, PermissionCode.SYSTEM_ADMIN):
        return True
    role_key = _normalize_role_key(getattr(viewer, "role", None))
    return role_key in {
        "суперадмин",
        "системныйадмин",
        "системныйадминистратор",
        "superadmin",
        "systemadmin",
        "systemadministrator",
    }


def _ensure_staff_employees_export(user: User) -> None:
    _ensure_staff_view(user)
    ensure_permissions(user, PermissionCode.STAFF_EMPLOYEES_EXPORT)


EMPLOYEE_EXPORT_COLUMNS: dict[str, str] = {
    "staff_code": "Табельный номер",
    "full_name": "ФИО",
    "phone_number": "Телефон",
    "company_name": "Компания",
    "position_name": "Должность",
    "iiko_id": "Код сотрудника (Айко)",
    "gender": "Пол",
    "hire_date": "Дата найма",
    "fire_date": "Дата увольнения",
    "birth_date": "Дата рождения",
    "is_cis_employee": "Сотрудник СНГ",
    "restaurants": "Рестораны",
    "status": "Статус",
}


def _format_employee_phone(value: Optional[str]) -> str:
    if value is None or value == "":
        return ""
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return str(value)
    normalized = digits
    if normalized.startswith("8"):
        normalized = f"7{normalized[1:]}"
    if not normalized.startswith("7"):
        normalized = f"7{normalized}"
    normalized = normalized[:11]
    if len(normalized) < 11:
        return str(value)
    area = normalized[1:4]
    first = normalized[4:7]
    second = normalized[7:9]
    third = normalized[9:11]
    return f"+7({area})-{first}-{second}-{third}"


def _format_employee_gender(value: Optional[str]) -> str:
    if value == "male":
        return "Мужской"
    if value == "female":
        return "Женский"
    return ""


def _employee_export_full_name(user: User) -> str:
    last_name = getattr(user, "last_name", None) or ""
    first_name = getattr(user, "first_name", None) or ""
    parts = [part for part in [last_name, first_name] if part]
    if parts:
        return " ".join(parts)
    middle_name = getattr(user, "middle_name", None) or ""
    parts = [part for part in [last_name, first_name, middle_name] if part]
    if parts:
        return " ".join(parts)
    return getattr(user, "username", None) or ""


def _employee_export_restaurants(user: User) -> str:
    restaurants = getattr(user, "restaurants", None) or []
    names: list[str] = []
    for restaurant in restaurants:
        if not restaurant:
            continue
        name = getattr(restaurant, "name", None)
        if name:
            names.append(str(name))
            continue
        rid = getattr(restaurant, "id", None)
        if rid is not None:
            names.append(f"ID {rid}")
    return ", ".join([n for n in names if n])


def _employee_export_value(user: User, column_id: str) -> Any:
    if column_id == "staff_code":
        return getattr(user, "staff_code", None) or ""
    if column_id == "full_name":
        return _employee_export_full_name(user)
    if column_id == "phone_number":
        return _format_employee_phone(getattr(user, "phone_number", None))
    if column_id == "company_name":
        company = getattr(user, "company", None)
        return getattr(company, "name", None) or ""
    if column_id == "position_name":
        position = getattr(user, "position", None)
        return getattr(position, "name", None) or ""
    if column_id == "iiko_id":
        return getattr(user, "iiko_id", None) or ""
    if column_id == "gender":
        return _format_employee_gender(getattr(user, "gender", None))
    if column_id == "hire_date":
        return getattr(user, "hire_date", None) or None
    if column_id == "fire_date":
        return getattr(user, "fire_date", None) or None
    if column_id == "birth_date":
        return getattr(user, "birth_date", None) or None
    if column_id == "is_cis_employee":
        return "Да" if bool(getattr(user, "is_cis_employee", False)) else "Нет"
    if column_id == "restaurants":
        return _employee_export_restaurants(user)
    if column_id == "status":
        return "Уволен" if bool(getattr(user, "fired", False)) else "Активен"
    return ""


class StaffEmployeesExportRequest(BaseModel):
    user_ids: List[int] = Field(default_factory=list, description="Ordered user IDs in current UI scope")
    column_ids: List[str] = Field(default_factory=list, description="Ordered column IDs to include")


def _can_edit_user(db: Session, viewer: User, target: User) -> bool:
    if has_permission(viewer, PermissionCode.STAFF_MANAGE_ALL):
        return True
    if has_permission(viewer, PermissionCode.STAFF_MANAGE_SUBORDINATES):
        return can_manage_user(viewer, target)
    if (
        has_permission(viewer, PermissionCode.STAFF_EMPLOYEES_MANAGE)
        or has_permission(viewer, PermissionCode.EMPLOYEES_CARD_MANAGE)
    ) and users_share_restaurant(db, viewer, target.id):
        return True
    return False


def _ensure_can_edit_user(db: Session, viewer: User, target: User) -> None:
    if _can_edit_user(db, viewer, target):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: insufficient permissions to manage this employee",
    )


def _can_sync_user_iiko(db: Session, viewer: User, target: User) -> bool:
    if _can_edit_user(db, viewer, target):
        return True

    has_sync_permissions = (
        has_permission(viewer, PermissionCode.STAFF_EMPLOYEES_IIKO_SYNC)
        or has_permission(viewer, PermissionCode.IIKO_MANAGE)
    )
    if not has_sync_permissions:
        return False

    return users_share_restaurant(db, viewer, target.id)


def _ensure_can_sync_user_iiko(db: Session, viewer: User, target: User) -> None:
    if _can_sync_user_iiko(db, viewer, target):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: insufficient permissions to sync this employee with iiko",
    )
