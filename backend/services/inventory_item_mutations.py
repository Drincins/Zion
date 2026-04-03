from __future__ import annotations

from backend.services.image_uploads import normalize_uploaded_image
from backend.routers.inventory_routes.common import (
    AttachmentUploadResponse,
    Decimal,
    HTTPException,
    InvItem,
    InvItemChange,
    InvItemCreate,
    InvItemRead,
    InvItemUpdate,
    Optional,
    PermissionCode,
    PermissionKey,
    RestaurantSubdivision,
    Session,
    UploadFile,
    User,
    ensure_permissions,
    generate_presigned_url,
    upload_bytes,
    _build_inventory_photo_key,
    _create_item_instances,
    _ensure_inventory_nomenclature_create,
    _ensure_inventory_nomenclature_delete,
    _ensure_inventory_nomenclature_edit,
    _ensure_inventory_nomenclature_view,
    _ensure_restaurant_allowed,
    _generate_item_code,
    _item_schema,
    _log_item_change,
    _log_item_instance_events,
    _log_movement_event,
    _resolve_kind_for_item,
    _resolve_photo_url,
    _resolve_storage_place,
    _sync_item_instance_codes,
    _update_stock,
    get_user_restaurant_ids,
    status,
)


def create_inventory_item(
    *,
    payload: InvItemCreate,
    db: Session,
    current_user: User,
) -> InvItemRead:
    _ensure_inventory_nomenclature_create(current_user)
    code = (payload.code or "").strip() or _generate_item_code(db)
    existing_code = db.query(InvItem).filter(InvItem.code == code).first()
    if existing_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item code already exists")
    kind = _resolve_kind_for_item(
        db,
        group_id=payload.group_id,
        category_id=payload.category_id,
        kind_id=payload.kind_id,
    )
    default_cost = payload.default_cost if payload.default_cost is not None else payload.cost
    normalized_cost = default_cost if default_cost is not None else payload.cost
    if normalized_cost is None:
        normalized_cost = Decimal("0")
    obj = InvItem(
        code=code,
        name=payload.name,
        category_id=payload.category_id,
        group_id=payload.group_id,
        kind_id=kind.id,
        cost=normalized_cost,
        default_cost=default_cost,
        note=payload.note,
        manufacturer=payload.manufacturer,
        storage_conditions=payload.storage_conditions,
        photo_url=payload.photo_url,
        use_instance_codes=payload.use_instance_codes,
        is_active=payload.is_active,
    )
    db.add(obj)
    try:
        db.flush()
        _log_movement_event(
            db,
            action_type="item_created",
            actor_id=current_user.id,
            item=obj,
            comment="Создана новая карточка товара",
        )
        initial_quantity = max(int(payload.initial_quantity or 0), 0)
        if initial_quantity > 0:
            location_kind = payload.initial_location_kind or "warehouse"
            location_restaurant_id: int | None = None
            location_storage_place_id: int | None = None
            location_subdivision_id: int | None = None
            initial_unit_cost = default_cost if default_cost is not None else normalized_cost

            if location_kind == "restaurant":
                if payload.initial_restaurant_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="initial_restaurant_id is required",
                    )
                allowed_restaurants = get_user_restaurant_ids(db, current_user)
                location_restaurant_id = int(payload.initial_restaurant_id)
                _ensure_restaurant_allowed(allowed_restaurants, location_restaurant_id)
                location_storage_place_id = _resolve_storage_place(
                    db=db,
                    current_user=current_user,
                    restaurant_id=location_restaurant_id,
                    storage_place_id=payload.initial_storage_place_id,
                    field_label="initial_storage_place_id",
                )
            elif location_kind == "subdivision":
                if payload.initial_subdivision_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="initial_subdivision_id is required",
                    )
                subdivision_id = int(payload.initial_subdivision_id)
                subdivision_exists = (
                    db.query(RestaurantSubdivision.id)
                    .filter(RestaurantSubdivision.id == subdivision_id)
                    .first()
                )
                if not subdivision_exists:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Subdivision not found",
                    )
                location_subdivision_id = subdivision_id
            elif location_kind != "warehouse":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported initial_location_kind",
                )

            created_instances = _create_item_instances(
                db,
                item=obj,
                quantity=initial_quantity,
                location_kind=location_kind,
                unit_cost=initial_unit_cost,
                restaurant_id=location_restaurant_id,
                storage_place_id=location_storage_place_id,
                subdivision_id=location_subdivision_id,
            )
            if location_kind == "restaurant" and location_restaurant_id is not None:
                _update_stock(
                    db,
                    restaurant_id=location_restaurant_id,
                    item=obj,
                    delta_qty=initial_quantity,
                    cost=Decimal(initial_unit_cost),
                )
            _log_movement_event(
                db,
                action_type="quantity_increase",
                actor_id=current_user.id,
                item=obj,
                quantity=initial_quantity,
                to_location_kind=location_kind,
                to_restaurant_id=location_restaurant_id,
                to_storage_place_id=location_storage_place_id,
                to_subdivision_id=location_subdivision_id,
                comment="Первичное количество при создании товара",
            )
            _log_item_instance_events(
                db,
                instances=created_instances,
                action_type="quantity_increase",
                actor_id=current_user.id,
                item=obj,
                to_location_kind=location_kind,
                to_restaurant_id=location_restaurant_id,
                to_storage_place_id=location_storage_place_id,
                to_subdivision_id=location_subdivision_id,
                comment="Первичное количество при создании товара",
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(obj)
    return _item_schema(obj)


def update_inventory_item(
    *,
    item_id: int,
    payload: InvItemUpdate,
    db: Session,
    current_user: User,
) -> InvItemRead:
    _ensure_inventory_nomenclature_edit(current_user)
    obj = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    original = {
        "code": obj.code,
        "name": obj.name,
        "category_id": obj.category_id,
        "group_id": obj.group_id,
        "kind_id": obj.kind_id,
        "cost": obj.cost,
        "default_cost": obj.default_cost,
        "photo_url": obj.photo_url,
        "note": obj.note,
        "manufacturer": obj.manufacturer,
        "storage_conditions": obj.storage_conditions,
        "use_instance_codes": obj.use_instance_codes,
        "is_active": obj.is_active,
    }
    if payload.code:
        new_code = payload.code.strip()
        existing = db.query(InvItem).filter(InvItem.code == new_code).filter(InvItem.id != item_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item code already exists")
        obj.code = new_code
    next_group_id = payload.group_id if payload.group_id is not None else obj.group_id
    next_category_id = payload.category_id if payload.category_id is not None else obj.category_id
    category_scope_changed = payload.group_id is not None or payload.category_id is not None
    next_kind_id = payload.kind_id if payload.kind_id is not None else (None if category_scope_changed else obj.kind_id)

    kind_needs_resolve = payload.group_id is not None or payload.category_id is not None or payload.kind_id is not None
    if kind_needs_resolve:
        resolved_kind = _resolve_kind_for_item(
            db,
            group_id=next_group_id,
            category_id=next_category_id,
            kind_id=next_kind_id,
        )
        obj.group_id = next_group_id
        obj.category_id = next_category_id
        obj.kind_id = resolved_kind.id
    if payload.name is not None:
        obj.name = payload.name
    if payload.cost is not None:
        obj.cost = payload.cost
        obj.default_cost = payload.cost
    if payload.default_cost is not None:
        obj.default_cost = payload.default_cost
        obj.cost = payload.default_cost if payload.cost is None else obj.cost
    if payload.photo_url is not None:
        obj.photo_url = payload.photo_url
    if payload.note is not None:
        obj.note = payload.note
    if payload.manufacturer is not None:
        obj.manufacturer = payload.manufacturer
    if payload.storage_conditions is not None:
        obj.storage_conditions = payload.storage_conditions
    if payload.use_instance_codes is not None:
        obj.use_instance_codes = bool(payload.use_instance_codes)
    if payload.is_active is not None:
        obj.is_active = bool(payload.is_active)

    should_resync_instance_codes = obj.code != original["code"] or obj.use_instance_codes != original["use_instance_codes"]
    if should_resync_instance_codes:
        _sync_item_instance_codes(db, item=obj)

    changes = [
        ("code", original["code"], obj.code),
        ("name", original["name"], obj.name),
        ("category_id", original["category_id"], obj.category_id),
        ("group_id", original["group_id"], obj.group_id),
        ("kind_id", original["kind_id"], obj.kind_id),
        ("cost", original["cost"], obj.cost),
        ("default_cost", original["default_cost"], obj.default_cost),
        ("photo_url", original["photo_url"], obj.photo_url),
        ("note", original["note"], obj.note),
        ("manufacturer", original["manufacturer"], obj.manufacturer),
        ("storage_conditions", original["storage_conditions"], obj.storage_conditions),
        ("use_instance_codes", original["use_instance_codes"], obj.use_instance_codes),
        ("is_active", original["is_active"], obj.is_active),
    ]
    for field, old_value, new_value in changes:
        _log_item_change(db, item_id=item_id, field=field, old_value=old_value, new_value=new_value, user_id=current_user.id)
        if old_value == new_value:
            continue
        _log_movement_event(
            db,
            action_type="cost_changed" if field in {"cost", "default_cost"} else "item_updated",
            actor_id=current_user.id,
            item=obj,
            field=field,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            comment="Изменены параметры карточки товара",
        )
    db.commit()
    db.refresh(obj)
    return _item_schema(obj)


def delete_inventory_item(
    *,
    item_id: int,
    db: Session,
    current_user: User,
) -> dict[str, bool]:
    _ensure_inventory_nomenclature_delete(current_user)
    obj = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    _log_movement_event(
        db,
        action_type="item_deleted",
        actor_id=current_user.id,
        item=obj,
        comment="Карточка товара удалена",
    )
    db.delete(obj)
    db.commit()
    return {"ok": True}


async def upload_inventory_item_photo_attachment(
    *,
    file: UploadFile,
    current_user: User,
) -> AttachmentUploadResponse:
    ensure_permissions(
        current_user,
        PermissionCode.INVENTORY_MANAGE,
        PermissionKey.INVENTORY_NOMENCLATURE_MANAGE,
        PermissionKey.INVENTORY_NOMENCLATURE_CREATE,
        PermissionKey.INVENTORY_NOMENCLATURE_EDIT,
    )

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image uploads are allowed")

    upload_filename, upload_content, upload_content_type = normalize_uploaded_image(
        filename=file.filename,
        content=await file.read(),
        content_type=file.content_type,
    )

    key = _build_inventory_photo_key(upload_filename)
    upload_bytes(key, upload_content, upload_content_type)
    url = _resolve_photo_url(key)
    return AttachmentUploadResponse(attachment_key=key, attachment_url=url or key)


def list_inventory_item_changes(
    *,
    item_id: int,
    db: Session,
    current_user: User,
) -> list[InvItemChange]:
    _ensure_inventory_nomenclature_view(current_user)
    return (
        db.query(InvItemChange)
        .filter(InvItemChange.item_id == item_id)
        .order_by(InvItemChange.changed_at.desc())
        .all()
    )
