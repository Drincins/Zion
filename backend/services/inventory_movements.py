from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.bd.models import (
    InvItem,
    InvItemInstance,
    RestaurantSubdivision,
    User,
)
from backend.schemas import (
    InvItemAllocateCreate,
    InvItemAllocateRead,
    InvItemQuantityUpdate,
    InvItemQuantityUpdateRead,
    InvItemTransferCreate,
    InvItemTransferRead,
)
from backend.services.inventory_domain import (
    _build_instance_codes_response,
    _create_item_instances,
    _ensure_restaurant_allowed,
    _log_item_instance_events,
    _log_movement_event,
    _resolve_instance_code_for_location,
    _resolve_location,
    _resolve_storage_place,
    _update_stock,
)
from backend.utils import get_user_restaurant_ids


def transfer_item(
    *,
    db: Session,
    current_user: User,
    item_id: int,
    payload: InvItemTransferCreate,
) -> InvItemTransferRead:
    if payload.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be greater than zero")

    item = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    source_kind = payload.source_kind or "warehouse"
    source_restaurant_id: int | None = None
    source_storage_place_id: int | None = None
    source_subdivision_id: int | None = None
    if source_kind == "restaurant":
        if payload.source_restaurant_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_restaurant_id is required for source_kind=restaurant")
        allowed_restaurants = get_user_restaurant_ids(db, current_user)
        _ensure_restaurant_allowed(allowed_restaurants, int(payload.source_restaurant_id))
        source_restaurant_id = int(payload.source_restaurant_id)
        source_storage_place_id = _resolve_storage_place(
            db=db,
            current_user=current_user,
            restaurant_id=source_restaurant_id,
            storage_place_id=payload.source_storage_place_id,
            field_label="source_storage_place_id",
        )
    elif source_kind == "subdivision":
        if payload.source_subdivision_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_subdivision_id is required for source_kind=subdivision")
        subdivision_exists = (
            db.query(RestaurantSubdivision.id)
            .filter(RestaurantSubdivision.id == int(payload.source_subdivision_id))
            .first()
        )
        if not subdivision_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source subdivision not found")
        source_subdivision_id = int(payload.source_subdivision_id)
    elif source_kind != "warehouse":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported source_kind")

    target_restaurant_id: int | None = None
    target_storage_place_id: int | None = None
    target_subdivision_id: int | None = None
    if payload.target_kind == "restaurant":
        if payload.restaurant_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="restaurant_id is required for restaurant transfer")
        allowed_restaurants = get_user_restaurant_ids(db, current_user)
        _ensure_restaurant_allowed(allowed_restaurants, int(payload.restaurant_id))
        target_restaurant_id = int(payload.restaurant_id)
        target_storage_place_id = _resolve_storage_place(
            db=db,
            current_user=current_user,
            restaurant_id=target_restaurant_id,
            storage_place_id=payload.storage_place_id,
            field_label="storage_place_id",
        )
    elif payload.target_kind == "subdivision":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer to subdivision is not supported. Use restaurant or warehouse.",
        )
    elif payload.target_kind != "warehouse":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported target_kind")

    if (
        source_kind == payload.target_kind
        and source_restaurant_id == target_restaurant_id
        and source_storage_place_id == target_storage_place_id
        and source_subdivision_id == target_subdivision_id
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source and target locations are the same")

    source_filters = [
        InvItemInstance.item_id == item_id,
        InvItemInstance.location_kind == source_kind,
    ]
    if source_kind == "restaurant":
        source_filters.append(InvItemInstance.restaurant_id == source_restaurant_id)
        if source_storage_place_id is None:
            source_filters.append(InvItemInstance.storage_place_id.is_(None))
        else:
            source_filters.append(InvItemInstance.storage_place_id == source_storage_place_id)
    elif source_kind == "subdivision":
        source_filters.append(InvItemInstance.subdivision_id == source_subdivision_id)

    instances = (
        db.query(InvItemInstance)
        .filter(*source_filters)
        .order_by(InvItemInstance.sequence_no.asc())
        .with_for_update()
        .limit(payload.quantity)
        .all()
    )
    if len(instances) < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough quantity in source location",
        )

    transfer_arrival_at = datetime.utcnow()
    for instance in instances:
        instance.location_kind = payload.target_kind
        instance.restaurant_id = target_restaurant_id if payload.target_kind == "restaurant" else None
        instance.storage_place_id = target_storage_place_id if payload.target_kind == "restaurant" else None
        instance.subdivision_id = target_subdivision_id if payload.target_kind == "subdivision" else None
        instance.arrived_at = transfer_arrival_at
        instance.instance_code = _resolve_instance_code_for_location(
            item=item,
            sequence_no=instance.sequence_no,
            location_kind=instance.location_kind,
            restaurant_id=instance.restaurant_id,
        )

    _log_movement_event(
        db,
        action_type="transfer",
        actor_id=current_user.id,
        item=item,
        quantity=len(instances),
        from_location_kind=source_kind,
        from_restaurant_id=source_restaurant_id,
        from_storage_place_id=source_storage_place_id,
        from_subdivision_id=source_subdivision_id,
        to_location_kind=payload.target_kind,
        to_restaurant_id=target_restaurant_id,
        to_storage_place_id=target_storage_place_id,
        to_subdivision_id=target_subdivision_id,
        comment=payload.comment or "Перевод товара между подразделениями",
    )
    _log_item_instance_events(
        db,
        instances=instances,
        action_type="transfer",
        actor_id=current_user.id,
        item=item,
        from_location_kind=source_kind,
        from_restaurant_id=source_restaurant_id,
        from_storage_place_id=source_storage_place_id,
        from_subdivision_id=source_subdivision_id,
        to_location_kind=payload.target_kind,
        to_restaurant_id=target_restaurant_id,
        to_storage_place_id=target_storage_place_id,
        to_subdivision_id=target_subdivision_id,
        comment=payload.comment or "Перевод товара между подразделениями",
    )

    db.commit()
    return InvItemTransferRead(
        item_id=item_id,
        moved=len(instances),
        source_kind=source_kind,
        source_restaurant_id=source_restaurant_id,
        source_storage_place_id=source_storage_place_id,
        source_subdivision_id=source_subdivision_id,
        target_kind=payload.target_kind,
        restaurant_id=target_restaurant_id,
        storage_place_id=target_storage_place_id,
        subdivision_id=target_subdivision_id,
        instance_codes=_build_instance_codes_response(item, instances),
    )


def allocate_item(
    *,
    db: Session,
    current_user: User,
    item_id: int,
    payload: InvItemAllocateCreate,
) -> InvItemAllocateRead:
    item = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    restaurant_id, subdivision_id = _resolve_location(
        db=db,
        current_user=current_user,
        location_kind=payload.location_kind,
        restaurant_id=payload.restaurant_id,
        subdivision_id=payload.subdivision_id,
        restaurant_required=True,
        subdivision_required=True,
    )
    storage_place_id = _resolve_storage_place(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id if payload.location_kind == "restaurant" else None,
        storage_place_id=payload.storage_place_id,
    )

    base_cost = item.default_cost if item.default_cost is not None else item.cost
    unit_cost = payload.unit_cost if payload.unit_cost is not None else base_cost
    unit_cost_decimal = Decimal(unit_cost if unit_cost is not None else 0)

    created = _create_item_instances(
        db,
        item=item,
        quantity=payload.quantity,
        location_kind=payload.location_kind,
        unit_cost=unit_cost_decimal,
        restaurant_id=restaurant_id,
        storage_place_id=storage_place_id,
        subdivision_id=subdivision_id,
    )
    if payload.location_kind == "restaurant" and restaurant_id is not None:
        _update_stock(
            db,
            restaurant_id=restaurant_id,
            item=item,
            delta_qty=payload.quantity,
            cost=unit_cost_decimal,
        )

    _log_movement_event(
        db,
        action_type="quantity_increase",
        actor_id=current_user.id,
        item=item,
        quantity=payload.quantity,
        to_location_kind=payload.location_kind,
        to_restaurant_id=restaurant_id,
        to_storage_place_id=storage_place_id,
        to_subdivision_id=subdivision_id,
        comment=payload.comment or "Добавление партии товара из каталога",
    )
    _log_item_instance_events(
        db,
        instances=created,
        action_type="quantity_increase",
        actor_id=current_user.id,
        item=item,
        to_location_kind=payload.location_kind,
        to_restaurant_id=restaurant_id,
        to_storage_place_id=storage_place_id,
        to_subdivision_id=subdivision_id,
        comment=payload.comment or "Добавление партии товара из каталога",
    )
    if payload.unit_cost is not None and base_cost is not None and Decimal(base_cost) != unit_cost_decimal:
        _log_movement_event(
            db,
            action_type="cost_changed",
            actor_id=current_user.id,
            item=item,
            field="batch_unit_cost",
            old_value=str(base_cost),
            new_value=str(unit_cost_decimal),
            to_location_kind=payload.location_kind,
            to_restaurant_id=restaurant_id,
            to_storage_place_id=storage_place_id,
            to_subdivision_id=subdivision_id,
            comment="Стоимость партии отличается от каталожной",
        )

    db.commit()

    return InvItemAllocateRead(
        item_id=item_id,
        location_kind=payload.location_kind,
        restaurant_id=restaurant_id,
        storage_place_id=storage_place_id,
        subdivision_id=subdivision_id,
        added=len(created),
        unit_cost=unit_cost_decimal,
        instance_codes=_build_instance_codes_response(item, created),
    )


def update_item_quantity(
    *,
    db: Session,
    current_user: User,
    item_id: int,
    payload: InvItemQuantityUpdate,
) -> InvItemQuantityUpdateRead:
    item = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    restaurant_id, subdivision_id = _resolve_location(
        db=db,
        current_user=current_user,
        location_kind=payload.location_kind,
        restaurant_id=payload.restaurant_id,
        subdivision_id=payload.subdivision_id,
        restaurant_required=True,
        subdivision_required=True,
    )
    storage_place_id = _resolve_storage_place(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id if payload.location_kind == "restaurant" else None,
        storage_place_id=payload.storage_place_id,
    )

    location_filters = [
        InvItemInstance.item_id == item_id,
        InvItemInstance.location_kind == payload.location_kind,
    ]
    if payload.location_kind == "restaurant":
        location_filters.append(InvItemInstance.restaurant_id == restaurant_id)
        if storage_place_id is None:
            location_filters.append(InvItemInstance.storage_place_id.is_(None))
        else:
            location_filters.append(InvItemInstance.storage_place_id == storage_place_id)
    elif payload.location_kind == "subdivision":
        location_filters.append(InvItemInstance.subdivision_id == subdivision_id)

    instances = (
        db.query(InvItemInstance)
        .filter(*location_filters)
        .order_by(InvItemInstance.sequence_no.asc())
        .with_for_update()
        .all()
    )
    previous_quantity = len(instances)
    target_quantity = int(payload.quantity)
    delta = target_quantity - previous_quantity
    base_cost = item.default_cost if item.default_cost is not None else item.cost
    unit_cost_decimal = Decimal(payload.unit_cost if payload.unit_cost is not None else (base_cost if base_cost is not None else 0))

    if delta > 0:
        created_instances = _create_item_instances(
            db,
            item=item,
            quantity=delta,
            location_kind=payload.location_kind,
            unit_cost=unit_cost_decimal,
            restaurant_id=restaurant_id,
            storage_place_id=storage_place_id,
            subdivision_id=subdivision_id,
        )
        if payload.location_kind == "restaurant" and restaurant_id is not None:
            _update_stock(
                db,
                restaurant_id=restaurant_id,
                item=item,
                delta_qty=delta,
                cost=unit_cost_decimal,
            )
        _log_movement_event(
            db,
            action_type="quantity_adjusted",
            actor_id=current_user.id,
            item=item,
            quantity=delta,
            to_location_kind=payload.location_kind,
            to_restaurant_id=restaurant_id,
            to_storage_place_id=storage_place_id,
            to_subdivision_id=subdivision_id,
            field="quantity",
            old_value=str(previous_quantity),
            new_value=str(target_quantity),
            comment=payload.comment or "Изменение количества",
        )
        _log_item_instance_events(
            db,
            instances=created_instances,
            action_type="quantity_adjusted",
            actor_id=current_user.id,
            item=item,
            to_location_kind=payload.location_kind,
            to_restaurant_id=restaurant_id,
            to_storage_place_id=storage_place_id,
            to_subdivision_id=subdivision_id,
            comment=payload.comment or "Изменение количества",
        )
    elif delta < 0:
        remove_count = abs(delta)
        removing = instances[:remove_count]
        _log_item_instance_events(
            db,
            instances=removing,
            action_type="writeoff",
            actor_id=current_user.id,
            item=item,
            from_location_kind=payload.location_kind,
            from_restaurant_id=restaurant_id,
            from_storage_place_id=storage_place_id,
            from_subdivision_id=subdivision_id,
            comment=payload.comment or "Списание товара",
        )
        for instance in removing:
            db.delete(instance)
        if payload.location_kind == "restaurant" and restaurant_id is not None:
            _update_stock(
                db,
                restaurant_id=restaurant_id,
                item=item,
                delta_qty=-remove_count,
                cost=unit_cost_decimal,
            )
        _log_movement_event(
            db,
            action_type="writeoff",
            actor_id=current_user.id,
            item=item,
            quantity=remove_count,
            from_location_kind=payload.location_kind,
            from_restaurant_id=restaurant_id,
            from_storage_place_id=storage_place_id,
            from_subdivision_id=subdivision_id,
            field="quantity",
            old_value=str(previous_quantity),
            new_value=str(target_quantity),
            comment=payload.comment or "Списание товара",
        )
    if delta > 0 and payload.unit_cost is not None and base_cost is not None and Decimal(base_cost) != unit_cost_decimal:
        _log_movement_event(
            db,
            action_type="cost_changed",
            actor_id=current_user.id,
            item=item,
            field="batch_unit_cost",
            old_value=str(base_cost),
            new_value=str(unit_cost_decimal),
            to_location_kind=payload.location_kind,
            to_restaurant_id=restaurant_id,
            to_storage_place_id=storage_place_id,
            to_subdivision_id=subdivision_id,
            comment="Стоимость добавленной партии отличается от каталожной",
        )
    db.commit()

    return InvItemQuantityUpdateRead(
        item_id=item_id,
        location_kind=payload.location_kind,
        restaurant_id=restaurant_id,
        storage_place_id=storage_place_id,
        subdivision_id=subdivision_id,
        previous_quantity=previous_quantity,
        quantity=target_quantity,
        delta=delta,
    )
