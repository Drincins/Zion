from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.bd.models import (
    InvCategory,
    InvGroup,
    InvKind,
    InvItem,
    InvMovementEvent,
    User,
)
from backend.schemas import InvMovementEventRead
from backend.services.inventory_serializers import (
    _combine_int_filters,
    _combine_str_filters,
    _event_matches_allowed_restaurants,
    _load_actor_name_map,
    _load_location_name_maps,
    _location_name,
    _movement_action_label,
)
from backend.utils import get_user_restaurant_ids


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
