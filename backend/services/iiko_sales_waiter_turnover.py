from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.iiko_catalog import IikoWaiterTurnoverSetting
from backend.bd.models import Position, User
from backend.services.iiko_sales_scope import resolve_scoped_company_id, restrict_company_scoped_query

TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT = "sum_without_discount"
TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT = "sum_with_discount"
TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY = "discount_only"

TURNOVER_AMOUNT_MODES = {
    TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
    TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT,
    TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY,
}

WAITER_MODE_ORDER_CLOSE = "order_close"
WAITER_MODE_ITEM_PUNCH = "item_punch"

DELETED_MODE_ALL = "all"
DELETED_MODE_ONLY = "only_deleted"
DELETED_MODE_WITHOUT = "without_deleted"


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def _split_filter_values(values: Optional[List[str]]) -> List[str]:
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


def normalize_text_list(values: Optional[List[str]]) -> List[str]:
    return _split_filter_values(values)


def normalize_int_list(values: Optional[List[int]]) -> List[int]:
    unique: List[int] = []
    seen = set()
    for value in values or []:
        try:
            parsed = int(value)
        except Exception:
            continue
        if parsed <= 0 or parsed in seen:
            continue
        seen.add(parsed)
        unique.append(parsed)
    return unique


def normalize_turnover_amount_mode(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    aliases = {
        "": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "sum": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "gross": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "sum_without_discount": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "sum_with_discount": TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT,
        "net": TURNOVER_AMOUNT_MODE_SUM_WITH_DISCOUNT,
        "discount": TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY,
        "discount_only": TURNOVER_AMOUNT_MODE_DISCOUNT_ONLY,
    }
    return aliases.get(clean, TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT)


def normalize_waiter_mode(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    aliases = {
        "": WAITER_MODE_ORDER_CLOSE,
        "order_close": WAITER_MODE_ORDER_CLOSE,
        "order_closed": WAITER_MODE_ORDER_CLOSE,
        "close_order": WAITER_MODE_ORDER_CLOSE,
        "order_waiter": WAITER_MODE_ORDER_CLOSE,
        "close": WAITER_MODE_ORDER_CLOSE,
        "closed": WAITER_MODE_ORDER_CLOSE,
        "item_punch": WAITER_MODE_ITEM_PUNCH,
        "punch": WAITER_MODE_ITEM_PUNCH,
        "item_waiter": WAITER_MODE_ITEM_PUNCH,
        "dish_waiter": WAITER_MODE_ITEM_PUNCH,
        "dish_seller": WAITER_MODE_ITEM_PUNCH,
    }
    return aliases.get(clean, WAITER_MODE_ORDER_CLOSE)


def normalize_deleted_mode(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    aliases = {
        "": DELETED_MODE_ALL,
        "all": DELETED_MODE_ALL,
        "only_deleted": DELETED_MODE_ONLY,
        "deleted_only": DELETED_MODE_ONLY,
        "only": DELETED_MODE_ONLY,
        "deleted": DELETED_MODE_ONLY,
        "without_deleted": DELETED_MODE_WITHOUT,
        "exclude_deleted": DELETED_MODE_WITHOUT,
        "without": DELETED_MODE_WITHOUT,
        "active_only": DELETED_MODE_WITHOUT,
    }
    return aliases.get(clean, DELETED_MODE_ALL)


def waiter_turnover_settings_query(db: Session, current_user: User):
    return restrict_company_scoped_query(
        db.query(IikoWaiterTurnoverSetting),
        IikoWaiterTurnoverSetting.company_id,
        db,
        current_user,
    )


def resolve_settings_company_id(
    db: Session,
    current_user: User,
    requested_company_id: Optional[int] = None,
) -> Optional[int]:
    return resolve_scoped_company_id(db, current_user, requested_company_id)


def waiter_turnover_settings_company_query(
    db: Session,
    current_user: User,
    company_id: Optional[int],
):
    q = waiter_turnover_settings_query(db, current_user)
    if company_id is None:
        return q.filter(sa.literal(False))
    return q.filter(IikoWaiterTurnoverSetting.company_id == company_id)


def normalize_rule_name(value: Optional[str], fallback: str = "Правило") -> str:
    clean = _clean_optional_text(value)
    return clean or fallback


def default_waiter_turnover_rule_name(existing_count: int) -> str:
    if existing_count <= 0:
        return "Основное правило"
    return f"Правило {existing_count + 1}"


def waiter_turnover_rules_list_payload(rows: List[IikoWaiterTurnoverSetting]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "id": str(row.id) if row.id is not None else None,
                "rule_name": normalize_rule_name(row.rule_name, "Без названия"),
                "is_active": bool(row.is_active),
                "real_money_only": bool(row.real_money_only),
                "amount_mode": normalize_turnover_amount_mode(row.amount_mode),
                "deleted_mode": normalize_deleted_mode(row.deleted_mode),
                "waiter_mode": normalize_waiter_mode(row.waiter_mode),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        )
    return items


def find_waiter_turnover_rule(
    db: Session,
    current_user: User,
    company_id: Optional[int],
    rule_id: UUID,
) -> Optional[IikoWaiterTurnoverSetting]:
    return (
        waiter_turnover_settings_company_query(db, current_user, company_id)
        .filter(IikoWaiterTurnoverSetting.id == rule_id)
        .first()
    )


def apply_waiter_turnover_settings_payload(
    db: Session,
    row: IikoWaiterTurnoverSetting,
    payload: Any,
    company_id: Optional[int],
) -> None:
    if payload.rule_name is not None:
        row.rule_name = normalize_rule_name(payload.rule_name, row.rule_name or "Правило")
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)
    if payload.real_money_only is not None:
        row.real_money_only = bool(payload.real_money_only)
    if payload.amount_mode is not None:
        row.amount_mode = normalize_turnover_amount_mode(payload.amount_mode)
    if payload.deleted_mode is not None:
        row.deleted_mode = normalize_deleted_mode(payload.deleted_mode)
    if payload.waiter_mode is not None:
        row.waiter_mode = normalize_waiter_mode(payload.waiter_mode)
    if payload.comment is not None:
        row.comment = _clean_optional_text(payload.comment)

    if payload.position_ids is not None:
        candidate_ids = normalize_int_list(payload.position_ids)
        if candidate_ids:
            if company_id is None:
                raise HTTPException(status_code=400, detail="Company scope is required for position filters")
            existing_ids = {
                int(pos_id)
                for (pos_id,) in (
                    db.query(Position.id)
                    .join(User, User.position_id == Position.id)
                    .filter(User.company_id == company_id)
                    .filter(Position.id.in_(candidate_ids))
                    .distinct()
                    .all()
                )
                if pos_id is not None
            }
            invalid_ids = [pos_id for pos_id in candidate_ids if pos_id not in existing_ids]
            if invalid_ids:
                raise HTTPException(
                    status_code=400,
                    detail="One or more positions are outside of your company scope",
                )
            row.position_ids = [pos_id for pos_id in candidate_ids if pos_id in existing_ids]
        else:
            row.position_ids = []

    if payload.include_groups is not None:
        row.include_groups = normalize_text_list(payload.include_groups)
    if payload.exclude_groups is not None:
        row.exclude_groups = normalize_text_list(payload.exclude_groups)
    if payload.include_categories is not None:
        row.include_categories = normalize_text_list(payload.include_categories)
    if payload.exclude_categories is not None:
        row.exclude_categories = normalize_text_list(payload.exclude_categories)
    if payload.include_positions is not None:
        row.include_positions = normalize_text_list(payload.include_positions)
    if payload.exclude_positions is not None:
        row.exclude_positions = normalize_text_list(payload.exclude_positions)
    if payload.include_payment_method_guids is not None:
        row.include_payment_method_guids = normalize_text_list(payload.include_payment_method_guids)


def deactivate_other_waiter_turnover_rules(
    db: Session,
    company_id: Optional[int],
    keep_rule_id: UUID,
) -> None:
    q = db.query(IikoWaiterTurnoverSetting).filter(IikoWaiterTurnoverSetting.id != keep_rule_id)
    if company_id is None:
        q = q.filter(IikoWaiterTurnoverSetting.company_id.is_(None))
    else:
        q = q.filter(IikoWaiterTurnoverSetting.company_id == company_id)
    q.update({IikoWaiterTurnoverSetting.is_active: False}, synchronize_session=False)


def position_options_for_settings(db: Session, company_id: Optional[int]) -> List[Dict[str, Any]]:
    if company_id is None:
        return []
    rows = (
        db.query(Position.id, Position.name)
        .join(User, User.position_id == Position.id)
        .filter(User.company_id == company_id)
        .distinct()
        .order_by(Position.name.asc(), Position.id.asc())
        .all()
    )
    result: List[Dict[str, Any]] = []
    for pos_id, pos_name in rows:
        if pos_id is None:
            continue
        result.append(
            {
                "id": int(pos_id),
                "name": str(pos_name or f"Position #{pos_id}"),
            }
        )
    return result


def default_waiter_turnover_settings(company_id: Optional[int]) -> Dict[str, Any]:
    return {
        "id": None,
        "company_id": company_id,
        "rule_name": "Основное правило",
        "is_active": False,
        "real_money_only": True,
        "amount_mode": TURNOVER_AMOUNT_MODE_SUM_WITHOUT_DISCOUNT,
        "deleted_mode": DELETED_MODE_WITHOUT,
        "waiter_mode": WAITER_MODE_ORDER_CLOSE,
        "position_ids": [],
        "include_groups": [],
        "exclude_groups": [],
        "include_categories": [],
        "exclude_categories": [],
        "include_positions": [],
        "exclude_positions": [],
        "include_payment_method_guids": [],
        "comment": None,
        "created_at": None,
        "updated_at": None,
    }


def serialize_waiter_turnover_settings(
    row: Optional[IikoWaiterTurnoverSetting],
    company_id: Optional[int],
) -> Dict[str, Any]:
    if not row:
        return default_waiter_turnover_settings(company_id)
    return {
        "id": str(row.id) if row.id is not None else None,
        "company_id": row.company_id,
        "rule_name": normalize_rule_name(row.rule_name, "Основное правило"),
        "is_active": bool(row.is_active),
        "real_money_only": bool(row.real_money_only),
        "amount_mode": normalize_turnover_amount_mode(row.amount_mode),
        "deleted_mode": normalize_deleted_mode(row.deleted_mode),
        "waiter_mode": normalize_waiter_mode(row.waiter_mode),
        "position_ids": normalize_int_list(row.position_ids if isinstance(row.position_ids, list) else []),
        "include_groups": normalize_text_list(row.include_groups if isinstance(row.include_groups, list) else []),
        "exclude_groups": normalize_text_list(row.exclude_groups if isinstance(row.exclude_groups, list) else []),
        "include_categories": normalize_text_list(
            row.include_categories if isinstance(row.include_categories, list) else []
        ),
        "exclude_categories": normalize_text_list(
            row.exclude_categories if isinstance(row.exclude_categories, list) else []
        ),
        "include_positions": normalize_text_list(
            row.include_positions if isinstance(row.include_positions, list) else []
        ),
        "exclude_positions": normalize_text_list(
            row.exclude_positions if isinstance(row.exclude_positions, list) else []
        ),
        "include_payment_method_guids": normalize_text_list(
            row.include_payment_method_guids if isinstance(row.include_payment_method_guids, list) else []
        ),
        "comment": _clean_optional_text(row.comment),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_waiter_turnover_rules_response(
    db: Session,
    current_user: User,
    *,
    requested_company_id: Optional[int] = None,
) -> Dict[str, Any]:
    resolved_company_id = resolve_settings_company_id(db, current_user, requested_company_id)
    rows = (
        waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
        .order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
            IikoWaiterTurnoverSetting.created_at.desc().nullslast(),
        )
        .all()
    )
    return {
        "company_id": resolved_company_id,
        "items": waiter_turnover_rules_list_payload(rows),
        "position_options": position_options_for_settings(db, resolved_company_id),
    }


def get_waiter_turnover_rule_payload(
    db: Session,
    current_user: User,
    *,
    rule_id: UUID,
    requested_company_id: Optional[int] = None,
) -> Dict[str, Any]:
    resolved_company_id = resolve_settings_company_id(db, current_user, requested_company_id)
    row = find_waiter_turnover_rule(db, current_user, resolved_company_id, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    payload = serialize_waiter_turnover_settings(row, resolved_company_id)
    payload["position_options"] = position_options_for_settings(db, resolved_company_id)
    return payload


def create_waiter_turnover_rule(
    db: Session,
    current_user: User,
    payload: Any,
    *,
    requested_company_id: Optional[int] = None,
) -> Dict[str, Any]:
    resolved_company_id = resolve_settings_company_id(db, current_user, requested_company_id)
    company_q = waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
    existing_count = company_q.count()

    row = IikoWaiterTurnoverSetting(company_id=resolved_company_id)
    row.rule_name = normalize_rule_name(
        payload.rule_name,
        default_waiter_turnover_rule_name(existing_count),
    )
    row.is_active = bool(payload.is_active) if payload.is_active is not None else existing_count == 0
    db.add(row)
    apply_waiter_turnover_settings_payload(db, row, payload, resolved_company_id)
    db.flush()
    if row.is_active:
        deactivate_other_waiter_turnover_rules(db, resolved_company_id, row.id)
    db.commit()
    db.refresh(row)

    result = serialize_waiter_turnover_settings(row, resolved_company_id)
    result["position_options"] = position_options_for_settings(db, resolved_company_id)
    return result


def update_waiter_turnover_rule(
    db: Session,
    current_user: User,
    *,
    rule_id: UUID,
    payload: Any,
    requested_company_id: Optional[int] = None,
) -> Dict[str, Any]:
    resolved_company_id = resolve_settings_company_id(db, current_user, requested_company_id)
    row = find_waiter_turnover_rule(db, current_user, resolved_company_id, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")

    apply_waiter_turnover_settings_payload(db, row, payload, resolved_company_id)
    db.add(row)
    db.flush()
    if row.is_active:
        deactivate_other_waiter_turnover_rules(db, resolved_company_id, row.id)
    db.commit()
    db.refresh(row)

    result = serialize_waiter_turnover_settings(row, resolved_company_id)
    result["position_options"] = position_options_for_settings(db, resolved_company_id)
    return result


def delete_waiter_turnover_rule(
    db: Session,
    current_user: User,
    *,
    rule_id: UUID,
    requested_company_id: Optional[int] = None,
) -> None:
    resolved_company_id = resolve_settings_company_id(db, current_user, requested_company_id)
    row = find_waiter_turnover_rule(db, current_user, resolved_company_id, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")

    was_active = bool(row.is_active)
    db.delete(row)
    db.flush()
    if was_active:
        fallback = (
            waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
            .order_by(IikoWaiterTurnoverSetting.updated_at.desc().nullslast())
            .first()
        )
        if fallback:
            fallback.is_active = True
            db.add(fallback)
    db.commit()


def get_waiter_turnover_settings_payload(
    db: Session,
    current_user: User,
    *,
    requested_company_id: Optional[int] = None,
    rule_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    resolved_company_id = resolve_settings_company_id(db, current_user, requested_company_id)
    q = waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
    if rule_id is not None:
        row = q.filter(IikoWaiterTurnoverSetting.id == rule_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Rule not found")
    else:
        row = q.order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
        ).first()
    payload = serialize_waiter_turnover_settings(row, resolved_company_id)
    payload["position_options"] = position_options_for_settings(db, resolved_company_id)
    payload["rules"] = waiter_turnover_rules_list_payload(
        q.order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
        ).all()
    )
    return payload


def upsert_waiter_turnover_settings(
    db: Session,
    current_user: User,
    payload: Any,
    *,
    requested_company_id: Optional[int] = None,
    rule_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    resolved_company_id = resolve_settings_company_id(db, current_user, requested_company_id)
    q = waiter_turnover_settings_company_query(db, current_user, resolved_company_id)
    row = None
    if rule_id is not None:
        row = q.filter(IikoWaiterTurnoverSetting.id == rule_id).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Rule not found")
    else:
        row = q.order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
        ).first()

    if row is None:
        row = IikoWaiterTurnoverSetting(
            company_id=resolved_company_id,
            rule_name=normalize_rule_name(payload.rule_name, "Основное правило"),
        )
        db.add(row)

    apply_waiter_turnover_settings_payload(db, row, payload, resolved_company_id)
    db.add(row)
    db.flush()
    if row.is_active:
        deactivate_other_waiter_turnover_rules(db, resolved_company_id, row.id)
    db.commit()
    db.refresh(row)

    result = serialize_waiter_turnover_settings(row, resolved_company_id)
    result["position_options"] = position_options_for_settings(db, resolved_company_id)
    result["rules"] = waiter_turnover_rules_list_payload(
        q.order_by(
            IikoWaiterTurnoverSetting.is_active.desc(),
            IikoWaiterTurnoverSetting.updated_at.desc().nullslast(),
        ).all()
    )
    return result
