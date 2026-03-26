from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import User
from backend.schemas.iiko_sales import (
    CreateIikoNonCashTypeRequest,
    UpdateIikoNonCashEmployeeLimitRequest,
    UpdateIikoNonCashTypeRequest,
    UpdateIikoPaymentMethodRequest,
    UpsertIikoNonCashEmployeeLimitRequest,
)
from backend.services.iiko_sales_finance_reports import (
    list_non_cash_consumption_payload as _list_non_cash_consumption_payload,
    list_revenue_by_payment_methods_payload as _list_revenue_by_payment_methods_payload,
)
from backend.services.iiko_sales_finance_refs import (
    create_non_cash_type as _create_non_cash_type,
    delete_non_cash_employee_limit as _delete_non_cash_employee_limit,
    list_non_cash_employee_limits_payload as _list_non_cash_employee_limits_payload,
    list_non_cash_types_payload as _list_non_cash_types_payload,
    list_payment_methods_payload as _list_payment_methods_payload,
    update_non_cash_employee_limit as _update_non_cash_employee_limit,
    update_non_cash_type as _update_non_cash_type,
    update_payment_method as _update_payment_method,
    upsert_non_cash_employee_limit as _upsert_non_cash_employee_limit,
)
from backend.services.permissions import PermissionCode, ensure_permissions
from backend.utils import get_current_user

from .common import SALES_REPORT_MONEY_PERMISSIONS

router = APIRouter()


@router.get("/payment-methods")
def list_payment_methods(
    include_inactive: bool = Query(True),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    return _list_payment_methods_payload(
        db,
        current_user,
        include_inactive=include_inactive,
        category=category,
    )


@router.patch("/payment-methods/{guid}")
def update_payment_method(
    guid: str,
    payload: UpdateIikoPaymentMethodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _update_payment_method(
        db,
        current_user,
        guid=guid,
        category=payload.category,
        comment=payload.comment,
        is_active=payload.is_active,
    )


@router.get("/non-cash-types")
def list_non_cash_types(
    include_inactive: bool = Query(True),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    return _list_non_cash_types_payload(
        db,
        current_user,
        include_inactive=include_inactive,
        category=category,
    )


@router.post("/non-cash-types")
def create_non_cash_type(
    payload: CreateIikoNonCashTypeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _create_non_cash_type(
        db,
        current_user,
        non_cash_type_id=payload.id,
        name=payload.name,
        category=payload.category,
        comment=payload.comment,
        is_active=payload.is_active,
    )


@router.patch("/non-cash-types/{non_cash_type_id}")
def update_non_cash_type(
    non_cash_type_id: str,
    payload: UpdateIikoNonCashTypeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _update_non_cash_type(
        db,
        current_user,
        non_cash_type_id=non_cash_type_id,
        category=payload.category,
        comment=payload.comment,
        is_active=payload.is_active,
    )


@router.get("/non-cash-employee-limits")
def list_non_cash_employee_limits(
    include_inactive: bool = Query(True),
    non_cash_type_id: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    return _list_non_cash_employee_limits_payload(
        db,
        current_user,
        include_inactive=include_inactive,
        non_cash_type_id=non_cash_type_id,
        user_id=user_id,
    )


@router.put("/non-cash-employee-limits")
def upsert_non_cash_employee_limit(
    payload: UpsertIikoNonCashEmployeeLimitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _upsert_non_cash_employee_limit(
        db,
        current_user,
        non_cash_type_id=payload.non_cash_type_id,
        user_id=payload.user_id,
        period_type=payload.period_type,
        limit_amount=payload.limit_amount,
        comment=payload.comment,
        is_active=payload.is_active,
    )


@router.patch("/non-cash-employee-limits/{limit_id}")
def update_non_cash_employee_limit(
    limit_id: str,
    payload: UpdateIikoNonCashEmployeeLimitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _update_non_cash_employee_limit(
        db,
        current_user,
        limit_id=limit_id,
        period_type=payload.period_type,
        limit_amount=payload.limit_amount,
        comment=payload.comment,
        is_active=payload.is_active,
    )


@router.delete("/non-cash-employee-limits/{limit_id}")
def delete_non_cash_employee_limit(
    limit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _delete_non_cash_employee_limit(db, current_user, limit_id=limit_id)


@router.get("/non-cash-consumption")
def list_non_cash_consumption(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_id: Optional[int] = Query(None),
    non_cash_type_id: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    include_inactive_limits: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    return _list_non_cash_consumption_payload(
        db,
        current_user,
        from_date=from_date,
        to_date=to_date,
        restaurant_id=restaurant_id,
        non_cash_type_id=non_cash_type_id,
        user_id=user_id,
        include_inactive_limits=include_inactive_limits,
    )


@router.get("/revenue-by-payment-methods")
def get_revenue_by_payment_methods(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    restaurant_ids: Optional[List[int]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_REPORT_MONEY_PERMISSIONS)
    return _list_revenue_by_payment_methods_payload(
        db,
        current_user,
        from_date=from_date,
        to_date=to_date,
        restaurant_ids=restaurant_ids,
    )
