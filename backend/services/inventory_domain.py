from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.bd.models import (
    InvCategory,
    InvItem,
    InvItemChange,
    InvItemInstance,
    InvItemInstanceEvent,
    InvItemStock,
    InvKind,
    InvMovementEvent,
    InvStoragePlace,
    RestaurantSubdivision,
    User,
)
from backend.utils import get_user_restaurant_ids

INVENTORY_PHOTO_PREFIX = (
    os.getenv("INVENTORY_PHOTO_PREFIX")
    or os.getenv("TG_BOT_S3_PREFIX")
    or "inventory_bot"
).strip("/") or "inventory_bot"


def _build_inventory_photo_key(filename: str | None) -> str:
    base, ext = os.path.splitext(filename or "photo")
    safe_base = base.replace("/", "_") or "photo"
    safe_ext = ext if ext else ".jpg"
    return f"{INVENTORY_PHOTO_PREFIX}/{safe_base}_{uuid4().hex}{safe_ext}"


def _generate_item_code(db: Session) -> str:
    max_id = db.query(func.max(InvItem.id)).scalar() or 0
    return f"ITEM-{max_id + 1:06d}"


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


def _sync_item_instance_codes(db: Session, *, item: InvItem) -> None:
    instances = (
        db.query(InvItemInstance)
        .filter(InvItemInstance.item_id == item.id)
        .order_by(InvItemInstance.sequence_no.asc())
        .with_for_update()
        .all()
    )
    for instance in instances:
        instance.instance_code = _resolve_instance_code_for_location(
            item=item,
            sequence_no=instance.sequence_no,
            location_kind=instance.location_kind,
            restaurant_id=instance.restaurant_id,
        )


def _resolve_kind_for_item(
    db: Session,
    *,
    group_id: int,
    category_id: int,
    kind_id: int | None,
) -> InvKind:
    category = (
        db.query(InvCategory)
        .filter(InvCategory.id == category_id, InvCategory.group_id == group_id)
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category does not belong to selected group",
        )

    if kind_id is not None:
        kind = (
            db.query(InvKind)
            .filter(
                InvKind.id == kind_id,
                InvKind.category_id == category_id,
                InvKind.group_id == group_id,
            )
            .first()
        )
        if not kind:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kind does not belong to selected category",
            )
        return kind

    kind = (
        db.query(InvKind)
        .filter(
            InvKind.category_id == category_id,
            InvKind.group_id == group_id,
            InvKind.name == "Прочее",
        )
        .first()
    )
    if kind:
        return kind

    kind = InvKind(name="Прочее", category_id=category_id, group_id=group_id)
    db.add(kind)
    db.flush()
    return kind


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


def _log_item_change(
    db: Session,
    *,
    item_id: int,
    field: str,
    old_value,
    new_value,
    user_id: int | None,
) -> None:
    if (old_value or "") == (new_value or ""):
        return
    db.add(
        InvItemChange(
            item_id=item_id,
            field=field,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by=user_id,
        )
    )


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
