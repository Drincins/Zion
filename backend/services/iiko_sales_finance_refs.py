from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.bd.iiko_catalog import (
    IikoNonCashEmployeeLimit,
    IikoNonCashPaymentType,
    IikoPaymentMethod,
)
from backend.bd.models import User
from backend.services.iiko_sales_report_dimensions import user_display_name, user_names_by_ids
from backend.services.iiko_sales_scope import (
    get_user_company_scope_ids,
    resolve_scoped_company_id,
    restrict_company_scoped_query,
)


def payment_methods_query(db: Session, current_user: User):
    return restrict_company_scoped_query(
        db.query(IikoPaymentMethod),
        IikoPaymentMethod.company_id,
        db,
        current_user,
    )


def non_cash_types_query(db: Session, current_user: User):
    return restrict_company_scoped_query(
        db.query(IikoNonCashPaymentType),
        IikoNonCashPaymentType.company_id,
        db,
        current_user,
    )


def non_cash_limits_query(db: Session, current_user: User):
    return restrict_company_scoped_query(
        db.query(IikoNonCashEmployeeLimit),
        IikoNonCashEmployeeLimit.company_id,
        db,
        current_user,
    )


def serialize_payment_method(row: IikoPaymentMethod) -> Dict[str, Any]:
    return {
        "guid": row.guid,
        "company_id": row.company_id,
        "name": row.name,
        "category": row.category,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_non_cash_type(row: IikoNonCashPaymentType) -> Dict[str, Any]:
    return {
        "id": row.id,
        "company_id": row.company_id,
        "name": row.name,
        "category": row.category,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_non_cash_limit(
    row: IikoNonCashEmployeeLimit,
    *,
    non_cash_name: Optional[str],
    user_name: Optional[str],
) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "non_cash_type_id": row.non_cash_type_id,
        "non_cash_type_name": non_cash_name,
        "user_id": row.user_id,
        "user_name": user_name,
        "period_type": row.period_type,
        "limit_amount": float(row.limit_amount) if row.limit_amount is not None else None,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def upsert_payment_methods(
    db: Session,
    *,
    company_id: Optional[int],
    methods: Dict[str, str],
    updated_at: datetime,
) -> int:
    payload = []
    for guid, name in (methods or {}).items():
        clean_guid = str(guid).strip() if guid is not None else ""
        if not clean_guid:
            continue
        clean_name = str(name).strip() if name is not None else ""
        payload.append(
            {
                "guid": clean_guid,
                "company_id": company_id,
                "name": clean_name or clean_guid,
                "updated_at": updated_at,
            }
        )
    if not payload:
        return 0
    payload.sort(key=lambda row: str(row.get("guid") or ""))
    stmt = insert(IikoPaymentMethod).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["guid"],
        set_={
            "name": stmt.excluded.name,
            "company_id": stmt.excluded.company_id,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    db.execute(stmt)
    return len(payload)


def upsert_non_cash_types(
    db: Session,
    *,
    company_id: Optional[int],
    types_map: Dict[str, str],
    updated_at: datetime,
) -> int:
    payload = []
    for non_cash_id, name in (types_map or {}).items():
        clean_id = str(non_cash_id).strip() if non_cash_id is not None else ""
        if not clean_id:
            continue
        clean_name = str(name).strip() if name is not None else ""
        payload.append(
            {
                "id": clean_id,
                "company_id": company_id,
                "name": clean_name or clean_id,
                "updated_at": updated_at,
            }
        )
    if not payload:
        return 0
    payload.sort(key=lambda row: str(row.get("id") or ""))
    stmt = insert(IikoNonCashPaymentType).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "name": stmt.excluded.name,
            "company_id": stmt.excluded.company_id,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    db.execute(stmt)
    return len(payload)


def payment_method_lookup_by_guid(
    db: Session,
    current_user: User,
    guids: set[str],
) -> Dict[str, Dict[str, Any]]:
    if not guids:
        return {}
    rows = payment_methods_query(db, current_user).filter(IikoPaymentMethod.guid.in_(sorted(guids))).all()
    return {
        str(row.guid): {
            "name": row.name,
            "category": row.category,
            "is_active": bool(row.is_active),
        }
        for row in rows
    }


def non_cash_lookup_by_id(
    db: Session,
    current_user: User,
    ids: set[str],
) -> Dict[str, Dict[str, Any]]:
    if not ids:
        return {}
    rows = non_cash_types_query(db, current_user).filter(IikoNonCashPaymentType.id.in_(sorted(ids))).all()
    return {
        str(row.id): {
            "name": row.name,
            "category": row.category,
            "is_active": bool(row.is_active),
        }
        for row in rows
    }


def normalize_period_type(value: Optional[str]) -> str:
    clean = (value or "").strip().lower()
    if not clean:
        return "month"
    allowed = {"day", "week", "month", "custom"}
    return clean if clean in allowed else "month"


def to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def list_payment_methods_payload(
    db: Session,
    current_user: User,
    *,
    include_inactive: bool = True,
    category: Optional[str] = None,
) -> list[Dict[str, Any]]:
    query = payment_methods_query(db, current_user)
    if not include_inactive:
        query = query.filter(IikoPaymentMethod.is_active.is_(True))

    if category:
        clean_category = category.strip()
        if clean_category.lower() in {"null", "none", "-"}:
            query = query.filter(IikoPaymentMethod.category.is_(None))
        else:
            query = query.filter(IikoPaymentMethod.category == clean_category)

    rows = query.order_by(IikoPaymentMethod.name.asc(), IikoPaymentMethod.guid.asc()).all()
    return [serialize_payment_method(row) for row in rows]


def update_payment_method(
    db: Session,
    current_user: User,
    *,
    guid: str,
    category: Optional[str],
    comment: Optional[str],
    is_active: Optional[bool],
) -> Dict[str, Any]:
    row = payment_methods_query(db, current_user).filter(IikoPaymentMethod.guid == guid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Payment method not found")

    if category is not None:
        clean_category = category.strip()
        row.category = clean_category or None

    if comment is not None:
        clean_comment = comment.strip()
        row.comment = clean_comment or None

    if is_active is not None:
        row.is_active = bool(is_active)

    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_payment_method(row)


def list_non_cash_types_payload(
    db: Session,
    current_user: User,
    *,
    include_inactive: bool = True,
    category: Optional[str] = None,
) -> list[Dict[str, Any]]:
    query = non_cash_types_query(db, current_user)
    if not include_inactive:
        query = query.filter(IikoNonCashPaymentType.is_active.is_(True))

    if category:
        clean_category = category.strip()
        if clean_category.lower() in {"null", "none", "-"}:
            query = query.filter(IikoNonCashPaymentType.category.is_(None))
        else:
            query = query.filter(IikoNonCashPaymentType.category == clean_category)

    rows = query.order_by(IikoNonCashPaymentType.name.asc(), IikoNonCashPaymentType.id.asc()).all()
    return [serialize_non_cash_type(row) for row in rows]


def create_non_cash_type(
    db: Session,
    current_user: User,
    *,
    non_cash_type_id: str,
    name: str,
    category: Optional[str],
    comment: Optional[str],
    is_active: bool,
) -> Dict[str, Any]:
    clean_id = (non_cash_type_id or "").strip()
    clean_name = (name or "").strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="id is required")
    if not clean_name:
        raise HTTPException(status_code=400, detail="name is required")

    existing = non_cash_types_query(db, current_user).filter(IikoNonCashPaymentType.id == clean_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Non-cash type already exists")

    company_id = resolve_scoped_company_id(db, current_user)
    row = IikoNonCashPaymentType(
        id=clean_id,
        company_id=company_id,
        name=clean_name,
        category=(category or "").strip() or None,
        comment=(comment or "").strip() or None,
        is_active=bool(is_active),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_non_cash_type(row)


def update_non_cash_type(
    db: Session,
    current_user: User,
    *,
    non_cash_type_id: str,
    category: Optional[str],
    comment: Optional[str],
    is_active: Optional[bool],
) -> Dict[str, Any]:
    row = non_cash_types_query(db, current_user).filter(IikoNonCashPaymentType.id == non_cash_type_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Non-cash type not found")

    if category is not None:
        clean_category = category.strip()
        row.category = clean_category or None

    if comment is not None:
        clean_comment = comment.strip()
        row.comment = clean_comment or None

    if is_active is not None:
        row.is_active = bool(is_active)

    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_non_cash_type(row)


def list_non_cash_employee_limits_payload(
    db: Session,
    current_user: User,
    *,
    include_inactive: bool = True,
    non_cash_type_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> list[Dict[str, Any]]:
    query = non_cash_limits_query(db, current_user)
    if not include_inactive:
        query = query.filter(IikoNonCashEmployeeLimit.is_active.is_(True))

    clean_non_cash_type_id = (non_cash_type_id or "").strip() or None
    if clean_non_cash_type_id:
        query = query.filter(IikoNonCashEmployeeLimit.non_cash_type_id == clean_non_cash_type_id)
    if user_id is not None:
        query = query.filter(IikoNonCashEmployeeLimit.user_id == user_id)

    rows = query.order_by(
        IikoNonCashEmployeeLimit.non_cash_type_id.asc(),
        IikoNonCashEmployeeLimit.user_id.asc(),
        IikoNonCashEmployeeLimit.period_type.asc(),
    ).all()

    non_cash_ids = {row.non_cash_type_id for row in rows if row.non_cash_type_id}
    user_ids = {int(row.user_id) for row in rows if row.user_id is not None}
    non_cash_lookup = non_cash_lookup_by_id(db, current_user, non_cash_ids)
    user_name_by_id = user_names_by_ids(db, user_ids)

    return [
        serialize_non_cash_limit(
            row,
            non_cash_name=non_cash_lookup.get(str(row.non_cash_type_id), {}).get("name"),
            user_name=user_name_by_id.get(int(row.user_id)) if row.user_id is not None else None,
        )
        for row in rows
    ]


def upsert_non_cash_employee_limit(
    db: Session,
    current_user: User,
    *,
    non_cash_type_id: str,
    user_id: int,
    period_type: str,
    limit_amount: Any,
    comment: Optional[str],
    is_active: bool,
) -> Dict[str, Any]:
    clean_non_cash_type_id = (non_cash_type_id or "").strip()
    if not clean_non_cash_type_id:
        raise HTTPException(status_code=400, detail="non_cash_type_id is required")

    normalized_period_type = normalize_period_type(period_type)
    parsed_limit_amount = to_decimal(limit_amount)
    if limit_amount is not None and parsed_limit_amount is None:
        raise HTTPException(status_code=400, detail="limit_amount must be a number")

    non_cash_row = (
        non_cash_types_query(db, current_user)
        .filter(IikoNonCashPaymentType.id == clean_non_cash_type_id)
        .first()
    )
    if not non_cash_row:
        raise HTTPException(status_code=404, detail="Non-cash type not found")

    user_row = db.query(User).filter(User.id == user_id).first()
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    company_scope_ids = get_user_company_scope_ids(db, current_user)
    if company_scope_ids is not None and (
        user_row.company_id is None or int(user_row.company_id) not in company_scope_ids
    ):
        raise HTTPException(status_code=400, detail="User is outside of your company scope")

    row = (
        non_cash_limits_query(db, current_user)
        .filter(IikoNonCashEmployeeLimit.non_cash_type_id == clean_non_cash_type_id)
        .filter(IikoNonCashEmployeeLimit.user_id == user_id)
        .filter(IikoNonCashEmployeeLimit.period_type == normalized_period_type)
        .first()
    )
    if row is None:
        row = IikoNonCashEmployeeLimit(
            company_id=non_cash_row.company_id or getattr(current_user, "company_id", None),
            non_cash_type_id=clean_non_cash_type_id,
            user_id=user_id,
            period_type=normalized_period_type,
        )

    row.limit_amount = parsed_limit_amount
    row.comment = (comment or "").strip() or None
    row.is_active = bool(is_active)

    db.add(row)
    db.commit()
    db.refresh(row)

    return serialize_non_cash_limit(
        row,
        non_cash_name=non_cash_row.name,
        user_name=user_display_name(
            user_row.first_name,
            user_row.last_name,
            user_row.middle_name,
            user_row.username,
        ),
    )


def update_non_cash_employee_limit(
    db: Session,
    current_user: User,
    *,
    limit_id: str,
    period_type: Optional[str],
    limit_amount: Any,
    comment: Optional[str],
    is_active: Optional[bool],
) -> Dict[str, Any]:
    row = non_cash_limits_query(db, current_user).filter(IikoNonCashEmployeeLimit.id == limit_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Non-cash employee limit not found")

    if period_type is not None:
        row.period_type = normalize_period_type(period_type)
    if limit_amount is not None:
        parsed_amount = to_decimal(limit_amount)
        if parsed_amount is None:
            raise HTTPException(status_code=400, detail="limit_amount must be a number")
        row.limit_amount = parsed_amount
    if comment is not None:
        row.comment = comment.strip() or None
    if is_active is not None:
        row.is_active = bool(is_active)

    db.add(row)
    db.commit()
    db.refresh(row)

    non_cash_name = (
        non_cash_types_query(db, current_user)
        .filter(IikoNonCashPaymentType.id == row.non_cash_type_id)
        .with_entities(IikoNonCashPaymentType.name)
        .scalar()
    )
    user_name = user_names_by_ids(db, {int(row.user_id)}).get(int(row.user_id)) if row.user_id is not None else None
    return serialize_non_cash_limit(row, non_cash_name=non_cash_name, user_name=user_name)


def delete_non_cash_employee_limit(
    db: Session,
    current_user: User,
    *,
    limit_id: str,
) -> Dict[str, Any]:
    row = non_cash_limits_query(db, current_user).filter(IikoNonCashEmployeeLimit.id == limit_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Non-cash employee limit not found")

    db.delete(row)
    db.commit()
    return {"status": "ok", "id": str(row.id)}
