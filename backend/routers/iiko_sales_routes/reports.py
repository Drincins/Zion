from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import User
from backend.services.iiko_sales_order_item_reports import (
    list_items_payload as _list_items_payload,
    list_orders_payload as _list_orders_payload,
)
from backend.services.iiko_sales_waiter_reports import (
    list_waiter_sales_options_cached_payload as _list_waiter_sales_options_cached_payload,
    list_waiter_sales_report_payload as _list_waiter_sales_report_payload,
    list_waiter_sales_report_positions_payload as _list_waiter_sales_report_positions_payload,
)
from backend.services.permissions import ensure_permissions
from backend.utils import get_current_user

from .common import (
    SALES_REPORT_VIEW_PERMISSIONS,
    can_view_sales_money,
)

router = APIRouter()


@router.get("/waiter-sales-report/options")
def list_waiter_sales_report_options(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_id: Optional[int] = Query(None),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    positions_limit: int = Query(500, ge=50, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    return _list_waiter_sales_options_cached_payload(
        db,
        current_user,
        from_date=from_date,
        to_date=to_date,
        restaurant_id=restaurant_id,
        waiter_mode=waiter_mode,
        deleted_mode=deleted_mode,
        positions_limit=positions_limit,
    )


@router.get("/waiter-sales-report")
def list_waiter_sales_report(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_id: Optional[int] = Query(None),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    waiter_user_id: Optional[int] = Query(None),
    waiter_iiko_id: Optional[str] = Query(None),
    waiter_iiko_code: Optional[str] = Query(None),
    include_payment_types: Optional[List[str]] = Query(None),
    include_groups: Optional[List[str]] = Query(None),
    exclude_groups: Optional[List[str]] = Query(None),
    include_categories: Optional[List[str]] = Query(None),
    exclude_categories: Optional[List[str]] = Query(None),
    include_positions: Optional[List[str]] = Query(None),
    exclude_positions: Optional[List[str]] = Query(None),
    include_halls: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    return _list_waiter_sales_report_payload(
        db,
        current_user,
        from_date=from_date,
        to_date=to_date,
        restaurant_id=restaurant_id,
        waiter_mode=waiter_mode,
        deleted_mode=deleted_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=waiter_iiko_id,
        waiter_iiko_code=waiter_iiko_code,
        include_payment_types=include_payment_types,
        include_groups=include_groups,
        exclude_groups=exclude_groups,
        include_categories=include_categories,
        exclude_categories=exclude_categories,
        include_positions=include_positions,
        exclude_positions=exclude_positions,
        include_halls=include_halls,
        can_view_money=can_view_sales_money(current_user),
    )


@router.get("/waiter-sales-report/positions")
def list_waiter_sales_report_positions(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_id: Optional[int] = Query(None),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    waiter_user_id: Optional[int] = Query(None),
    waiter_iiko_id: Optional[str] = Query(None),
    waiter_iiko_code: Optional[str] = Query(None),
    include_payment_types: Optional[List[str]] = Query(None),
    include_groups: Optional[List[str]] = Query(None),
    exclude_groups: Optional[List[str]] = Query(None),
    include_categories: Optional[List[str]] = Query(None),
    exclude_categories: Optional[List[str]] = Query(None),
    include_positions: Optional[List[str]] = Query(None),
    exclude_positions: Optional[List[str]] = Query(None),
    include_halls: Optional[List[str]] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    try:
        return _list_waiter_sales_report_positions_payload(
            db,
            current_user,
            from_date=from_date,
            to_date=to_date,
            restaurant_id=restaurant_id,
            waiter_mode=waiter_mode,
            deleted_mode=deleted_mode,
            waiter_user_id=waiter_user_id,
            waiter_iiko_id=waiter_iiko_id,
            waiter_iiko_code=waiter_iiko_code,
            include_payment_types=include_payment_types,
            include_groups=include_groups,
            exclude_groups=exclude_groups,
            include_categories=include_categories,
            exclude_categories=exclude_categories,
            include_positions=include_positions,
            exclude_positions=exclude_positions,
            include_halls=include_halls,
            limit=limit,
            can_view_money=can_view_sales_money(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/orders")
def list_orders(
    restaurant_id: Optional[int] = Query(None),
    source_restaurant_id: Optional[int] = Query(None),
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    waiter_user_id: Optional[int] = Query(None),
    waiter_iiko_id: Optional[str] = Query(None),
    waiter_iiko_code: Optional[str] = Query(None),
    dish_code: Optional[str] = Query(None),
    include_payment_types: Optional[List[str]] = Query(None),
    include_groups: Optional[List[str]] = Query(None),
    include_categories: Optional[List[str]] = Query(None),
    include_positions: Optional[List[str]] = Query(None),
    include_halls: Optional[List[str]] = Query(None),
    include_departments: Optional[List[str]] = Query(None),
    include_tables: Optional[List[str]] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    with_meta: bool = Query(False, description="Return object {items,total,limit,offset} instead of plain list"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    return _list_orders_payload(
        db,
        current_user,
        restaurant_id=restaurant_id,
        source_restaurant_id=source_restaurant_id,
        from_date=from_date,
        to_date=to_date,
        dish_code=dish_code,
        deleted_mode=deleted_mode,
        waiter_mode=waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=waiter_iiko_id,
        waiter_iiko_code=waiter_iiko_code,
        include_payment_types=include_payment_types,
        include_groups=include_groups,
        include_categories=include_categories,
        include_positions=include_positions,
        include_halls=include_halls,
        include_departments=include_departments,
        include_tables=include_tables,
        limit=limit,
        offset=offset,
        with_meta=with_meta,
    )


@router.get("/items")
def list_items(
    restaurant_id: Optional[int] = Query(None),
    source_restaurant_id: Optional[int] = Query(None),
    order_id: Optional[UUID] = Query(None, description="Local order UUID"),
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    dish_code: Optional[str] = Query(None),
    deleted_mode: str = Query("all", description="all | only_deleted | without_deleted"),
    waiter_mode: str = Query("order_close", description="order_close | item_punch"),
    waiter_user_id: Optional[int] = Query(None),
    waiter_iiko_id: Optional[str] = Query(None),
    waiter_iiko_code: Optional[str] = Query(None),
    include_payment_types: Optional[List[str]] = Query(None),
    include_groups: Optional[List[str]] = Query(None),
    include_categories: Optional[List[str]] = Query(None),
    include_positions: Optional[List[str]] = Query(None),
    include_halls: Optional[List[str]] = Query(None),
    include_departments: Optional[List[str]] = Query(None),
    include_tables: Optional[List[str]] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    with_meta: bool = Query(False, description="Return object {items,total,limit,offset} instead of plain list"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_VIEW_PERMISSIONS)
    return _list_items_payload(
        db,
        current_user,
        restaurant_id=restaurant_id,
        source_restaurant_id=source_restaurant_id,
        order_id=order_id,
        from_date=from_date,
        to_date=to_date,
        dish_code=dish_code,
        deleted_mode=deleted_mode,
        waiter_mode=waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=waiter_iiko_id,
        waiter_iiko_code=waiter_iiko_code,
        include_payment_types=include_payment_types,
        include_groups=include_groups,
        include_categories=include_categories,
        include_positions=include_positions,
        include_halls=include_halls,
        include_departments=include_departments,
        include_tables=include_tables,
        limit=limit,
        offset=offset,
        with_meta=with_meta,
        can_view_money=can_view_sales_money(current_user),
    )
