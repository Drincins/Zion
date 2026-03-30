from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from backend.routers.inventory_routes.common import (
    InvItemAllocateCreate,
    InvItemAllocateRead,
    InvItemQuantityUpdate,
    InvItemQuantityUpdateRead,
    InvItemTransferCreate,
    InvItemTransferRead,
    InvMovementEventRead,
    InventoryMovementActionOption,
    Optional,
    Query,
    Session,
    User,
    datetime,
    get_current_user,
    get_db,
    load_inventory_movement_events,
    run_inventory_allocate_item,
    run_inventory_transfer_item,
    run_inventory_update_item_quantity,
    _ensure_inventory_movements_create,
    _ensure_inventory_movements_view,
    _movement_action_label,
)

router = APIRouter()


@router.post("/items/{item_id}/transfer", response_model=InvItemTransferRead, status_code=status.HTTP_201_CREATED)
def transfer_item_to_department(
    item_id: int,
    payload: InvItemTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemTransferRead:
    _ensure_inventory_movements_create(current_user)
    return run_inventory_transfer_item(
        db=db,
        current_user=current_user,
        item_id=item_id,
        payload=payload,
    )


@router.post("/items/{item_id}/allocate", response_model=InvItemAllocateRead, status_code=status.HTTP_201_CREATED)
def allocate_item_to_location(
    item_id: int,
    payload: InvItemAllocateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemAllocateRead:
    _ensure_inventory_movements_create(current_user)
    return run_inventory_allocate_item(
        db=db,
        current_user=current_user,
        item_id=item_id,
        payload=payload,
    )


@router.post("/items/{item_id}/quantity", response_model=InvItemQuantityUpdateRead, status_code=status.HTTP_200_OK)
def update_item_quantity_at_location(
    item_id: int,
    payload: InvItemQuantityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemQuantityUpdateRead:
    _ensure_inventory_movements_create(current_user)
    return run_inventory_update_item_quantity(
        db=db,
        current_user=current_user,
        item_id=item_id,
        payload=payload,
    )


@router.get("/movements/actions", response_model=list[InventoryMovementActionOption])
def list_movement_actions(
    current_user: User = Depends(get_current_user),
) -> list[InventoryMovementActionOption]:
    _ensure_inventory_movements_view(current_user)
    ordered = [
        "item_created",
        "quantity_increase",
        "transfer",
        "quantity_adjusted",
        "writeoff",
        "cost_changed",
        "item_updated",
        "item_deleted",
        "record_created",
        "record_updated",
        "record_deleted",
    ]
    return [InventoryMovementActionOption(value=value, label=_movement_action_label(value)) for value in ordered]


@router.get("/movements", response_model=list[InvMovementEventRead])
def list_movement_events(
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),
    item_ids: Optional[list[int]] = Query(None),
    item_ids_bracket: Optional[list[int]] = Query(None, alias="item_ids[]"),
    group_ids: Optional[list[int]] = Query(None),
    group_ids_bracket: Optional[list[int]] = Query(None, alias="group_ids[]"),
    category_ids: Optional[list[int]] = Query(None),
    category_ids_bracket: Optional[list[int]] = Query(None, alias="category_ids[]"),
    kind_ids: Optional[list[int]] = Query(None),
    kind_ids_bracket: Optional[list[int]] = Query(None, alias="kind_ids[]"),
    object_ids: Optional[list[str]] = Query(None),
    object_ids_bracket: Optional[list[str]] = Query(None, alias="object_ids[]"),
    action_types: Optional[list[str]] = Query(None),
    action_types_bracket: Optional[list[str]] = Query(None, alias="action_types[]"),
    actor_ids: Optional[list[int]] = Query(None),
    actor_ids_bracket: Optional[list[int]] = Query(None, alias="actor_ids[]"),
    q: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvMovementEventRead]:
    _ensure_inventory_movements_view(current_user)
    return load_inventory_movement_events(
        db=db,
        current_user=current_user,
        created_from=created_from,
        created_to=created_to,
        item_ids=item_ids,
        item_ids_bracket=item_ids_bracket,
        group_ids=group_ids,
        group_ids_bracket=group_ids_bracket,
        category_ids=category_ids,
        category_ids_bracket=category_ids_bracket,
        kind_ids=kind_ids,
        kind_ids_bracket=kind_ids_bracket,
        object_ids=object_ids,
        object_ids_bracket=object_ids_bracket,
        action_types=action_types,
        action_types_bracket=action_types_bracket,
        actor_ids=actor_ids,
        actor_ids_bracket=actor_ids_bracket,
        q=q,
        limit=limit,
    )
