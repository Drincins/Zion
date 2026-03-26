from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from backend.routers.inventory_routes.common import (
    AttachmentUploadResponse,
    InvItem,
    InvItemChange,
    InvItemChangeRead,
    InvItemCreate,
    InvItemLocationSummary,
    InvItemRead,
    InvItemUpdate,
    InvItemInstance,
    InvStoragePlace,
    Optional,
    Restaurant,
    RestaurantSubdivision,
    Session,
    User,
    PermissionCode,
    PermissionKey,
    ensure_permissions,
    get_current_user,
    get_db,
    _ensure_inventory_lookup_access,
)
from backend.services.inventory_item_listing import list_inventory_items
from backend.services.inventory_item_mutations import (
    create_inventory_item,
    delete_inventory_item,
    list_inventory_item_changes,
    update_inventory_item,
    upload_inventory_item_photo_attachment,
)

router = APIRouter()


@router.get("/items", response_model=list[InvItemRead])
def list_items(
    item_ids: Optional[list[int]] = Query(None),
    item_ids_bracket: Optional[list[int]] = Query(None, alias="item_ids[]"),
    group_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    kind_id: Optional[int] = Query(None),
    restaurant_ids: Optional[list[int]] = Query(None),
    restaurant_ids_bracket: Optional[list[int]] = Query(None, alias="restaurant_ids[]"),
    storage_place_ids: Optional[list[int]] = Query(None),
    storage_place_ids_bracket: Optional[list[int]] = Query(None, alias="storage_place_ids[]"),
    subdivision_ids: Optional[list[int]] = Query(None),
    subdivision_ids_bracket: Optional[list[int]] = Query(None, alias="subdivision_ids[]"),
    include_warehouse: bool = Query(False),
    only_in_locations: bool = Query(False),
    include_locations: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvItemRead]:
    return list_inventory_items(
        db=db,
        current_user=current_user,
        item_ids=item_ids,
        item_ids_bracket=item_ids_bracket,
        group_id=group_id,
        category_id=category_id,
        kind_id=kind_id,
        restaurant_ids=restaurant_ids,
        restaurant_ids_bracket=restaurant_ids_bracket,
        storage_place_ids=storage_place_ids,
        storage_place_ids_bracket=storage_place_ids_bracket,
        subdivision_ids=subdivision_ids,
        subdivision_ids_bracket=subdivision_ids_bracket,
        include_warehouse=include_warehouse,
        only_in_locations=only_in_locations,
        include_locations=include_locations,
    )


@router.post("/items", response_model=InvItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: InvItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemRead:
    return create_inventory_item(payload=payload, db=db, current_user=current_user)


@router.put("/items/{item_id}", response_model=InvItemRead)
def update_item(
    item_id: int,
    payload: InvItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemRead:
    return update_inventory_item(item_id=item_id, payload=payload, db=db, current_user=current_user)


@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    return delete_inventory_item(item_id=item_id, db=db, current_user=current_user)


@router.post("/items/photo", response_model=AttachmentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_inventory_item_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> AttachmentUploadResponse:
    return await upload_inventory_item_photo_attachment(file=file, current_user=current_user)


@router.get("/items/{item_id}/changes", response_model=list[InvItemChangeRead])
def list_item_changes(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvItemChange]:
    return list_inventory_item_changes(item_id=item_id, db=db, current_user=current_user)
