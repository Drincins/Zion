from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.bd.models import (
    InvItem,
    InvItemInstance,
    InvItemInstanceEvent,
    InvItemStock,
    InvMovementEvent,
    User,
)
from backend.schemas import (
    InventoryItemInstanceEventRead,
    InventoryItemInstanceSummaryRead,
    InventoryRestaurantItemArrivalRead,
    InventoryRestaurantItemCardRead,
)
from backend.services.inventory_domain import _ensure_restaurant_allowed, _resolve_storage_place
from backend.services.inventory_serializers import (
    _instance_event_action_label,
    _instance_event_matches_restaurant,
    _instance_event_matches_storage_place,
    _load_actor_name_map,
    _load_instance_event_type_map,
    _load_location_name_maps,
    _location_name,
    _movement_action_label,
    _normalize_inventory_string,
    _serialize_instance_event as serialize_inventory_instance_event,
)
from backend.utils import get_user_restaurant_ids


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
