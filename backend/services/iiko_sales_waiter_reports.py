from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.iiko_catalog import IikoProduct, IikoProductRestaurant, IikoProductSetting
from backend.bd.iiko_sales import IikoSaleItem, IikoSaleOrder
from backend.bd.models import User
from backend.services.iiko_api import to_iso_date
from backend.services.iiko_sales_layouts import (
    apply_hall_filter_to_base_query,
    collect_halls_from_order_rows,
)
from backend.services.iiko_sales_report_dimensions import (
    dish_category_sql_expr,
    dish_group_sql_expr,
    non_uuid_text_sql,
    user_meta_by_iiko_codes,
    user_meta_by_iiko_ids,
    user_names_by_ids,
)
from backend.services.iiko_sales_report_filters import (
    apply_deleted_mode_filter,
    apply_waiter_filter_to_items_query,
    clean_optional_text,
    lower_values,
    resolve_waiter_identity,
    split_filter_values,
    waiter_dimension_exprs,
)
from backend.services.iiko_sales_scope import ensure_user_access_to_restaurant, list_accessible_restaurants
from backend.services.iiko_sales_waiter_turnover import (
    WAITER_MODE_ITEM_PUNCH,
    normalize_deleted_mode,
    normalize_waiter_mode,
)
from backend.services.reference_cache import cached_reference_data

WAITER_SALES_OPTIONS_CACHE_SCOPE = "iiko-sales:waiter-sales-options"
WAITER_SALES_OPTIONS_CACHE_TTL_SECONDS = 45


def prepare_waiter_sales_filter_values(
    *,
    include_groups: Optional[List[str]] = None,
    exclude_groups: Optional[List[str]] = None,
    include_categories: Optional[List[str]] = None,
    exclude_categories: Optional[List[str]] = None,
    include_positions: Optional[List[str]] = None,
    exclude_positions: Optional[List[str]] = None,
    include_payment_types: Optional[List[str]] = None,
    include_halls: Optional[List[str]] = None,
) -> dict[str, List[str]]:
    include_groups_list = split_filter_values(include_groups)
    exclude_groups_list = split_filter_values(exclude_groups)
    include_categories_list = split_filter_values(include_categories)
    exclude_categories_list = split_filter_values(exclude_categories)
    include_positions_list = split_filter_values(include_positions)
    exclude_positions_list = split_filter_values(exclude_positions)
    include_payment_types_list = split_filter_values(include_payment_types)
    include_halls_list = split_filter_values(include_halls)

    return {
        "include_groups_list": include_groups_list,
        "exclude_groups_list": exclude_groups_list,
        "include_categories_list": include_categories_list,
        "exclude_categories_list": exclude_categories_list,
        "include_positions_list": include_positions_list,
        "exclude_positions_list": exclude_positions_list,
        "include_payment_types_list": include_payment_types_list,
        "include_halls_list": include_halls_list,
        "include_groups_lower": lower_values(include_groups_list),
        "exclude_groups_lower": lower_values(exclude_groups_list),
        "include_categories_lower": lower_values(include_categories_list),
        "exclude_categories_lower": lower_values(exclude_categories_list),
        "include_positions_lower": lower_values(include_positions_list),
        "exclude_positions_lower": lower_values(exclude_positions_list),
        "include_payment_types_lower": lower_values(include_payment_types_list),
        "include_halls_lower": lower_values(include_halls_list),
    }


def build_waiter_sales_base_items_query(
    db: Session,
    *,
    accessible_ids: List[int],
    start: date,
    end_exclusive: date,
    resolved_deleted_mode: str,
):
    base_q = (
        db.query(IikoSaleItem)
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_exclusive)
    )
    return apply_deleted_mode_filter(
        base_q,
        deleted_mode=resolved_deleted_mode,
        order_deleted_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["OrderDeleted"].astext,
            IikoSaleOrder.raw_payload["OrderDeleted"].astext,
        ),
        deleted_with_writeoff_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
            IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
        ),
    )


def apply_waiter_sales_scope_filters(
    db: Session,
    current_user: User,
    base_q,
    *,
    restaurant_id: Optional[int],
    resolved_waiter_mode: str,
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
    include_halls_lower: List[str],
):
    if restaurant_id is not None:
        base_q = base_q.filter(IikoSaleOrder.restaurant_id == restaurant_id)

    base_q = apply_waiter_filter_to_items_query(
        db,
        base_q,
        waiter_mode=resolved_waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=waiter_iiko_id,
        waiter_iiko_code=waiter_iiko_code,
    )

    if include_halls_lower:
        base_q = apply_hall_filter_to_base_query(db, current_user, base_q, include_halls_lower)

    return base_q


def apply_waiter_sales_dimension_filters(
    base_q,
    *,
    group_expr,
    category_expr,
    position_expr,
    payment_type_expr,
    include_groups_lower: List[str],
    exclude_groups_lower: List[str],
    include_categories_lower: List[str],
    exclude_categories_lower: List[str],
    include_positions_lower: List[str],
    exclude_positions_lower: List[str],
    include_payment_types_lower: List[str],
):
    group_expr_lower = sa.func.lower(sa.func.coalesce(group_expr, ""))
    category_expr_lower = sa.func.lower(sa.func.coalesce(category_expr, ""))
    position_expr_lower = sa.func.lower(sa.func.coalesce(position_expr, ""))
    payment_type_expr_lower = sa.func.lower(sa.func.coalesce(payment_type_expr, ""))

    if include_groups_lower:
        base_q = base_q.filter(group_expr_lower.in_(include_groups_lower))
    if exclude_groups_lower:
        base_q = base_q.filter(~group_expr_lower.in_(exclude_groups_lower))
    if include_categories_lower:
        base_q = base_q.filter(category_expr_lower.in_(include_categories_lower))
    if exclude_categories_lower:
        base_q = base_q.filter(~category_expr_lower.in_(exclude_categories_lower))
    if include_positions_lower:
        base_q = base_q.filter(position_expr_lower.in_(include_positions_lower))
    if exclude_positions_lower:
        base_q = base_q.filter(~position_expr_lower.in_(exclude_positions_lower))
    if include_payment_types_lower:
        base_q = base_q.filter(payment_type_expr_lower.in_(include_payment_types_lower))

    return base_q


def waiter_sales_position_expr():
    return sa.func.coalesce(IikoSaleItem.dish_name, IikoProduct.name, IikoSaleItem.dish_code)


def waiter_sales_payment_type_expr():
    return sa.func.coalesce(
        IikoSaleItem.raw_payload["PayTypes"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType"].astext,
        IikoSaleItem.raw_payload["PaymentType"].astext,
        IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
        IikoSaleItem.raw_payload["PaymentType.Id"].astext,
    )


def _catalog_category_expr():
    return sa.func.coalesce(
        non_uuid_text_sql(IikoProductSetting.custom_product_category),
        non_uuid_text_sql(
            sa.func.jsonb_extract_path_text(IikoProduct.raw_payload, "product", "product_category")
        ),
        non_uuid_text_sql(IikoProduct.product_category),
    )


def _catalog_categories_for_restaurants(
    db: Session,
    current_user: User,
    *,
    restaurant_ids: List[int],
) -> List[str]:
    if not restaurant_ids:
        return []

    catalog_category_expr = _catalog_category_expr()
    catalog_q = (
        db.query(IikoProduct.id)
        .select_from(IikoProduct)
        .join(IikoProductRestaurant, IikoProductRestaurant.product_id == IikoProduct.id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .filter(IikoProductRestaurant.restaurant_id.in_(restaurant_ids))
    )
    if getattr(current_user, "company_id", None) is not None:
        catalog_q = catalog_q.filter(IikoProduct.company_id == current_user.company_id)

    return [
        value
        for (value,) in (
            catalog_q.with_entities(catalog_category_expr)
            .filter(catalog_category_expr.isnot(None))
            .distinct()
            .order_by(catalog_category_expr.asc())
            .all()
        )
        if value
    ]


def _sorted_distinct_values(query, expr, *, limit: Optional[int] = None) -> List[str]:
    entities_q = (
        query.with_entities(expr)
        .filter(expr.isnot(None))
        .distinct()
        .order_by(expr.asc())
    )
    if limit is not None:
        entities_q = entities_q.limit(limit)
    return [value for (value,) in entities_q.all() if value]


def _extract_departments(order_rows: Sequence[Any]) -> List[str]:
    return sorted(
        {
            str(getattr(row, "department", "")).strip()
            for row in order_rows
            if getattr(row, "department", None) is not None and str(getattr(row, "department", "")).strip()
        },
        key=lambda value: str(value).casefold(),
    )


def _extract_tables(order_rows: Sequence[Any]) -> List[str]:
    return sorted(
        {
            str(getattr(row, "table_num", "")).strip()
            for row in order_rows
            if getattr(row, "table_num", None) is not None and str(getattr(row, "table_num", "")).strip()
        },
        key=lambda value: str(value).casefold(),
    )


def _build_waiter_sales_waiters(
    db: Session,
    *,
    base_items_q,
    resolved_waiter_mode: str,
) -> List[dict[str, Any]]:
    waiter_exprs = waiter_dimension_exprs(resolved_waiter_mode)
    waiter_rows = (
        base_items_q.with_entities(
            waiter_exprs["waiter_user_id"].label("waiter_user_id"),
            waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
            waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
            waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
        )
        .distinct()
        .all()
    )
    user_ids = {int(row.waiter_user_id) for row in waiter_rows if row.waiter_user_id is not None}
    iiko_ids = {str(row.waiter_iiko_id) for row in waiter_rows if row.waiter_iiko_id}
    iiko_codes = {str(row.waiter_iiko_code) for row in waiter_rows if row.waiter_iiko_code}
    user_name_by_id = user_names_by_ids(db, user_ids)
    user_meta_by_iiko_id = user_meta_by_iiko_ids(db, iiko_ids)
    user_meta_by_iiko_code = user_meta_by_iiko_codes(db, iiko_codes)

    waiters: List[dict[str, Any]] = []
    seen_waiters: set[tuple[Optional[int], Optional[str], Optional[str]]] = set()
    for row in waiter_rows:
        waiter_user_id_value = int(row.waiter_user_id) if row.waiter_user_id is not None else None
        waiter_iiko_id_value = clean_optional_text(row.waiter_iiko_id)
        waiter_iiko_code_value = clean_optional_text(row.waiter_iiko_code)
        resolved_user_id, resolved_name = resolve_waiter_identity(
            waiter_user_id=waiter_user_id_value,
            waiter_iiko_id=waiter_iiko_id_value,
            waiter_iiko_code=waiter_iiko_code_value,
            waiter_name_iiko=clean_optional_text(row.waiter_name_iiko),
            user_name_by_id=user_name_by_id,
            user_meta_by_iiko_id=user_meta_by_iiko_id,
            user_meta_by_iiko_code=user_meta_by_iiko_code,
        )
        dedupe_key = (resolved_user_id, waiter_iiko_id_value, waiter_iiko_code_value)
        if dedupe_key in seen_waiters:
            continue
        seen_waiters.add(dedupe_key)
        waiters.append(
            {
                "user_id": resolved_user_id,
                "iiko_id": waiter_iiko_id_value,
                "iiko_code": waiter_iiko_code_value,
                "name": resolved_name,
            }
        )
    waiters.sort(key=lambda item: str(item.get("name") or "").casefold())
    return waiters


def serialize_waiter_sales_restaurants(
    accessible_restaurants: Sequence[Any],
    *,
    restaurant_name_by_id: dict[int, str],
) -> List[dict[str, Any]]:
    return [
        {
            "id": int(getattr(restaurant, "id")),
            "name": restaurant_name_by_id.get(int(getattr(restaurant, "id"))) or getattr(restaurant, "name", ""),
        }
        for restaurant in accessible_restaurants
        if getattr(restaurant, "id", None) is not None
    ]


def load_waiter_sales_options(
    db: Session,
    current_user: User,
    *,
    accessible_restaurants: Sequence[Any],
    accessible_ids: List[int],
    restaurant_name_by_id: dict[int, str],
    normalized_from_date: str,
    normalized_to_date: str,
    restaurant_id: Optional[int],
    resolved_waiter_mode: str,
    resolved_deleted_mode: str,
    positions_limit: int,
) -> dict[str, Any]:
    start = datetime.strptime(normalized_from_date, "%Y-%m-%d").date()
    end_excl = datetime.strptime(normalized_to_date, "%Y-%m-%d").date() + timedelta(days=1)

    base_items_q = build_waiter_sales_base_items_query(
        db,
        accessible_ids=accessible_ids,
        start=start,
        end_exclusive=end_excl,
        resolved_deleted_mode=resolved_deleted_mode,
    )
    if restaurant_id is not None:
        base_items_q = base_items_q.filter(IikoSaleOrder.restaurant_id == restaurant_id)

    group_expr = dish_group_sql_expr()
    position_expr = waiter_sales_position_expr()
    payment_type_expr = waiter_sales_payment_type_expr()

    accessible_ids_set = set(accessible_ids)
    catalog_restaurant_ids = accessible_ids
    if restaurant_id is not None:
        catalog_restaurant_ids = [restaurant_id] if restaurant_id in accessible_ids_set else []

    groups = _sorted_distinct_values(base_items_q, group_expr)
    categories = _catalog_categories_for_restaurants(
        db,
        current_user,
        restaurant_ids=catalog_restaurant_ids,
    )
    positions = _sorted_distinct_values(base_items_q, position_expr, limit=positions_limit)
    payment_types = _sorted_distinct_values(base_items_q, payment_type_expr)

    hall_order_rows = (
        base_items_q.with_entities(
            IikoSaleOrder.restaurant_id.label("restaurant_id"),
            IikoSaleOrder.source_restaurant_id.label("source_restaurant_id"),
            IikoSaleOrder.department.label("department"),
            IikoSaleOrder.table_num.label("table_num"),
        )
        .distinct()
        .all()
    )

    return {
        "deleted_mode": resolved_deleted_mode,
        "waiter_mode": resolved_waiter_mode,
        "restaurants": serialize_waiter_sales_restaurants(
            accessible_restaurants,
            restaurant_name_by_id=restaurant_name_by_id,
        ),
        "waiters": _build_waiter_sales_waiters(
            db,
            base_items_q=base_items_q,
            resolved_waiter_mode=resolved_waiter_mode,
        ),
        "halls": collect_halls_from_order_rows(db, current_user, hall_order_rows),
        "departments": _extract_departments(hall_order_rows),
        "tables": _extract_tables(hall_order_rows),
        "groups": groups,
        "categories": categories,
        "positions": positions,
        "payment_types": payment_types,
    }


def list_waiter_sales_options_payload(
    db: Session,
    current_user: User,
    *,
    from_date: str,
    to_date: str,
    restaurant_id: Optional[int],
    waiter_mode: str,
    deleted_mode: str,
    positions_limit: int,
) -> dict[str, Any]:
    resolved_deleted_mode = normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = normalize_waiter_mode(waiter_mode)
    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)

    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = [restaurant.id for restaurant in accessible_restaurants]
    restaurant_name_by_id = {restaurant.id: restaurant.name for restaurant in accessible_restaurants}
    if not accessible_ids:
        return {
            "deleted_mode": resolved_deleted_mode,
            "waiter_mode": resolved_waiter_mode,
            "restaurants": [],
            "waiters": [],
            "halls": [],
            "departments": [],
            "tables": [],
            "groups": [],
            "categories": [],
            "positions": [],
            "payment_types": [],
        }

    return load_waiter_sales_options(
        db,
        current_user,
        accessible_restaurants=accessible_restaurants,
        accessible_ids=accessible_ids,
        restaurant_name_by_id=restaurant_name_by_id,
        normalized_from_date=to_iso_date(from_date),
        normalized_to_date=to_iso_date(to_date),
        restaurant_id=restaurant_id,
        resolved_waiter_mode=resolved_waiter_mode,
        resolved_deleted_mode=resolved_deleted_mode,
        positions_limit=positions_limit,
    )


def list_waiter_sales_options_cached_payload(
    db: Session,
    current_user: User,
    *,
    from_date: str,
    to_date: str,
    restaurant_id: Optional[int],
    waiter_mode: str,
    deleted_mode: str,
    positions_limit: int,
) -> dict[str, Any]:
    resolved_deleted_mode = normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = normalize_waiter_mode(waiter_mode)
    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = [restaurant.id for restaurant in accessible_restaurants]
    cache_key = (
        int(getattr(current_user, "id", 0) or 0),
        tuple(sorted(accessible_ids)),
        to_iso_date(from_date),
        to_iso_date(to_date),
        int(restaurant_id) if restaurant_id is not None else None,
        resolved_waiter_mode,
        resolved_deleted_mode,
        int(positions_limit),
    )

    def _load_options_payload() -> dict[str, Any]:
        return list_waiter_sales_options_payload(
            db,
            current_user,
            from_date=from_date,
            to_date=to_date,
            restaurant_id=restaurant_id,
            waiter_mode=resolved_waiter_mode,
            deleted_mode=resolved_deleted_mode,
            positions_limit=positions_limit,
        )

    return cached_reference_data(
        WAITER_SALES_OPTIONS_CACHE_SCOPE,
        cache_key,
        _load_options_payload,
        ttl_seconds=WAITER_SALES_OPTIONS_CACHE_TTL_SECONDS,
    )


def load_waiter_identity_maps(
    db: Session,
    rows: Sequence[Any],
    *,
    waiter_user_id: Optional[int] = None,
    waiter_iiko_id: Optional[str] = None,
    waiter_iiko_code: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    user_ids = {int(row.waiter_user_id) for row in rows if getattr(row, "waiter_user_id", None) is not None}
    iiko_ids = {str(row.waiter_iiko_id) for row in rows if getattr(row, "waiter_iiko_id", None)}
    iiko_codes = {str(row.waiter_iiko_code) for row in rows if getattr(row, "waiter_iiko_code", None)}
    if waiter_user_id is not None:
        user_ids.add(int(waiter_user_id))
    clean_iiko_id = clean_optional_text(waiter_iiko_id)
    clean_iiko_code = clean_optional_text(waiter_iiko_code)
    if clean_iiko_id:
        iiko_ids.add(clean_iiko_id)
    if clean_iiko_code:
        iiko_codes.add(clean_iiko_code)
    return {
        "user_name_by_id": user_names_by_ids(db, user_ids),
        "user_meta_by_iiko_id": user_meta_by_iiko_ids(db, iiko_ids),
        "user_meta_by_iiko_code": user_meta_by_iiko_codes(db, iiko_codes),
    }


def build_waiter_sales_order_metrics_by_key(order_metrics_rows: Sequence[Any]) -> Dict[tuple[Any, ...], Dict[str, Any]]:
    metrics_by_key: Dict[tuple[Any, ...], Dict[str, Any]] = {}
    for row in order_metrics_rows:
        key = (
            int(row.restaurant_id) if row.restaurant_id is not None else None,
            int(row.waiter_user_id) if row.waiter_user_id is not None else None,
            str(row.waiter_iiko_id) if row.waiter_iiko_id else None,
            str(row.waiter_iiko_code) if row.waiter_iiko_code else None,
            str(row.waiter_name_iiko) if row.waiter_name_iiko else None,
        )
        metrics_by_key[key] = {
            "orders_count": int(row.orders_count or 0),
            "guests_count": int(row.guests_count or 0),
        }
    return metrics_by_key


def build_waiter_sales_report_payload(
    rows: Sequence[Any],
    *,
    restaurant_name_by_id: Dict[int, str],
    order_metrics_by_key: Dict[tuple[Any, ...], Dict[str, Any]],
    identity_maps: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    user_name_by_id = identity_maps["user_name_by_id"]
    user_meta_by_iiko_id = identity_maps["user_meta_by_iiko_id"]
    user_meta_by_iiko_code = identity_maps["user_meta_by_iiko_code"]

    items: List[Dict[str, Any]] = []
    totals = {
        "orders_count": 0,
        "guests_count": 0,
        "items_count": 0,
        "qty": 0.0,
        "kitchen_load_qty": 0.0,
        "hall_load_qty": 0.0,
        "sum": 0.0,
        "discount_sum": 0.0,
    }
    totals_by_restaurant_map: Dict[int, Dict[str, Any]] = {}
    totals_by_waiter_map: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        waiter_user_id_value = int(row.waiter_user_id) if row.waiter_user_id is not None else None
        waiter_iiko_id_value = clean_optional_text(row.waiter_iiko_id)
        waiter_iiko_code_value = clean_optional_text(row.waiter_iiko_code)
        resolved_user_id, waiter_name = resolve_waiter_identity(
            waiter_user_id=waiter_user_id_value,
            waiter_iiko_id=waiter_iiko_id_value,
            waiter_iiko_code=waiter_iiko_code_value,
            waiter_name_iiko=clean_optional_text(row.waiter_name_iiko),
            user_name_by_id=user_name_by_id,
            user_meta_by_iiko_id=user_meta_by_iiko_id,
            user_meta_by_iiko_code=user_meta_by_iiko_code,
        )

        metrics_key = (
            int(row.restaurant_id) if row.restaurant_id is not None else None,
            waiter_user_id_value,
            waiter_iiko_id_value,
            waiter_iiko_code_value,
            str(row.waiter_name_iiko) if row.waiter_name_iiko else None,
        )
        order_metrics = order_metrics_by_key.get(metrics_key, {})

        orders_count = int(order_metrics.get("orders_count") or row.orders_count or 0)
        guests_count = int(order_metrics.get("guests_count") or 0)
        items_count = int(row.items_count or 0)
        qty_value = float(row.qty or 0)
        kitchen_load_value = float(row.kitchen_load_qty or 0)
        hall_load_value = float(row.hall_load_qty or 0)
        sum_value = float(row.sum or 0)
        discount_value = float(row.discount_sum or 0)

        items.append(
            {
                "restaurant_id": int(row.restaurant_id) if row.restaurant_id is not None else None,
                "restaurant_name": restaurant_name_by_id.get(int(row.restaurant_id))
                if row.restaurant_id is not None
                else None,
                "waiter_user_id": resolved_user_id,
                "waiter_iiko_id": waiter_iiko_id_value,
                "waiter_iiko_code": waiter_iiko_code_value,
                "waiter_name": waiter_name,
                "waiter_name_iiko": row.waiter_name_iiko,
                "orders_count": orders_count,
                "guests_count": guests_count,
                "items_count": items_count,
                "qty": qty_value,
                "kitchen_load_qty": kitchen_load_value,
                "hall_load_qty": hall_load_value,
                "sum": sum_value,
                "discount_sum": discount_value,
            }
        )

        totals["orders_count"] += orders_count
        totals["guests_count"] += guests_count
        totals["items_count"] += items_count
        totals["qty"] += qty_value
        totals["kitchen_load_qty"] += kitchen_load_value
        totals["hall_load_qty"] += hall_load_value
        totals["sum"] += sum_value
        totals["discount_sum"] += discount_value

        if row.restaurant_id is not None:
            rest_id = int(row.restaurant_id)
            rest_bucket = totals_by_restaurant_map.setdefault(
                rest_id,
                {
                    "restaurant_id": rest_id,
                    "restaurant_name": restaurant_name_by_id.get(rest_id),
                    "orders_count": 0,
                    "guests_count": 0,
                    "items_count": 0,
                    "qty": 0.0,
                    "kitchen_load_qty": 0.0,
                    "hall_load_qty": 0.0,
                    "sum": 0.0,
                    "discount_sum": 0.0,
                },
            )
            rest_bucket["orders_count"] += orders_count
            rest_bucket["guests_count"] += guests_count
            rest_bucket["items_count"] += items_count
            rest_bucket["qty"] += qty_value
            rest_bucket["kitchen_load_qty"] += kitchen_load_value
            rest_bucket["hall_load_qty"] += hall_load_value
            rest_bucket["sum"] += sum_value
            rest_bucket["discount_sum"] += discount_value

        waiter_key = (
            f"user:{resolved_user_id}"
            if resolved_user_id is not None
            else f"iiko:{waiter_iiko_id_value or 'none'}:code:{waiter_iiko_code_value or 'none'}"
        )
        waiter_bucket = totals_by_waiter_map.setdefault(
            waiter_key,
            {
                "waiter_user_id": resolved_user_id,
                "waiter_iiko_id": waiter_iiko_id_value,
                "waiter_iiko_code": waiter_iiko_code_value,
                "waiter_name": waiter_name,
                "orders_count": 0,
                "guests_count": 0,
                "items_count": 0,
                "qty": 0.0,
                "kitchen_load_qty": 0.0,
                "hall_load_qty": 0.0,
                "sum": 0.0,
                "discount_sum": 0.0,
            },
        )
        waiter_bucket["orders_count"] += orders_count
        waiter_bucket["guests_count"] += guests_count
        waiter_bucket["items_count"] += items_count
        waiter_bucket["qty"] += qty_value
        waiter_bucket["kitchen_load_qty"] += kitchen_load_value
        waiter_bucket["hall_load_qty"] += hall_load_value
        waiter_bucket["sum"] += sum_value
        waiter_bucket["discount_sum"] += discount_value

    return {
        "items": items,
        "totals": totals,
        "totals_by_restaurant": sorted(
            totals_by_restaurant_map.values(),
            key=lambda row: (row.get("restaurant_name") or ""),
        ),
        "totals_by_waiter": sorted(
            totals_by_waiter_map.values(),
            key=lambda row: (row.get("waiter_name") or ""),
        ),
    }


def zero_money_metrics(target: Optional[Dict[str, Any]]) -> None:
    if not isinstance(target, dict):
        return
    if "sum" in target:
        target["sum"] = 0.0
    if "discount_sum" in target:
        target["discount_sum"] = 0.0


def list_waiter_sales_report_payload(
    db: Session,
    current_user: User,
    *,
    from_date: str,
    to_date: str,
    restaurant_id: Optional[int],
    waiter_mode: str,
    deleted_mode: str,
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
    include_payment_types: Optional[List[str]],
    include_groups: Optional[List[str]],
    exclude_groups: Optional[List[str]],
    include_categories: Optional[List[str]],
    exclude_categories: Optional[List[str]],
    include_positions: Optional[List[str]],
    exclude_positions: Optional[List[str]],
    include_halls: Optional[List[str]],
    can_view_money: bool,
) -> Dict[str, Any]:
    resolved_deleted_mode = normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = normalize_waiter_mode(waiter_mode)
    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)

    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = [restaurant.id for restaurant in accessible_restaurants]
    restaurant_name_by_id = {restaurant.id: restaurant.name for restaurant in accessible_restaurants}
    if not accessible_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "deleted_mode": resolved_deleted_mode,
            "waiter_mode": resolved_waiter_mode,
            "items": [],
            "totals": {
                "orders_count": 0,
                "guests_count": 0,
                "items_count": 0,
                "qty": 0.0,
                "kitchen_load_qty": 0.0,
                "hall_load_qty": 0.0,
                "sum": 0.0,
                "discount_sum": 0.0,
            },
            "totals_by_restaurant": [],
            "totals_by_waiter": [],
        }

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)

    filters = prepare_waiter_sales_filter_values(
        include_groups=include_groups,
        exclude_groups=exclude_groups,
        include_categories=include_categories,
        exclude_categories=exclude_categories,
        include_positions=include_positions,
        exclude_positions=exclude_positions,
        include_payment_types=include_payment_types,
        include_halls=include_halls,
    )

    group_expr = dish_group_sql_expr()
    category_expr = dish_category_sql_expr()
    position_expr = waiter_sales_position_expr()
    payment_type_expr = waiter_sales_payment_type_expr()
    order_number_expr = sa.func.coalesce(
        IikoSaleOrder.order_num,
        IikoSaleOrder.iiko_order_id,
        sa.cast(IikoSaleOrder.id, sa.String),
    )
    portion_coef_kitchen_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_kitchen, 1.0), sa.Float)
    portion_coef_hall_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_hall, 1.0), sa.Float)
    kitchen_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_kitchen_expr
    hall_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_hall_expr

    base_q = build_waiter_sales_base_items_query(
        db,
        accessible_ids=accessible_ids,
        start=start,
        end_exclusive=end_excl,
        resolved_deleted_mode=resolved_deleted_mode,
    )
    base_q = apply_waiter_sales_scope_filters(
        db,
        current_user,
        base_q,
        restaurant_id=restaurant_id,
        resolved_waiter_mode=resolved_waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=waiter_iiko_id,
        waiter_iiko_code=waiter_iiko_code,
        include_halls_lower=filters["include_halls_lower"],
    )
    base_q = apply_waiter_sales_dimension_filters(
        base_q,
        group_expr=group_expr,
        category_expr=category_expr,
        position_expr=position_expr,
        payment_type_expr=payment_type_expr,
        include_groups_lower=filters["include_groups_lower"],
        exclude_groups_lower=filters["exclude_groups_lower"],
        include_categories_lower=filters["include_categories_lower"],
        exclude_categories_lower=filters["exclude_categories_lower"],
        include_positions_lower=filters["include_positions_lower"],
        exclude_positions_lower=filters["exclude_positions_lower"],
        include_payment_types_lower=filters["include_payment_types_lower"],
    )

    waiter_exprs = waiter_dimension_exprs(resolved_waiter_mode)
    if resolved_waiter_mode == WAITER_MODE_ITEM_PUNCH:
        waiter_orders_subq = (
            base_q.with_entities(
                IikoSaleOrder.id.label("order_id"),
                IikoSaleOrder.restaurant_id.label("restaurant_id"),
                waiter_exprs["waiter_user_id"].label("waiter_user_id"),
                waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
                waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
                waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
            )
            .distinct()
            .subquery(name="waiter_filtered_orders")
        )
        order_metrics_rows = (
            db.query(
                waiter_orders_subq.c.restaurant_id.label("restaurant_id"),
                waiter_orders_subq.c.waiter_user_id.label("waiter_user_id"),
                waiter_orders_subq.c.waiter_iiko_id.label("waiter_iiko_id"),
                waiter_orders_subq.c.waiter_iiko_code.label("waiter_iiko_code"),
                waiter_orders_subq.c.waiter_name_iiko.label("waiter_name_iiko"),
                sa.func.count(waiter_orders_subq.c.order_id).label("orders_count"),
                sa.func.coalesce(sa.func.sum(IikoSaleOrder.guest_num), 0).label("guests_count"),
            )
            .join(IikoSaleOrder, IikoSaleOrder.id == waiter_orders_subq.c.order_id)
            .group_by(
                waiter_orders_subq.c.restaurant_id,
                waiter_orders_subq.c.waiter_user_id,
                waiter_orders_subq.c.waiter_iiko_id,
                waiter_orders_subq.c.waiter_iiko_code,
                waiter_orders_subq.c.waiter_name_iiko,
            )
            .all()
        )
    else:
        filtered_order_ids_subq = (
            base_q.with_entities(IikoSaleOrder.id.label("order_id"))
            .distinct()
            .subquery(name="waiter_filtered_orders")
        )
        order_metrics_rows = (
            db.query(
                IikoSaleOrder.restaurant_id.label("restaurant_id"),
                waiter_exprs["waiter_user_id"].label("waiter_user_id"),
                waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
                waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
                waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
                sa.func.count(sa.distinct(order_number_expr)).label("orders_count"),
                sa.func.coalesce(sa.func.sum(IikoSaleOrder.guest_num), 0).label("guests_count"),
            )
            .join(filtered_order_ids_subq, filtered_order_ids_subq.c.order_id == IikoSaleOrder.id)
            .group_by(
                IikoSaleOrder.restaurant_id,
                waiter_exprs["waiter_user_id"],
                waiter_exprs["waiter_iiko_id"],
                waiter_exprs["waiter_iiko_code"],
                waiter_exprs["waiter_name_iiko"],
            )
            .all()
        )

    order_metrics_by_key = build_waiter_sales_order_metrics_by_key(order_metrics_rows)
    rows = (
        base_q.with_entities(
            IikoSaleOrder.restaurant_id.label("restaurant_id"),
            waiter_exprs["waiter_user_id"].label("waiter_user_id"),
            waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
            waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
            waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
            sa.func.count(sa.distinct(order_number_expr)).label("orders_count"),
            sa.func.count(IikoSaleItem.id).label("items_count"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("qty"),
            sa.func.coalesce(sa.func.sum(kitchen_load_expr), 0).label("kitchen_load_qty"),
            sa.func.coalesce(sa.func.sum(hall_load_expr), 0).label("hall_load_qty"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("sum"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.discount_sum), 0).label("discount_sum"),
        )
        .group_by(
            IikoSaleOrder.restaurant_id,
            waiter_exprs["waiter_user_id"],
            waiter_exprs["waiter_iiko_id"],
            waiter_exprs["waiter_iiko_code"],
            waiter_exprs["waiter_name_iiko"],
        )
        .order_by(
            IikoSaleOrder.restaurant_id.asc(),
            waiter_exprs["waiter_name_iiko"].asc().nullslast(),
            waiter_exprs["waiter_iiko_id"].asc().nullslast(),
            waiter_exprs["waiter_iiko_code"].asc().nullslast(),
        )
        .all()
    )

    identity_maps = load_waiter_identity_maps(db, rows)
    report_payload = build_waiter_sales_report_payload(
        rows,
        restaurant_name_by_id=restaurant_name_by_id,
        order_metrics_by_key=order_metrics_by_key,
        identity_maps=identity_maps,
    )
    items = report_payload["items"]
    totals = report_payload["totals"]
    totals_by_restaurant = report_payload["totals_by_restaurant"]
    totals_by_waiter = report_payload["totals_by_waiter"]

    if not can_view_money:
        zero_money_metrics(totals)
        for row in items:
            zero_money_metrics(row)
        for row in totals_by_restaurant:
            zero_money_metrics(row)
        for row in totals_by_waiter:
            zero_money_metrics(row)

    return {
        "from_date": start.isoformat(),
        "to_date": (end_excl - timedelta(days=1)).isoformat(),
        "deleted_mode": resolved_deleted_mode,
        "waiter_mode": resolved_waiter_mode,
        "items": items,
        "totals": {
            "orders_count": int(totals["orders_count"]),
            "guests_count": int(totals["guests_count"]),
            "items_count": int(totals["items_count"]),
            "qty": round(float(totals["qty"]), 3),
            "kitchen_load_qty": round(float(totals["kitchen_load_qty"]), 3),
            "hall_load_qty": round(float(totals["hall_load_qty"]), 3),
            "sum": round(float(totals["sum"]), 2),
            "discount_sum": round(float(totals["discount_sum"]), 2),
        },
        "totals_by_restaurant": totals_by_restaurant,
        "totals_by_waiter": totals_by_waiter,
    }


def build_waiter_positions_payload(
    rows: Sequence[Any],
    *,
    restaurant_name_by_id: Dict[int, str],
    identity_maps: Dict[str, Dict[str, Any]],
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
    totals: Dict[str, Any],
) -> Dict[str, Any]:
    user_name_by_id = identity_maps["user_name_by_id"]
    user_meta_by_iiko_id = identity_maps["user_meta_by_iiko_id"]
    user_meta_by_iiko_code = identity_maps["user_meta_by_iiko_code"]

    items: List[Dict[str, Any]] = []
    waiter_payload: Optional[Dict[str, Any]] = None

    for row in rows:
        waiter_user_id_value = int(row.waiter_user_id) if row.waiter_user_id is not None else None
        waiter_iiko_id_value = clean_optional_text(row.waiter_iiko_id)
        waiter_iiko_code_value = clean_optional_text(row.waiter_iiko_code)
        resolved_user_id, waiter_name = resolve_waiter_identity(
            waiter_user_id=waiter_user_id_value,
            waiter_iiko_id=waiter_iiko_id_value,
            waiter_iiko_code=waiter_iiko_code_value,
            waiter_name_iiko=clean_optional_text(row.waiter_name_iiko),
            user_name_by_id=user_name_by_id,
            user_meta_by_iiko_id=user_meta_by_iiko_id,
            user_meta_by_iiko_code=user_meta_by_iiko_code,
        )

        if waiter_payload is None:
            waiter_payload = {
                "waiter_user_id": resolved_user_id,
                "waiter_iiko_id": waiter_iiko_id_value,
                "waiter_iiko_code": waiter_iiko_code_value,
                "waiter_name": waiter_name,
                "waiter_name_iiko": row.waiter_name_iiko,
            }

        items.append(
            {
                "restaurant_id": int(row.restaurant_id) if row.restaurant_id is not None else None,
                "restaurant_name": restaurant_name_by_id.get(int(row.restaurant_id))
                if row.restaurant_id is not None
                else None,
                "dish_code": row.dish_code,
                "dish_name": row.dish_name,
                "dish_group": row.dish_group,
                "dish_category": row.dish_category,
                "dish_measure_unit": row.dish_measure_unit,
                "payment_type": row.payment_type,
                "orders_count": int(row.orders_count or 0),
                "items_count": int(row.items_count or 0),
                "qty": float(row.qty or 0),
                "kitchen_load_qty": float(row.kitchen_load_qty or 0),
                "hall_load_qty": float(row.hall_load_qty or 0),
                "sum": float(row.sum or 0),
                "discount_sum": float(row.discount_sum or 0),
            }
        )

    if waiter_payload is None:
        resolved_user_id, resolved_waiter_name = resolve_waiter_identity(
            waiter_user_id=waiter_user_id,
            waiter_iiko_id=clean_optional_text(waiter_iiko_id),
            waiter_iiko_code=clean_optional_text(waiter_iiko_code),
            waiter_name_iiko=None,
            user_name_by_id=user_name_by_id,
            user_meta_by_iiko_id=user_meta_by_iiko_id,
            user_meta_by_iiko_code=user_meta_by_iiko_code,
        )
        waiter_payload = {
            "waiter_user_id": resolved_user_id,
            "waiter_iiko_id": clean_optional_text(waiter_iiko_id),
            "waiter_iiko_code": clean_optional_text(waiter_iiko_code),
            "waiter_name": resolved_waiter_name,
            "waiter_name_iiko": None,
        }

    return {
        "items": items,
        "waiter": waiter_payload,
        "totals": {
            "orders_count": int(totals["orders_count"]),
            "guests_count": int(totals["guests_count"]),
            "items_count": int(totals["items_count"]),
            "qty": float(totals["qty"]),
            "kitchen_load_qty": float(totals["kitchen_load_qty"]),
            "hall_load_qty": float(totals["hall_load_qty"]),
            "sum": float(totals["sum"]),
            "discount_sum": float(totals["discount_sum"]),
        },
    }


def list_waiter_sales_report_positions_payload(
    db: Session,
    current_user: User,
    *,
    from_date: str,
    to_date: str,
    restaurant_id: Optional[int],
    waiter_mode: str,
    deleted_mode: str,
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
    include_payment_types: Optional[List[str]],
    include_groups: Optional[List[str]],
    exclude_groups: Optional[List[str]],
    include_categories: Optional[List[str]],
    exclude_categories: Optional[List[str]],
    include_positions: Optional[List[str]],
    exclude_positions: Optional[List[str]],
    include_halls: Optional[List[str]],
    limit: int,
    can_view_money: bool,
) -> Dict[str, Any]:
    resolved_deleted_mode = normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = normalize_waiter_mode(waiter_mode)

    clean_waiter_iiko_id = clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = clean_optional_text(waiter_iiko_code)
    if waiter_user_id is None and clean_waiter_iiko_id is None and clean_waiter_iiko_code is None:
        raise ValueError("waiter_user_id, waiter_iiko_id or waiter_iiko_code is required")

    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)

    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = [restaurant.id for restaurant in accessible_restaurants]
    restaurant_name_by_id = {restaurant.id: restaurant.name for restaurant in accessible_restaurants}
    if not accessible_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "deleted_mode": resolved_deleted_mode,
            "waiter_mode": resolved_waiter_mode,
            "waiter": None,
            "items": [],
            "totals": {
                "orders_count": 0,
                "guests_count": 0,
                "items_count": 0,
                "qty": 0.0,
                "kitchen_load_qty": 0.0,
                "hall_load_qty": 0.0,
                "sum": 0.0,
                "discount_sum": 0.0,
            },
        }

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)

    filters = prepare_waiter_sales_filter_values(
        include_groups=include_groups,
        exclude_groups=exclude_groups,
        include_categories=include_categories,
        exclude_categories=exclude_categories,
        include_positions=include_positions,
        exclude_positions=exclude_positions,
        include_payment_types=include_payment_types,
        include_halls=include_halls,
    )

    group_expr = dish_group_sql_expr()
    category_expr = dish_category_sql_expr()
    position_expr = waiter_sales_position_expr()
    payment_type_expr = waiter_sales_payment_type_expr()
    order_number_expr = sa.func.coalesce(
        IikoSaleOrder.order_num,
        IikoSaleOrder.iiko_order_id,
        sa.cast(IikoSaleOrder.id, sa.String),
    )
    portion_coef_kitchen_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_kitchen, 1.0), sa.Float)
    portion_coef_hall_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_hall, 1.0), sa.Float)
    kitchen_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_kitchen_expr
    hall_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_hall_expr

    base_q = build_waiter_sales_base_items_query(
        db,
        accessible_ids=accessible_ids,
        start=start,
        end_exclusive=end_excl,
        resolved_deleted_mode=resolved_deleted_mode,
    )
    base_q = apply_waiter_sales_scope_filters(
        db,
        current_user,
        base_q,
        restaurant_id=restaurant_id,
        resolved_waiter_mode=resolved_waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=clean_waiter_iiko_id,
        waiter_iiko_code=clean_waiter_iiko_code,
        include_halls_lower=filters["include_halls_lower"],
    )
    base_q = apply_waiter_sales_dimension_filters(
        base_q,
        group_expr=group_expr,
        category_expr=category_expr,
        position_expr=position_expr,
        payment_type_expr=payment_type_expr,
        include_groups_lower=filters["include_groups_lower"],
        exclude_groups_lower=filters["exclude_groups_lower"],
        include_categories_lower=filters["include_categories_lower"],
        exclude_categories_lower=filters["exclude_categories_lower"],
        include_positions_lower=filters["include_positions_lower"],
        exclude_positions_lower=filters["exclude_positions_lower"],
        include_payment_types_lower=filters["include_payment_types_lower"],
    )

    waiter_exprs = waiter_dimension_exprs(resolved_waiter_mode)

    rows = (
        base_q.with_entities(
            IikoSaleOrder.restaurant_id.label("restaurant_id"),
            waiter_exprs["waiter_user_id"].label("waiter_user_id"),
            waiter_exprs["waiter_iiko_id"].label("waiter_iiko_id"),
            waiter_exprs["waiter_iiko_code"].label("waiter_iiko_code"),
            waiter_exprs["waiter_name_iiko"].label("waiter_name_iiko"),
            IikoSaleItem.dish_code.label("dish_code"),
            position_expr.label("dish_name"),
            group_expr.label("dish_group"),
            category_expr.label("dish_category"),
            IikoSaleItem.dish_measure_unit.label("dish_measure_unit"),
            payment_type_expr.label("payment_type"),
            sa.func.count(sa.distinct(order_number_expr)).label("orders_count"),
            sa.func.count(IikoSaleItem.id).label("items_count"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("qty"),
            sa.func.coalesce(sa.func.sum(kitchen_load_expr), 0).label("kitchen_load_qty"),
            sa.func.coalesce(sa.func.sum(hall_load_expr), 0).label("hall_load_qty"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("sum"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.discount_sum), 0).label("discount_sum"),
        )
        .group_by(
            IikoSaleOrder.restaurant_id,
            waiter_exprs["waiter_user_id"],
            waiter_exprs["waiter_iiko_id"],
            waiter_exprs["waiter_iiko_code"],
            waiter_exprs["waiter_name_iiko"],
            IikoSaleItem.dish_code,
            position_expr,
            group_expr,
            category_expr,
            IikoSaleItem.dish_measure_unit,
            payment_type_expr,
        )
        .order_by(
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).desc(),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).desc(),
            position_expr.asc().nullslast(),
        )
        .limit(limit)
        .all()
    )

    totals_row = base_q.with_entities(
        sa.func.count(sa.distinct(order_number_expr)).label("orders_count"),
        sa.func.count(IikoSaleItem.id).label("items_count"),
        sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("qty"),
        sa.func.coalesce(sa.func.sum(kitchen_load_expr), 0).label("kitchen_load_qty"),
        sa.func.coalesce(sa.func.sum(hall_load_expr), 0).label("hall_load_qty"),
        sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("sum"),
        sa.func.coalesce(sa.func.sum(IikoSaleItem.discount_sum), 0).label("discount_sum"),
    ).one()
    filtered_order_ids_subq = base_q.with_entities(
        IikoSaleOrder.id.label("order_id")
    ).distinct().subquery(name="waiter_positions_filtered_orders")
    guests_total_row = (
        db.query(
            sa.func.coalesce(sa.func.sum(IikoSaleOrder.guest_num), 0).label("guests_count"),
        )
        .join(filtered_order_ids_subq, filtered_order_ids_subq.c.order_id == IikoSaleOrder.id)
        .one()
    )

    totals = {
        "orders_count": int(totals_row.orders_count or 0),
        "guests_count": int(guests_total_row.guests_count or 0),
        "items_count": int(totals_row.items_count or 0),
        "qty": float(totals_row.qty or 0),
        "kitchen_load_qty": float(totals_row.kitchen_load_qty or 0),
        "hall_load_qty": float(totals_row.hall_load_qty or 0),
        "sum": float(totals_row.sum or 0),
        "discount_sum": float(totals_row.discount_sum or 0),
    }
    identity_maps = load_waiter_identity_maps(
        db,
        rows,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=clean_waiter_iiko_id,
        waiter_iiko_code=clean_waiter_iiko_code,
    )
    positions_payload = build_waiter_positions_payload(
        rows,
        restaurant_name_by_id=restaurant_name_by_id,
        identity_maps=identity_maps,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=clean_waiter_iiko_id,
        waiter_iiko_code=clean_waiter_iiko_code,
        totals=totals,
    )
    items = positions_payload["items"]
    waiter_payload = positions_payload["waiter"]
    totals = positions_payload["totals"]

    if not can_view_money:
        zero_money_metrics(totals)
        for row in items:
            zero_money_metrics(row)

    return {
        "from_date": start.isoformat(),
        "to_date": (end_excl - timedelta(days=1)).isoformat(),
        "deleted_mode": resolved_deleted_mode,
        "waiter_mode": resolved_waiter_mode,
        "restaurant_id": restaurant_id,
        "waiter": waiter_payload,
        "items": items,
        "totals": {
            "orders_count": int(totals["orders_count"]),
            "guests_count": int(totals["guests_count"]),
            "items_count": int(totals["items_count"]),
            "qty": round(float(totals["qty"]), 3),
            "kitchen_load_qty": round(float(totals["kitchen_load_qty"]), 3),
            "hall_load_qty": round(float(totals["hall_load_qty"]), 3),
            "sum": round(float(totals["sum"]), 2),
            "discount_sum": round(float(totals["discount_sum"]), 2),
        },
    }
