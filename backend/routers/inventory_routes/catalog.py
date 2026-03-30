from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.routers.inventory_routes.common import (
    InvCategory,
    InvCategoryCreate,
    InvCategoryRead,
    InvCategoryUpdate,
    InvGroup,
    InvGroupCreate,
    InvGroupRead,
    InvGroupUpdate,
    InvKind,
    InvKindCreate,
    InvKindRead,
    InvKindUpdate,
    InventoryDepartmentOption,
    Optional,
    Restaurant,
    RestaurantSubdivision,
    Session,
    User,
    get_current_user,
    get_db,
    get_user_restaurant_ids,
    _ensure_inventory_lookup_access,
    _ensure_inventory_nomenclature_create,
    _ensure_inventory_nomenclature_delete,
    _ensure_inventory_nomenclature_edit,
    _ensure_inventory_nomenclature_view,
    _ensure_restaurant_allowed,
)

router = APIRouter()


@router.get("/groups", response_model=list[InvGroupRead])
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvGroup]:
    _ensure_inventory_nomenclature_view(current_user)
    return db.query(InvGroup).order_by(InvGroup.name.asc()).all()


@router.post("/groups", response_model=InvGroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: InvGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvGroup:
    _ensure_inventory_nomenclature_create(current_user)
    group = InvGroup(name=payload.name)
    db.add(group)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(group)
    return group


@router.put("/groups/{group_id}", response_model=InvGroupRead)
def update_group(
    group_id: int,
    payload: InvGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvGroup:
    _ensure_inventory_nomenclature_edit(current_user)
    group = db.query(InvGroup).filter(InvGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if payload.name is not None:
        group.name = payload.name
    db.commit()
    db.refresh(group)
    return group


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    _ensure_inventory_nomenclature_delete(current_user)
    group = db.query(InvGroup).filter(InvGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    db.delete(group)
    db.commit()
    return {"ok": True}


@router.get("/categories", response_model=list[InvCategoryRead])
def list_categories(
    group_id: Optional[int] = Query(None, description="Filter by group"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvCategory]:
    _ensure_inventory_nomenclature_view(current_user)
    query = db.query(InvCategory)
    if group_id is not None:
        query = query.filter(InvCategory.group_id == group_id)
    return query.order_by(InvCategory.name.asc()).all()


@router.post("/categories", response_model=InvCategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: InvCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvCategory:
    _ensure_inventory_nomenclature_create(current_user)
    obj = InvCategory(name=payload.name, group_id=payload.group_id)
    db.add(obj)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(obj)
    return obj


@router.put("/categories/{category_id}", response_model=InvCategoryRead)
def update_category(
    category_id: int,
    payload: InvCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvCategory:
    _ensure_inventory_nomenclature_edit(current_user)
    obj = db.query(InvCategory).filter(InvCategory.id == category_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if payload.name is not None:
        obj.name = payload.name
    if payload.group_id is not None:
        obj.group_id = payload.group_id
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    _ensure_inventory_nomenclature_delete(current_user)
    obj = db.query(InvCategory).filter(InvCategory.id == category_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.get("/departments", response_model=list[InventoryDepartmentOption])
def list_inventory_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InventoryDepartmentOption]:
    _ensure_inventory_lookup_access(current_user)
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    restaurants_query = db.query(Restaurant)
    if allowed_restaurants is not None:
        if allowed_restaurants:
            restaurants_query = restaurants_query.filter(Restaurant.id.in_(allowed_restaurants))
        else:
            restaurants_query = restaurants_query.filter(False)
    restaurants = restaurants_query.order_by(Restaurant.name.asc()).all()
    subdivisions = db.query(RestaurantSubdivision).order_by(RestaurantSubdivision.name.asc()).all()

    options: list[InventoryDepartmentOption] = [
        InventoryDepartmentOption(id="all_departments", type="meta", label="Все подразделения"),
        InventoryDepartmentOption(id="all_restaurants", type="meta", label="Все рестораны"),
        InventoryDepartmentOption(id="warehouse", type="warehouse", label="Склад"),
    ]
    for restaurant in restaurants:
        options.append(
            InventoryDepartmentOption(
                id=f"restaurant:{restaurant.id}",
                type="restaurant",
                label=restaurant.name,
                restaurant_id=restaurant.id,
            )
        )
    for subdivision in subdivisions:
        options.append(
            InventoryDepartmentOption(
                id=f"subdivision:{subdivision.id}",
                type="subdivision",
                label=subdivision.name,
                subdivision_id=subdivision.id,
            )
        )
    return options


@router.get("/types", response_model=list[InvKindRead])
def list_kinds(
    group_id: Optional[int] = Query(None, description="Filter by group"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvKind]:
    _ensure_inventory_nomenclature_view(current_user)
    query = db.query(InvKind)
    if group_id is not None:
        query = query.filter(InvKind.group_id == group_id)
    if category_id is not None:
        query = query.filter(InvKind.category_id == category_id)
    return query.order_by(InvKind.name.asc()).all()


@router.post("/types", response_model=InvKindRead, status_code=status.HTTP_201_CREATED)
def create_kind(
    payload: InvKindCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvKind:
    _ensure_inventory_nomenclature_create(current_user)
    category = (
        db.query(InvCategory)
        .filter(InvCategory.id == payload.category_id, InvCategory.group_id == payload.group_id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category does not belong to selected group")

    kind = InvKind(name=payload.name, category_id=payload.category_id, group_id=payload.group_id)
    db.add(kind)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(kind)
    return kind


@router.put("/types/{kind_id}", response_model=InvKindRead)
def update_kind(
    kind_id: int,
    payload: InvKindUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvKind:
    _ensure_inventory_nomenclature_edit(current_user)
    kind = db.query(InvKind).filter(InvKind.id == kind_id).first()
    if not kind:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kind not found")

    next_group_id = payload.group_id if payload.group_id is not None else kind.group_id
    next_category_id = payload.category_id if payload.category_id is not None else kind.category_id
    if payload.group_id is not None or payload.category_id is not None:
        category = (
            db.query(InvCategory)
            .filter(InvCategory.id == next_category_id, InvCategory.group_id == next_group_id)
            .first()
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category does not belong to selected group",
            )
        kind.group_id = next_group_id
        kind.category_id = next_category_id
    if payload.name is not None:
        kind.name = payload.name
    db.commit()
    db.refresh(kind)
    return kind


@router.delete("/types/{kind_id}")
def delete_kind(
    kind_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    _ensure_inventory_nomenclature_delete(current_user)
    kind = db.query(InvKind).filter(InvKind.id == kind_id).first()
    if not kind:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kind not found")
    db.delete(kind)
    db.commit()
    return {"ok": True}
