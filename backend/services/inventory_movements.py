from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.bd.models import (
    InvItem,
    InvItemInstance,
    InvItemInstanceEvent,
    InvItemStock,
    InvMovementEvent,
    InvStoragePlace,
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
from backend.utils import get_user_restaurant_ids


def _build_instance_code(item_code: str, sequence_no: int) -> str:
    return f"{item_code}-{sequence_no}"


def _resolve_instance_code_for_location(
    *,
    item: InvItem,
    sequence_no: int,
    location_kind: str,
    restaurant_id: int | None,
) -> str | None:
    if item.use_instance_codes:
        return _build_instance_code(item.code, sequence_no)
    return None


def _build_instance_codes_response(item: InvItem, instances: list[InvItemInstance]) -> list[str]:
    if not instances:
        return []
    if item.use_instance_codes:
        return [instance.instance_code for instance in instances if instance.instance_code]
    return [item.code]


def _next_item_instance_sequence(db: Session, item_id: int) -> int:
    return int(db.query(func.max(InvItemInstance.sequence_no)).filter(InvItemInstance.item_id == item_id).scalar() or 0)


def _create_item_instances(
    db: Session,
    *,
    item: InvItem,
    quantity: int,
    location_kind: str,
    unit_cost: Decimal | None = None,
    restaurant_id: int | None = None,
    storage_place_id: int | None = None,
    subdivision_id: int | None = None,
) -> list[InvItemInstance]:
    if quantity <= 0:
        return []
    start_seq = _next_item_instance_sequence(db, item.id)
    arrival_ts = datetime.utcnow()
    created: list[InvItemInstance] = []
    for offset in range(1, quantity + 1):
        sequence_no = start_seq + offset
        instance = InvItemInstance(
            item_id=item.id,
            sequence_no=sequence_no,
            instance_code=_resolve_instance_code_for_location(
                item=item,
                sequence_no=sequence_no,
                location_kind=location_kind,
                restaurant_id=restaurant_id,
            ),
            purchase_cost=unit_cost if unit_cost is not None else (item.default_cost if item.default_cost is not None else item.cost),
            location_kind=location_kind,
            restaurant_id=restaurant_id,
            storage_place_id=storage_place_id,
            subdivision_id=subdivision_id,
            arrived_at=arrival_ts,
        )
        db.add(instance)
        created.append(instance)
    db.flush()
    return created


def _update_stock(db: Session, *, restaurant_id: int, item: InvItem, delta_qty: int, cost: Decimal) -> None:
    stock = (
        db.query(InvItemStock)
        .filter(InvItemStock.restaurant_id == restaurant_id, InvItemStock.item_id == item.id)
        .with_for_update()
        .first()
    )
    if not stock:
        stock = InvItemStock(
            restaurant_id=restaurant_id,
            item_id=item.id,
            quantity=0,
            avg_cost=item.default_cost if item.default_cost is not None else item.cost,
        )
        db.add(stock)
        db.flush()

    current_qty = int(stock.quantity or 0)
    current_avg = Decimal(stock.avg_cost or 0)
    total_cost = current_avg * current_qty
    delta_dec = Decimal(delta_qty)

    if delta_qty >= 0:
        total_cost += delta_dec * cost
    else:
        total_cost += delta_dec * current_avg

    new_qty = current_qty + delta_qty
    if new_qty <= 0:
        stock.quantity = 0
    else:
        stock.quantity = new_qty
        try:
            stock.avg_cost = (total_cost / Decimal(new_qty)).quantize(Decimal("0.01"))
        except Exception:
            stock.avg_cost = total_cost / Decimal(new_qty)
    stock.updated_at = datetime.utcnow()


def _ensure_restaurant_allowed(allowed: Optional[set[int]], restaurant_id: int) -> None:
    if allowed is None:
        return
    if restaurant_id in allowed:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to this restaurant is not allowed")


def _resolve_storage_place(
    *,
    db: Session,
    current_user: User,
    restaurant_id: int | None,
    storage_place_id: int | None,
    field_label: str = "storage_place_id",
    require_active: bool = True,
) -> int | None:
    if storage_place_id is None:
        return None
    if restaurant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_label} can be used only with restaurant location",
        )
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, int(restaurant_id))
    query = db.query(InvStoragePlace).filter(InvStoragePlace.id == int(storage_place_id))
    if require_active:
        query = query.filter(InvStoragePlace.is_active.is_(True))
    row = query.first()
    if not row or row.scope_kind != "restaurant" or int(row.restaurant_id or 0) != int(restaurant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_label} does not belong to selected restaurant",
        )
    return int(row.id)


def _resolve_location(
    *,
    db: Session,
    current_user: User,
    location_kind: str,
    restaurant_id: int | None,
    subdivision_id: int | None,
    restaurant_required: bool,
    subdivision_required: bool,
    restaurant_field_label: str = "restaurant_id",
    subdivision_field_label: str = "subdivision_id",
) -> tuple[int | None, int | None]:
    resolved_restaurant_id: int | None = None
    resolved_subdivision_id: int | None = None
    if location_kind == "restaurant":
        if restaurant_required and restaurant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{restaurant_field_label} is required for location_kind=restaurant",
            )
        if restaurant_id is not None:
            resolved_restaurant_id = int(restaurant_id)
            allowed_restaurants = get_user_restaurant_ids(db, current_user)
            _ensure_restaurant_allowed(allowed_restaurants, resolved_restaurant_id)
    elif location_kind == "subdivision":
        if subdivision_required and subdivision_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{subdivision_field_label} is required for location_kind=subdivision",
            )
        if subdivision_id is not None:
            resolved_subdivision_id = int(subdivision_id)
            subdivision_exists = (
                db.query(RestaurantSubdivision.id)
                .filter(RestaurantSubdivision.id == resolved_subdivision_id)
                .first()
            )
            if not subdivision_exists:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subdivision not found")
    elif location_kind != "warehouse":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported location_kind")
    return resolved_restaurant_id, resolved_subdivision_id


def _log_item_instance_events(
    db: Session,
    *,
    instances: list[InvItemInstance],
    action_type: str,
    actor_id: int | None = None,
    item: InvItem,
    from_location_kind: str | None = None,
    from_restaurant_id: int | None = None,
    from_storage_place_id: int | None = None,
    from_subdivision_id: int | None = None,
    to_location_kind: str | None = None,
    to_restaurant_id: int | None = None,
    to_storage_place_id: int | None = None,
    to_subdivision_id: int | None = None,
    comment: str | None = None,
) -> None:
    for instance in instances:
        db.add(
            InvItemInstanceEvent(
                action_type=action_type,
                actor_id=actor_id,
                item_id=item.id,
                instance_id=instance.id,
                sequence_no=instance.sequence_no,
                instance_code_snapshot=instance.instance_code,
                purchase_cost=instance.purchase_cost,
                from_location_kind=from_location_kind,
                from_restaurant_id=from_restaurant_id,
                from_storage_place_id=from_storage_place_id,
                from_subdivision_id=from_subdivision_id,
                to_location_kind=to_location_kind,
                to_restaurant_id=to_restaurant_id,
                to_storage_place_id=to_storage_place_id,
                to_subdivision_id=to_subdivision_id,
                comment=comment,
            )
        )


def _log_movement_event(
    db: Session,
    *,
    action_type: str,
    actor_id: int | None = None,
    item: InvItem | None = None,
    item_id: int | None = None,
    item_code: str | None = None,
    item_name: str | None = None,
    group_id: int | None = None,
    category_id: int | None = None,
    kind_id: int | None = None,
    quantity: int | None = None,
    from_location_kind: str | None = None,
    from_restaurant_id: int | None = None,
    from_storage_place_id: int | None = None,
    from_subdivision_id: int | None = None,
    to_location_kind: str | None = None,
    to_restaurant_id: int | None = None,
    to_storage_place_id: int | None = None,
    to_subdivision_id: int | None = None,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    comment: str | None = None,
) -> None:
    if item is not None:
        item_id = item.id
        item_code = item.code
        item_name = item.name
        group_id = item.group_id
        category_id = item.category_id
        kind_id = item.kind_id

    db.add(
        InvMovementEvent(
            action_type=action_type,
            actor_id=actor_id,
            item_id=item_id,
            item_code=item_code,
            item_name=item_name,
            group_id=group_id,
            category_id=category_id,
            kind_id=kind_id,
            quantity=quantity,
            from_location_kind=from_location_kind,
            from_restaurant_id=from_restaurant_id,
            from_storage_place_id=from_storage_place_id,
            from_subdivision_id=from_subdivision_id,
            to_location_kind=to_location_kind,
            to_restaurant_id=to_restaurant_id,
            to_storage_place_id=to_storage_place_id,
            to_subdivision_id=to_subdivision_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            comment=comment,
        )
    )


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
