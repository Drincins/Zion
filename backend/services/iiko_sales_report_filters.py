from __future__ import annotations

from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.iiko_sales import IikoSaleItem, IikoSaleOrder
from backend.bd.models import User
from backend.services.iiko_sales_waiter_turnover import (
    DELETED_MODE_ONLY,
    DELETED_MODE_WITHOUT,
    WAITER_MODE_ITEM_PUNCH,
    WAITER_MODE_ORDER_CLOSE,
    normalize_deleted_mode,
    normalize_waiter_mode,
)


def clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def split_filter_values(values: Optional[List[str]]) -> List[str]:
    parts: List[str] = []
    for value in values or []:
        if value is None:
            continue
        text = str(value).replace("\n", ",").replace(";", ",")
        for chunk in text.split(","):
            clean = chunk.strip()
            if clean:
                parts.append(clean)
    unique: List[str] = []
    seen = set()
    for value in parts:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def lower_values(values: List[str]) -> List[str]:
    return [value.casefold() for value in values if value]


def waiter_dimension_exprs(waiter_mode: Optional[str]) -> Dict[str, Any]:
    resolved_waiter_mode = normalize_waiter_mode(waiter_mode)
    if resolved_waiter_mode == WAITER_MODE_ITEM_PUNCH:
        waiter_iiko_id_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["DishWaiter.Id"].astext,
            IikoSaleItem.raw_payload["DishSeller.Id"].astext,
            IikoSaleItem.raw_payload["DishEmployee.Id"].astext,
            IikoSaleItem.raw_payload["Waiter.Id"].astext,
            IikoSaleItem.raw_payload["AuthUser.Id"].astext,
            IikoSaleItem.auth_user_iiko_id,
        )
        waiter_iiko_code_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["DishWaiter.Code"].astext,
            IikoSaleItem.raw_payload["DishSeller.Code"].astext,
            IikoSaleItem.raw_payload["DishEmployee.Code"].astext,
            IikoSaleItem.raw_payload["Waiter.Code"].astext,
            IikoSaleItem.raw_payload["AuthUser.Code"].astext,
        )
        waiter_name_iiko_expr = sa.func.coalesce(
            IikoSaleItem.raw_payload["DishWaiter.Name"].astext,
            IikoSaleItem.raw_payload["DishWaiter"].astext,
            IikoSaleItem.raw_payload["DishSeller.Name"].astext,
            IikoSaleItem.raw_payload["DishSeller"].astext,
            IikoSaleItem.raw_payload["DishEmployee.Name"].astext,
            IikoSaleItem.raw_payload["DishEmployee"].astext,
            IikoSaleItem.raw_payload["Waiter.Name"].astext,
            IikoSaleItem.raw_payload["Waiter"].astext,
            IikoSaleItem.raw_payload["WaiterName"].astext,
            IikoSaleItem.raw_payload["AuthUser.Name"].astext,
            IikoSaleOrder.order_waiter_name,
        )
        return {
            "waiter_user_id": IikoSaleItem.auth_user_id,
            "waiter_iiko_id": waiter_iiko_id_expr,
            "waiter_iiko_code": waiter_iiko_code_expr,
            "waiter_name_iiko": waiter_name_iiko_expr,
        }

    return {
        "waiter_user_id": IikoSaleOrder.order_waiter_user_id,
        "waiter_iiko_id": IikoSaleOrder.order_waiter_iiko_id,
        "waiter_iiko_code": sa.cast(sa.literal(None), sa.String),
        "waiter_name_iiko": IikoSaleOrder.order_waiter_name,
    }


def resolve_waiter_identity(
    *,
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
    waiter_name_iiko: Optional[str],
    user_name_by_id: Dict[int, str],
    user_meta_by_iiko_id: Dict[str, Dict[str, Any]],
    user_meta_by_iiko_code: Dict[str, Dict[str, Any]],
) -> tuple[Optional[int], str]:
    clean_waiter_iiko_id = clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = clean_optional_text(waiter_iiko_code)
    clean_waiter_name_iiko = clean_optional_text(waiter_name_iiko)

    resolved_user_id = int(waiter_user_id) if waiter_user_id is not None else None
    if resolved_user_id is None and clean_waiter_iiko_id:
        maybe_user_id = user_meta_by_iiko_id.get(clean_waiter_iiko_id, {}).get("id")
        if maybe_user_id is not None:
            resolved_user_id = int(maybe_user_id)
    if resolved_user_id is None and clean_waiter_iiko_code:
        maybe_user_id = user_meta_by_iiko_code.get(clean_waiter_iiko_code, {}).get("id")
        if maybe_user_id is not None:
            resolved_user_id = int(maybe_user_id)

    resolved_name = (
        user_name_by_id.get(resolved_user_id)
        if resolved_user_id is not None
        else user_meta_by_iiko_id.get(clean_waiter_iiko_id or "", {}).get("name")
        if clean_waiter_iiko_id
        else user_meta_by_iiko_code.get(clean_waiter_iiko_code or "", {}).get("name")
        if clean_waiter_iiko_code
        else None
    ) or clean_waiter_name_iiko or clean_waiter_iiko_code or clean_waiter_iiko_id or "Без привязки"

    return resolved_user_id, resolved_name


def apply_waiter_filter_to_items_query(
    db: Session,
    query,
    *,
    waiter_mode: Optional[str],
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
):
    resolved_waiter_mode = normalize_waiter_mode(waiter_mode)
    clean_waiter_iiko_id = clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = clean_optional_text(waiter_iiko_code)

    if resolved_waiter_mode == WAITER_MODE_ORDER_CLOSE:
        if waiter_user_id is not None:
            query = query.filter(IikoSaleOrder.order_waiter_user_id == int(waiter_user_id))
        if clean_waiter_iiko_id:
            query = query.filter(IikoSaleOrder.order_waiter_iiko_id == clean_waiter_iiko_id)
        return query

    waiter_exprs = waiter_dimension_exprs(resolved_waiter_mode)
    waiter_iiko_id_norm_expr = sa.func.trim(sa.func.coalesce(waiter_exprs["waiter_iiko_id"], ""))
    waiter_iiko_code_norm_expr = sa.func.trim(sa.func.coalesce(waiter_exprs["waiter_iiko_code"], ""))

    if waiter_user_id is not None:
        conditions = [IikoSaleItem.auth_user_id == int(waiter_user_id)]
        user_row = (
            db.query(User.iiko_id, User.iiko_code)
            .filter(User.id == int(waiter_user_id))
            .first()
        )
        if user_row:
            user_iiko_id = clean_optional_text(getattr(user_row, "iiko_id", None))
            user_iiko_code = clean_optional_text(getattr(user_row, "iiko_code", None))
            if user_iiko_id:
                conditions.append(waiter_iiko_id_norm_expr == user_iiko_id)
            if user_iiko_code:
                conditions.append(waiter_iiko_code_norm_expr == user_iiko_code)
        query = query.filter(sa.or_(*conditions))

    if clean_waiter_iiko_id:
        query = query.filter(waiter_iiko_id_norm_expr == clean_waiter_iiko_id)
    if clean_waiter_iiko_code:
        query = query.filter(waiter_iiko_code_norm_expr == clean_waiter_iiko_code)

    return query


def is_not_deleted_state(value: Optional[str]) -> bool:
    clean = (value or "").strip()
    if not clean:
        return True
    return clean.upper() == "NOT_DELETED"


def states_indicate_deleted(
    order_deleted_state: Optional[str],
    deleted_with_writeoff_state: Optional[str],
) -> bool:
    return not (
        is_not_deleted_state(order_deleted_state)
        and is_not_deleted_state(deleted_with_writeoff_state)
    )


def payload_deleted_states(payload: Any) -> tuple[Optional[str], Optional[str]]:
    return (
        clean_optional_text(payload.get("OrderDeleted") if isinstance(payload, dict) else None),
        clean_optional_text(payload.get("DeletedWithWriteoff") if isinstance(payload, dict) else None),
    )


def serialize_deleted_payload(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        order_deleted_state, deleted_with_writeoff_state = payload_deleted_states(payload)
    else:
        order_deleted_state = None
        deleted_with_writeoff_state = None
    return {
        "order_deleted_state": order_deleted_state,
        "deleted_with_writeoff_state": deleted_with_writeoff_state,
        "is_deleted": states_indicate_deleted(order_deleted_state, deleted_with_writeoff_state),
    }


def is_not_deleted_expr(field_expr: Any):
    normalized = sa.func.upper(sa.func.trim(sa.func.coalesce(field_expr, "")))
    return sa.or_(normalized == "", normalized == "NOT_DELETED")


def apply_deleted_mode_filter(
    query,
    *,
    deleted_mode: str,
    order_deleted_expr: Any,
    deleted_with_writeoff_expr: Any,
):
    mode = normalize_deleted_mode(deleted_mode)
    is_not_deleted = sa.and_(
        is_not_deleted_expr(order_deleted_expr),
        is_not_deleted_expr(deleted_with_writeoff_expr),
    )
    if mode == DELETED_MODE_ONLY:
        return query.filter(sa.not_(is_not_deleted))
    if mode == DELETED_MODE_WITHOUT:
        return query.filter(is_not_deleted)
    return query
