from __future__ import annotations

import json
from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload

from backend.bd.database import get_db
from backend.bd.models import EmployeeChangeEvent, Position, User, Role
from backend.schemas import (
    EmployeeChangeEventListResponse,
    EmployeeChangeEventRead,
    EmployeeChangeEventUpdate,
)
from backend.services.permissions import PermissionCode, ensure_permissions, can_view_rate
from backend.utils import get_current_user

router = APIRouter(prefix="/employee-change-events", tags=["Employee change events"])

_RATE_FIELDS = {"rate", "individual_rate", "position_rate"}


def _normalize_role_key(role: Optional[Role]) -> str:
    name = getattr(role, "name", None) or ""
    return name.strip().lower().replace(" ", "").replace("-", "")


def _is_superadmin(user: User) -> bool:
    role_key = _normalize_role_key(getattr(user, "role", None))
    return role_key in {
        "суперадмин",
        "системныйадмин",
        "системныйадминистратор",
        "superadmin",
        "systemadmin",
        "systemadministrator",
    }


def _mask_attendance_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return value

    def mask_entry(entry: dict) -> bool:
        changed = False
        if entry.get("rate") is not None:
            entry["rate"] = "$$$"
            changed = True
        if entry.get("pay_amount") is not None:
            entry["pay_amount"] = "$$$"
            changed = True
        return changed

    changed = False
    if isinstance(parsed, list):
        for entry in parsed:
            if isinstance(entry, dict):
                if mask_entry(entry):
                    changed = True
    elif isinstance(parsed, dict):
        changed = mask_entry(parsed)

    if not changed:
        return value
    return json.dumps(parsed, ensure_ascii=False)


def _mask_attendance_json(value):
    if not value:
        return value

    def mask_entry(entry: dict) -> bool:
        changed = False
        if entry.get("rate") is not None:
            entry["rate"] = "$$$"
            changed = True
        if entry.get("pay_amount") is not None:
            entry["pay_amount"] = "$$$"
            changed = True
        return changed

    changed = False
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict):
                if mask_entry(entry):
                    changed = True
    elif isinstance(value, dict):
        changed = mask_entry(value)

    return value if not changed else value


def _mask_sensitive_changes(
    items: list[EmployeeChangeEvent],
    current_user: User,
    db: Session,
) -> list[EmployeeChangeEvent]:
    if not items:
        return items
    target_ids = {
        item.user_id
        for item in items
        if item.field in _RATE_FIELDS or item.field == "attendance"
    }
    if not target_ids:
        return items
    users = (
        db.query(User)
        .options(
            joinedload(User.role),
            joinedload(User.position).joinedload(Position.role),
        )
        .filter(User.id.in_(target_ids))
        .all()
    )
    user_map = {user.id: user for user in users}
    for item in items:
        if item.field not in _RATE_FIELDS and item.field != "attendance":
            continue
        target = user_map.get(item.user_id)
        if item.field in _RATE_FIELDS:
            if not target or not can_view_rate(current_user, target):
                item.old_value = "$$$"
                item.new_value = "$$$"
                item.old_value_json = "$$$"
                item.new_value_json = "$$$"
            continue
        if item.field == "attendance" and (not target or not can_view_rate(current_user, target)):
            item.old_value = _mask_attendance_value(item.old_value)
            item.new_value = _mask_attendance_value(item.new_value)
            item.old_value_json = _mask_attendance_json(item.old_value_json)
            item.new_value_json = _mask_attendance_json(item.new_value_json)
    return items


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@router.get("", response_model=EmployeeChangeEventListResponse)
def list_employee_change_events(
    user_id: Optional[int] = Query(None),
    field: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeChangeEventListResponse:
    ensure_permissions(
        current_user,
        PermissionCode.EMPLOYEE_CHANGES_VIEW,
        PermissionCode.EMPLOYEE_CHANGES_MANAGE,
        PermissionCode.EMPLOYEE_CHANGES_DELETE,
    )
    if user_id is None and not _is_superadmin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    query = db.query(EmployeeChangeEvent).options(
        joinedload(EmployeeChangeEvent.changed_by),
        joinedload(EmployeeChangeEvent.user),
    )
    if user_id is not None:
        query = query.filter(EmployeeChangeEvent.user_id == user_id)
    if field:
        query = query.filter(EmployeeChangeEvent.field == field)
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start:
        query = query.filter(EmployeeChangeEvent.created_at >= datetime.combine(start, time.min))
    if end:
        query = query.filter(EmployeeChangeEvent.created_at <= datetime.combine(end, time.max))
    items = (
        query.order_by(EmployeeChangeEvent.created_at.desc(), EmployeeChangeEvent.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = _mask_sensitive_changes(items, current_user, db)
    return EmployeeChangeEventListResponse(
        items=[EmployeeChangeEventRead.model_validate(item) for item in items]
    )


@router.patch("/{event_id}", response_model=EmployeeChangeEventRead)
def update_employee_change_event(
    event_id: int,
    payload: EmployeeChangeEventUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmployeeChangeEventRead:
    ensure_permissions(current_user, PermissionCode.EMPLOYEE_CHANGES_MANAGE)
    event = db.query(EmployeeChangeEvent).filter(EmployeeChangeEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(event, key, value)

    db.commit()
    db.refresh(event)
    return EmployeeChangeEventRead.model_validate(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee_change_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    ensure_permissions(current_user, PermissionCode.EMPLOYEE_CHANGES_DELETE)
    event = db.query(EmployeeChangeEvent).filter(EmployeeChangeEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    db.delete(event)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
