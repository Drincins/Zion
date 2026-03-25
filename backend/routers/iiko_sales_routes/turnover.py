from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import User
from backend.schemas.iiko_sales import UpdateIikoWaiterTurnoverSettingsRequest
from backend.services.iiko_sales_waiter_turnover import (
    create_waiter_turnover_rule as _create_waiter_turnover_rule,
    delete_waiter_turnover_rule as _delete_waiter_turnover_rule,
    get_waiter_turnover_rule_payload as _get_waiter_turnover_rule_payload,
    get_waiter_turnover_settings_payload as _get_waiter_turnover_settings_payload,
    list_waiter_turnover_rules_response as _list_waiter_turnover_rules_response,
    update_waiter_turnover_rule as _update_waiter_turnover_rule,
    upsert_waiter_turnover_settings as _upsert_waiter_turnover_settings,
)
from backend.services.permissions import PermissionCode, ensure_permissions
from backend.utils import get_current_user

router = APIRouter()


@router.get("/waiter-turnover-rules")
def list_waiter_turnover_rules(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    return _list_waiter_turnover_rules_response(
        db,
        current_user,
        requested_company_id=company_id,
    )


@router.get("/waiter-turnover-rules/{rule_id}")
def get_waiter_turnover_rule(
    rule_id: UUID,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    return _get_waiter_turnover_rule_payload(
        db,
        current_user,
        rule_id=rule_id,
        requested_company_id=company_id,
    )


@router.post("/waiter-turnover-rules")
def create_waiter_turnover_rule(
    payload: UpdateIikoWaiterTurnoverSettingsRequest,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _create_waiter_turnover_rule(
        db,
        current_user,
        payload,
        requested_company_id=company_id,
    )


@router.patch("/waiter-turnover-rules/{rule_id}")
def update_waiter_turnover_rule(
    rule_id: UUID,
    payload: UpdateIikoWaiterTurnoverSettingsRequest,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _update_waiter_turnover_rule(
        db,
        current_user,
        rule_id=rule_id,
        payload=payload,
        requested_company_id=company_id,
    )


@router.delete("/waiter-turnover-rules/{rule_id}", status_code=204)
def delete_waiter_turnover_rule(
    rule_id: UUID,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    _delete_waiter_turnover_rule(
        db,
        current_user,
        rule_id=rule_id,
        requested_company_id=company_id,
    )
    return None


@router.get("/waiter-turnover-settings")
def get_waiter_turnover_settings(
    company_id: Optional[int] = Query(None),
    rule_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_VIEW, PermissionCode.IIKO_MANAGE)
    return _get_waiter_turnover_settings_payload(
        db,
        current_user,
        requested_company_id=company_id,
        rule_id=rule_id,
    )


@router.put("/waiter-turnover-settings")
def upsert_waiter_turnover_settings(
    payload: UpdateIikoWaiterTurnoverSettingsRequest,
    company_id: Optional[int] = Query(None),
    rule_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, PermissionCode.IIKO_MANAGE)
    return _upsert_waiter_turnover_settings(
        db,
        current_user,
        payload,
        requested_company_id=company_id,
        rule_id=rule_id,
    )
