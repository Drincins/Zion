from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from backend.bd.models import (
    InvCategory,
    InvGroup,
    InvKind,
    InvInstanceEventType,
    InvItem,
    InvItemInstance,
    InvItemInstanceEvent,
    InvItemRecord,
    InvItemStock,
    InvMovementEvent,
    InvStoragePlace,
    Restaurant,
    RestaurantSubdivision,
    User,
)
from backend.schemas import (
    InventoryBalance,
    InventoryBalanceItem,
    InventoryItemInstanceEventRead,
    InventoryItemInstanceSummaryRead,
    InvMovementEventRead,
    InventoryRestaurantItemArrivalRead,
    InventoryRestaurantItemCardRead,
)
from backend.utils import get_user_restaurant_ids
from backend.services.inventory_movements import _ensure_restaurant_allowed, _resolve_storage_place

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
    {"code": "quantity_increase", "name": "Поступление", "description": "Автоматическое событие прихода единицы товара.", "is_manual": False, "is_active": True, "status_key": None, "status_label": None, "sort_order": 10},
    {"code": "quantity_adjusted", "name": "Корректировка", "description": "Автоматическая корректировка количества единиц товара.", "is_manual": False, "is_active": True, "status_key": None, "status_label": None, "sort_order": 20},
    {"code": "transfer", "name": "Перемещение", "description": "Автоматическое перемещение единицы товара между локациями.", "is_manual": False, "is_active": True, "status_key": None, "status_label": None, "sort_order": 30},
    {"code": "writeoff", "name": "Списание", "description": "Автоматическое списание единицы товара.", "is_manual": False, "is_active": True, "status_key": None, "status_label": None, "sort_order": 40},
    {"code": "repair", "name": "Ремонт", "description": "Ручное сервисное событие для ремонта единицы товара.", "is_manual": True, "is_active": True, "status_key": "repair", "status_label": "В ремонте", "sort_order": 100},
    {"code": "maintenance", "name": "ТО", "description": "Ручное сервисное событие для технического обслуживания.", "is_manual": True, "is_active": True, "status_key": "maintenance", "status_label": "На ТО", "sort_order": 110},
    {"code": "inspection", "name": "Проверка", "description": "Ручное сервисное событие для проверки состояния единицы товара.", "is_manual": True, "is_active": True, "status_key": "inspection", "status_label": "Проверяется", "sort_order": 120},
    {"code": "note", "name": "Комментарий", "description": "Ручное текстовое событие без смены статуса единицы товара.", "is_manual": True, "is_active": True, "status_key": None, "status_label": None, "sort_order": 130},
)
DEFAULT_INSTANCE_EVENT_TYPE_MAP = {str(item["code"]): dict(item) for item in DEFAULT_INSTANCE_EVENT_TYPES}


def _normalize_inventory_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


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


def _instance_event_action_label(
    action_type: str,
    *,
    event_type_map: dict[str, dict[str, object]] | None = None,
) -> str:
    config = (event_type_map or {}).get(action_type)
    if config and _normalize_inventory_string(str(config.get("name") or "")):
        return str(config["name"])
    legacy = DEFAULT_INSTANCE_EVENT_TYPE_MAP.get(action_type)
    if legacy:
        return str(legacy["name"])
    return _movement_action_label(action_type)


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


def serialize_inventory_instance_event(
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


def list_inventory_balances(
    *,
    db: Session,
    current_user: User,
    restaurant_id: int | None = None,
) -> list[InventoryBalance]:
    allowed_restaurants = get_user_restaurant_ids(db, current_user)

    if restaurant_id is not None:
        _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)
        restaurant_ids = [restaurant_id]
    else:
        if allowed_restaurants is None:
            restaurant_ids = [row[0] for row in db.query(Restaurant.id).order_by(Restaurant.id.asc()).all()]
        else:
            restaurant_ids = sorted(allowed_restaurants)

    if not restaurant_ids:
        return []

    rows = (
        db.query(
            InvItemStock.restaurant_id.label("restaurant_id"),
            InvItemStock.item_id.label("item_id"),
            InvItem.name.label("item_name"),
            InvItemStock.quantity.label("quantity"),
            InvItemStock.avg_cost.label("avg_cost"),
        )
        .join(InvItem, InvItem.id == InvItemStock.item_id)
        .filter(InvItemStock.restaurant_id.in_(restaurant_ids))
        .order_by(InvItemStock.restaurant_id.asc(), InvItem.name.asc())
        .all()
    )

    count_rows = (
        db.query(
            InvItemRecord.restaurant_id.label("restaurant_id"),
            InvItemRecord.item_id.label("item_id"),
            func.count(InvItemRecord.id).label("record_count"),
        )
        .filter(InvItemRecord.restaurant_id.in_(restaurant_ids))
        .group_by(InvItemRecord.restaurant_id, InvItemRecord.item_id)
        .all()
    )

    record_count_map: dict[tuple[int, int], int] = {
        (int(row.restaurant_id), int(row.item_id)): int(row.record_count or 0) for row in count_rows
    }

    result_map: dict[int, InventoryBalance] = {
        rest_id: InventoryBalance(
            restaurant_id=rest_id,
            total_quantity=0,
            total_cost=Decimal("0"),
            record_count=0,
            items=[],
        )
        for rest_id in restaurant_ids
    }

    for row in rows:
        rest_id = int(row.restaurant_id)
        item_quantity = int(row.quantity or 0)
        avg_cost = Decimal(row.avg_cost or 0)
        item_total_cost = avg_cost * item_quantity
        record_count = record_count_map.get((rest_id, int(row.item_id)), 0)

        entry = result_map[rest_id]
        entry.items.append(
            InventoryBalanceItem(
                item_id=int(row.item_id),
                item_name=str(row.item_name),
                total_quantity=item_quantity,
                total_cost=item_total_cost,
                record_count=record_count,
            )
        )
        entry.total_quantity += item_quantity
        entry.total_cost += item_total_cost
        entry.record_count += record_count

    return [result_map[rest_id] for rest_id in restaurant_ids]


def get_restaurant_balance(
    *,
    db: Session,
    current_user: User,
    restaurant_id: int,
) -> InventoryBalance:
    balances = list_inventory_balances(db=db, current_user=current_user, restaurant_id=restaurant_id)
    return balances[0] if balances else InventoryBalance(
        restaurant_id=restaurant_id,
        total_quantity=0,
        total_cost=Decimal("0"),
        record_count=0,
        items=[],
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


def list_movement_events(
    *,
    db: Session,
    current_user: User,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    item_ids: list[int] | None = None,
    item_ids_bracket: list[int] | None = None,
    group_ids: list[int] | None = None,
    group_ids_bracket: list[int] | None = None,
    category_ids: list[int] | None = None,
    category_ids_bracket: list[int] | None = None,
    kind_ids: list[int] | None = None,
    kind_ids_bracket: list[int] | None = None,
    object_ids: list[str] | None = None,
    object_ids_bracket: list[str] | None = None,
    action_types: list[str] | None = None,
    action_types_bracket: list[str] | None = None,
    actor_ids: list[int] | None = None,
    actor_ids_bracket: list[int] | None = None,
    q: str | None = None,
    limit: int = 500,
) -> list[InvMovementEventRead]:
    query = db.query(InvMovementEvent)
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None:
        if allowed_restaurants:
            for condition in _event_matches_allowed_restaurants(allowed_restaurants):
                query = query.filter(condition)
        else:
            query = query.filter(
                or_(
                    InvMovementEvent.from_location_kind.is_(None),
                    InvMovementEvent.from_location_kind != "restaurant",
                ),
                or_(
                    InvMovementEvent.to_location_kind.is_(None),
                    InvMovementEvent.to_location_kind != "restaurant",
                ),
            )

    if created_from is not None:
        query = query.filter(InvMovementEvent.created_at >= created_from)
    if created_to is not None:
        query = query.filter(InvMovementEvent.created_at <= created_to)

    normalized_item_ids = _combine_int_filters(item_ids, item_ids_bracket)
    if normalized_item_ids:
        query = query.filter(InvMovementEvent.item_id.in_(normalized_item_ids))

    normalized_group_ids = _combine_int_filters(group_ids, group_ids_bracket)
    if normalized_group_ids:
        query = query.filter(InvMovementEvent.group_id.in_(normalized_group_ids))

    normalized_category_ids = _combine_int_filters(category_ids, category_ids_bracket)
    if normalized_category_ids:
        query = query.filter(InvMovementEvent.category_id.in_(normalized_category_ids))

    normalized_kind_ids = _combine_int_filters(kind_ids, kind_ids_bracket)
    if normalized_kind_ids:
        query = query.filter(InvMovementEvent.kind_id.in_(normalized_kind_ids))

    normalized_action_types = _combine_str_filters(action_types, action_types_bracket)
    if normalized_action_types:
        query = query.filter(InvMovementEvent.action_type.in_(normalized_action_types))

    normalized_actor_ids = _combine_int_filters(actor_ids, actor_ids_bracket)
    if normalized_actor_ids:
        query = query.filter(InvMovementEvent.actor_id.in_(normalized_actor_ids))

    normalized_object_ids = _combine_str_filters(object_ids, object_ids_bracket)
    object_conditions = []
    for object_id in normalized_object_ids:
        if object_id == "warehouse":
            object_conditions.append(
                or_(
                    InvMovementEvent.from_location_kind == "warehouse",
                    InvMovementEvent.to_location_kind == "warehouse",
                )
            )
            continue
        if object_id.startswith("restaurant:"):
            try:
                rest_id = int(object_id.split(":", 1)[1])
            except ValueError:
                continue
            object_conditions.append(
                or_(
                    InvMovementEvent.from_restaurant_id == rest_id,
                    InvMovementEvent.to_restaurant_id == rest_id,
                )
            )
            continue
        if object_id.startswith("subdivision:"):
            try:
                sub_id = int(object_id.split(":", 1)[1])
            except ValueError:
                continue
            object_conditions.append(
                or_(
                    InvMovementEvent.from_subdivision_id == sub_id,
                    InvMovementEvent.to_subdivision_id == sub_id,
                )
            )
            continue
    if object_conditions:
        query = query.filter(or_(*object_conditions))

    if q:
        stripped = q.strip()
        if stripped:
            term = f"%{stripped}%"
            query = query.filter(
                or_(
                    InvMovementEvent.item_code.ilike(term),
                    InvMovementEvent.item_name.ilike(term),
                    InvMovementEvent.comment.ilike(term),
                )
            )

    events = (
        query.order_by(InvMovementEvent.created_at.desc(), InvMovementEvent.id.desc())
        .limit(limit)
        .all()
    )
    if not events:
        return []

    actor_id_set = {event.actor_id for event in events if event.actor_id is not None}
    item_id_set = {event.item_id for event in events if event.item_id is not None}
    group_id_set = {event.group_id for event in events if event.group_id is not None}
    category_id_set = {event.category_id for event in events if event.category_id is not None}
    kind_id_set = {event.kind_id for event in events if event.kind_id is not None}
    restaurant_id_set = {
        rest_id
        for event in events
        for rest_id in [event.from_restaurant_id, event.to_restaurant_id]
        if rest_id is not None
    }
    subdivision_id_set = {
        sub_id
        for event in events
        for sub_id in [event.from_subdivision_id, event.to_subdivision_id]
        if sub_id is not None
    }
    storage_place_id_set = {
        place_id
        for event in events
        for place_id in [event.from_storage_place_id, event.to_storage_place_id]
        if place_id is not None
    }

    actor_map = _load_actor_name_map(db, {int(value) for value in actor_id_set})
    item_rows = (
        db.query(InvItem.id, InvItem.code, InvItem.name)
        .filter(InvItem.id.in_(item_id_set))
        .all()
        if item_id_set
        else []
    )
    item_map = {int(row.id): row for row in item_rows}

    group_map = {
        int(row.id): row.name
        for row in (
            db.query(InvGroup.id, InvGroup.name).filter(InvGroup.id.in_(group_id_set)).all()
            if group_id_set
            else []
        )
    }
    category_map = {
        int(row.id): row.name
        for row in (
            db.query(InvCategory.id, InvCategory.name).filter(InvCategory.id.in_(category_id_set)).all()
            if category_id_set
            else []
        )
    }
    kind_map = {
        int(row.id): row.name
        for row in (
            db.query(InvKind.id, InvKind.name).filter(InvKind.id.in_(kind_id_set)).all()
            if kind_id_set
            else []
        )
    }
    restaurant_names, storage_place_names, subdivision_names = _load_location_name_maps(
        db,
        restaurant_ids={int(value) for value in restaurant_id_set},
        storage_place_ids={int(value) for value in storage_place_id_set},
        subdivision_ids={int(value) for value in subdivision_id_set},
    )

    response: list[InvMovementEventRead] = []
    for event in events:
        item_row = item_map.get(event.item_id) if event.item_id is not None else None
        response.append(
            InvMovementEventRead(
                id=event.id,
                created_at=event.created_at,
                action_type=event.action_type,
                action_label=_movement_action_label(event.action_type),
                actor_id=event.actor_id,
                actor_name=actor_map.get(event.actor_id) if event.actor_id is not None else None,
                item_id=event.item_id,
                item_code=event.item_code or (item_row.code if item_row is not None else None),
                item_name=event.item_name or (item_row.name if item_row is not None else None),
                group_id=event.group_id,
                group_name=group_map.get(event.group_id) if event.group_id is not None else None,
                category_id=event.category_id,
                category_name=category_map.get(event.category_id) if event.category_id is not None else None,
                kind_id=event.kind_id,
                kind_name=kind_map.get(event.kind_id) if event.kind_id is not None else None,
                quantity=event.quantity,
                from_location_kind=event.from_location_kind,
                from_restaurant_id=event.from_restaurant_id,
                from_storage_place_id=event.from_storage_place_id,
                from_subdivision_id=event.from_subdivision_id,
                from_location_name=_location_name(
                    location_kind=event.from_location_kind,
                    restaurant_id=event.from_restaurant_id,
                    storage_place_id=event.from_storage_place_id,
                    subdivision_id=event.from_subdivision_id,
                    restaurant_names=restaurant_names,
                    storage_place_names=storage_place_names,
                    subdivision_names=subdivision_names,
                ),
                to_location_kind=event.to_location_kind,
                to_restaurant_id=event.to_restaurant_id,
                to_storage_place_id=event.to_storage_place_id,
                to_subdivision_id=event.to_subdivision_id,
                to_location_name=_location_name(
                    location_kind=event.to_location_kind,
                    restaurant_id=event.to_restaurant_id,
                    storage_place_id=event.to_storage_place_id,
                    subdivision_id=event.to_subdivision_id,
                    restaurant_names=restaurant_names,
                    storage_place_names=storage_place_names,
                    subdivision_names=subdivision_names,
                ),
                field=event.field,
                old_value=event.old_value,
                new_value=event.new_value,
                comment=event.comment,
            )
        )

    return response


def get_restaurant_item_card(
    *,
    db: Session,
    current_user: User,
    restaurant_id: int,
    item_id: int,
    storage_place_id: int | None = None,
) -> InventoryRestaurantItemCardRead:
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)

    item = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    normalized_storage_place_id = _resolve_storage_place(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id,
        storage_place_id=storage_place_id,
        require_active=False,
    )

    stock_row = (
        db.query(InvItemStock.quantity, InvItemStock.avg_cost)
        .filter(InvItemStock.restaurant_id == restaurant_id, InvItemStock.item_id == item_id)
        .first()
    )
    current_instances = (
        db.query(InvItemInstance)
        .filter(
            InvItemInstance.item_id == item_id,
            InvItemInstance.location_kind == "restaurant",
            InvItemInstance.restaurant_id == restaurant_id,
        )
        .filter(InvItemInstance.storage_place_id == normalized_storage_place_id if normalized_storage_place_id is not None else True)
        .order_by(InvItemInstance.sequence_no.asc())
        .all()
    )
    if stock_row is None and not current_instances:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item is not available in this restaurant")

    arrival_events = (
        db.query(InvMovementEvent)
        .filter(
            InvMovementEvent.item_id == item_id,
            InvMovementEvent.to_location_kind == "restaurant",
            InvMovementEvent.to_restaurant_id == restaurant_id,
            InvMovementEvent.action_type.in_(["quantity_increase", "transfer", "quantity_adjusted"]),
        )
        .filter(InvMovementEvent.to_storage_place_id == normalized_storage_place_id if normalized_storage_place_id is not None else True)
        .order_by(InvMovementEvent.created_at.desc(), InvMovementEvent.id.desc())
        .limit(60)
        .all()
    )

    instance_events: list[InvItemInstanceEvent] = []
    instance_event_type_map = _load_instance_event_type_map(db) if item.use_instance_codes else {}
    if item.use_instance_codes:
        instance_events = (
            db.query(InvItemInstanceEvent)
            .filter(
                InvItemInstanceEvent.item_id == item_id,
                InvItemInstanceEvent.instance_code_snapshot.isnot(None),
                _instance_event_matches_restaurant(restaurant_id),
            )
            .filter(_instance_event_matches_storage_place(normalized_storage_place_id) if normalized_storage_place_id is not None else True)
            .order_by(InvItemInstanceEvent.created_at.desc(), InvItemInstanceEvent.id.desc())
            .limit(800)
            .all()
        )

    actor_ids = {
        *{event.actor_id for event in arrival_events if event.actor_id is not None},
        *{event.actor_id for event in instance_events if event.actor_id is not None},
    }
    actor_map = _load_actor_name_map(db, {int(actor_id) for actor_id in actor_ids if actor_id is not None})

    restaurant_ids = {restaurant_id}
    storage_place_ids: set[int] = set()
    subdivision_ids: set[int] = set()
    for event in [*arrival_events, *instance_events]:
        if event.from_restaurant_id is not None:
            restaurant_ids.add(int(event.from_restaurant_id))
        if event.to_restaurant_id is not None:
            restaurant_ids.add(int(event.to_restaurant_id))
        if event.from_storage_place_id is not None:
            storage_place_ids.add(int(event.from_storage_place_id))
        if event.to_storage_place_id is not None:
            storage_place_ids.add(int(event.to_storage_place_id))
        if event.from_subdivision_id is not None:
            subdivision_ids.add(int(event.from_subdivision_id))
        if event.to_subdivision_id is not None:
            subdivision_ids.add(int(event.to_subdivision_id))

    restaurant_names, storage_place_names, subdivision_names = _load_location_name_maps(
        db,
        restaurant_ids=restaurant_ids,
        storage_place_ids=storage_place_ids,
        subdivision_ids=subdivision_ids,
    )

    arrivals = [
        InventoryRestaurantItemArrivalRead(
            id=event.id,
            created_at=event.created_at,
            action_type=event.action_type,
            action_label=_movement_action_label(event.action_type),
            actor_name=actor_map.get(event.actor_id) if event.actor_id is not None else None,
            quantity=int(event.quantity or 0),
            source_location_name=_location_name(
                location_kind=event.from_location_kind,
                restaurant_id=event.from_restaurant_id,
                storage_place_id=event.from_storage_place_id,
                subdivision_id=event.from_subdivision_id,
                restaurant_names=restaurant_names,
                storage_place_names=storage_place_names,
                subdivision_names=subdivision_names,
            ),
            target_location_name=_location_name(
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
        for event in arrival_events
    ]

    summary_map: dict[str, dict] = {}
    for instance in current_instances:
        code = instance.instance_code or f"{item.code}-{instance.sequence_no}"
        summary_map[code] = {
            "instance_id": instance.id,
            "instance_code": code,
            "sequence_no": instance.sequence_no,
            "purchase_cost": instance.purchase_cost,
            "arrived_at": instance.arrived_at,
            "is_current": True,
            "current_location_name": _location_name(
                location_kind="restaurant",
                restaurant_id=restaurant_id,
                storage_place_id=instance.storage_place_id,
                subdivision_id=None,
                restaurant_names=restaurant_names,
                storage_place_names=storage_place_names,
                subdivision_names=subdivision_names,
            ),
            "current_storage_place_id": instance.storage_place_id,
            "current_storage_place_name": storage_place_names.get(int(instance.storage_place_id)) if instance.storage_place_id is not None else None,
            "status_key": "in_stock",
            "status_label": "В ресторане",
            "last_event_at": None,
            "last_event_action": None,
            "last_event_label": None,
            "last_comment": None,
        }

    for event in instance_events:
        code = (event.instance_code_snapshot or "").strip()
        if not code:
            continue
        summary = summary_map.setdefault(
            code,
            {
                "instance_id": event.instance_id,
                "instance_code": code,
                "sequence_no": event.sequence_no,
                "purchase_cost": event.purchase_cost,
                "arrived_at": None,
                "is_current": False,
                "current_location_name": None,
                "status_key": "history",
                "status_label": "История",
                "last_event_at": None,
                "last_event_action": None,
                "last_event_label": None,
                "last_comment": None,
            },
        )
        if summary["last_event_at"] is None:
            summary["last_event_at"] = event.created_at
            summary["last_event_action"] = event.action_type
            summary["last_event_label"] = _instance_event_action_label(event.action_type, event_type_map=instance_event_type_map)
            summary["last_comment"] = event.comment
            if not summary["is_current"]:
                if event.action_type == "writeoff":
                    summary["status_key"] = "written_off"
                    summary["status_label"] = "Списан"
                elif event.action_type == "transfer" and event.from_restaurant_id == restaurant_id:
                    summary["status_key"] = "transferred_out"
                    summary["status_label"] = "Переведен"
                    summary["current_location_name"] = _location_name(
                        location_kind=event.to_location_kind,
                        restaurant_id=event.to_restaurant_id,
                        storage_place_id=event.to_storage_place_id,
                        subdivision_id=event.to_subdivision_id,
                        restaurant_names=restaurant_names,
                        storage_place_names=storage_place_names,
                        subdivision_names=subdivision_names,
                    )
                else:
                    summary["status_key"] = "history"
                    summary["status_label"] = _instance_event_action_label(event.action_type, event_type_map=instance_event_type_map)
        if summary["arrived_at"] is None and event.action_type in {"quantity_increase", "quantity_adjusted", "transfer"}:
            summary["arrived_at"] = event.created_at

    for summary in summary_map.values():
        if not summary["is_current"]:
            continue
        event_config = instance_event_type_map.get(str(summary["last_event_action"] or ""))
        status_key = _normalize_inventory_string(str(event_config.get("status_key") or "")) if event_config else None
        status_label = _normalize_inventory_string(str(event_config.get("status_label") or "")) if event_config else None
        if status_label:
            summary["status_key"] = status_key or "repair"
            summary["status_label"] = status_label
        else:
            summary["status_key"] = "in_stock"
            summary["status_label"] = "В ресторане"

    instances = [
        InventoryItemInstanceSummaryRead(**payload)
        for payload in sorted(
            summary_map.values(),
            key=lambda row: (0 if row["is_current"] else 1, str(row["instance_code"]).lower()),
        )
    ]

    return InventoryRestaurantItemCardRead(
        item_id=item_id,
        restaurant_id=restaurant_id,
        quantity=len(current_instances) if normalized_storage_place_id is not None else (int(stock_row.quantity or 0) if stock_row is not None else len(current_instances)),
        avg_cost=(
            (sum(Decimal(instance.purchase_cost or 0) for instance in current_instances) / Decimal(len(current_instances))).quantize(Decimal("0.01"))
            if current_instances and normalized_storage_place_id is not None
            else (stock_row.avg_cost if stock_row is not None else None)
        ),
        last_arrival_at=max((instance.arrived_at for instance in current_instances), default=None),
        storage_place_id=normalized_storage_place_id,
        instance_tracking_enabled=bool(item.use_instance_codes),
        arrivals=arrivals,
        instances=instances,
    )


def list_restaurant_item_instance_events(
    *,
    db: Session,
    current_user: User,
    restaurant_id: int,
    item_id: int,
    instance_code: str,
    storage_place_id: int | None = None,
) -> list[InventoryItemInstanceEventRead]:
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)

    item = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    normalized_storage_place_id = _resolve_storage_place(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id,
        storage_place_id=storage_place_id,
        require_active=False,
    )

    normalized_code = instance_code.strip()
    if not normalized_code:
        return []

    events = (
        db.query(InvItemInstanceEvent)
        .filter(
            InvItemInstanceEvent.item_id == item_id,
            InvItemInstanceEvent.instance_code_snapshot == normalized_code,
            _instance_event_matches_restaurant(restaurant_id),
        )
        .filter(_instance_event_matches_storage_place(normalized_storage_place_id) if normalized_storage_place_id is not None else True)
        .order_by(InvItemInstanceEvent.created_at.desc(), InvItemInstanceEvent.id.desc())
        .limit(200)
        .all()
    )
    if not events:
        return []
    instance_event_type_map = _load_instance_event_type_map(db)

    actor_map = _load_actor_name_map(db, {int(event.actor_id) for event in events if event.actor_id is not None})
    restaurant_ids = {
        int(rest_id)
        for event in events
        for rest_id in [event.from_restaurant_id, event.to_restaurant_id]
        if rest_id is not None
    }
    restaurant_ids.add(restaurant_id)
    subdivision_ids = {
        int(sub_id)
        for event in events
        for sub_id in [event.from_subdivision_id, event.to_subdivision_id]
        if sub_id is not None
    }
    storage_place_ids = {
        int(place_id)
        for event in events
        for place_id in [event.from_storage_place_id, event.to_storage_place_id]
        if place_id is not None
    }
    restaurant_names, storage_place_names, subdivision_names = _load_location_name_maps(
        db,
        restaurant_ids=restaurant_ids,
        storage_place_ids=storage_place_ids,
        subdivision_ids=subdivision_ids,
    )
    return [
        serialize_inventory_instance_event(
            event,
            actor_map=actor_map,
            restaurant_names=restaurant_names,
            storage_place_names=storage_place_names,
            subdivision_names=subdivision_names,
            event_type_map=instance_event_type_map,
        )
        for event in events
    ]
