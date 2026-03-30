from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.routers.inventory_routes.common import (
    InvInstanceEventType,
    InvItem,
    InvItemInstance,
    InventoryBalance,
    InventoryItemInstanceEventCreate,
    InventoryItemInstanceEventRead,
    InventoryRestaurantItemCardRead,
    Optional,
    Session,
    User,
    get_current_user,
    get_db,
    get_user_restaurant_ids,
    load_inventory_balances,
    load_inventory_restaurant_balance,
    load_inventory_restaurant_item_card,
    load_inventory_restaurant_item_instance_events,
    _ensure_inventory_balance_view,
    _ensure_inventory_movements_create,
    _ensure_restaurant_allowed,
    _load_actor_name_map,
    _load_instance_event_type_map,
    _load_location_name_maps,
    _serialize_instance_event,
)

router = APIRouter()


@router.get("/balance", response_model=list[InventoryBalance])
def list_inventory_balance(
    restaurant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InventoryBalance]:
    _ensure_inventory_balance_view(current_user)
    return load_inventory_balances(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id,
    )


@router.get("/balance/{restaurant_id}", response_model=InventoryBalance)
def get_restaurant_balance(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryBalance:
    _ensure_inventory_balance_view(current_user)
    return load_inventory_restaurant_balance(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id,
    )


@router.get("/balance/{restaurant_id}/items/{item_id}/card", response_model=InventoryRestaurantItemCardRead)
def get_restaurant_item_card(
    restaurant_id: int,
    item_id: int,
    storage_place_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryRestaurantItemCardRead:
    _ensure_inventory_balance_view(current_user)
    return load_inventory_restaurant_item_card(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id,
        item_id=item_id,
        storage_place_id=storage_place_id,
    )


@router.get("/balance/{restaurant_id}/items/{item_id}/instance-events", response_model=list[InventoryItemInstanceEventRead])
def list_restaurant_item_instance_events(
    restaurant_id: int,
    item_id: int,
    instance_code: str = Query(..., min_length=1),
    storage_place_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InventoryItemInstanceEventRead]:
    _ensure_inventory_balance_view(current_user)
    return load_inventory_restaurant_item_instance_events(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id,
        item_id=item_id,
        instance_code=instance_code,
        storage_place_id=storage_place_id,
    )


@router.post(
    "/balance/{restaurant_id}/items/{item_id}/instances/{instance_id}/events",
    response_model=InventoryItemInstanceEventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_restaurant_item_instance_event(
    restaurant_id: int,
    item_id: int,
    instance_id: int,
    payload: InventoryItemInstanceEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryItemInstanceEventRead:
    _ensure_inventory_movements_create(current_user)
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)

    item = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if not item.use_instance_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance tracking is disabled for this item",
        )

    instance = (
        db.query(InvItemInstance)
        .filter(
            InvItemInstance.id == instance_id,
            InvItemInstance.item_id == item_id,
            InvItemInstance.location_kind == "restaurant",
            InvItemInstance.restaurant_id == restaurant_id,
        )
        .first()
    )
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found in selected restaurant")
    event_type = db.query(InvInstanceEventType).filter(InvInstanceEventType.id == payload.event_type_id).first()
    if not event_type or not bool(event_type.is_manual) or not bool(event_type.is_active):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported instance event action")

    from backend.routers.inventory_routes.common import InvItemInstanceEvent

    event = InvItemInstanceEvent(
        action_type=event_type.code,
        actor_id=current_user.id,
        item_id=item_id,
        instance_id=instance.id,
        sequence_no=instance.sequence_no,
        instance_code_snapshot=instance.instance_code,
        purchase_cost=instance.purchase_cost,
        from_location_kind="restaurant",
        from_restaurant_id=restaurant_id,
        from_storage_place_id=instance.storage_place_id,
        to_location_kind="restaurant",
        to_restaurant_id=restaurant_id,
        to_storage_place_id=instance.storage_place_id,
        comment=(payload.comment or "").strip() or None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    actor_map = _load_actor_name_map(db, {current_user.id})
    restaurant_names, storage_place_names, subdivision_names = _load_location_name_maps(
        db,
        restaurant_ids={restaurant_id},
        storage_place_ids={int(instance.storage_place_id)} if instance.storage_place_id is not None else set(),
        subdivision_ids=set(),
    )
    instance_event_type_map = _load_instance_event_type_map(db)
    return _serialize_instance_event(
        event,
        actor_map=actor_map,
        restaurant_names=restaurant_names,
        storage_place_names=storage_place_names,
        subdivision_names=subdivision_names,
        event_type_map=instance_event_type_map,
    )
