# backend/routers/inventory.py
from __future__ import annotations

import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import (
    InvGroup,
    InvCategory,
    InvKind,
    InvItem,
    InvItemRecord,
    InvItemStock,
    InvItemChange,
    InvItemInstance,
    InvItemInstanceEvent,
    InvInstanceEventType,
    InvStoragePlace,
    InvMovementEvent,
    Restaurant,
    RestaurantSubdivision,
    User,
)
from backend.schemas import (
    InvGroupCreate,
    InvGroupRead,
    InvGroupUpdate,
    InvCategoryCreate,
    InvCategoryRead,
    InvCategoryUpdate,
    InvKindCreate,
    InvKindRead,
    InvKindUpdate,
    InvItemCreate,
    InvItemRead,
    InvItemUpdate,
    InvItemLocationSummary,
    InvItemRecordCreate,
    InvItemRecordRead,
    InvItemRecordUpdate,
    InventoryBalance,
    InventoryBalanceItem,
    AttachmentUploadResponse,
    InvItemChangeRead,
    InventoryDepartmentOption,
    InvItemTransferCreate,
    InvItemTransferRead,
    InvItemAllocateCreate,
    InvItemAllocateRead,
    InvItemQuantityUpdate,
    InvItemQuantityUpdateRead,
    InventoryMovementActionOption,
    InvMovementEventRead,
    InventoryRestaurantItemArrivalRead,
    InventoryItemInstanceSummaryRead,
    InventoryItemInstanceEventRead,
    InventoryItemInstanceEventCreate,
    InventoryRestaurantItemCardRead,
    InventoryInstanceEventTypeCreate,
    InventoryInstanceEventTypeRead,
    InventoryInstanceEventTypeUpdate,
    InventoryStoragePlaceCreate,
    InventoryStoragePlaceRead,
    InventoryStoragePlaceUpdate,
)
from backend.utils import get_current_user, get_user_restaurant_ids
from backend.services.permissions import PermissionCode, PermissionKey, ensure_permissions
from backend.services.s3 import generate_presigned_url, upload_bytes

router = APIRouter(prefix="/inventory", tags=["Inventory"])
logger = logging.getLogger(__name__)
INVENTORY_PHOTO_PREFIX = (
    os.getenv("INVENTORY_PHOTO_PREFIX")
    or os.getenv("TG_BOT_S3_PREFIX")
    or "inventory_bot"
).strip("/") or "inventory_bot"

MOVEMENT_ACTION_LABELS: dict[str, str] = {
    "item_created": "Создание товара",
    "item_updated": "Изменение карточки",
    "item_deleted": "Удаление товара",
    "transfer": "Перевод между подразделениями",
    "quantity_increase": "Поступление",
    "quantity_adjusted": "Изменение количества",
    "writeoff": "Списание",
    "cost_changed": "Изменение стоимости",
    "record_created": "Ручная операция",
    "record_updated": "Изменение операции",
    "record_deleted": "Удаление операции",
}

DEFAULT_INSTANCE_EVENT_TYPES: tuple[dict[str, object], ...] = (
    {
        "code": "quantity_increase",
        "name": "Поступление",
        "description": "Автоматическое событие прихода единицы товара.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 10,
    },
    {
        "code": "quantity_adjusted",
        "name": "Корректировка",
        "description": "Автоматическая корректировка количества единиц товара.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 20,
    },
    {
        "code": "transfer",
        "name": "Перемещение",
        "description": "Автоматическое перемещение единицы товара между локациями.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 30,
    },
    {
        "code": "writeoff",
        "name": "Списание",
        "description": "Автоматическое списание единицы товара.",
        "is_manual": False,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 40,
    },
    {
        "code": "repair",
        "name": "Ремонт",
        "description": "Ручное сервисное событие для ремонта единицы товара.",
        "is_manual": True,
        "is_active": True,
        "status_key": "repair",
        "status_label": "В ремонте",
        "sort_order": 100,
    },
    {
        "code": "maintenance",
        "name": "ТО",
        "description": "Ручное сервисное событие для технического обслуживания.",
        "is_manual": True,
        "is_active": True,
        "status_key": "maintenance",
        "status_label": "На ТО",
        "sort_order": 110,
    },
    {
        "code": "inspection",
        "name": "Проверка",
        "description": "Ручное сервисное событие для проверки состояния единицы товара.",
        "is_manual": True,
        "is_active": True,
        "status_key": "inspection",
        "status_label": "Проверяется",
        "sort_order": 120,
    },
    {
        "code": "note",
        "name": "Комментарий",
        "description": "Ручное текстовое событие без смены статуса единицы товара.",
        "is_manual": True,
        "is_active": True,
        "status_key": None,
        "status_label": None,
        "sort_order": 130,
    },
)
DEFAULT_INSTANCE_EVENT_TYPE_MAP = {
    str(item["code"]): dict(item)
    for item in DEFAULT_INSTANCE_EVENT_TYPES
}

INVENTORY_NOMENCLATURE_VIEW_PERMISSION_CODES = (
    PermissionCode.INVENTORY_VIEW,
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_VIEW,
    PermissionKey.INVENTORY_NOMENCLATURE_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_CREATE,
    PermissionKey.INVENTORY_NOMENCLATURE_EDIT,
    PermissionKey.INVENTORY_NOMENCLATURE_DELETE,
)
INVENTORY_NOMENCLATURE_CREATE_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_CREATE,
)
INVENTORY_NOMENCLATURE_EDIT_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_EDIT,
)
INVENTORY_NOMENCLATURE_DELETE_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_DELETE,
)
INVENTORY_MOVEMENTS_VIEW_PERMISSION_CODES = (
    PermissionCode.INVENTORY_VIEW,
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_VIEW,
    PermissionKey.INVENTORY_MOVEMENTS_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_CREATE,
    PermissionKey.INVENTORY_MOVEMENTS_EDIT,
    PermissionKey.INVENTORY_MOVEMENTS_DELETE,
)
INVENTORY_MOVEMENTS_CREATE_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_CREATE,
)
INVENTORY_MOVEMENTS_EDIT_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_EDIT,
)
INVENTORY_MOVEMENTS_DELETE_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_DELETE,
)
INVENTORY_LOOKUP_PERMISSION_CODES = tuple(
    dict.fromkeys(INVENTORY_NOMENCLATURE_VIEW_PERMISSION_CODES + INVENTORY_MOVEMENTS_VIEW_PERMISSION_CODES)
)


def _normalize_inventory_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_instance_event_type_code(value: str | None) -> str:
    normalized = _normalize_inventory_string(value)
    if normalized:
        return normalized.lower()
    return f"evt_{uuid4().hex[:12]}"


def _load_instance_event_type_map(db: Session) -> dict[str, dict[str, object]]:
    rows = (
        db.query(InvInstanceEventType)
        .order_by(InvInstanceEventType.sort_order.asc(), InvInstanceEventType.name.asc(), InvInstanceEventType.id.asc())
        .all()
    )
    mapping = {
        str(row.code): {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "description": row.description,
            "is_active": bool(row.is_active),
            "is_manual": bool(row.is_manual),
            "status_key": _normalize_inventory_string(row.status_key),
            "status_label": _normalize_inventory_string(row.status_label),
            "sort_order": int(row.sort_order or 100),
        }
        for row in rows
    }
    for code, payload in DEFAULT_INSTANCE_EVENT_TYPE_MAP.items():
        mapping.setdefault(code, dict(payload))
    return mapping


def _instance_event_type_label(action_type: str, *, event_type_map: dict[str, dict[str, object]] | None = None) -> str:
    config = (event_type_map or {}).get(action_type)
    if config and _normalize_inventory_string(str(config.get("name") or "")):
        return str(config["name"])
    legacy = DEFAULT_INSTANCE_EVENT_TYPE_MAP.get(action_type)
    if legacy:
        return str(legacy["name"])
    return _movement_action_label(action_type)


def _serialize_instance_event_type(row: InvInstanceEventType) -> InventoryInstanceEventTypeRead:
    return InventoryInstanceEventTypeRead(
        id=row.id,
        code=row.code,
        name=row.name,
        description=row.description,
        is_active=bool(row.is_active),
        is_manual=bool(row.is_manual),
        status_key=_normalize_inventory_string(row.status_key),
        status_label=_normalize_inventory_string(row.status_label),
        sort_order=int(row.sort_order or 100),
        created_at=row.created_at,
    )


def _serialize_storage_place(row: InvStoragePlace) -> InventoryStoragePlaceRead:
    return InventoryStoragePlaceRead(
        id=row.id,
        name=row.name,
        scope_kind=row.scope_kind,
        restaurant_id=row.restaurant_id,
        description=row.description,
        is_active=bool(row.is_active),
        sort_order=int(row.sort_order or 100),
        created_at=row.created_at,
    )


def _ensure_inventory_nomenclature_view(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_NOMENCLATURE_VIEW_PERMISSION_CODES)


def _ensure_inventory_nomenclature_create(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_NOMENCLATURE_CREATE_PERMISSION_CODES)


def _ensure_inventory_nomenclature_edit(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_NOMENCLATURE_EDIT_PERMISSION_CODES)


def _ensure_inventory_nomenclature_delete(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_NOMENCLATURE_DELETE_PERMISSION_CODES)


def _ensure_inventory_movements_view(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_MOVEMENTS_VIEW_PERMISSION_CODES)


def _ensure_inventory_movements_create(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_MOVEMENTS_CREATE_PERMISSION_CODES)


def _ensure_inventory_movements_edit(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_MOVEMENTS_EDIT_PERMISSION_CODES)


def _ensure_inventory_movements_delete(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_MOVEMENTS_DELETE_PERMISSION_CODES)


def _ensure_inventory_lookup_access(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_LOOKUP_PERMISSION_CODES)


def _ensure_inventory_balance_view(current_user: User) -> None:
    ensure_permissions(
        current_user,
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_MANAGE,
        PermissionKey.INVENTORY_BALANCE_VIEW,
    )


def _build_inventory_photo_key(filename: str | None) -> str:
    base, ext = os.path.splitext(filename or "photo")
    safe_base = base.replace("/", "_") or "photo"
    safe_ext = ext if ext else ".jpg"
    return f"{INVENTORY_PHOTO_PREFIX}/{safe_base}_{uuid4().hex}{safe_ext}"


def _generate_item_code(db: Session) -> str:
    # Simple sequential code based on max ID to keep uniqueness predictable.
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
    """Apply movement to stock table (quantity/avg_cost)."""

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
        total_cost += delta_dec * current_avg  # withdrawals use avg cost

    new_qty = current_qty + delta_qty
    if new_qty <= 0:
        stock.quantity = 0
        # keep avg cost as last known (avoid division by zero)
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


def _resolve_photo_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value
    try:
        return generate_presigned_url(value)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to build presigned URL for inventory photo %s", value, exc_info=True)
        return value


def _item_schema(
    item: InvItem,
    *,
    location_totals: list[InvItemLocationSummary] | None = None,
    total_quantity: int = 0,
    warehouse_quantity: int = 0,
) -> InvItemRead:
    return InvItemRead(
        id=item.id,
        code=item.code,
        name=item.name,
        category_id=item.category_id,
        group_id=item.group_id,
        kind_id=item.kind_id,
        cost=item.default_cost if item.default_cost is not None else item.cost,
        default_cost=item.default_cost,
        note=item.note,
        manufacturer=item.manufacturer,
        storage_conditions=item.storage_conditions,
        photo_url=_resolve_photo_url(item.photo_url),
        use_instance_codes=bool(item.use_instance_codes),
        is_active=bool(item.is_active),
        created_at=item.created_at,
        photo_key=item.photo_url,
        kind_name=getattr(getattr(item, "kind", None), "name", None),
        total_quantity=total_quantity,
        warehouse_quantity=warehouse_quantity,
        location_totals=location_totals or [],
    )


def _record_schema(record: InvItemRecord) -> InvItemRecordRead:
    return InvItemRecordRead(
        id=record.id,
        created_at=record.created_at,
        item_id=record.item_id,
        category_id=record.category_id,
        group_id=record.group_id,
        restaurant_id=record.restaurant_id,
        user_id=record.user_id,
        quantity=record.quantity,
        cost=record.cost,
        comment=record.comment,
        photo_url=_resolve_photo_url(record.photo_url),
        photo_key=record.photo_url,
    )


def _movement_action_label(action_type: str) -> str:
    return MOVEMENT_ACTION_LABELS.get(action_type, action_type)


def _instance_event_action_label(
    action_type: str,
    *,
    event_type_map: dict[str, dict[str, object]] | None = None,
) -> str:
    return _instance_event_type_label(action_type, event_type_map=event_type_map)


def _compose_user_name(*, first_name: str | None, last_name: str | None, middle_name: str | None, username: str | None, user_id: int | None) -> str | None:
    full_name = " ".join(part for part in [last_name, first_name, middle_name] if part).strip()
    if full_name:
        return full_name
    if username:
        return username
    if user_id is not None:
        return f"ID {user_id}"
    return None


def _location_name(
    *,
    location_kind: str | None,
    restaurant_id: int | None,
    storage_place_id: int | None,
    subdivision_id: int | None,
    restaurant_names: dict[int, str],
    storage_place_names: dict[int, str],
    subdivision_names: dict[int, str],
) -> str | None:
    if location_kind == "warehouse":
        return "Склад"
    if location_kind == "restaurant":
        base_name = "Ресторан" if restaurant_id is None else restaurant_names.get(restaurant_id, f"Ресторан #{restaurant_id}")
        if storage_place_id is None:
            return f"{base_name} · Без места хранения"
        storage_place_name = storage_place_names.get(storage_place_id, f"Место #{storage_place_id}")
        return f"{base_name} · {storage_place_name}"
    if location_kind == "subdivision":
        if subdivision_id is None:
            return "Подразделение"
        return subdivision_names.get(subdivision_id, f"Подразделение #{subdivision_id}")
    return None


def _load_actor_name_map(db: Session, actor_ids: set[int]) -> dict[int, str]:
    if not actor_ids:
        return {}
    actor_rows = (
        db.query(User.id, User.first_name, User.last_name, User.middle_name, User.username)
        .filter(User.id.in_(actor_ids))
        .all()
    )
    return {
        int(row.id): _compose_user_name(
            first_name=row.first_name,
            last_name=row.last_name,
            middle_name=row.middle_name,
            username=row.username,
            user_id=row.id,
        )
        for row in actor_rows
    }


def _load_location_name_maps(
    db: Session,
    *,
    restaurant_ids: set[int],
    storage_place_ids: set[int],
    subdivision_ids: set[int],
) -> tuple[dict[int, str], dict[int, str], dict[int, str]]:
    restaurant_names = {
        int(row.id): row.name
        for row in (
            db.query(Restaurant.id, Restaurant.name).filter(Restaurant.id.in_(restaurant_ids)).all()
            if restaurant_ids
            else []
        )
    }
    storage_place_names = {
        int(row.id): row.name
        for row in (
            db.query(InvStoragePlace.id, InvStoragePlace.name).filter(InvStoragePlace.id.in_(storage_place_ids)).all()
            if storage_place_ids
            else []
        )
    }
    subdivision_names = {
        int(row.id): row.name
        for row in (
            db.query(RestaurantSubdivision.id, RestaurantSubdivision.name)
            .filter(RestaurantSubdivision.id.in_(subdivision_ids))
            .all()
            if subdivision_ids
            else []
        )
    }
    return restaurant_names, storage_place_names, subdivision_names


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


def _serialize_instance_event(
    event: InvItemInstanceEvent,
    *,
    actor_map: dict[int, str],
    restaurant_names: dict[int, str],
    storage_place_names: dict[int, str],
    subdivision_names: dict[int, str],
    event_type_map: dict[str, dict[str, object]] | None = None,
) -> InventoryItemInstanceEventRead:
    return InventoryItemInstanceEventRead(
        id=event.id,
        created_at=event.created_at,
        action_type=event.action_type,
        action_label=_instance_event_action_label(event.action_type, event_type_map=event_type_map),
        actor_name=actor_map.get(event.actor_id) if event.actor_id is not None else None,
        instance_id=event.instance_id,
        instance_code=event.instance_code_snapshot,
        purchase_cost=event.purchase_cost,
        from_storage_place_id=event.from_storage_place_id,
        from_location_name=_location_name(
            location_kind=event.from_location_kind,
            restaurant_id=event.from_restaurant_id,
            storage_place_id=event.from_storage_place_id,
            subdivision_id=event.from_subdivision_id,
            restaurant_names=restaurant_names,
            storage_place_names=storage_place_names,
            subdivision_names=subdivision_names,
        ),
        to_storage_place_id=event.to_storage_place_id,
        to_location_name=_location_name(
            location_kind=event.to_location_kind,
            restaurant_id=event.to_restaurant_id,
            storage_place_id=event.to_storage_place_id,
            subdivision_id=event.to_subdivision_id,
            restaurant_names=restaurant_names,
            storage_place_names=storage_place_names,
            subdivision_names=subdivision_names,
        ),
        comment=event.comment,
    )


def _combine_int_filters(primary: list[int] | None, bracket: list[int] | None) -> list[int]:
    return sorted({int(value) for value in (primary or []) + (bracket or [])})


def _combine_str_filters(primary: list[str] | None, bracket: list[str] | None) -> list[str]:
    values = [str(value).strip() for value in (primary or []) + (bracket or [])]
    return [value for value in sorted(set(values)) if value]


def _event_matches_allowed_restaurants(allowed_restaurants: set[int]) -> list:
    return [
        or_(
            InvMovementEvent.from_location_kind.is_(None),
            InvMovementEvent.from_location_kind != "restaurant",
            InvMovementEvent.from_restaurant_id.in_(allowed_restaurants),
        ),
        or_(
            InvMovementEvent.to_location_kind.is_(None),
            InvMovementEvent.to_location_kind != "restaurant",
            InvMovementEvent.to_restaurant_id.in_(allowed_restaurants),
        ),
    ]


def _instance_event_matches_restaurant(restaurant_id: int):
    return or_(
        and_(
            InvItemInstanceEvent.to_location_kind == "restaurant",
            InvItemInstanceEvent.to_restaurant_id == restaurant_id,
        ),
        and_(
            InvItemInstanceEvent.from_location_kind == "restaurant",
            InvItemInstanceEvent.from_restaurant_id == restaurant_id,
        ),
    )


def _instance_event_matches_storage_place(storage_place_id: int):
    return or_(
        InvItemInstanceEvent.to_storage_place_id == storage_place_id,
        InvItemInstanceEvent.from_storage_place_id == storage_place_id,
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

    event = InvMovementEvent(
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
    db.add(event)


# ---- Groups CRUD ----
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


# ---- Categories CRUD ----
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


# ---- Kinds CRUD (third level under category) ----
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


# ---- Items CRUD ----
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
    _ensure_inventory_lookup_access(current_user)
    query = db.query(InvItem)
    normalized_item_ids = sorted({int(item_id) for item_id in (item_ids or []) + (item_ids_bracket or [])})
    if normalized_item_ids:
        query = query.filter(InvItem.id.in_(normalized_item_ids))
    if group_id is not None:
        query = query.filter(InvItem.group_id == group_id)
    if category_id is not None:
        query = query.filter(InvItem.category_id == category_id)
    if kind_id is not None:
        query = query.filter(InvItem.kind_id == kind_id)

    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    raw_restaurant_ids = sorted({int(rid) for rid in (restaurant_ids or []) + (restaurant_ids_bracket or [])})
    normalized_restaurant_ids: list[int] = []
    if raw_restaurant_ids:
        if allowed_restaurants is None:
            normalized_restaurant_ids = raw_restaurant_ids
        else:
            normalized_restaurant_ids = sorted(
                {int(rid) for rid in raw_restaurant_ids if int(rid) in allowed_restaurants}
            )

    normalized_subdivision_ids = sorted(
        {int(sid) for sid in (subdivision_ids or []) + (subdivision_ids_bracket or [])}
    )
    normalized_storage_place_ids = sorted(
        {int(place_id) for place_id in (storage_place_ids or []) + (storage_place_ids_bracket or [])}
    )

    location_conditions = []
    if include_warehouse:
        location_conditions.append(InvItemInstance.location_kind == "warehouse")
    if normalized_restaurant_ids:
        restaurant_condition = and_(
            InvItemInstance.location_kind == "restaurant",
            InvItemInstance.restaurant_id.in_(normalized_restaurant_ids),
        )
        if normalized_storage_place_ids:
            restaurant_condition = and_(
                restaurant_condition,
                InvItemInstance.storage_place_id.in_(normalized_storage_place_ids),
            )
        location_conditions.append(restaurant_condition)
    if normalized_subdivision_ids:
        location_conditions.append(
            and_(
                InvItemInstance.location_kind == "subdivision",
                InvItemInstance.subdivision_id.in_(normalized_subdivision_ids),
            )
        )

    should_filter_by_locations = bool(location_conditions) or only_in_locations
    if should_filter_by_locations:
        if not location_conditions:
            return []
        query = (
            query.join(InvItemInstance, InvItemInstance.item_id == InvItem.id)
            .filter(or_(*location_conditions))
            .distinct()
        )

    items = query.order_by(InvItem.name.asc()).all()
    if not items:
        return []

    if not include_locations:
        return [_item_schema(item) for item in items]

    item_ids = [item.id for item in items]
    summaries_query = (
        db.query(
            InvItemInstance.item_id.label("item_id"),
            InvItemInstance.location_kind.label("location_kind"),
            InvItemInstance.restaurant_id.label("restaurant_id"),
            InvItemInstance.storage_place_id.label("storage_place_id"),
            InvItemInstance.subdivision_id.label("subdivision_id"),
            func.count(InvItemInstance.id).label("quantity"),
            func.avg(
                func.coalesce(
                    InvItemInstance.purchase_cost,
                    InvItem.default_cost,
                    InvItem.cost,
                )
            ).label("avg_cost"),
            func.max(InvItemInstance.arrived_at).label("last_arrival_at"),
        )
        .join(InvItem, InvItem.id == InvItemInstance.item_id)
        .filter(InvItemInstance.item_id.in_(item_ids))
    )
    if should_filter_by_locations and location_conditions:
        summaries_query = summaries_query.filter(or_(*location_conditions))
    elif allowed_restaurants is not None:
        summaries_query = summaries_query.filter(
            or_(
                InvItemInstance.location_kind != "restaurant",
                InvItemInstance.restaurant_id.in_(allowed_restaurants),
            )
        )
    summary_rows = (
        summaries_query
        .group_by(
            InvItemInstance.item_id,
            InvItemInstance.location_kind,
            InvItemInstance.restaurant_id,
            InvItemInstance.storage_place_id,
            InvItemInstance.subdivision_id,
        )
        .all()
    )

    restaurant_names = {
        row.id: row.name
        for row in db.query(Restaurant.id, Restaurant.name).all()
    }
    storage_place_names = {
        row.id: row.name
        for row in db.query(InvStoragePlace.id, InvStoragePlace.name).all()
    }
    subdivision_names = {
        row.id: row.name
        for row in db.query(RestaurantSubdivision.id, RestaurantSubdivision.name).all()
    }

    item_location_map: dict[int, list[InvItemLocationSummary]] = {}
    total_qty_map: dict[int, int] = {}
    warehouse_qty_map: dict[int, int] = {}

    for row in summary_rows:
        item_id = int(row.item_id)
        location_kind = str(row.location_kind)
        quantity = int(row.quantity or 0)
        if quantity <= 0:
            continue
        if location_kind == "warehouse":
            location_name = "Склад"
            warehouse_qty_map[item_id] = warehouse_qty_map.get(item_id, 0) + quantity
        elif location_kind == "restaurant":
            restaurant_name = restaurant_names.get(int(row.restaurant_id), f"Ресторан #{row.restaurant_id}")
            if row.storage_place_id is not None:
                storage_place_name = storage_place_names.get(int(row.storage_place_id), f"Место #{row.storage_place_id}")
                location_name = f"{restaurant_name} · {storage_place_name}"
            else:
                location_name = f"{restaurant_name} · Без места хранения"
        else:
            location_name = subdivision_names.get(int(row.subdivision_id), f"Подразделение #{row.subdivision_id}")

        item_location_map.setdefault(item_id, []).append(
            InvItemLocationSummary(
                location_kind=location_kind,  # type: ignore[arg-type]
                restaurant_id=int(row.restaurant_id) if row.restaurant_id is not None else None,
                storage_place_id=int(row.storage_place_id) if row.storage_place_id is not None else None,
                storage_place_name=storage_place_names.get(int(row.storage_place_id)) if row.storage_place_id is not None else None,
                subdivision_id=int(row.subdivision_id) if row.subdivision_id is not None else None,
                location_name=location_name,
                quantity=quantity,
                avg_cost=row.avg_cost,
                last_arrival_at=row.last_arrival_at,
            )
        )
        total_qty_map[item_id] = total_qty_map.get(item_id, 0) + quantity

    return [
        _item_schema(
            item,
            location_totals=item_location_map.get(item.id, []),
            total_quantity=total_qty_map.get(item.id, 0),
            warehouse_quantity=warehouse_qty_map.get(item.id, 0),
        )
        for item in items
    ]


@router.post("/items", response_model=InvItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: InvItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.put("/items/{item_id}", response_model=InvItemRead)
def update_item(
    item_id: int,
    payload: InvItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        existing = (
            db.query(InvItem)
            .filter(InvItem.code == new_code)
            .filter(InvItem.id != item_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item code already exists")
        obj.code = new_code
    next_group_id = payload.group_id if payload.group_id is not None else obj.group_id
    next_category_id = payload.category_id if payload.category_id is not None else obj.category_id
    category_scope_changed = payload.group_id is not None or payload.category_id is not None
    next_kind_id = payload.kind_id if payload.kind_id is not None else (None if category_scope_changed else obj.kind_id)

    kind_needs_resolve = (
        payload.group_id is not None
        or payload.category_id is not None
        or payload.kind_id is not None
    )
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

    should_resync_instance_codes = (
        obj.code != original["code"] or obj.use_instance_codes != original["use_instance_codes"]
    )
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


@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.post("/items/photo", response_model=AttachmentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_inventory_item_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
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

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    key = _build_inventory_photo_key(file.filename)
    upload_bytes(key, content, file.content_type or "application/octet-stream")
    url = _resolve_photo_url(key)
    return AttachmentUploadResponse(attachment_key=key, attachment_url=url or key)


@router.post("/items/{item_id}/transfer", response_model=InvItemTransferRead, status_code=status.HTTP_201_CREATED)
def transfer_item_to_department(
    item_id: int,
    payload: InvItemTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemTransferRead:
    _ensure_inventory_movements_create(current_user)
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


@router.post("/items/{item_id}/allocate", response_model=InvItemAllocateRead, status_code=status.HTTP_201_CREATED)
def allocate_item_to_location(
    item_id: int,
    payload: InvItemAllocateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemAllocateRead:
    _ensure_inventory_movements_create(current_user)

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


@router.post("/items/{item_id}/quantity", response_model=InvItemQuantityUpdateRead, status_code=status.HTTP_200_OK)
def update_item_quantity_at_location(
    item_id: int,
    payload: InvItemQuantityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvItemQuantityUpdateRead:
    _ensure_inventory_movements_create(current_user)

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

    query = db.query(InvMovementEvent)
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    if allowed_restaurants is not None:
        if allowed_restaurants:
            for condition in _event_matches_allowed_restaurants(allowed_restaurants):
                query = query.filter(condition)
        else:
            query = query.filter(
                or_(
                    InvMovementEvent.from_location_kind.is_(None),
                    InvMovementEvent.from_location_kind != "restaurant",
                ),
                or_(
                    InvMovementEvent.to_location_kind.is_(None),
                    InvMovementEvent.to_location_kind != "restaurant",
                ),
            )

    if created_from is not None:
        query = query.filter(InvMovementEvent.created_at >= created_from)
    if created_to is not None:
        query = query.filter(InvMovementEvent.created_at <= created_to)

    normalized_item_ids = _combine_int_filters(item_ids, item_ids_bracket)
    if normalized_item_ids:
        query = query.filter(InvMovementEvent.item_id.in_(normalized_item_ids))

    normalized_group_ids = _combine_int_filters(group_ids, group_ids_bracket)
    if normalized_group_ids:
        query = query.filter(InvMovementEvent.group_id.in_(normalized_group_ids))

    normalized_category_ids = _combine_int_filters(category_ids, category_ids_bracket)
    if normalized_category_ids:
        query = query.filter(InvMovementEvent.category_id.in_(normalized_category_ids))

    normalized_kind_ids = _combine_int_filters(kind_ids, kind_ids_bracket)
    if normalized_kind_ids:
        query = query.filter(InvMovementEvent.kind_id.in_(normalized_kind_ids))

    normalized_action_types = _combine_str_filters(action_types, action_types_bracket)
    if normalized_action_types:
        query = query.filter(InvMovementEvent.action_type.in_(normalized_action_types))

    normalized_actor_ids = _combine_int_filters(actor_ids, actor_ids_bracket)
    if normalized_actor_ids:
        query = query.filter(InvMovementEvent.actor_id.in_(normalized_actor_ids))

    normalized_object_ids = _combine_str_filters(object_ids, object_ids_bracket)
    object_conditions = []
    for object_id in normalized_object_ids:
        if object_id == "warehouse":
            object_conditions.append(
                or_(
                    InvMovementEvent.from_location_kind == "warehouse",
                    InvMovementEvent.to_location_kind == "warehouse",
                )
            )
            continue
        if object_id.startswith("restaurant:"):
            try:
                rest_id = int(object_id.split(":", 1)[1])
            except ValueError:
                continue
            object_conditions.append(
                or_(
                    InvMovementEvent.from_restaurant_id == rest_id,
                    InvMovementEvent.to_restaurant_id == rest_id,
                )
            )
            continue
        if object_id.startswith("subdivision:"):
            try:
                sub_id = int(object_id.split(":", 1)[1])
            except ValueError:
                continue
            object_conditions.append(
                or_(
                    InvMovementEvent.from_subdivision_id == sub_id,
                    InvMovementEvent.to_subdivision_id == sub_id,
                )
            )
            continue
    if object_conditions:
        query = query.filter(or_(*object_conditions))

    if q:
        stripped = q.strip()
        if stripped:
            term = f"%{stripped}%"
            query = query.filter(
                or_(
                    InvMovementEvent.item_code.ilike(term),
                    InvMovementEvent.item_name.ilike(term),
                    InvMovementEvent.comment.ilike(term),
                )
            )

    events = (
        query.order_by(InvMovementEvent.created_at.desc(), InvMovementEvent.id.desc())
        .limit(limit)
        .all()
    )
    if not events:
        return []

    actor_id_set = {event.actor_id for event in events if event.actor_id is not None}
    item_id_set = {event.item_id for event in events if event.item_id is not None}
    group_id_set = {event.group_id for event in events if event.group_id is not None}
    category_id_set = {event.category_id for event in events if event.category_id is not None}
    kind_id_set = {event.kind_id for event in events if event.kind_id is not None}
    restaurant_id_set = {
        rest_id
        for event in events
        for rest_id in [event.from_restaurant_id, event.to_restaurant_id]
        if rest_id is not None
    }
    subdivision_id_set = {
        sub_id
        for event in events
        for sub_id in [event.from_subdivision_id, event.to_subdivision_id]
        if sub_id is not None
    }
    storage_place_id_set = {
        place_id
        for event in events
        for place_id in [event.from_storage_place_id, event.to_storage_place_id]
        if place_id is not None
    }

    actor_rows = (
        db.query(User.id, User.first_name, User.last_name, User.middle_name, User.username)
        .filter(User.id.in_(actor_id_set))
        .all()
        if actor_id_set
        else []
    )
    actor_map = {
        int(row.id): _compose_user_name(
            first_name=row.first_name,
            last_name=row.last_name,
            middle_name=row.middle_name,
            username=row.username,
            user_id=row.id,
        )
        for row in actor_rows
    }

    item_rows = (
        db.query(InvItem.id, InvItem.code, InvItem.name)
        .filter(InvItem.id.in_(item_id_set))
        .all()
        if item_id_set
        else []
    )
    item_map = {int(row.id): row for row in item_rows}

    group_map = {
        int(row.id): row.name
        for row in (
            db.query(InvGroup.id, InvGroup.name).filter(InvGroup.id.in_(group_id_set)).all()
            if group_id_set
            else []
        )
    }
    category_map = {
        int(row.id): row.name
        for row in (
            db.query(InvCategory.id, InvCategory.name).filter(InvCategory.id.in_(category_id_set)).all()
            if category_id_set
            else []
        )
    }
    kind_map = {
        int(row.id): row.name
        for row in (
            db.query(InvKind.id, InvKind.name).filter(InvKind.id.in_(kind_id_set)).all()
            if kind_id_set
            else []
        )
    }
    restaurant_names, storage_place_names, subdivision_names = _load_location_name_maps(
        db,
        restaurant_ids={int(value) for value in restaurant_id_set},
        storage_place_ids={int(value) for value in storage_place_id_set},
        subdivision_ids={int(value) for value in subdivision_id_set},
    )

    response: list[InvMovementEventRead] = []
    for event in events:
        item_row = item_map.get(event.item_id) if event.item_id is not None else None
        response.append(
            InvMovementEventRead(
                id=event.id,
                created_at=event.created_at,
                action_type=event.action_type,
                action_label=_movement_action_label(event.action_type),
                actor_id=event.actor_id,
                actor_name=actor_map.get(event.actor_id) if event.actor_id is not None else None,
                item_id=event.item_id,
                item_code=event.item_code or (item_row.code if item_row is not None else None),
                item_name=event.item_name or (item_row.name if item_row is not None else None),
                group_id=event.group_id,
                group_name=group_map.get(event.group_id) if event.group_id is not None else None,
                category_id=event.category_id,
                category_name=category_map.get(event.category_id) if event.category_id is not None else None,
                kind_id=event.kind_id,
                kind_name=kind_map.get(event.kind_id) if event.kind_id is not None else None,
                quantity=event.quantity,
                from_location_kind=event.from_location_kind,
                from_restaurant_id=event.from_restaurant_id,
                from_storage_place_id=event.from_storage_place_id,
                from_subdivision_id=event.from_subdivision_id,
                from_location_name=_location_name(
                    location_kind=event.from_location_kind,
                    restaurant_id=event.from_restaurant_id,
                    storage_place_id=event.from_storage_place_id,
                    subdivision_id=event.from_subdivision_id,
                    restaurant_names=restaurant_names,
                    storage_place_names=storage_place_names,
                    subdivision_names=subdivision_names,
                ),
                to_location_kind=event.to_location_kind,
                to_restaurant_id=event.to_restaurant_id,
                to_storage_place_id=event.to_storage_place_id,
                to_subdivision_id=event.to_subdivision_id,
                to_location_name=_location_name(
                    location_kind=event.to_location_kind,
                    restaurant_id=event.to_restaurant_id,
                    storage_place_id=event.to_storage_place_id,
                    subdivision_id=event.to_subdivision_id,
                    restaurant_names=restaurant_names,
                    storage_place_names=storage_place_names,
                    subdivision_names=subdivision_names,
                ),
                field=event.field,
                old_value=event.old_value,
                new_value=event.new_value,
                comment=event.comment,
            )
        )

    return response


# ---- Item records (legacy movements) ----
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

    # Apply stock adjustments
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


# ---- Balance endpoint ----
@router.get("/balance", response_model=list[InventoryBalance])
def list_inventory_balance(
    restaurant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InventoryBalance]:
    _ensure_inventory_balance_view(current_user)

    allowed_restaurants = get_user_restaurant_ids(db, current_user)

    restaurant_ids: list[int]
    if restaurant_id is not None:
        _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)
        restaurant_ids = [restaurant_id]
    else:
        if allowed_restaurants is None:
            restaurant_ids = [row[0] for row in db.query(Restaurant.id).order_by(Restaurant.id.asc()).all()]
        else:
            restaurant_ids = sorted(allowed_restaurants)

    if not restaurant_ids:
        return []

    rows = (
        db.query(
            InvItemStock.restaurant_id.label("restaurant_id"),
            InvItemStock.item_id.label("item_id"),
            InvItem.name.label("item_name"),
            InvItemStock.quantity.label("quantity"),
            InvItemStock.avg_cost.label("avg_cost"),
        )
        .join(InvItem, InvItem.id == InvItemStock.item_id)
        .filter(InvItemStock.restaurant_id.in_(restaurant_ids))
        .order_by(InvItemStock.restaurant_id.asc(), InvItem.name.asc())
        .all()
    )

    count_rows = (
        db.query(
            InvItemRecord.restaurant_id.label("restaurant_id"),
            InvItemRecord.item_id.label("item_id"),
            func.count(InvItemRecord.id).label("record_count"),
        )
        .filter(InvItemRecord.restaurant_id.in_(restaurant_ids))
        .group_by(InvItemRecord.restaurant_id, InvItemRecord.item_id)
        .all()
    )

    record_count_map: dict[tuple[int, int], int] = {
        (int(row.restaurant_id), int(row.item_id)): int(row.record_count or 0) for row in count_rows
    }

    result_map: dict[int, InventoryBalance] = {}
    for rest_id in restaurant_ids:
        result_map[rest_id] = InventoryBalance(
            restaurant_id=rest_id,
            total_quantity=0,
            total_cost=Decimal("0"),
            record_count=0,
            items=[],
        )

    for row in rows:
        rest_id = int(row.restaurant_id)
        item_quantity = int(row.quantity or 0)
        avg_cost = Decimal(row.avg_cost or 0)
        item_total_cost = avg_cost * item_quantity
        record_count = record_count_map.get((rest_id, int(row.item_id)), 0)

        entry = result_map.get(rest_id)
        if entry is None:
            entry = InventoryBalance(
                restaurant_id=rest_id,
                total_quantity=0,
                total_cost=Decimal("0"),
                record_count=0,
                items=[],
            )
            result_map[rest_id] = entry

        entry.items.append(
            InventoryBalanceItem(
                item_id=int(row.item_id),
                item_name=str(row.item_name),
                total_quantity=item_quantity,
                total_cost=item_total_cost,
                record_count=record_count,
            )
        )
        entry.total_quantity += item_quantity
        entry.total_cost += item_total_cost
        entry.record_count += record_count

    return [result_map[rest_id] for rest_id in restaurant_ids]


@router.get("/balance/{restaurant_id}", response_model=InventoryBalance)
def get_restaurant_balance(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryBalance:
    _ensure_inventory_balance_view(current_user)
    balances = list_inventory_balance(restaurant_id=restaurant_id, db=db, current_user=current_user)
    return balances[0] if balances else InventoryBalance(
        restaurant_id=restaurant_id,
        total_quantity=0,
        total_cost=Decimal("0"),
        record_count=0,
        items=[],
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
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)

    item = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    normalized_storage_place_id = _resolve_storage_place(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id,
        storage_place_id=storage_place_id,
        require_active=False,
    )

    stock_row = (
        db.query(InvItemStock.quantity, InvItemStock.avg_cost)
        .filter(InvItemStock.restaurant_id == restaurant_id, InvItemStock.item_id == item_id)
        .first()
    )
    current_instances = (
        db.query(InvItemInstance)
        .filter(
            InvItemInstance.item_id == item_id,
            InvItemInstance.location_kind == "restaurant",
            InvItemInstance.restaurant_id == restaurant_id,
        )
        .filter(
            InvItemInstance.storage_place_id == normalized_storage_place_id
            if normalized_storage_place_id is not None
            else True
        )
        .order_by(InvItemInstance.sequence_no.asc())
        .all()
    )
    if stock_row is None and not current_instances:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item is not available in this restaurant")

    arrival_events = (
        db.query(InvMovementEvent)
        .filter(
            InvMovementEvent.item_id == item_id,
            InvMovementEvent.to_location_kind == "restaurant",
            InvMovementEvent.to_restaurant_id == restaurant_id,
            InvMovementEvent.action_type.in_(["quantity_increase", "transfer", "quantity_adjusted"]),
        )
        .filter(
            InvMovementEvent.to_storage_place_id == normalized_storage_place_id
            if normalized_storage_place_id is not None
            else True
        )
        .order_by(InvMovementEvent.created_at.desc(), InvMovementEvent.id.desc())
        .limit(60)
        .all()
    )

    instance_events: list[InvItemInstanceEvent] = []
    instance_event_type_map = _load_instance_event_type_map(db) if item.use_instance_codes else {}
    if item.use_instance_codes:
        instance_events = (
            db.query(InvItemInstanceEvent)
            .filter(
                InvItemInstanceEvent.item_id == item_id,
                InvItemInstanceEvent.instance_code_snapshot.isnot(None),
                _instance_event_matches_restaurant(restaurant_id),
            )
            .filter(
                _instance_event_matches_storage_place(normalized_storage_place_id)
                if normalized_storage_place_id is not None
                else True
            )
            .order_by(InvItemInstanceEvent.created_at.desc(), InvItemInstanceEvent.id.desc())
            .limit(800)
            .all()
        )

    actor_ids = {
        *{event.actor_id for event in arrival_events if event.actor_id is not None},
        *{event.actor_id for event in instance_events if event.actor_id is not None},
    }
    actor_map = _load_actor_name_map(db, {int(actor_id) for actor_id in actor_ids if actor_id is not None})

    restaurant_ids = {restaurant_id}
    storage_place_ids: set[int] = set()
    subdivision_ids: set[int] = set()
    for event in arrival_events:
        if event.from_restaurant_id is not None:
            restaurant_ids.add(int(event.from_restaurant_id))
        if event.to_restaurant_id is not None:
            restaurant_ids.add(int(event.to_restaurant_id))
        if event.from_storage_place_id is not None:
            storage_place_ids.add(int(event.from_storage_place_id))
        if event.to_storage_place_id is not None:
            storage_place_ids.add(int(event.to_storage_place_id))
        if event.from_subdivision_id is not None:
            subdivision_ids.add(int(event.from_subdivision_id))
        if event.to_subdivision_id is not None:
            subdivision_ids.add(int(event.to_subdivision_id))
    for event in instance_events:
        if event.from_restaurant_id is not None:
            restaurant_ids.add(int(event.from_restaurant_id))
        if event.to_restaurant_id is not None:
            restaurant_ids.add(int(event.to_restaurant_id))
        if event.from_storage_place_id is not None:
            storage_place_ids.add(int(event.from_storage_place_id))
        if event.to_storage_place_id is not None:
            storage_place_ids.add(int(event.to_storage_place_id))
        if event.from_subdivision_id is not None:
            subdivision_ids.add(int(event.from_subdivision_id))
        if event.to_subdivision_id is not None:
            subdivision_ids.add(int(event.to_subdivision_id))

    restaurant_names, storage_place_names, subdivision_names = _load_location_name_maps(
        db,
        restaurant_ids=restaurant_ids,
        storage_place_ids=storage_place_ids,
        subdivision_ids=subdivision_ids,
    )

    arrivals = [
        InventoryRestaurantItemArrivalRead(
            id=event.id,
            created_at=event.created_at,
            action_type=event.action_type,
            action_label=_movement_action_label(event.action_type),
            actor_name=actor_map.get(event.actor_id) if event.actor_id is not None else None,
            quantity=int(event.quantity or 0),
            source_location_name=_location_name(
                location_kind=event.from_location_kind,
                restaurant_id=event.from_restaurant_id,
                storage_place_id=event.from_storage_place_id,
                subdivision_id=event.from_subdivision_id,
                restaurant_names=restaurant_names,
                storage_place_names=storage_place_names,
                subdivision_names=subdivision_names,
            ),
            target_location_name=_location_name(
                location_kind=event.to_location_kind,
                restaurant_id=event.to_restaurant_id,
                storage_place_id=event.to_storage_place_id,
                subdivision_id=event.to_subdivision_id,
                restaurant_names=restaurant_names,
                storage_place_names=storage_place_names,
                subdivision_names=subdivision_names,
            ),
            comment=event.comment,
        )
        for event in arrival_events
    ]

    summary_map: dict[str, dict] = {}
    for instance in current_instances:
        code = instance.instance_code or f"{item.code}-{instance.sequence_no}"
        summary_map[code] = {
            "instance_id": instance.id,
            "instance_code": code,
            "sequence_no": instance.sequence_no,
            "purchase_cost": instance.purchase_cost,
            "arrived_at": instance.arrived_at,
            "is_current": True,
            "current_location_name": _location_name(
                location_kind="restaurant",
                restaurant_id=restaurant_id,
                storage_place_id=instance.storage_place_id,
                subdivision_id=None,
                restaurant_names=restaurant_names,
                storage_place_names=storage_place_names,
                subdivision_names=subdivision_names,
            ),
            "current_storage_place_id": instance.storage_place_id,
            "current_storage_place_name": storage_place_names.get(int(instance.storage_place_id)) if instance.storage_place_id is not None else None,
            "status_key": "in_stock",
            "status_label": "В ресторане",
            "last_event_at": None,
            "last_event_action": None,
            "last_event_label": None,
            "last_comment": None,
        }

    for event in instance_events:
        code = (event.instance_code_snapshot or "").strip()
        if not code:
            continue
        summary = summary_map.setdefault(
            code,
            {
                "instance_id": event.instance_id,
                "instance_code": code,
                "sequence_no": event.sequence_no,
                "purchase_cost": event.purchase_cost,
                "arrived_at": None,
                "is_current": False,
                "current_location_name": None,
                "status_key": "history",
                "status_label": "История",
                "last_event_at": None,
                "last_event_action": None,
                "last_event_label": None,
                "last_comment": None,
            },
        )
        if summary["last_event_at"] is None:
            summary["last_event_at"] = event.created_at
            summary["last_event_action"] = event.action_type
            summary["last_event_label"] = _instance_event_action_label(
                event.action_type,
                event_type_map=instance_event_type_map,
            )
            summary["last_comment"] = event.comment
            if not summary["is_current"]:
                if event.action_type == "writeoff":
                    summary["status_key"] = "written_off"
                    summary["status_label"] = "Списан"
                elif event.action_type == "transfer" and event.from_restaurant_id == restaurant_id:
                    summary["status_key"] = "transferred_out"
                    summary["status_label"] = "Переведен"
                    summary["current_location_name"] = _location_name(
                        location_kind=event.to_location_kind,
                        restaurant_id=event.to_restaurant_id,
                        storage_place_id=event.to_storage_place_id,
                        subdivision_id=event.to_subdivision_id,
                        restaurant_names=restaurant_names,
                        storage_place_names=storage_place_names,
                        subdivision_names=subdivision_names,
                    )
                else:
                    summary["status_key"] = "history"
                    summary["status_label"] = _instance_event_action_label(
                        event.action_type,
                        event_type_map=instance_event_type_map,
                    )
        if summary["arrived_at"] is None and event.action_type in {"quantity_increase", "quantity_adjusted", "transfer"}:
            summary["arrived_at"] = event.created_at

    for summary in summary_map.values():
        if not summary["is_current"]:
            continue
        event_config = instance_event_type_map.get(str(summary["last_event_action"] or ""))
        status_key = _normalize_inventory_string(str(event_config.get("status_key") or "")) if event_config else None
        status_label = _normalize_inventory_string(str(event_config.get("status_label") or "")) if event_config else None
        if status_label:
            summary["status_key"] = status_key or "repair"
            summary["status_label"] = status_label
        else:
            summary["status_key"] = "in_stock"
            summary["status_label"] = "В ресторане"

    instances = [
        InventoryItemInstanceSummaryRead(**payload)
        for payload in sorted(
            summary_map.values(),
            key=lambda row: (
                0 if row["is_current"] else 1,
                str(row["instance_code"]).lower(),
            ),
        )
    ]

    return InventoryRestaurantItemCardRead(
        item_id=item_id,
        restaurant_id=restaurant_id,
        quantity=len(current_instances) if normalized_storage_place_id is not None else (int(stock_row.quantity or 0) if stock_row is not None else len(current_instances)),
        avg_cost=(
            (sum(Decimal(instance.purchase_cost or 0) for instance in current_instances) / Decimal(len(current_instances))).quantize(Decimal("0.01"))
            if current_instances and normalized_storage_place_id is not None
            else (stock_row.avg_cost if stock_row is not None else None)
        ),
        last_arrival_at=max((instance.arrived_at for instance in current_instances), default=None),
        storage_place_id=normalized_storage_place_id,
        instance_tracking_enabled=bool(item.use_instance_codes),
        arrivals=arrivals,
        instances=instances,
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
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    _ensure_restaurant_allowed(allowed_restaurants, restaurant_id)

    item = db.query(InvItem).filter(InvItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    normalized_storage_place_id = _resolve_storage_place(
        db=db,
        current_user=current_user,
        restaurant_id=restaurant_id,
        storage_place_id=storage_place_id,
        require_active=False,
    )

    normalized_code = instance_code.strip()
    if not normalized_code:
        return []

    events = (
        db.query(InvItemInstanceEvent)
        .filter(
            InvItemInstanceEvent.item_id == item_id,
            InvItemInstanceEvent.instance_code_snapshot == normalized_code,
            _instance_event_matches_restaurant(restaurant_id),
        )
        .filter(
            _instance_event_matches_storage_place(normalized_storage_place_id)
            if normalized_storage_place_id is not None
            else True
        )
        .order_by(InvItemInstanceEvent.created_at.desc(), InvItemInstanceEvent.id.desc())
        .limit(200)
        .all()
    )
    if not events:
        return []
    instance_event_type_map = _load_instance_event_type_map(db)

    actor_map = _load_actor_name_map(
        db,
        {int(event.actor_id) for event in events if event.actor_id is not None},
    )
    restaurant_ids = {
        int(rest_id)
        for event in events
        for rest_id in [event.from_restaurant_id, event.to_restaurant_id]
        if rest_id is not None
    }
    restaurant_ids.add(restaurant_id)
    subdivision_ids = {
        int(sub_id)
        for event in events
        for sub_id in [event.from_subdivision_id, event.to_subdivision_id]
        if sub_id is not None
    }
    storage_place_ids = {
        int(place_id)
        for event in events
        for place_id in [event.from_storage_place_id, event.to_storage_place_id]
        if place_id is not None
    }
    restaurant_names, storage_place_names, subdivision_names = _load_location_name_maps(
        db,
        restaurant_ids=restaurant_ids,
        storage_place_ids=storage_place_ids,
        subdivision_ids=subdivision_ids,
    )
    return [
        _serialize_instance_event(
            event,
            actor_map=actor_map,
            restaurant_names=restaurant_names,
            storage_place_names=storage_place_names,
            subdivision_names=subdivision_names,
            event_type_map=instance_event_type_map,
        )
        for event in events
    ]


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
    event_type = (
        db.query(InvInstanceEventType)
        .filter(InvInstanceEventType.id == payload.event_type_id)
        .first()
    )
    if not event_type or not bool(event_type.is_manual) or not bool(event_type.is_active):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported instance event action")

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


@router.get("/items/{item_id}/changes", response_model=list[InvItemChangeRead])
def list_item_changes(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvItemChange]:
    ensure_permissions(
        current_user,
        PermissionCode.INVENTORY_VIEW,
        PermissionKey.INVENTORY_NOMENCLATURE_VIEW,
    )
    changes = (
        db.query(InvItemChange)
        .filter(InvItemChange.item_id == item_id)
        .order_by(InvItemChange.changed_at.desc())
        .all()
    )
    return changes
