from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.iiko_catalog import IikoProduct, IikoProductSetting
from backend.bd.iiko_sales import IikoSaleItem
from backend.bd.models import User

_UUID_REGEX_SQL = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


def clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def looks_like_uuid(value: Optional[str]) -> bool:
    text = clean_optional_text(value)
    if not text:
        return False
    try:
        UUID(text)
        return True
    except Exception:
        return False


def extract_payload_text(payload: Any, key: str) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    value = payload.get(key)
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def extract_payload_text_any(payload: Any, keys: list[str]) -> Optional[str]:
    for key in keys:
        value = extract_payload_text(payload, key)
        if value:
            return value
    return None


def extract_dish_category_name(payload: Any) -> Optional[str]:
    category_value = extract_payload_text_any(
        payload,
        [
            "DishCategory.Name",
            "DishCategory",
            "DishCategoryFullName",
            "DishCategory.Title",
            "DishCategory.Text",
        ],
    )
    if category_value and not looks_like_uuid(category_value):
        return category_value
    return None


def non_uuid_text_sql(expr: Any):
    text_expr = sa.func.nullif(sa.func.trim(sa.cast(expr, sa.String)), "")
    return sa.case((text_expr.op("~*")(_UUID_REGEX_SQL), sa.null()), else_=text_expr)


def dish_group_sql_expr():
    return sa.func.coalesce(
        sa.func.nullif(IikoProductSetting.custom_product_group_type, ""),
        sa.func.nullif(IikoSaleItem.dish_group, ""),
    )


def dish_category_sql_expr(*, with_fallback: bool = False):
    payload_category_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["DishCategory.Name"].astext,
        IikoSaleItem.raw_payload["DishCategory"].astext,
        IikoSaleItem.raw_payload["DishCategoryFullName"].astext,
        IikoSaleItem.raw_payload["DishCategory.Title"].astext,
        IikoSaleItem.raw_payload["DishCategory.Text"].astext,
    )
    category_id_expr = sa.func.nullif(sa.func.trim(sa.cast(IikoSaleItem.dish_category_id, sa.String)), "")
    safe_category_id_expr = sa.case((category_id_expr.op("~*")(_UUID_REGEX_SQL), sa.null()), else_=category_id_expr)
    category_expr = sa.func.coalesce(
        non_uuid_text_sql(IikoProductSetting.custom_product_category),
        non_uuid_text_sql(sa.func.jsonb_extract_path_text(IikoProduct.raw_payload, "product", "product_category")),
        non_uuid_text_sql(IikoProduct.product_category),
        non_uuid_text_sql(payload_category_expr),
        safe_category_id_expr,
    )
    if with_fallback:
        return sa.func.coalesce(category_expr, sa.literal("Uncategorized"))
    return category_expr


def user_display_name(
    first_name: Optional[str],
    last_name: Optional[str],
    middle_name: Optional[str],
    username: Optional[str],
) -> str:
    parts = [
        (last_name or "").strip(),
        (first_name or "").strip(),
        (middle_name or "").strip(),
    ]
    full_name = " ".join(part for part in parts if part)
    return full_name or (username or "").strip() or "-"


def user_names_by_ids(db: Session, user_ids: set[int]) -> Dict[int, str]:
    if not user_ids:
        return {}
    rows = (
        db.query(User.id, User.first_name, User.last_name, User.middle_name, User.username)
        .filter(User.id.in_(sorted(user_ids)))
        .all()
    )
    mapping: Dict[int, str] = {}
    for user_id, first_name, last_name, middle_name, username in rows:
        mapping[int(user_id)] = user_display_name(first_name, last_name, middle_name, username)
    return mapping


def user_meta_by_iiko_ids(db: Session, iiko_ids: set[str]) -> Dict[str, Dict[str, Any]]:
    clean_ids = sorted({str(value).strip() for value in iiko_ids if value})
    if not clean_ids:
        return {}
    rows = (
        db.query(User.id, User.iiko_id, User.first_name, User.last_name, User.middle_name, User.username)
        .filter(User.iiko_id.in_(clean_ids))
        .all()
    )
    mapping: Dict[str, Dict[str, Any]] = {}
    for user_id, iiko_id, first_name, last_name, middle_name, username in rows:
        if not iiko_id:
            continue
        key = str(iiko_id).strip()
        if not key:
            continue
        mapping[key] = {
            "id": int(user_id),
            "name": user_display_name(first_name, last_name, middle_name, username),
        }
    return mapping


def user_meta_by_iiko_codes(db: Session, iiko_codes: set[str]) -> Dict[str, Dict[str, Any]]:
    clean_codes = sorted({str(value).strip() for value in iiko_codes if value})
    if not clean_codes:
        return {}
    rows = (
        db.query(User.id, User.iiko_code, User.first_name, User.last_name, User.middle_name, User.username)
        .filter(User.iiko_code.in_(clean_codes))
        .all()
    )
    mapping: Dict[str, Dict[str, Any]] = {}
    for user_id, iiko_code, first_name, last_name, middle_name, username in rows:
        if not iiko_code:
            continue
        key = str(iiko_code).strip()
        if not key:
            continue
        mapping[key] = {
            "id": int(user_id),
            "name": user_display_name(first_name, last_name, middle_name, username),
        }
    return mapping
