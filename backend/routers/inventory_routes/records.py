from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.routers.inventory_routes.common import (
    Decimal,
    InvItem,
    InvItemRecord,
    InvItemRecordCreate,
    InvItemRecordRead,
    InvItemRecordUpdate,
    Optional,
    Session,
    User,
    datetime,
    get_current_user,
    get_db,
    get_user_restaurant_ids,
    _ensure_inventory_movements_create,
    _ensure_inventory_movements_delete,
    _ensure_inventory_movements_edit,
    _ensure_inventory_movements_view,
    _ensure_restaurant_allowed,
    _log_movement_event,
    _record_schema,
    _update_stock,
)

router = APIRouter()


@router.get("/records", response_model=list[InvItemRecordRead])
def list_records(
    restaurant_id: Optional[int] = Query(None),
    item_id: Optional[int] = Query(None),
    group_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvItemRecord]:
    _ensure_inventory_movements_view(current_user)
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    query = db.query(InvItemRecord)
    if restaurant_id is not None:
        _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)
        query = query.filter(InvItemRecord.restaurant_id == restaurant_id)
    elif allowed_restaurants is not None:
        if not allowed_restaurants:
            return []
        query = query.filter(InvItemRecord.restaurant_id.in_(allowed_restaurants))
    if item_id is not None:
        query = query.filter(InvItemRecord.item_id == item_id)
    if group_id is not None:
        query = query.filter(InvItemRecord.group_id == group_id)
    if category_id is not None:
        query = query.filter(InvItemRecord.category_id == category_id)
    if created_from is not None:
        query = query.filter(InvItemRecord.created_at >= created_from)
    if created_to is not None:
        query = query.filter(InvItemRecord.created_at <= created_to)
    records = query.order_by(InvItemRecord.created_at.desc()).all()
    return [_record_schema(record) for record in records]


@router.post("/records", response_model=InvItemRecordRead, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: InvItemRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemRecord:
    _ensure_inventory_movements_create(current_user)
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, payload.restaurant_id)
    item = db.query(InvItem).filter(InvItem.id == payload.item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    cost_value = payload.cost
    if cost_value is None:
        cost_value = item.default_cost if item.default_cost is not None else item.cost
    if cost_value is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cost is required for this item")
    obj = InvItemRecord(
        item_id=payload.item_id,
        category_id=payload.category_id,
        group_id=payload.group_id,
        restaurant_id=payload.restaurant_id,
        user_id=payload.user_id,
        quantity=payload.quantity,
        cost=cost_value,
        comment=payload.comment,
        photo_url=payload.photo_url,
    )
    _update_stock(
        db,
        restaurant_id=payload.restaurant_id,
        item=item,
        delta_qty=payload.quantity,
        cost=Decimal(cost_value),
    )
    action_type = "record_created"
    from_location_kind: str | None = None
    to_location_kind: str | None = None
    from_restaurant_id: int | None = None
    to_restaurant_id: int | None = None
    if payload.quantity > 0:
        action_type = "quantity_increase"
        to_location_kind = "restaurant"
        to_restaurant_id = payload.restaurant_id
    elif payload.quantity < 0:
        action_type = "writeoff"
        from_location_kind = "restaurant"
        from_restaurant_id = payload.restaurant_id

    _log_movement_event(
        db,
        action_type=action_type,
        actor_id=current_user.id,
        item=item,
        quantity=payload.quantity,
        from_location_kind=from_location_kind,
        from_restaurant_id=from_restaurant_id,
        to_location_kind=to_location_kind,
        to_restaurant_id=to_restaurant_id,
        comment=payload.comment,
    )
    db.add(obj)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(obj)
    return _record_schema(obj)


@router.put("/records/{record_id}", response_model=InvItemRecordRead)
def update_record(
    record_id: int,
    payload: InvItemRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemRecord:
    _ensure_inventory_movements_edit(current_user)
    obj = db.query(InvItemRecord).filter(InvItemRecord.id == record_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    old_restaurant_id = obj.restaurant_id
    old_item_id = obj.item_id
    old_quantity = obj.quantity
    old_cost = Decimal(obj.cost)
    old_comment = obj.comment
    old_photo_url = obj.photo_url
    old_user_id = obj.user_id

    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, obj.restaurant_id)

    if payload.item_id is not None:
        new_item = db.query(InvItem).filter(InvItem.id == payload.item_id).first()
        if not new_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        obj.item_id = payload.item_id
    if payload.category_id is not None:
        obj.category_id = payload.category_id
    if payload.group_id is not None:
        obj.group_id = payload.group_id
    if payload.restaurant_id is not None:
        _ensure_restaurant_allowed(allowed_restaurants, payload.restaurant_id)
        obj.restaurant_id = payload.restaurant_id
    if payload.user_id is not None:
        obj.user_id = payload.user_id
    if payload.quantity is not None:
        obj.quantity = payload.quantity
    if payload.cost is not None:
        obj.cost = payload.cost
    if payload.comment is not None:
        obj.comment = payload.comment
    if payload.photo_url is not None:
        obj.photo_url = payload.photo_url

    new_item = db.query(InvItem).filter(InvItem.id == obj.item_id).first()
    if not new_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    new_restaurant_id = obj.restaurant_id
    new_quantity = obj.quantity
    new_cost = Decimal(obj.cost)

    if old_restaurant_id != new_restaurant_id or old_item_id != obj.item_id:
        old_item = db.query(InvItem).filter(InvItem.id == old_item_id).first()
        if old_item:
            _update_stock(
                db,
                restaurant_id=old_restaurant_id,
                item=old_item,
                delta_qty=-old_quantity,
                cost=old_cost,
            )
        _update_stock(
            db,
            restaurant_id=new_restaurant_id,
            item=new_item,
            delta_qty=new_quantity,
            cost=new_cost,
        )
    else:
        delta_qty = new_quantity - old_quantity
        if delta_qty != 0:
            _update_stock(
                db,
                restaurant_id=new_restaurant_id,
                item=new_item,
                delta_qty=delta_qty,
                cost=new_cost,
            )

    if old_restaurant_id != new_restaurant_id or old_quantity != new_quantity or old_item_id != obj.item_id:
        _log_movement_event(
            db,
            action_type="quantity_adjusted",
            actor_id=current_user.id,
            item=new_item,
            quantity=new_quantity - old_quantity,
            from_location_kind="restaurant",
            from_restaurant_id=old_restaurant_id,
            to_location_kind="restaurant",
            to_restaurant_id=new_restaurant_id,
            field="quantity",
            old_value=str(old_quantity),
            new_value=str(new_quantity),
            comment=obj.comment,
        )
    if old_cost != new_cost:
        _log_movement_event(
            db,
            action_type="cost_changed",
            actor_id=current_user.id,
            item=new_item,
            field="cost",
            old_value=str(old_cost),
            new_value=str(new_cost),
            comment=obj.comment,
        )
    if (
        old_comment != obj.comment
        or old_photo_url != obj.photo_url
        or old_user_id != obj.user_id
    ) and old_cost == new_cost and old_restaurant_id == new_restaurant_id and old_quantity == new_quantity and old_item_id == obj.item_id:
        _log_movement_event(
            db,
            action_type="record_updated",
            actor_id=current_user.id,
            item=new_item,
            quantity=new_quantity,
            to_location_kind="restaurant",
            to_restaurant_id=new_restaurant_id,
            comment=obj.comment,
        )

    db.commit()
    db.refresh(obj)
    return _record_schema(obj)


@router.delete("/records/{record_id}")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    _ensure_inventory_movements_delete(current_user)
    obj = db.query(InvItemRecord).filter(InvItemRecord.id == record_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, obj.restaurant_id)
    item = db.query(InvItem).filter(InvItem.id == obj.item_id).first()
    if item:
        _update_stock(
            db,
            restaurant_id=obj.restaurant_id,
            item=item,
            delta_qty=-obj.quantity,
            cost=Decimal(obj.cost),
        )
        _log_movement_event(
            db,
            action_type="record_deleted",
            actor_id=current_user.id,
            item=item,
            quantity=obj.quantity,
            from_location_kind="restaurant",
            from_restaurant_id=obj.restaurant_id,
            field="record_id",
            old_value=str(obj.id),
            comment=obj.comment,
        )
    db.delete(obj)
    db.commit()
    return {"ok": True}
