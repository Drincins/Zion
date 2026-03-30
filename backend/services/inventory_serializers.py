from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.bd.models import (
    InvInstanceEventType,
    InvItem,
    InvItemInstanceEvent,
    InvItemRecord,
    InvMovementEvent,
    InvStoragePlace,
    Restaurant,
    RestaurantSubdivision,
    User,
)
from backend.schemas import (
    InvItemLocationSummary,
    InvItemRead,
    InvItemRecordRead,
    InventoryInstanceEventTypeRead,
    InventoryItemInstanceEventRead,
    InventoryStoragePlaceRead,
)
from backend.services.s3 import generate_presigned_url

logger = logging.getLogger(__name__)

MOVEMENT_ACTION_LABELS: dict[str, str] = {
    "item_created": "Создание товара",
    "item_updated": "Изменение карточки",
    "item_deleted": "Удаление товара",
    "transfer": "Перевод между подразделениями",
    "quantity_increase": "Поступление",
    "quantity_adjusted": "Изменение количества",
    "writeoff": "Списание",
    "cost_changed": "Изменение стоимости",
    "record_created": "Ручная операция",
    "record_updated": "Изменение операции",
    "record_deleted": "Удаление операции",
}

DEFAULT_INSTANCE_EVENT_TYPES: tuple[dict[str, object], ...] = (
    {
        "code": "quantity_increase",
        "name": "Поступление",
        "description": "Автоматическое событие прихода единицы товара.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 10,
    },
    {
        "code": "quantity_adjusted",
        "name": "Корректировка",
        "description": "Автоматическая корректировка количества единиц товара.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 20,
    },
    {
        "code": "transfer",
        "name": "Перемещение",
        "description": "Автоматическое перемещение единицы товара между локациями.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 30,
    },
    {
        "code": "writeoff",
        "name": "Списание",
        "description": "Автоматическое списание единицы товара.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 40,
    },
    {
        "code": "repair",
        "name": "Ремонт",
        "description": "Ручное сервисное событие для ремонта единицы товара.",
        "is_manual": True,
        "is_active": True,
        "status_key": "repair",
        "status_label": "В ремонте",
        "sort_order": 100,
    },
    {
        "code": "maintenance",
        "name": "ТО",
        "description": "Ручное сервисное событие для технического обслуживания.",
        "is_manual": True,
        "is_active": True,
        "status_key": "maintenance",
        "status_label": "На ТО",
        "sort_order": 110,
    },
    {
        "code": "inspection",
        "name": "Проверка",
        "description": "Ручное сервисное событие для проверки состояния единицы товара.",
        "is_manual": True,
        "is_active": True,
        "status_key": "inspection",
        "status_label": "Проверяется",
        "sort_order": 120,
    },
    {
        "code": "note",
        "name": "Комментарий",
        "description": "Ручное текстовое событие без смены статуса единицы товара.",
        "is_manual": True,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 130,
    },
)
DEFAULT_INSTANCE_EVENT_TYPE_MAP = {
    str(item["code"]): dict(item)
    for item in DEFAULT_INSTANCE_EVENT_TYPES
}


def _normalize_inventory_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_instance_event_type_code(value: str | None) -> str:
    normalized = _normalize_inventory_string(value)
    if normalized:
        return normalized.lower()
    return f"evt_{uuid4().hex[:12]}"


def _load_instance_event_type_map(db: Session) -> dict[str, dict[str, object]]:
    rows = (
        db.query(InvInstanceEventType)
        .order_by(InvInstanceEventType.sort_order.asc(), InvInstanceEventType.name.asc(), InvInstanceEventType.id.asc())
        .all()
    )
    mapping = {
        str(row.code): {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "description": row.description,
            "is_active": bool(row.is_active),
            "is_manual": bool(row.is_manual),
            "status_key": _normalize_inventory_string(row.status_key),
            "status_label": _normalize_inventory_string(row.status_label),
            "sort_order": int(row.sort_order or 100),
        }
        for row in rows
    }
    for code, payload in DEFAULT_INSTANCE_EVENT_TYPE_MAP.items():
        mapping.setdefault(code, dict(payload))
    return mapping


def _movement_action_label(action_type: str) -> str:
    return MOVEMENT_ACTION_LABELS.get(action_type, action_type)


def _instance_event_type_label(action_type: str, *, event_type_map: dict[str, dict[str, object]] | None = None) -> str:
    config = (event_type_map or {}).get(action_type)
    if config and _normalize_inventory_string(str(config.get("name") or "")):
        return str(config["name"])
    legacy = DEFAULT_INSTANCE_EVENT_TYPE_MAP.get(action_type)
    if legacy:
        return str(legacy["name"])
    return _movement_action_label(action_type)


def _serialize_instance_event_type(row: InvInstanceEventType) -> InventoryInstanceEventTypeRead:
    return InventoryInstanceEventTypeRead(
        id=row.id,
        code=row.code,
        name=row.name,
        description=row.description,
        is_active=bool(row.is_active),
        is_manual=bool(row.is_manual),
        status_key=_normalize_inventory_string(row.status_key),
        status_label=_normalize_inventory_string(row.status_label),
        sort_order=int(row.sort_order or 100),
        created_at=row.created_at,
    )


def _serialize_storage_place(row: InvStoragePlace) -> InventoryStoragePlaceRead:
    return InventoryStoragePlaceRead(
        id=row.id,
        name=row.name,
        scope_kind=row.scope_kind,
        restaurant_id=row.restaurant_id,
        description=row.description,
        is_active=bool(row.is_active),
        sort_order=int(row.sort_order or 100),
        created_at=row.created_at,
    )


def _resolve_photo_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value
    try:
        return generate_presigned_url(value)
    except Exception:
        logger.warning("Failed to build presigned URL for inventory photo %s", value, exc_info=True)
        return value


def _item_schema(
    item: InvItem,
    *,
    location_totals: list[InvItemLocationSummary] | None = None,
    total_quantity: int = 0,
    warehouse_quantity: int = 0,
) -> InvItemRead:
    return InvItemRead(
        id=item.id,
        code=item.code,
        name=item.name,
        category_id=item.category_id,
        group_id=item.group_id,
        kind_id=item.kind_id,
        cost=item.default_cost if item.default_cost is not None else item.cost,
        default_cost=item.default_cost,
        note=item.note,
        manufacturer=item.manufacturer,
        storage_conditions=item.storage_conditions,
        photo_url=_resolve_photo_url(item.photo_url),
        use_instance_codes=bool(item.use_instance_codes),
        is_active=bool(item.is_active),
        created_at=item.created_at,
        photo_key=item.photo_url,
        kind_name=getattr(getattr(item, "kind", None), "name", None),
        total_quantity=total_quantity,
        warehouse_quantity=warehouse_quantity,
        location_totals=location_totals or [],
    )


def _record_schema(record: InvItemRecord) -> InvItemRecordRead:
    return InvItemRecordRead(
        id=record.id,
        created_at=record.created_at,
        item_id=record.item_id,
        category_id=record.category_id,
        group_id=record.group_id,
        restaurant_id=record.restaurant_id,
        user_id=record.user_id,
        quantity=record.quantity,
        cost=record.cost,
        comment=record.comment,
        photo_url=_resolve_photo_url(record.photo_url),
        photo_key=record.photo_url,
    )


def _instance_event_action_label(
    action_type: str,
    *,
    event_type_map: dict[str, dict[str, object]] | None = None,
) -> str:
    return _instance_event_type_label(action_type, event_type_map=event_type_map)


def _compose_user_name(*, first_name: str | None, last_name: str | None, middle_name: str | None, username: str | None, user_id: int | None) -> str | None:
    full_name = " ".join(part for part in [last_name, first_name, middle_name] if part).strip()
    if full_name:
        return full_name
    if username:
        return username
    if user_id is not None:
        return f"ID {user_id}"
    return None


def _location_name(
    *,
    location_kind: str | None,
    restaurant_id: int | None,
    storage_place_id: int | None,
    subdivision_id: int | None,
    restaurant_names: dict[int, str],
    storage_place_names: dict[int, str],
    subdivision_names: dict[int, str],
) -> str | None:
    if location_kind == "warehouse":
        return "Склад"
    if location_kind == "restaurant":
        base_name = "Ресторан" if restaurant_id is None else restaurant_names.get(restaurant_id, f"Ресторан #{restaurant_id}")
        if storage_place_id is None:
            return f"{base_name} · Без места хранения"
        storage_place_name = storage_place_names.get(storage_place_id, f"Место #{storage_place_id}")
        return f"{base_name} · {storage_place_name}"
    if location_kind == "subdivision":
        if subdivision_id is None:
            return "Подразделение"
        return subdivision_names.get(subdivision_id, f"Подразделение #{subdivision_id}")
    return None


def _load_actor_name_map(db: Session, actor_ids: set[int]) -> dict[int, str]:
    if not actor_ids:
        return {}
    actor_rows = (
        db.query(User.id, User.first_name, User.last_name, User.middle_name, User.username)
        .filter(User.id.in_(actor_ids))
        .all()
    )
    return {
        int(row.id): _compose_user_name(
            first_name=row.first_name,
            last_name=row.last_name,
            middle_name=row.middle_name,
            username=row.username,
            user_id=row.id,
        )
        for row in actor_rows
    }


def _load_location_name_maps(
    db: Session,
    *,
    restaurant_ids: set[int],
    storage_place_ids: set[int],
    subdivision_ids: set[int],
) -> tuple[dict[int, str], dict[int, str], dict[int, str]]:
    restaurant_names = {
        int(row.id): row.name
        for row in (
            db.query(Restaurant.id, Restaurant.name).filter(Restaurant.id.in_(restaurant_ids)).all()
            if restaurant_ids
            else []
        )
    }
    storage_place_names = {
        int(row.id): row.name
        for row in (
            db.query(InvStoragePlace.id, InvStoragePlace.name).filter(InvStoragePlace.id.in_(storage_place_ids)).all()
            if storage_place_ids
            else []
        )
    }
    subdivision_names = {
        int(row.id): row.name
        for row in (
            db.query(RestaurantSubdivision.id, RestaurantSubdivision.name)
            .filter(RestaurantSubdivision.id.in_(subdivision_ids))
            .all()
            if subdivision_ids
            else []
        )
    }
    return restaurant_names, storage_place_names, subdivision_names


def _serialize_instance_event(
    event: InvItemInstanceEvent,
    *,
    actor_map: dict[int, str],
    restaurant_names: dict[int, str],
    storage_place_names: dict[int, str],
    subdivision_names: dict[int, str],
    event_type_map: dict[str, dict[str, object]] | None = None,
) -> InventoryItemInstanceEventRead:
    return InventoryItemInstanceEventRead(
        id=event.id,
        created_at=event.created_at,
        action_type=event.action_type,
        action_label=_instance_event_action_label(event.action_type, event_type_map=event_type_map),
        actor_name=actor_map.get(event.actor_id) if event.actor_id is not None else None,
        instance_id=event.instance_id,
        instance_code=event.instance_code_snapshot,
        purchase_cost=event.purchase_cost,
        from_storage_place_id=event.from_storage_place_id,
        from_location_name=_location_name(
            location_kind=event.from_location_kind,
            restaurant_id=event.from_restaurant_id,
            storage_place_id=event.from_storage_place_id,
            subdivision_id=event.from_subdivision_id,
            restaurant_names=restaurant_names,
            storage_place_names=storage_place_names,
            subdivision_names=subdivision_names,
        ),
        to_storage_place_id=event.to_storage_place_id,
        to_location_name=_location_name(
            location_kind=event.to_location_kind,
            restaurant_id=event.to_restaurant_id,
            storage_place_id=event.to_storage_place_id,
            subdivision_id=event.to_subdivision_id,
            restaurant_names=restaurant_names,
            storage_place_names=storage_place_names,
            subdivision_names=subdivision_names,
        ),
        comment=event.comment,
    )


def _combine_int_filters(primary: list[int] | None, bracket: list[int] | None) -> list[int]:
    return sorted({int(value) for value in (primary or []) + (bracket or [])})


def _combine_str_filters(primary: list[str] | None, bracket: list[str] | None) -> list[str]:
    values = [str(value).strip() for value in (primary or []) + (bracket or [])]
    return [value for value in sorted(set(values)) if value]


def _event_matches_allowed_restaurants(allowed_restaurants: set[int]) -> list:
    return [
        or_(
            InvMovementEvent.from_location_kind.is_(None),
            InvMovementEvent.from_location_kind != "restaurant",
            InvMovementEvent.from_restaurant_id.in_(allowed_restaurants),
        ),
        or_(
            InvMovementEvent.to_location_kind.is_(None),
            InvMovementEvent.to_location_kind != "restaurant",
            InvMovementEvent.to_restaurant_id.in_(allowed_restaurants),
        ),
    ]


def _instance_event_matches_restaurant(restaurant_id: int):
    return or_(
        and_(
            InvItemInstanceEvent.to_location_kind == "restaurant",
            InvItemInstanceEvent.to_restaurant_id == restaurant_id,
        ),
        and_(
            InvItemInstanceEvent.from_location_kind == "restaurant",
            InvItemInstanceEvent.from_restaurant_id == restaurant_id,
        ),
    )


def _instance_event_matches_storage_place(storage_place_id: int):
    return or_(
        InvItemInstanceEvent.to_storage_place_id == storage_place_id,
        InvItemInstanceEvent.from_storage_place_id == storage_place_id,
    )
