"""Helpers for employee change history logging."""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from backend.bd.models import EmployeeChangeEvent, User
from backend.services.request_context import get_request_context


def _serialize_value(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _coerce_json(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (date, datetime, Decimal)):
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed and trimmed[0] in "[{":
            try:
                return json.loads(trimmed)
            except (TypeError, ValueError):
                return None
    return None


def format_ref(entity, name_attr: str = "name") -> Optional[dict]:
    if not entity:
        return None
    return {
        "id": getattr(entity, "id", None),
        "name": getattr(entity, name_attr, None),
    }


def log_employee_changes(
    db: Session,
    *,
    user_id: int,
    changed_by_id: Optional[int],
    changes: Iterable[dict],
    source: str = "manual",
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    restaurant_id: Optional[int] = None,
    position_id: Optional[int] = None,
    role_id: Optional[int] = None,
) -> list[EmployeeChangeEvent]:
    events: list[EmployeeChangeEvent] = []
    ctx = get_request_context()
    target_user: Optional[User] = None
    if user_id and (restaurant_id is None or position_id is None or role_id is None):
        target_user = db.query(User).filter(User.id == user_id).first()
    default_entity_type = entity_type or "user"
    default_entity_id = entity_id or user_id
    for change in changes:
        field = change.get("field")
        if not field:
            continue
        raw_old = change.get("old_value")
        raw_new = change.get("new_value")
        event = EmployeeChangeEvent(
            user_id=user_id,
            changed_by_id=changed_by_id,
            entity_type=change.get("entity_type") or default_entity_type,
            entity_id=change.get("entity_id") or default_entity_id,
            field=str(field),
            old_value=_serialize_value(raw_old),
            new_value=_serialize_value(raw_new),
            old_value_json=_coerce_json(raw_old),
            new_value_json=_coerce_json(raw_new),
            source=change.get("source") or source,
            comment=change.get("comment"),
            request_id=change.get("request_id") or (ctx.request_id if ctx else None),
            ip_address=change.get("ip_address") or (ctx.ip_address if ctx else None),
            user_agent=change.get("user_agent") or (ctx.user_agent if ctx else None),
            endpoint=change.get("endpoint") or (ctx.endpoint if ctx else None),
            method=change.get("method") or (ctx.method if ctx else None),
            restaurant_id=change.get("restaurant_id")
            or restaurant_id
            or getattr(target_user, "workplace_restaurant_id", None),
            position_id=change.get("position_id") or position_id or getattr(target_user, "position_id", None),
            role_id=change.get("role_id") or role_id or getattr(target_user, "role_id", None),
        )
        events.append(event)
    if events:
        db.add_all(events)
    return events
