from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.iiko_catalog import IikoProduct, IikoProductSetting
from backend.bd.iiko_sales import IikoSaleItem, IikoSaleOrder
from backend.bd.models import User
from backend.services.iiko_api import to_iso_date
from backend.services.iiko_sales_finance_refs import non_cash_lookup_by_id, payment_method_lookup_by_guid
from backend.services.iiko_sales_order_item_support import (
    apply_item_report_scope_filters,
    apply_order_report_scope_filters,
    build_item_report_aux_lookups,
    build_order_hall_meta_by_id,
    build_orders_item_scope_subquery,
    collect_item_report_payload_context,
    collect_order_report_payload_context,
    prepare_order_item_filter_values,
    serialize_item_report_rows,
    serialize_order_report_rows,
)
from backend.services.iiko_sales_report_dimensions import (
    clean_optional_text,
    dish_category_sql_expr,
    dish_group_sql_expr,
    user_names_by_ids,
)
from backend.services.iiko_sales_report_filters import (
    apply_deleted_mode_filter,
    apply_waiter_filter_to_items_query,
)
from backend.services.iiko_sales_scope import ensure_user_access_to_restaurant, list_accessible_restaurants
from backend.services.iiko_sales_waiter_reports import (
    waiter_sales_payment_type_expr,
    waiter_sales_position_expr,
    zero_money_metrics,
)
from backend.services.iiko_sales_waiter_turnover import (
    normalize_deleted_mode,
    normalize_waiter_mode,
)


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
    aux_lookups = build_item_report_aux_lookups(
        db,
        current_user,
        payload_context=payload_context,
        rows=rows,
    )

    items = serialize_item_report_rows(
        rows,
        restaurant_name_by_id=restaurant_name_by_id,
        order_meta_by_id=order_meta_by_id,
        payment_lookup=aux_lookups["payment_lookup"],
        non_cash_lookup=aux_lookups["non_cash_lookup"],
        user_name_by_id=aux_lookups["user_name_by_id"],
        user_meta_by_iiko_id=aux_lookups["user_meta_by_iiko_id"],
        user_meta_by_iiko_code=aux_lookups["user_meta_by_iiko_code"],
        product_meta_by_id=aux_lookups["product_meta_by_id"],
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
