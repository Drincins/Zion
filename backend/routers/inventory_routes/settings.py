from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.routers.inventory_routes.common import (
    InvInstanceEventType,
    InvStoragePlace,
    InventoryInstanceEventTypeCreate,
    InventoryInstanceEventTypeRead,
    InventoryInstanceEventTypeUpdate,
    InventoryStoragePlaceCreate,
    InventoryStoragePlaceRead,
    InventoryStoragePlaceUpdate,
    Optional,
    Session,
    User,
    get_current_user,
    get_db,
    get_user_restaurant_ids,
    _ensure_inventory_nomenclature_edit,
    _ensure_inventory_nomenclature_view,
    _ensure_restaurant_allowed,
    _normalize_instance_event_type_code,
    _normalize_inventory_string,
    _serialize_instance_event_type,
    _serialize_storage_place,
)

router = APIRouter()


@router.get("/settings/instance-event-types", response_model=list[InventoryInstanceEventTypeRead])
def list_inventory_instance_event_types(
    manual_only: bool = Query(False),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InventoryInstanceEventTypeRead]:
    _ensure_inventory_nomenclature_view(current_user)
    query = db.query(InvInstanceEventType)
    if manual_only:
        query = query.filter(InvInstanceEventType.is_manual.is_(True))
    if active_only:
        query = query.filter(InvInstanceEventType.is_active.is_(True))
    rows = query.order_by(
        InvInstanceEventType.sort_order.asc(),
        InvInstanceEventType.name.asc(),
        InvInstanceEventType.id.asc(),
    ).all()
    return [_serialize_instance_event_type(row) for row in rows]


@router.post(
    "/settings/instance-event-types",
    response_model=InventoryInstanceEventTypeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_instance_event_type(
    payload: InventoryInstanceEventTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryInstanceEventTypeRead:
    _ensure_inventory_nomenclature_edit(current_user)
    code = _normalize_instance_event_type_code(payload.code)
    if db.query(InvInstanceEventType.id).filter(InvInstanceEventType.code == code).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Тип работ с таким кодом уже существует")

    row = InvInstanceEventType(
        code=code,
        name=(payload.name or "").strip(),
        description=_normalize_inventory_string(payload.description),
        is_active=bool(payload.is_active),
        is_manual=bool(payload.is_manual),
        status_key=_normalize_inventory_string(payload.status_key),
        status_label=_normalize_inventory_string(payload.status_label),
        sort_order=int(payload.sort_order or 100),
    )
    if not row.name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название типа работ обязательно")
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_instance_event_type(row)


@router.put("/settings/instance-event-types/{event_type_id}", response_model=InventoryInstanceEventTypeRead)
def update_inventory_instance_event_type(
    event_type_id: int,
    payload: InventoryInstanceEventTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryInstanceEventTypeRead:
    _ensure_inventory_nomenclature_edit(current_user)
    row = db.query(InvInstanceEventType).filter(InvInstanceEventType.id == event_type_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тип работ не найден")

    if payload.code is not None:
        next_code = _normalize_instance_event_type_code(payload.code)
        existing = (
            db.query(InvInstanceEventType.id)
            .filter(InvInstanceEventType.code == next_code, InvInstanceEventType.id != event_type_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Тип работ с таким кодом уже существует")
        row.code = next_code
    if payload.name is not None:
        next_name = (payload.name or "").strip()
        if not next_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название типа работ обязательно")
        row.name = next_name
    if payload.description is not None:
        row.description = _normalize_inventory_string(payload.description)
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)
    if payload.is_manual is not None:
        row.is_manual = bool(payload.is_manual)
    if payload.status_key is not None:
        row.status_key = _normalize_inventory_string(payload.status_key)
    if payload.status_label is not None:
        row.status_label = _normalize_inventory_string(payload.status_label)
    if payload.sort_order is not None:
        row.sort_order = int(payload.sort_order)
    db.commit()
    db.refresh(row)
    return _serialize_instance_event_type(row)


@router.get("/settings/storage-places", response_model=list[InventoryStoragePlaceRead])
def list_inventory_storage_places(
    active_only: bool = Query(False),
    restaurant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InventoryStoragePlaceRead]:
    _ensure_inventory_nomenclature_view(current_user)
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    query = db.query(InvStoragePlace).filter(InvStoragePlace.scope_kind == "restaurant")
    if active_only:
        query = query.filter(InvStoragePlace.is_active.is_(True))
    if restaurant_id is not None:
        _ensure_restaurant_allowed(allowed_restaurants, int(restaurant_id))
        query = query.filter(InvStoragePlace.restaurant_id == int(restaurant_id))
    if allowed_restaurants is not None:
        if allowed_restaurants:
            query = query.filter(InvStoragePlace.restaurant_id.in_(allowed_restaurants))
        else:
            query = query.filter(False)
    rows = query.order_by(
        InvStoragePlace.sort_order.asc(),
        InvStoragePlace.name.asc(),
        InvStoragePlace.id.asc(),
    ).all()
    return [_serialize_storage_place(row) for row in rows]


@router.post("/settings/storage-places", response_model=InventoryStoragePlaceRead, status_code=status.HTTP_201_CREATED)
def create_inventory_storage_place(
    payload: InventoryStoragePlaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryStoragePlaceRead:
    _ensure_inventory_nomenclature_edit(current_user)
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название места хранения обязательно")

    restaurant_id = int(payload.restaurant_id) if payload.restaurant_id is not None else None
    if restaurant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для места хранения нужен restaurant_id")
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)

    duplicate = (
        db.query(InvStoragePlace.id)
        .filter(
            InvStoragePlace.name == name,
            InvStoragePlace.scope_kind == "restaurant",
            InvStoragePlace.restaurant_id == restaurant_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Такое место хранения уже существует")

    row = InvStoragePlace(
        name=name,
        scope_kind="restaurant",
        restaurant_id=restaurant_id,
        description=_normalize_inventory_string(payload.description),
        is_active=bool(payload.is_active),
        sort_order=int(payload.sort_order or 100),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_storage_place(row)


@router.put("/settings/storage-places/{storage_place_id}", response_model=InventoryStoragePlaceRead)
def update_inventory_storage_place(
    storage_place_id: int,
    payload: InventoryStoragePlaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryStoragePlaceRead:
    _ensure_inventory_nomenclature_edit(current_user)
    row = db.query(InvStoragePlace).filter(InvStoragePlace.id == storage_place_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Место хранения не найдено")

    next_name = row.name if payload.name is None else (payload.name or "").strip()
    if not next_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название места хранения обязательно")
    next_restaurant_id = row.restaurant_id if payload.restaurant_id is None else payload.restaurant_id
    if next_restaurant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для места хранения нужен restaurant_id")
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, int(next_restaurant_id))
    next_restaurant_id = int(next_restaurant_id)

    duplicate = (
        db.query(InvStoragePlace.id)
        .filter(
            InvStoragePlace.name == next_name,
            InvStoragePlace.scope_kind == "restaurant",
            InvStoragePlace.restaurant_id == next_restaurant_id,
            InvStoragePlace.id != storage_place_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Такое место хранения уже существует")

    row.name = next_name
    row.scope_kind = "restaurant"
    row.restaurant_id = next_restaurant_id
    if payload.description is not None:
        row.description = _normalize_inventory_string(payload.description)
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)
    if payload.sort_order is not None:
        row.sort_order = int(payload.sort_order)
    db.commit()
    db.refresh(row)
    return _serialize_storage_place(row)


@router.delete("/settings/storage-places/{storage_place_id}")
def delete_inventory_storage_place(
    storage_place_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    _ensure_inventory_nomenclature_edit(current_user)
    row = db.query(InvStoragePlace).filter(InvStoragePlace.id == storage_place_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Место хранения не найдено")
    if row.scope_kind == "restaurant" and row.restaurant_id is not None:
        allowed_restaurants = get_user_restaurant_ids(db, current_user)
        _ensure_restaurant_allowed(allowed_restaurants, int(row.restaurant_id))
    db.delete(row)
    db.commit()
    return {"ok": True}
