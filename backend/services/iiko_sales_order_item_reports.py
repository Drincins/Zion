from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Sequence, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.iiko_catalog import IikoProduct, IikoProductSetting
from backend.bd.iiko_sales import IikoSaleItem, IikoSaleOrder, IikoSalesHallTable
from backend.bd.models import User
from backend.services.iiko_api import to_iso_date
from backend.services.iiko_sales_finance_refs import (
    non_cash_lookup_by_id,
    payment_method_lookup_by_guid,
)
from backend.services.iiko_sales_layouts import (
    apply_hall_filter_to_base_query,
    build_sales_hall_table_resolver,
    sales_hall_tables_query,
)
from backend.services.iiko_sales_report_dimensions import (
    clean_optional_text,
    dish_category_sql_expr,
    dish_group_sql_expr,
    extract_dish_category_name,
    looks_like_uuid,
    user_meta_by_iiko_codes,
    user_meta_by_iiko_ids,
    user_names_by_ids,
)
from backend.services.iiko_sales_report_filters import (
    apply_deleted_mode_filter,
    apply_waiter_filter_to_items_query,
    lower_values,
    serialize_deleted_payload,
    split_filter_values,
)
from backend.services.iiko_sales_scope import ensure_user_access_to_restaurant, list_accessible_restaurants
from backend.services.iiko_sales_payloads import (
    extract_dish_waiter_fields,
    extract_non_cash_fields,
    extract_payload_text,
    extract_payment_method_fields,
)
from backend.services.iiko_sales_waiter_reports import (
    apply_waiter_sales_dimension_filters,
    waiter_sales_payment_type_expr,
    waiter_sales_position_expr,
    zero_money_metrics,
)
from backend.services.iiko_sales_waiter_turnover import (
    normalize_deleted_mode,
    normalize_waiter_mode,
)


def prepare_order_item_filter_values(
    *,
    include_groups: Optional[List[str]] = None,
    include_categories: Optional[List[str]] = None,
    include_positions: Optional[List[str]] = None,
    include_payment_types: Optional[List[str]] = None,
    include_halls: Optional[List[str]] = None,
    include_departments: Optional[List[str]] = None,
    include_tables: Optional[List[str]] = None,
) -> dict[str, List[str]]:
    return {
        "include_groups_lower": lower_values(split_filter_values(include_groups)),
        "include_categories_lower": lower_values(split_filter_values(include_categories)),
        "include_positions_lower": lower_values(split_filter_values(include_positions)),
        "include_payment_types_lower": lower_values(split_filter_values(include_payment_types)),
        "include_halls_lower": lower_values(split_filter_values(include_halls)),
        "include_departments_lower": lower_values(split_filter_values(include_departments)),
        "include_tables_lower": lower_values(split_filter_values(include_tables)),
    }


def apply_order_report_scope_filters(
    db: Session,
    current_user: User,
    query,
    *,
    restaurant_id: Optional[int],
    source_restaurant_id: Optional[int],
    include_departments_lower: List[str],
    include_tables_lower: List[str],
    include_halls_lower: List[str],
):
    if restaurant_id is not None:
        query = query.filter(IikoSaleOrder.restaurant_id == restaurant_id)
    if source_restaurant_id is not None:
        query = query.filter(
            sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id) == source_restaurant_id
        )
    if include_departments_lower:
        query = query.filter(
            sa.func.lower(sa.func.coalesce(IikoSaleOrder.department, "")).in_(include_departments_lower)
        )
    if include_tables_lower:
        query = query.filter(
            sa.func.lower(sa.func.coalesce(IikoSaleOrder.table_num, "")).in_(include_tables_lower)
        )
    if include_halls_lower:
        query = apply_hall_filter_to_base_query(db, current_user, query, include_halls_lower)
    return query


def apply_item_report_scope_filters(
    db: Session,
    current_user: User,
    query,
    *,
    restaurant_id: Optional[int],
    source_restaurant_id: Optional[int],
    order_id,
    include_departments_lower: List[str],
    include_tables_lower: List[str],
    include_halls_lower: List[str],
):
    query = apply_order_report_scope_filters(
        db,
        current_user,
        query,
        restaurant_id=restaurant_id,
        source_restaurant_id=source_restaurant_id,
        include_departments_lower=include_departments_lower,
        include_tables_lower=include_tables_lower,
        include_halls_lower=include_halls_lower,
    )
    if order_id is not None:
        query = query.filter(IikoSaleItem.order_id == order_id)
    return query


def build_orders_item_scope_subquery(
    db: Session,
    current_user: User,
    *,
    accessible_ids: List[int],
    start: date,
    end_exclusive: date,
    resolved_deleted_mode: str,
    resolved_waiter_mode: str,
    restaurant_id: Optional[int],
    source_restaurant_id: Optional[int],
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
    clean_dish_code: Optional[str],
    include_groups_lower: List[str],
    include_categories_lower: List[str],
    include_positions_lower: List[str],
    include_payment_types_lower: List[str],
    include_halls_lower: List[str],
    include_departments_lower: List[str],
    include_tables_lower: List[str],
):
    scoped_items_q = (
        db.query(IikoSaleItem.order_id.label("order_id"))
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_exclusive)
    )
    scoped_items_q = apply_deleted_mode_filter(
        scoped_items_q,
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
    scoped_items_q = apply_order_report_scope_filters(
        db,
        current_user,
        scoped_items_q,
        restaurant_id=restaurant_id,
        source_restaurant_id=source_restaurant_id,
        include_departments_lower=include_departments_lower,
        include_tables_lower=include_tables_lower,
        include_halls_lower=include_halls_lower,
    )
    scoped_items_q = apply_waiter_filter_to_items_query(
        db,
        scoped_items_q,
        waiter_mode=resolved_waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=waiter_iiko_id,
        waiter_iiko_code=waiter_iiko_code,
    )
    if clean_dish_code:
        scoped_items_q = scoped_items_q.filter(IikoSaleItem.dish_code == clean_dish_code)

    scoped_items_q = apply_waiter_sales_dimension_filters(
        scoped_items_q,
        group_expr=dish_group_sql_expr(),
        category_expr=dish_category_sql_expr(),
        position_expr=waiter_sales_position_expr(),
        payment_type_expr=waiter_sales_payment_type_expr(),
        include_groups_lower=include_groups_lower,
        exclude_groups_lower=[],
        include_categories_lower=include_categories_lower,
        exclude_categories_lower=[],
        include_positions_lower=include_positions_lower,
        exclude_positions_lower=[],
        include_payment_types_lower=include_payment_types_lower,
    )
    return scoped_items_q.distinct().subquery(name="sales_orders_items_scope")


def build_order_hall_meta_by_id(
    db: Session,
    current_user: User,
    order_rows: Sequence[Any],
) -> Dict[str, Dict[str, Any]]:
    meta_by_id: Dict[str, Dict[str, Any]] = {}
    if not order_rows:
        return meta_by_id

    hall_rows_q = sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.is_active.is_(True))
    restaurant_ids = {
        int(getattr(order_row, "restaurant_id"))
        for order_row in order_rows
        if getattr(order_row, "restaurant_id", None) is not None
    }
    if restaurant_ids:
        hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.restaurant_id.in_(sorted(restaurant_ids)))
    resolve_hall = build_sales_hall_table_resolver(hall_rows_q.all())

    for order_row in order_rows:
        row_id = getattr(order_row, "id", None)
        if row_id is None:
            continue
        resolved = resolve_hall(
            restaurant_id=getattr(order_row, "restaurant_id", None),
            source_restaurant_id=getattr(order_row, "source_restaurant_id", None),
            department=getattr(order_row, "department", None),
            table_num=getattr(order_row, "table_num", None),
        )
        meta_by_id[str(row_id)] = {
            "department": getattr(order_row, "department", None),
            "table_num": getattr(order_row, "table_num", None),
            "hall_name": resolved.get("hall_name"),
            "hall_name_norm": resolved.get("hall_name_norm"),
            "zone_name": resolved.get("zone_name"),
            "zone_name_norm": resolved.get("zone_name_norm"),
            "table_name": resolved.get("table_name"),
            "table_capacity": resolved.get("capacity"),
        }
    return meta_by_id


def build_product_meta_by_id(
    db: Session,
    *,
    product_ids: set[str],
) -> Dict[str, Dict[str, Any]]:
    if not product_ids:
        return {}

    coef_rows = (
        db.query(
            IikoProduct.id.label("product_id"),
            IikoProductSetting.portion_coef_kitchen.label("portion_coef_kitchen"),
            IikoProductSetting.portion_coef_hall.label("portion_coef_hall"),
            IikoProduct.product_category.label("product_category"),
            sa.func.jsonb_extract_path_text(
                IikoProduct.raw_payload,
                "product",
                "product_category",
            ).label("legacy_product_category"),
            IikoProductSetting.custom_product_category.label("custom_product_category"),
        )
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .filter(IikoProduct.id.in_(product_ids))
        .all()
    )

    product_meta_by_id: Dict[str, Dict[str, Any]] = {}
    for coef_row in coef_rows:
        custom_category = clean_optional_text(getattr(coef_row, "custom_product_category", None))
        base_category = clean_optional_text(getattr(coef_row, "product_category", None))
        legacy_category = clean_optional_text(getattr(coef_row, "legacy_product_category", None))
        product_meta_by_id[str(coef_row.product_id)] = {
            "portion_coef_kitchen": float(coef_row.portion_coef_kitchen)
            if coef_row.portion_coef_kitchen is not None
            else None,
            "portion_coef_hall": float(coef_row.portion_coef_hall)
            if coef_row.portion_coef_hall is not None
            else None,
            "dish_category": custom_category or legacy_category or base_category,
        }
    return product_meta_by_id


def collect_order_report_payload_context(rows: Sequence[Any]) -> Dict[str, Any]:
    payment_by_order_id: Dict[str, tuple[Optional[str], Optional[str]]] = {}
    non_cash_by_order_id: Dict[str, tuple[Optional[str], Optional[str]]] = {}
    cashier_name_iiko_by_order_id: Dict[str, Optional[str]] = {}
    auth_user_name_iiko_by_order_id: Dict[str, Optional[str]] = {}
    order_waiter_name_iiko_by_order_id: Dict[str, Optional[str]] = {}
    payment_guids: set[str] = set()
    non_cash_ids: set[str] = set()
    user_ids: set[int] = set()

    for row in rows:
        row_id = str(getattr(row, "id"))
        raw_payload = getattr(row, "raw_payload", None)
        pay_guid, pay_name = extract_payment_method_fields(raw_payload)
        non_cash_id, non_cash_name = extract_non_cash_fields(raw_payload)
        payment_by_order_id[row_id] = (pay_guid, pay_name)
        non_cash_by_order_id[row_id] = (non_cash_id, non_cash_name)
        cashier_name_iiko_by_order_id[row_id] = extract_payload_text(raw_payload, "Cashier.Name")
        auth_user_name_iiko_by_order_id[row_id] = extract_payload_text(raw_payload, "AuthUser.Name")
        order_waiter_name_iiko_by_order_id[row_id] = extract_payload_text(raw_payload, "OrderWaiter.Name")
        if pay_guid:
            payment_guids.add(pay_guid)
        if non_cash_id:
            non_cash_ids.add(non_cash_id)
        if getattr(row, "order_waiter_user_id", None) is not None:
            user_ids.add(int(getattr(row, "order_waiter_user_id")))
        if getattr(row, "cashier_user_id", None) is not None:
            user_ids.add(int(getattr(row, "cashier_user_id")))
        if getattr(row, "auth_user_id", None) is not None:
            user_ids.add(int(getattr(row, "auth_user_id")))

    return {
        "payment_by_order_id": payment_by_order_id,
        "non_cash_by_order_id": non_cash_by_order_id,
        "cashier_name_iiko_by_order_id": cashier_name_iiko_by_order_id,
        "auth_user_name_iiko_by_order_id": auth_user_name_iiko_by_order_id,
        "order_waiter_name_iiko_by_order_id": order_waiter_name_iiko_by_order_id,
        "payment_guids": payment_guids,
        "non_cash_ids": non_cash_ids,
        "user_ids": user_ids,
    }


def serialize_order_report_rows(
    rows: Sequence[Any],
    *,
    restaurant_name_by_id: Dict[int, str],
    order_hall_meta_by_id: Dict[str, Dict[str, Any]],
    payment_lookup: Dict[str, Dict[str, Any]],
    non_cash_lookup: Dict[str, Dict[str, Any]],
    user_name_by_id: Dict[int, str],
    payload_context: Dict[str, Any],
) -> List[Dict[str, Any]]:
    payment_by_order_id = payload_context.get("payment_by_order_id") or {}
    non_cash_by_order_id = payload_context.get("non_cash_by_order_id") or {}
    cashier_name_iiko_by_order_id = payload_context.get("cashier_name_iiko_by_order_id") or {}
    auth_user_name_iiko_by_order_id = payload_context.get("auth_user_name_iiko_by_order_id") or {}
    order_waiter_name_iiko_by_order_id = payload_context.get("order_waiter_name_iiko_by_order_id") or {}

    items: List[Dict[str, Any]] = []
    for row in rows:
        row_id = str(getattr(row, "id"))
        order_hall_meta = order_hall_meta_by_id.get(row_id) or {}
        payment_pair = payment_by_order_id.get(row_id, (None, None))
        non_cash_pair = non_cash_by_order_id.get(row_id, (None, None))

        items.append(
            {
                "id": row_id,
                "company_id": getattr(row, "company_id", None),
                "restaurant_id": getattr(row, "restaurant_id", None),
                "restaurant_name": restaurant_name_by_id.get(getattr(row, "restaurant_id", None)),
                "source_restaurant_id": getattr(row, "source_restaurant_id", None),
                "source_restaurant_name": (
                    restaurant_name_by_id.get(getattr(row, "source_restaurant_id", None))
                    if getattr(row, "source_restaurant_id", None) is not None
                    else restaurant_name_by_id.get(getattr(row, "restaurant_id", None))
                ),
                "iiko_order_id": getattr(row, "iiko_order_id", None),
                "order_num": getattr(row, "order_num", None),
                "open_date": getattr(row, "open_date", None).isoformat() if getattr(row, "open_date", None) else None,
                "opened_at": getattr(row, "opened_at", None).isoformat() if getattr(row, "opened_at", None) else None,
                "closed_at": getattr(row, "closed_at", None).isoformat() if getattr(row, "closed_at", None) else None,
                "department": getattr(row, "department", None),
                "hall_name": order_hall_meta.get("hall_name"),
                "hall_name_norm": order_hall_meta.get("hall_name_norm"),
                "zone_name": order_hall_meta.get("zone_name"),
                "zone_name_norm": order_hall_meta.get("zone_name_norm"),
                "table_num": getattr(row, "table_num", None),
                "table_name": order_hall_meta.get("table_name"),
                "table_capacity": order_hall_meta.get("table_capacity"),
                "guest_num": getattr(row, "guest_num", None),
                "order_waiter_iiko_id": getattr(row, "order_waiter_iiko_id", None),
                "order_waiter_name": getattr(row, "order_waiter_name", None),
                "order_waiter_name_iiko": order_waiter_name_iiko_by_order_id.get(row_id)
                or getattr(row, "order_waiter_name", None),
                "cashier_iiko_id": getattr(row, "cashier_iiko_id", None),
                "cashier_code": getattr(row, "cashier_code", None),
                "cashier_name_iiko": cashier_name_iiko_by_order_id.get(row_id),
                "auth_user_iiko_id": getattr(row, "auth_user_iiko_id", None),
                "auth_user_name_iiko": auth_user_name_iiko_by_order_id.get(row_id),
                "order_waiter_user_id": getattr(row, "order_waiter_user_id", None),
                "order_waiter_user_name": (
                    user_name_by_id.get(int(getattr(row, "order_waiter_user_id")))
                    if getattr(row, "order_waiter_user_id", None) is not None
                    else None
                ),
                "cashier_user_id": getattr(row, "cashier_user_id", None),
                "cashier_user_name": (
                    user_name_by_id.get(int(getattr(row, "cashier_user_id")))
                    if getattr(row, "cashier_user_id", None) is not None
                    else None
                ),
                "auth_user_id": getattr(row, "auth_user_id", None),
                "auth_user_name": (
                    user_name_by_id.get(int(getattr(row, "auth_user_id")))
                    if getattr(row, "auth_user_id", None) is not None
                    else None
                ),
                "payment_method_guid": payment_pair[0],
                "payment_method_name": payment_lookup.get(payment_pair[0], {}).get("name") or payment_pair[1],
                "non_cash_payment_type_id": non_cash_pair[0],
                "non_cash_payment_type_name": non_cash_lookup.get(non_cash_pair[0], {}).get("name") or non_cash_pair[1],
                "non_cash_payment_type_category": non_cash_lookup.get(non_cash_pair[0], {}).get("category"),
                "non_cash_payment_type_is_active": non_cash_lookup.get(non_cash_pair[0], {}).get("is_active"),
                "payment_method_category": payment_lookup.get(payment_pair[0], {}).get("category"),
                "payment_method_is_active": payment_lookup.get(payment_pair[0], {}).get("is_active"),
                **serialize_deleted_payload(getattr(row, "raw_payload", None)),
                "created_at": getattr(row, "created_at", None).isoformat() if getattr(row, "created_at", None) else None,
                "updated_at": getattr(row, "updated_at", None).isoformat() if getattr(row, "updated_at", None) else None,
            }
        )
    return items


def collect_item_report_payload_context(rows: Sequence[Any]) -> Dict[str, Any]:
    payment_by_item_id: Dict[str, tuple[Optional[str], Optional[str]]] = {}
    non_cash_by_item_id: Dict[str, tuple[Optional[str], Optional[str]]] = {}
    cashier_name_iiko_by_item_id: Dict[str, Optional[str]] = {}
    auth_user_name_iiko_by_item_id: Dict[str, Optional[str]] = {}
    order_waiter_name_iiko_by_item_id: Dict[str, Optional[str]] = {}
    dish_waiter_iiko_id_by_item_id: Dict[str, Optional[str]] = {}
    dish_waiter_name_iiko_by_item_id: Dict[str, Optional[str]] = {}
    dish_waiter_code_by_item_id: Dict[str, Optional[str]] = {}
    dish_waiter_source_by_item_id: Dict[str, Optional[str]] = {}
    payment_guids: set[str] = set()
    non_cash_ids: set[str] = set()
    user_ids: set[int] = set()
    iiko_ids: set[str] = set()
    iiko_codes: set[str] = set()

    for row in rows:
        row_id = str(getattr(row, "id"))
        raw_payload = getattr(row, "raw_payload", None)
        pay_guid, pay_name = extract_payment_method_fields(raw_payload)
        non_cash_id, non_cash_name = extract_non_cash_fields(raw_payload)
        dish_waiter_iiko_id, dish_waiter_name_iiko, dish_waiter_code, dish_waiter_source = extract_dish_waiter_fields(
            raw_payload
        )

        payment_by_item_id[row_id] = (pay_guid, pay_name)
        non_cash_by_item_id[row_id] = (non_cash_id, non_cash_name)
        cashier_name_iiko_by_item_id[row_id] = extract_payload_text(raw_payload, "Cashier.Name")
        auth_user_name_iiko_by_item_id[row_id] = extract_payload_text(raw_payload, "AuthUser.Name")
        order_waiter_name_iiko_by_item_id[row_id] = extract_payload_text(raw_payload, "OrderWaiter.Name")
        dish_waiter_iiko_id_by_item_id[row_id] = dish_waiter_iiko_id
        dish_waiter_name_iiko_by_item_id[row_id] = dish_waiter_name_iiko
        dish_waiter_code_by_item_id[row_id] = dish_waiter_code
        dish_waiter_source_by_item_id[row_id] = dish_waiter_source

        if pay_guid:
            payment_guids.add(pay_guid)
        if non_cash_id:
            non_cash_ids.add(non_cash_id)
        if getattr(row, "auth_user_id", None) is not None:
            user_ids.add(int(getattr(row, "auth_user_id")))
        if getattr(row, "auth_user_iiko_id", None):
            iiko_ids.add(str(getattr(row, "auth_user_iiko_id")))
        if getattr(row, "order_waiter_iiko_id", None):
            iiko_ids.add(str(getattr(row, "order_waiter_iiko_id")))
        if dish_waiter_iiko_id:
            iiko_ids.add(str(dish_waiter_iiko_id))
        if dish_waiter_code:
            iiko_codes.add(str(dish_waiter_code))

    return {
        "payment_by_item_id": payment_by_item_id,
        "non_cash_by_item_id": non_cash_by_item_id,
        "cashier_name_iiko_by_item_id": cashier_name_iiko_by_item_id,
        "auth_user_name_iiko_by_item_id": auth_user_name_iiko_by_item_id,
        "order_waiter_name_iiko_by_item_id": order_waiter_name_iiko_by_item_id,
        "dish_waiter_iiko_id_by_item_id": dish_waiter_iiko_id_by_item_id,
        "dish_waiter_name_iiko_by_item_id": dish_waiter_name_iiko_by_item_id,
        "dish_waiter_code_by_item_id": dish_waiter_code_by_item_id,
        "dish_waiter_source_by_item_id": dish_waiter_source_by_item_id,
        "payment_guids": payment_guids,
        "non_cash_ids": non_cash_ids,
        "user_ids": user_ids,
        "iiko_ids": iiko_ids,
        "iiko_codes": iiko_codes,
    }


def serialize_item_report_rows(
    rows: Sequence[Any],
    *,
    restaurant_name_by_id: Dict[int, str],
    order_meta_by_id: Dict[str, Dict[str, Any]],
    payment_lookup: Dict[str, Dict[str, Any]],
    non_cash_lookup: Dict[str, Dict[str, Any]],
    user_name_by_id: Dict[int, str],
    user_meta_by_iiko_id: Dict[str, Dict[str, Any]],
    user_meta_by_iiko_code: Dict[str, Dict[str, Any]],
    product_meta_by_id: Dict[str, Dict[str, Any]],
    payload_context: Dict[str, Any],
) -> List[Dict[str, Any]]:
    payment_by_item_id = payload_context.get("payment_by_item_id") or {}
    non_cash_by_item_id = payload_context.get("non_cash_by_item_id") or {}
    cashier_name_iiko_by_item_id = payload_context.get("cashier_name_iiko_by_item_id") or {}
    auth_user_name_iiko_by_item_id = payload_context.get("auth_user_name_iiko_by_item_id") or {}
    order_waiter_name_iiko_by_item_id = payload_context.get("order_waiter_name_iiko_by_item_id") or {}
    dish_waiter_iiko_id_by_item_id = payload_context.get("dish_waiter_iiko_id_by_item_id") or {}
    dish_waiter_name_iiko_by_item_id = payload_context.get("dish_waiter_name_iiko_by_item_id") or {}
    dish_waiter_code_by_item_id = payload_context.get("dish_waiter_code_by_item_id") or {}
    dish_waiter_source_by_item_id = payload_context.get("dish_waiter_source_by_item_id") or {}

    items: List[Dict[str, Any]] = []
    for row in rows:
        row_id = str(getattr(row, "id"))
        order_meta = order_meta_by_id.get(str(getattr(row, "order_id"))) or {}
        payment_pair = payment_by_item_id.get(row_id, (None, None))
        non_cash_pair = non_cash_by_item_id.get(row_id, (None, None))
        qty_value = float(getattr(row, "qty", None)) if getattr(row, "qty", None) is not None else None
        sum_value = float(getattr(row, "sum", None)) if getattr(row, "sum", None) is not None else None
        discount_value = (
            float(getattr(row, "discount_sum", None))
            if getattr(row, "discount_sum", None) is not None
            else None
        )

        dish_waiter_iiko_id = dish_waiter_iiko_id_by_item_id.get(row_id)
        dish_waiter_name_iiko = dish_waiter_name_iiko_by_item_id.get(row_id)
        dish_waiter_code = dish_waiter_code_by_item_id.get(row_id)
        dish_waiter_source = dish_waiter_source_by_item_id.get(row_id)
        dish_waiter_meta: Dict[str, Any] = {}
        if dish_waiter_iiko_id:
            dish_waiter_meta = user_meta_by_iiko_id.get(str(dish_waiter_iiko_id), {})
        if not dish_waiter_meta and dish_waiter_code:
            dish_waiter_meta = user_meta_by_iiko_code.get(str(dish_waiter_code), {})
        dish_waiter_user_id = dish_waiter_meta.get("id")
        dish_waiter_user_name = dish_waiter_meta.get("name")

        product_meta = product_meta_by_id.get(str(getattr(row, "iiko_product_id")), {})
        kitchen_coef = product_meta.get("portion_coef_kitchen")
        hall_coef = product_meta.get("portion_coef_hall")
        dish_category_from_product = clean_optional_text(product_meta.get("dish_category"))
        if looks_like_uuid(dish_category_from_product):
            dish_category_from_product = None
        dish_category_from_payload = extract_dish_category_name(getattr(row, "raw_payload", None))
        dish_category_id = clean_optional_text(getattr(row, "dish_category_id", None))
        dish_category_from_id = dish_category_id if dish_category_id and not looks_like_uuid(dish_category_id) else None
        dish_category_resolved = dish_category_from_payload or dish_category_from_product or dish_category_from_id

        kitchen_load_value = (
            qty_value * (kitchen_coef if kitchen_coef is not None else 1.0)
            if qty_value is not None
            else None
        )
        hall_load_value = (
            qty_value * (hall_coef if hall_coef is not None else 1.0)
            if qty_value is not None
            else None
        )

        items.append(
            {
                "id": row_id,
                "order_id": str(getattr(row, "order_id")),
                "company_id": getattr(row, "company_id", None),
                "restaurant_id": getattr(row, "restaurant_id", None),
                "restaurant_name": restaurant_name_by_id.get(getattr(row, "restaurant_id", None)),
                "source_restaurant_id": getattr(row, "source_restaurant_id", None),
                "source_restaurant_name": (
                    restaurant_name_by_id.get(getattr(row, "source_restaurant_id", None))
                    if getattr(row, "source_restaurant_id", None) is not None
                    else restaurant_name_by_id.get(getattr(row, "restaurant_id", None))
                ),
                "department": order_meta.get("department"),
                "hall_name": order_meta.get("hall_name"),
                "hall_name_norm": order_meta.get("hall_name_norm"),
                "zone_name": order_meta.get("zone_name"),
                "zone_name_norm": order_meta.get("zone_name_norm"),
                "table_num": order_meta.get("table_num"),
                "table_name": order_meta.get("table_name"),
                "table_capacity": order_meta.get("table_capacity"),
                "open_date": getattr(row, "open_date", None).isoformat() if getattr(row, "open_date", None) else None,
                "line_key": getattr(row, "line_key", None),
                "dish_code": getattr(row, "dish_code", None),
                "dish_name": getattr(row, "dish_name", None),
                "dish_group": getattr(row, "dish_group", None),
                "dish_category_id": getattr(row, "dish_category_id", None),
                "dish_category": dish_category_resolved,
                "dish_measure_unit": getattr(row, "dish_measure_unit", None),
                "cooking_place": getattr(row, "cooking_place", None),
                "qty": qty_value,
                "portion_coef_kitchen": kitchen_coef,
                "portion_coef_hall": hall_coef,
                "kitchen_load_qty": kitchen_load_value,
                "hall_load_qty": hall_load_value,
                "sum": sum_value,
                "discount_sum": discount_value,
                "cashier_code": getattr(row, "cashier_code", None),
                "cashier_name_iiko": cashier_name_iiko_by_item_id.get(row_id),
                "order_waiter_iiko_id": getattr(row, "order_waiter_iiko_id", None),
                "order_waiter_name_iiko": order_waiter_name_iiko_by_item_id.get(row_id),
                "order_waiter_user_name": (
                    user_meta_by_iiko_id.get(str(getattr(row, "order_waiter_iiko_id")), {}).get("name")
                    if getattr(row, "order_waiter_iiko_id", None)
                    else None
                ),
                "dish_waiter_iiko_id": dish_waiter_iiko_id,
                "dish_waiter_code": dish_waiter_code,
                "dish_waiter_name_iiko": dish_waiter_name_iiko,
                "dish_waiter_source": dish_waiter_source,
                "dish_waiter_user_id": dish_waiter_user_id,
                "dish_waiter_user_name": dish_waiter_user_name
                or dish_waiter_name_iiko
                or dish_waiter_code
                or dish_waiter_iiko_id,
                "auth_user_iiko_id": getattr(row, "auth_user_iiko_id", None),
                "auth_user_name_iiko": auth_user_name_iiko_by_item_id.get(row_id),
                "auth_user_id": getattr(row, "auth_user_id", None),
                "auth_user_name": (
                    user_name_by_id.get(int(getattr(row, "auth_user_id")))
                    if getattr(row, "auth_user_id", None) is not None
                    else user_meta_by_iiko_id.get(str(getattr(row, "auth_user_iiko_id")), {}).get("name")
                    if getattr(row, "auth_user_iiko_id", None)
                    else None
                ),
                "iiko_product_id": getattr(row, "iiko_product_id", None),
                "payment_method_guid": payment_pair[0],
                "payment_method_name": payment_lookup.get(payment_pair[0], {}).get("name") or payment_pair[1],
                "non_cash_payment_type_id": non_cash_pair[0],
                "non_cash_payment_type_name": non_cash_lookup.get(non_cash_pair[0], {}).get("name") or non_cash_pair[1],
                "non_cash_payment_type_category": non_cash_lookup.get(non_cash_pair[0], {}).get("category"),
                "non_cash_payment_type_is_active": non_cash_lookup.get(non_cash_pair[0], {}).get("is_active"),
                "payment_method_category": payment_lookup.get(payment_pair[0], {}).get("category"),
                "payment_method_is_active": payment_lookup.get(payment_pair[0], {}).get("is_active"),
                **serialize_deleted_payload(getattr(row, "raw_payload", None)),
                "created_at": getattr(row, "created_at", None).isoformat() if getattr(row, "created_at", None) else None,
                "updated_at": getattr(row, "updated_at", None).isoformat() if getattr(row, "updated_at", None) else None,
            }
        )

    return items


def list_orders_payload(
    db: Session,
    current_user: User,
    *,
    restaurant_id: Optional[int],
    source_restaurant_id: Optional[int],
    from_date: str,
    to_date: str,
    dish_code: Optional[str],
    deleted_mode: str,
    waiter_mode: str,
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
    include_payment_types: Optional[List[str]],
    include_groups: Optional[List[str]],
    include_categories: Optional[List[str]],
    include_positions: Optional[List[str]],
    include_halls: Optional[List[str]],
    include_departments: Optional[List[str]],
    include_tables: Optional[List[str]],
    limit: int,
    offset: int,
    with_meta: bool,
) -> Any:
    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
    if source_restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)

    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = [restaurant.id for restaurant in accessible_restaurants]
    restaurant_name_by_id = {restaurant.id: restaurant.name for restaurant in accessible_restaurants}
    if not accessible_ids:
        if with_meta:
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        return []

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)
    resolved_deleted_mode = normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = normalize_waiter_mode(waiter_mode)
    clean_waiter_iiko_id = clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = clean_optional_text(waiter_iiko_code)
    clean_dish_code = clean_optional_text(dish_code)

    filters = prepare_order_item_filter_values(
        include_groups=include_groups,
        include_categories=include_categories,
        include_positions=include_positions,
        include_payment_types=include_payment_types,
        include_halls=include_halls,
        include_departments=include_departments,
        include_tables=include_tables,
    )

    query = (
        db.query(IikoSaleOrder)
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_excl)
        .order_by(IikoSaleOrder.open_date.desc(), IikoSaleOrder.opened_at.desc().nullslast(), IikoSaleOrder.id.desc())
    )
    query = apply_deleted_mode_filter(
        query,
        deleted_mode=resolved_deleted_mode,
        order_deleted_expr=IikoSaleOrder.raw_payload["OrderDeleted"].astext,
        deleted_with_writeoff_expr=IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
    )
    query = apply_order_report_scope_filters(
        db,
        current_user,
        query,
        restaurant_id=restaurant_id,
        source_restaurant_id=source_restaurant_id,
        include_departments_lower=filters["include_departments_lower"],
        include_tables_lower=filters["include_tables_lower"],
        include_halls_lower=filters["include_halls_lower"],
    )

    has_item_scope_filters = bool(
        filters["include_groups_lower"]
        or filters["include_categories_lower"]
        or filters["include_positions_lower"]
        or filters["include_payment_types_lower"]
        or clean_dish_code
        or waiter_user_id is not None
        or clean_waiter_iiko_id
        or clean_waiter_iiko_code
    )
    if has_item_scope_filters:
        scoped_items_subq = build_orders_item_scope_subquery(
            db,
            current_user,
            accessible_ids=accessible_ids,
            start=start,
            end_exclusive=end_excl,
            resolved_deleted_mode=resolved_deleted_mode,
            resolved_waiter_mode=resolved_waiter_mode,
            restaurant_id=restaurant_id,
            source_restaurant_id=source_restaurant_id,
            waiter_user_id=waiter_user_id,
            waiter_iiko_id=clean_waiter_iiko_id,
            waiter_iiko_code=clean_waiter_iiko_code,
            clean_dish_code=clean_dish_code,
            include_groups_lower=filters["include_groups_lower"],
            include_categories_lower=filters["include_categories_lower"],
            include_positions_lower=filters["include_positions_lower"],
            include_payment_types_lower=filters["include_payment_types_lower"],
            include_halls_lower=filters["include_halls_lower"],
            include_departments_lower=filters["include_departments_lower"],
            include_tables_lower=filters["include_tables_lower"],
        )
        query = query.filter(IikoSaleOrder.id.in_(sa.select(scoped_items_subq.c.order_id)))

    total = query.count() if with_meta else None
    rows = query.offset(offset).limit(limit).all()

    order_hall_meta_by_id = build_order_hall_meta_by_id(db, current_user, rows)
    payload_context = collect_order_report_payload_context(rows)
    payment_lookup = payment_method_lookup_by_guid(db, current_user, payload_context["payment_guids"])
    non_cash_lookup = non_cash_lookup_by_id(db, current_user, payload_context["non_cash_ids"])
    user_name_by_id = user_names_by_ids(db, payload_context["user_ids"])

    items = serialize_order_report_rows(
        rows,
        restaurant_name_by_id=restaurant_name_by_id,
        order_hall_meta_by_id=order_hall_meta_by_id,
        payment_lookup=payment_lookup,
        non_cash_lookup=non_cash_lookup,
        user_name_by_id=user_name_by_id,
        payload_context=payload_context,
    )
    if with_meta:
        return {"items": items, "total": total, "limit": limit, "offset": offset}
    return items


def list_items_payload(
    db: Session,
    current_user: User,
    *,
    restaurant_id: Optional[int],
    source_restaurant_id: Optional[int],
    order_id: Optional[Any],
    from_date: str,
    to_date: str,
    dish_code: Optional[str],
    deleted_mode: str,
    waiter_mode: str,
    waiter_user_id: Optional[int],
    waiter_iiko_id: Optional[str],
    waiter_iiko_code: Optional[str],
    include_payment_types: Optional[List[str]],
    include_groups: Optional[List[str]],
    include_categories: Optional[List[str]],
    include_positions: Optional[List[str]],
    include_halls: Optional[List[str]],
    include_departments: Optional[List[str]],
    include_tables: Optional[List[str]],
    limit: int,
    offset: int,
    with_meta: bool,
    can_view_money: bool,
) -> Any:
    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
    if source_restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)

    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = [restaurant.id for restaurant in accessible_restaurants]
    restaurant_name_by_id = {restaurant.id: restaurant.name for restaurant in accessible_restaurants}
    if not accessible_ids:
        if with_meta:
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "totals": {
                    "qty": 0.0,
                    "kitchen_load_qty": 0.0,
                    "hall_load_qty": 0.0,
                    "sum": 0.0,
                    "discount_sum": 0.0,
                },
            }
        return []

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)
    resolved_deleted_mode = normalize_deleted_mode(deleted_mode)
    resolved_waiter_mode = normalize_waiter_mode(waiter_mode)
    clean_waiter_iiko_id = clean_optional_text(waiter_iiko_id)
    clean_waiter_iiko_code = clean_optional_text(waiter_iiko_code)
    clean_dish_code = clean_optional_text(dish_code)

    filters = prepare_order_item_filter_values(
        include_groups=include_groups,
        include_categories=include_categories,
        include_positions=include_positions,
        include_payment_types=include_payment_types,
        include_halls=include_halls,
        include_departments=include_departments,
        include_tables=include_tables,
    )

    base_q = (
        db.query(IikoSaleItem)
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_excl)
    )

    group_expr = dish_group_sql_expr()
    category_expr = dish_category_sql_expr()
    position_expr = waiter_sales_position_expr()
    payment_type_expr = waiter_sales_payment_type_expr()
    group_expr_lower = sa.func.lower(sa.func.coalesce(group_expr, ""))
    category_expr_lower = sa.func.lower(sa.func.coalesce(category_expr, ""))
    position_expr_lower = sa.func.lower(sa.func.coalesce(position_expr, ""))
    payment_type_expr_lower = sa.func.lower(sa.func.coalesce(payment_type_expr, ""))

    portion_coef_kitchen_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_kitchen, 1.0), sa.Float)
    portion_coef_hall_expr = sa.cast(sa.func.coalesce(IikoProductSetting.portion_coef_hall, 1.0), sa.Float)
    kitchen_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_kitchen_expr
    hall_load_expr = sa.func.coalesce(IikoSaleItem.qty, 0) * portion_coef_hall_expr
    base_q = apply_deleted_mode_filter(
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
    base_q = apply_item_report_scope_filters(
        db,
        current_user,
        base_q,
        restaurant_id=restaurant_id,
        source_restaurant_id=source_restaurant_id,
        order_id=order_id,
        include_departments_lower=filters["include_departments_lower"],
        include_tables_lower=filters["include_tables_lower"],
        include_halls_lower=filters["include_halls_lower"],
    )

    base_q = apply_waiter_filter_to_items_query(
        db,
        base_q,
        waiter_mode=resolved_waiter_mode,
        waiter_user_id=waiter_user_id,
        waiter_iiko_id=clean_waiter_iiko_id,
        waiter_iiko_code=clean_waiter_iiko_code,
    )

    if clean_dish_code:
        base_q = base_q.filter(IikoSaleItem.dish_code == clean_dish_code)
    if filters["include_groups_lower"]:
        base_q = base_q.filter(group_expr_lower.in_(filters["include_groups_lower"]))
    if filters["include_categories_lower"]:
        base_q = base_q.filter(category_expr_lower.in_(filters["include_categories_lower"]))
    if filters["include_positions_lower"]:
        base_q = base_q.filter(position_expr_lower.in_(filters["include_positions_lower"]))
    if filters["include_payment_types_lower"]:
        base_q = base_q.filter(payment_type_expr_lower.in_(filters["include_payment_types_lower"]))

    total = base_q.count() if with_meta else None
    totals = None
    if with_meta:
        qty_total, kitchen_load_total, hall_load_total, sum_total, discount_total = (
            base_q.with_entities(
                sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0),
                sa.func.coalesce(sa.func.sum(kitchen_load_expr), 0),
                sa.func.coalesce(sa.func.sum(hall_load_expr), 0),
                sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0),
                sa.func.coalesce(sa.func.sum(IikoSaleItem.discount_sum), 0),
            ).one()
        )
        totals = {
            "qty": float(qty_total or 0),
            "kitchen_load_qty": float(kitchen_load_total or 0),
            "hall_load_qty": float(hall_load_total or 0),
            "sum": float(sum_total or 0),
            "discount_sum": float(discount_total or 0),
        }

    rows = (
        base_q.order_by(IikoSaleItem.open_date.desc(), IikoSaleItem.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    order_meta_by_id: Dict[str, Dict[str, Any]] = {}
    order_ids_for_rows = {row.order_id for row in rows if getattr(row, "order_id", None) is not None}
    if order_ids_for_rows:
        order_rows = (
            db.query(
                IikoSaleOrder.id.label("id"),
                IikoSaleOrder.restaurant_id.label("restaurant_id"),
                IikoSaleOrder.source_restaurant_id.label("source_restaurant_id"),
                IikoSaleOrder.department.label("department"),
                IikoSaleOrder.table_num.label("table_num"),
            )
            .filter(IikoSaleOrder.id.in_(sorted(order_ids_for_rows, key=lambda value: str(value))))
            .all()
        )
        order_meta_by_id = build_order_hall_meta_by_id(db, current_user, order_rows)

    payload_context = collect_item_report_payload_context(rows)
    payment_lookup = payment_method_lookup_by_guid(db, current_user, payload_context["payment_guids"])
    non_cash_lookup = non_cash_lookup_by_id(db, current_user, payload_context["non_cash_ids"])
    user_name_by_id = user_names_by_ids(db, payload_context["user_ids"])
    user_meta_by_iiko_id = user_meta_by_iiko_ids(db, payload_context["iiko_ids"])
    user_meta_by_iiko_code = user_meta_by_iiko_codes(db, payload_context["iiko_codes"])

    product_ids = {str(row.iiko_product_id) for row in rows if row.iiko_product_id}
    product_meta_by_id = build_product_meta_by_id(db, product_ids=product_ids)

    items = serialize_item_report_rows(
        rows,
        restaurant_name_by_id=restaurant_name_by_id,
        order_meta_by_id=order_meta_by_id,
        payment_lookup=payment_lookup,
        non_cash_lookup=non_cash_lookup,
        user_name_by_id=user_name_by_id,
        user_meta_by_iiko_id=user_meta_by_iiko_id,
        user_meta_by_iiko_code=user_meta_by_iiko_code,
        product_meta_by_id=product_meta_by_id,
        payload_context=payload_context,
    )
    if not can_view_money:
        if totals is not None:
            zero_money_metrics(totals)
        for row in items:
            zero_money_metrics(row)
    if with_meta:
        return {"items": items, "total": total, "limit": limit, "offset": offset, "totals": totals}
    return items
