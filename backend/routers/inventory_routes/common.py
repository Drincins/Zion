from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import (
    InvCategory,
    InvGroup,
    InvInstanceEventType,
    InvItem,
    InvItemChange,
    InvItemInstance,
    InvItemInstanceEvent,
    InvItemRecord,
    InvItemStock,
    InvKind,
    InvMovementEvent,
    InvStoragePlace,
    Restaurant,
    RestaurantSubdivision,
    User,
)
from backend.schemas import (
    AttachmentUploadResponse,
    InvCategoryCreate,
    InvCategoryRead,
    InvCategoryUpdate,
    InvGroupCreate,
    InvGroupRead,
    InvGroupUpdate,
    InvItemAllocateCreate,
    InvItemAllocateRead,
    InvItemChangeRead,
    InvItemCreate,
    InvItemLocationSummary,
    InvItemQuantityUpdate,
    InvItemQuantityUpdateRead,
    InvItemRead,
    InvItemRecordCreate,
    InvItemRecordRead,
    InvItemRecordUpdate,
    InvItemTransferCreate,
    InvItemTransferRead,
    InvItemUpdate,
    InvKindCreate,
    InvKindRead,
    InvKindUpdate,
    InvMovementEventRead,
    InventoryBalance,
    InventoryDepartmentOption,
    InventoryInstanceEventTypeCreate,
    InventoryInstanceEventTypeRead,
    InventoryInstanceEventTypeUpdate,
    InventoryItemInstanceEventCreate,
    InventoryItemInstanceEventRead,
    InventoryMovementActionOption,
    InventoryRestaurantItemCardRead,
    InventoryStoragePlaceCreate,
    InventoryStoragePlaceRead,
    InventoryStoragePlaceUpdate,
)
from backend.routers.inventory_routes.helpers import (
    _build_instance_codes_response,
    _build_inventory_photo_key,
    _create_item_instances,
    _ensure_restaurant_allowed,
    _generate_item_code,
    _log_item_change,
    _log_item_instance_events,
    _log_movement_event,
    _resolve_kind_for_item,
    _resolve_location,
    _resolve_storage_place,
    _sync_item_instance_codes,
    _update_stock,
)
from backend.routers.inventory_routes.permissions import (
    _ensure_inventory_balance_view,
    _ensure_inventory_lookup_access,
    _ensure_inventory_movements_create,
    _ensure_inventory_movements_delete,
    _ensure_inventory_movements_edit,
    _ensure_inventory_movements_view,
    _ensure_inventory_nomenclature_create,
    _ensure_inventory_nomenclature_delete,
    _ensure_inventory_nomenclature_edit,
    _ensure_inventory_nomenclature_view,
    ensure_permissions,
    PermissionCode,
    PermissionKey,
)
from backend.routers.inventory_routes.serializers import (
    DEFAULT_INSTANCE_EVENT_TYPE_MAP,
    DEFAULT_INSTANCE_EVENT_TYPES,
    MOVEMENT_ACTION_LABELS,
    _combine_int_filters,
    _combine_str_filters,
    _event_matches_allowed_restaurants,
    _instance_event_matches_restaurant,
    _instance_event_matches_storage_place,
    _item_schema,
    _load_actor_name_map,
    _load_instance_event_type_map,
    _load_location_name_maps,
    _movement_action_label,
    _normalize_instance_event_type_code,
    _normalize_inventory_string,
    _record_schema,
    _resolve_photo_url,
    _serialize_instance_event,
    _serialize_instance_event_type,
    _serialize_storage_place,
)
from backend.services.inventory_movements import (
    allocate_item as run_inventory_allocate_item,
    transfer_item as run_inventory_transfer_item,
    update_item_quantity as run_inventory_update_item_quantity,
)
from backend.services.inventory_queries import (
    get_restaurant_balance as load_inventory_restaurant_balance,
    get_restaurant_item_card as load_inventory_restaurant_item_card,
    list_inventory_balances as load_inventory_balances,
    list_movement_events as load_inventory_movement_events,
    list_restaurant_item_instance_events as load_inventory_restaurant_item_instance_events,
)
from backend.services.s3 import generate_presigned_url, upload_bytes
from backend.utils import get_current_user, get_user_restaurant_ids
