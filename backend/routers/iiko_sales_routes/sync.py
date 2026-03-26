from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import User
from backend.schemas.iiko_sales import (
    ClearIikoSalesRequest,
    SyncIikoSalesNetworkRequest,
    SyncIikoSalesRequest,
)
from backend.services.iiko_sales_sync_runtime import (
    clear_iiko_sales_payload as _clear_iiko_sales_payload,
    sync_iiko_sales_network_payload as _sync_iiko_sales_network_payload,
    sync_iiko_sales_payload as _sync_iiko_sales_payload,
    sync_sales_orders_and_items_resilient as _sync_sales_orders_and_items_resilient,
)
from backend.services.permissions import PermissionCode, ensure_permissions
from backend.utils import get_current_user

router = APIRouter()


@router.post("/sync")
def sync_iiko_sales(
    payload: SyncIikoSalesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _sync_iiko_sales_payload(
        db,
        current_user,
        restaurant_id=payload.restaurant_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
        sync_runner=_sync_sales_orders_and_items_resilient,
        sync_actor=f"user:{int(current_user.id)}",
    )


@router.post("/sync-network")
def sync_iiko_sales_network(
    payload: SyncIikoSalesNetworkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _sync_iiko_sales_network_payload(
        db,
        current_user,
        from_date=payload.from_date,
        to_date=payload.to_date,
        restaurant_ids=payload.restaurant_ids,
        stop_on_error=payload.stop_on_error,
        sync_runner=_sync_sales_orders_and_items_resilient,
        sync_actor=f"user:{int(current_user.id)}",
    )


@router.post("/clear")
def clear_iiko_sales(
    payload: ClearIikoSalesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _clear_iiko_sales_payload(
        db,
        current_user,
        restaurant_id=payload.restaurant_id,
    )
