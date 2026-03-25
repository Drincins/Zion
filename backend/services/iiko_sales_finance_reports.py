from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Sequence

import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.bd.iiko_catalog import (
    IikoNonCashEmployeeLimit,
    IikoNonCashPaymentType,
    IikoPaymentMethod,
    IikoProduct,
    IikoProductSetting,
)
from backend.bd.iiko_sales import IikoSaleItem, IikoSaleOrder
from backend.bd.models import User
from backend.services.iiko_api import to_iso_date
from backend.services.iiko_sales_finance_refs import (
    non_cash_limits_query,
    non_cash_lookup_by_id,
    non_cash_types_query,
    payment_methods_query,
    serialize_non_cash_limit,
)
from backend.services.iiko_sales_payloads import (
    build_synthetic_payment_guid,
    normalize_non_cash_type,
    normalize_payment_method,
)
from backend.services.iiko_sales_report_dimensions import dish_category_sql_expr, user_names_by_ids
from backend.services.iiko_sales_report_filters import apply_deleted_mode_filter, clean_optional_text
from backend.services.iiko_sales_scope import ensure_user_access_to_restaurant, list_accessible_restaurants


def build_payment_methods_reference(
    payment_methods_rows: Sequence[Any],
) -> tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    payment_methods_by_guid: Dict[str, Dict[str, Any]] = {}
    payment_guid_by_name: Dict[str, str] = {}
    for guid, name, category in payment_methods_rows:
        clean_guid = clean_optional_text(guid)
        if not clean_guid:
            continue
        clean_name = clean_optional_text(name) or clean_guid
        payment_methods_by_guid[clean_guid] = {
            "guid": clean_guid,
            "name": clean_name,
            "category": clean_optional_text(category),
        }
        payment_guid_by_name.setdefault(clean_name.casefold(), clean_guid)
    return payment_methods_by_guid, payment_guid_by_name


def build_revenue_by_payment_methods_payload(
    rows: Sequence[Any],
    *,
    payment_methods_by_guid: Dict[str, Dict[str, Any]],
    payment_guid_by_name: Dict[str, str],
    dates: List[str],
) -> Dict[str, Any]:
    methods_by_guid: Dict[str, Dict[str, Any]] = {}
    totals_by_date: Dict[str, float] = {date_key: 0.0 for date_key in dates}
    total_amount = 0.0

    for row in rows:
        open_date = getattr(row, "open_date", None)
        if open_date is None:
            continue
        date_key = open_date.isoformat()
        if date_key not in totals_by_date:
            continue

        raw_guid, raw_name = normalize_payment_method(
            getattr(row, "payment_guid", None),
            getattr(row, "payment_name", None),
        )
        if not raw_guid and not raw_name:
            continue

        resolved_guid = raw_guid
        method_meta = payment_methods_by_guid.get(resolved_guid) if resolved_guid else None
        if method_meta is None and raw_name:
            mapped_guid = payment_guid_by_name.get(raw_name.casefold())
            if mapped_guid:
                resolved_guid = mapped_guid
                method_meta = payment_methods_by_guid.get(mapped_guid)

        if method_meta and method_meta.get("category") and method_meta.get("category") != "real_money":
            continue

        if not resolved_guid:
            resolved_guid = build_synthetic_payment_guid(raw_name or "unknown")

        amount = float(getattr(row, "amount", 0) or 0)
        if not amount:
            continue

        method_bucket = methods_by_guid.setdefault(
            resolved_guid,
            {
                "method_guid": resolved_guid,
                "method_name": (method_meta or {}).get("name") or raw_name or resolved_guid,
                "by_date": {date: 0.0 for date in dates},
                "total_amount": 0.0,
            },
        )
        method_bucket["by_date"][date_key] = float(method_bucket["by_date"].get(date_key) or 0) + amount
        method_bucket["total_amount"] = float(method_bucket.get("total_amount") or 0) + amount
        totals_by_date[date_key] = float(totals_by_date.get(date_key) or 0) + amount
        total_amount += amount

    methods = list(methods_by_guid.values())
    methods.sort(key=lambda item: str(item.get("method_name") or "").casefold())
    return {
        "methods": methods,
        "totals_by_date": totals_by_date,
        "total_amount": total_amount,
    }


def list_revenue_by_payment_methods_payload(
    db: Session,
    current_user: User,
    *,
    from_date: str,
    to_date: str,
    restaurant_ids: List[int] | None,
) -> Dict[str, Any]:
    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = {int(row.id) for row in accessible_restaurants}
    restaurant_name_by_id = {int(row.id): row.name for row in accessible_restaurants}
    if not accessible_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "restaurants": [],
            "selected_restaurant_ids": [],
            "dates": [],
            "methods": [],
            "totals_by_date": {},
            "total_amount": 0.0,
        }

    selected_restaurant_ids: List[int]
    if restaurant_ids:
        unique_requested_ids = sorted({int(value) for value in restaurant_ids if value is not None})
        unavailable_ids = [rest_id for rest_id in unique_requested_ids if rest_id not in accessible_ids]
        if unavailable_ids:
            raise HTTPException(status_code=404, detail=f"Restaurant not found or unavailable: {unavailable_ids[0]}")
        selected_restaurant_ids = unique_requested_ids
    else:
        selected_restaurant_ids = sorted(accessible_ids)

    if not selected_restaurant_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "restaurants": [],
            "selected_restaurant_ids": [],
            "dates": [],
            "methods": [],
            "totals_by_date": {},
            "total_amount": 0.0,
        }

    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date()
    if start > end:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    end_excl = end + timedelta(days=1)

    payment_methods_rows = (
        payment_methods_query(db, current_user)
        .with_entities(IikoPaymentMethod.guid, IikoPaymentMethod.name, IikoPaymentMethod.category)
        .all()
    )
    payment_methods_by_guid, payment_guid_by_name = build_payment_methods_reference(payment_methods_rows)

    payment_guid_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["PayTypes.GUID"].astext,
        IikoSaleItem.raw_payload["PaymentType.Id"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext,
    )
    payment_name_expr = sa.func.coalesce(
        IikoSaleItem.raw_payload["PayTypes"].astext,
        IikoSaleItem.raw_payload["PaymentType"].astext,
        IikoSaleItem.raw_payload["NonCashPaymentType"].astext,
    )

    base_q = (
        db.query(IikoSaleItem)
        .join(IikoSaleOrder, IikoSaleOrder.id == IikoSaleItem.order_id)
        .filter(IikoSaleOrder.restaurant_id.in_(selected_restaurant_ids))
        .filter(IikoSaleOrder.open_date >= start)
        .filter(IikoSaleOrder.open_date < end_excl)
    )
    base_q = apply_deleted_mode_filter(
        base_q,
        deleted_mode="without_deleted",
        order_deleted_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["OrderDeleted"].astext,
            IikoSaleOrder.raw_payload["OrderDeleted"].astext,
        ),
        deleted_with_writeoff_expr=sa.func.coalesce(
            IikoSaleItem.raw_payload["DeletedWithWriteoff"].astext,
            IikoSaleOrder.raw_payload["DeletedWithWriteoff"].astext,
        ),
    )
    non_cash_id_expr = sa.func.trim(sa.func.coalesce(IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext, ""))
    non_cash_name_expr = sa.func.trim(sa.func.coalesce(IikoSaleItem.raw_payload["NonCashPaymentType"].astext, ""))
    base_q = base_q.filter(non_cash_id_expr == "").filter(non_cash_name_expr == "")

    gross_sum_expr = sa.func.coalesce(IikoSaleItem.sum, 0) - sa.func.abs(sa.func.coalesce(IikoSaleItem.discount_sum, 0))
    rows = (
        base_q.with_entities(
            IikoSaleOrder.open_date.label("open_date"),
            payment_guid_expr.label("payment_guid"),
            payment_name_expr.label("payment_name"),
            sa.func.coalesce(sa.func.sum(gross_sum_expr), 0).label("amount"),
        )
        .group_by(IikoSaleOrder.open_date, payment_guid_expr, payment_name_expr)
        .all()
    )

    current = start
    dates: List[str] = []
    while current <= end:
        date_key = current.isoformat()
        dates.append(date_key)
        current += timedelta(days=1)

    revenue_payload = build_revenue_by_payment_methods_payload(
        rows,
        payment_methods_by_guid=payment_methods_by_guid,
        payment_guid_by_name=payment_guid_by_name,
        dates=dates,
    )
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "restaurants": [{"id": rest_id, "name": restaurant_name_by_id.get(rest_id)} for rest_id in selected_restaurant_ids],
        "selected_restaurant_ids": selected_restaurant_ids,
        "dates": dates,
        "methods": revenue_payload["methods"],
        "totals_by_date": revenue_payload["totals_by_date"],
        "total_amount": revenue_payload["total_amount"],
    }


def build_non_cash_name_index(known_non_cash_rows: Sequence[Any]) -> Dict[str, str]:
    non_cash_id_by_name: Dict[str, str] = {}
    for known_id, known_name in known_non_cash_rows:
        clean_name = clean_optional_text(known_name)
        clean_id = clean_optional_text(known_id)
        if not clean_name or not clean_id:
            continue
        non_cash_id_by_name.setdefault(clean_name.casefold(), clean_id)
    return non_cash_id_by_name


def accumulate_non_cash_consumption(
    consumption_rows: Sequence[Any],
    *,
    non_cash_id_by_name: Dict[str, str],
    clean_non_cash_type_id: str | None,
) -> Dict[str, Dict[str, Any]]:
    consumption_by_type: Dict[str, Dict[str, Any]] = {}
    for row in consumption_rows:
        type_id, type_name = normalize_non_cash_type(row.non_cash_type_id, row.non_cash_type_name)
        if not type_id:
            continue
        if type_name and str(type_id).startswith("non_cash_name::"):
            mapped_id = non_cash_id_by_name.get(type_name.casefold())
            if mapped_id:
                type_id = mapped_id
        if clean_non_cash_type_id and str(type_id) != clean_non_cash_type_id:
            continue

        key = str(type_id)
        existing = consumption_by_type.setdefault(
            key,
            {
                "name": type_name,
                "consumed_amount": 0.0,
                "consumed_qty": 0.0,
                "orders_count": 0,
                "items_count": 0,
                "restaurants": {},
            },
        )

        amount = float(row.consumed_amount or 0)
        qty = float(row.consumed_qty or 0)
        orders_count = int(row.orders_count or 0)
        items_count = int(row.items_count or 0)

        existing["consumed_amount"] = float(existing.get("consumed_amount") or 0) + amount
        existing["consumed_qty"] = float(existing.get("consumed_qty") or 0) + qty
        existing["orders_count"] = int(existing.get("orders_count") or 0) + orders_count
        existing["items_count"] = int(existing.get("items_count") or 0) + items_count
        if not existing.get("name") and type_name:
            existing["name"] = type_name

        rest_id = int(row.restaurant_id) if row.restaurant_id is not None else None
        if rest_id is not None:
            rest_stats = existing["restaurants"].setdefault(
                rest_id,
                {
                    "consumed_amount": 0.0,
                    "consumed_qty": 0.0,
                    "orders_count": 0,
                    "items_count": 0,
                },
            )
            rest_stats["consumed_amount"] = float(rest_stats.get("consumed_amount") or 0) + amount
            rest_stats["consumed_qty"] = float(rest_stats.get("consumed_qty") or 0) + qty
            rest_stats["orders_count"] = int(rest_stats.get("orders_count") or 0) + orders_count
            rest_stats["items_count"] = int(rest_stats.get("items_count") or 0) + items_count

    return consumption_by_type


def serialize_non_cash_category_stats(categories_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for category_name, stats in categories_map.items():
        rows.append(
            {
                "category_name": category_name or "Uncategorized",
                "consumed_amount": float(stats.get("consumed_amount") or 0),
                "consumed_qty": float(stats.get("consumed_qty") or 0),
                "orders_count": int(stats.get("orders_count") or 0),
                "items_count": int(stats.get("items_count") or 0),
            }
        )
    rows.sort(
        key=lambda item: (
            -float(item.get("consumed_amount") or 0),
            str(item.get("category_name") or ""),
        )
    )
    return rows


def serialize_non_cash_restaurant_stats(
    restaurants_map: Dict[int, Dict[str, Any]],
    *,
    restaurant_name_by_id: Dict[int, str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rest_id in sorted(restaurants_map.keys()):
        rest_stats = restaurants_map.get(rest_id) or {}
        rows.append(
            {
                "restaurant_id": int(rest_id),
                "restaurant_name": restaurant_name_by_id.get(int(rest_id)),
                "consumed_amount": float(rest_stats.get("consumed_amount") or 0),
                "consumed_qty": float(rest_stats.get("consumed_qty") or 0),
                "orders_count": int(rest_stats.get("orders_count") or 0),
                "items_count": int(rest_stats.get("items_count") or 0),
            }
        )
    return rows


def accumulate_non_cash_categories(
    category_rows: Sequence[Any],
    *,
    non_cash_id_by_name: Dict[str, str],
    clean_non_cash_type_id: str | None,
) -> Dict[str, Dict[int, Dict[str, Dict[str, Any]]]]:
    categories_by_type_by_restaurant: Dict[str, Dict[int, Dict[str, Dict[str, Any]]]] = {}
    for row in category_rows:
        type_id, type_name = normalize_non_cash_type(row.non_cash_type_id, row.non_cash_type_name)
        if not type_id:
            continue
        if type_name and str(type_id).startswith("non_cash_name::"):
            mapped_id = non_cash_id_by_name.get(type_name.casefold())
            if mapped_id:
                type_id = mapped_id
        if clean_non_cash_type_id and str(type_id) != clean_non_cash_type_id:
            continue
        rest_id = int(row.restaurant_id) if row.restaurant_id is not None else None
        if rest_id is None:
            continue
        category_name = str(row.category_name or "").strip() or "Uncategorized"
        amount = float(row.consumed_amount or 0)
        qty = float(row.consumed_qty or 0)
        orders_count = int(row.orders_count or 0)
        items_count = int(row.items_count or 0)

        category_bucket = (
            categories_by_type_by_restaurant
            .setdefault(str(type_id), {})
            .setdefault(rest_id, {})
            .setdefault(
                category_name,
                {
                    "consumed_amount": 0.0,
                    "consumed_qty": 0.0,
                    "orders_count": 0,
                    "items_count": 0,
                },
            )
        )
        category_bucket["consumed_amount"] = float(category_bucket.get("consumed_amount") or 0) + amount
        category_bucket["consumed_qty"] = float(category_bucket.get("consumed_qty") or 0) + qty
        category_bucket["orders_count"] = int(category_bucket.get("orders_count") or 0) + orders_count
        category_bucket["items_count"] = int(category_bucket.get("items_count") or 0) + items_count
    return categories_by_type_by_restaurant


def build_non_cash_limits_payload(
    limit_rows: Sequence[Any],
    *,
    consumption_by_type: Dict[str, Dict[str, Any]],
    categories_by_type_by_restaurant: Dict[str, Dict[int, Dict[str, Dict[str, Any]]]],
    non_cash_lookup: Dict[str, Dict[str, Any]],
    user_name_by_id: Dict[int, str],
    limits_count_by_type: Dict[str, int],
    restaurant_name_by_id: Dict[int, str],
    user_workplace_restaurant_by_id: Dict[int, int | None],
    serialize_non_cash_limit,
) -> tuple[List[Dict[str, Any]], set[str]]:
    items: List[Dict[str, Any]] = []
    mapped_non_cash_ids: set[str] = set()
    for row in limit_rows:
        type_id = str(row.non_cash_type_id)
        mapped_non_cash_ids.add(type_id)
        consumed_total = consumption_by_type.get(type_id, {})
        consumed = consumed_total
        categories_by_restaurant = categories_by_type_by_restaurant.get(type_id, {})
        assigned_restaurant_id = None
        if limits_count_by_type.get(type_id, 0) > 1 and row.user_id is not None:
            assigned_restaurant_id = user_workplace_restaurant_by_id.get(int(row.user_id))
            if assigned_restaurant_id is not None:
                consumed = (consumed_total.get("restaurants") or {}).get(int(assigned_restaurant_id), {})
        limit_categories: Dict[str, Dict[str, Any]] = {}
        if assigned_restaurant_id is not None:
            source_categories = categories_by_restaurant.get(int(assigned_restaurant_id), {})
            for category_name, stats in source_categories.items():
                limit_categories[category_name] = {
                    "consumed_amount": float(stats.get("consumed_amount") or 0),
                    "consumed_qty": float(stats.get("consumed_qty") or 0),
                    "orders_count": int(stats.get("orders_count") or 0),
                    "items_count": int(stats.get("items_count") or 0),
                }
        else:
            for source_categories in categories_by_restaurant.values():
                for category_name, stats in source_categories.items():
                    bucket = limit_categories.setdefault(
                        category_name,
                        {
                            "consumed_amount": 0.0,
                            "consumed_qty": 0.0,
                            "orders_count": 0,
                            "items_count": 0,
                        },
                    )
                    bucket["consumed_amount"] = float(bucket.get("consumed_amount") or 0) + float(
                        stats.get("consumed_amount") or 0
                    )
                    bucket["consumed_qty"] = float(bucket.get("consumed_qty") or 0) + float(stats.get("consumed_qty") or 0)
                    bucket["orders_count"] = int(bucket.get("orders_count") or 0) + int(stats.get("orders_count") or 0)
                    bucket["items_count"] = int(bucket.get("items_count") or 0) + int(stats.get("items_count") or 0)
        limit_amount = float(row.limit_amount) if row.limit_amount is not None else None
        consumed_amount = float(consumed.get("consumed_amount") or 0)
        balance_amount = None if limit_amount is None else limit_amount - consumed_amount
        items.append(
            {
                **serialize_non_cash_limit(
                    row,
                    non_cash_name=non_cash_lookup.get(type_id, {}).get("name"),
                    user_name=user_name_by_id.get(int(row.user_id)) if row.user_id is not None else None,
                ),
                "consumed_amount": consumed_amount,
                "consumed_qty": float(consumed.get("consumed_qty") or 0),
                "orders_count": int(consumed.get("orders_count") or 0),
                "items_count": int(consumed.get("items_count") or 0),
                "balance_amount": balance_amount,
                "assigned_restaurant_id": assigned_restaurant_id,
                "assigned_restaurant_name": (
                    restaurant_name_by_id.get(int(assigned_restaurant_id))
                    if assigned_restaurant_id is not None
                    else None
                ),
                "by_restaurant": serialize_non_cash_restaurant_stats(
                    consumed_total.get("restaurants") or {},
                    restaurant_name_by_id=restaurant_name_by_id,
                ),
                "by_category": serialize_non_cash_category_stats(limit_categories),
            }
        )
    return items, mapped_non_cash_ids


def build_non_cash_unmapped_payload(
    consumption_by_type: Dict[str, Dict[str, Any]],
    *,
    mapped_non_cash_ids: set[str],
    non_cash_lookup: Dict[str, Dict[str, Any]],
    restaurant_name_by_id: Dict[int, str],
) -> List[Dict[str, Any]]:
    unmapped: List[Dict[str, Any]] = []
    for type_id, consumed in consumption_by_type.items():
        if type_id in mapped_non_cash_ids:
            continue
        unmapped.append(
            {
                "non_cash_type_id": type_id,
                "non_cash_type_name": non_cash_lookup.get(type_id, {}).get("name") or consumed.get("name") or type_id,
                "consumed_amount": float(consumed.get("consumed_amount") or 0),
                "consumed_qty": float(consumed.get("consumed_qty") or 0),
                "orders_count": int(consumed.get("orders_count") or 0),
                "items_count": int(consumed.get("items_count") or 0),
                "by_restaurant": serialize_non_cash_restaurant_stats(
                    consumed.get("restaurants") or {},
                    restaurant_name_by_id=restaurant_name_by_id,
                ),
            }
        )
    return unmapped


def build_non_cash_types_payload(
    consumption_by_type: Dict[str, Dict[str, Any]],
    *,
    mapped_non_cash_ids: set[str],
    non_cash_lookup: Dict[str, Dict[str, Any]],
    limits_count_by_type: Dict[str, int],
    restaurant_name_by_id: Dict[int, str],
) -> List[Dict[str, Any]]:
    types: List[Dict[str, Any]] = []
    type_keys = sorted(set(consumption_by_type.keys()) | set(mapped_non_cash_ids))
    for type_id in type_keys:
        consumed = consumption_by_type.get(type_id, {})
        lookup = non_cash_lookup.get(type_id, {})
        types.append(
            {
                "non_cash_type_id": type_id,
                "non_cash_type_name": lookup.get("name") or consumed.get("name") or type_id,
                "category": lookup.get("category"),
                "is_active": lookup.get("is_active"),
                "employees_count": int(limits_count_by_type.get(type_id) or 0),
                "consumed_amount": float(consumed.get("consumed_amount") or 0),
                "consumed_qty": float(consumed.get("consumed_qty") or 0),
                "orders_count": int(consumed.get("orders_count") or 0),
                "items_count": int(consumed.get("items_count") or 0),
                "by_restaurant": serialize_non_cash_restaurant_stats(
                    consumed.get("restaurants") or {},
                    restaurant_name_by_id=restaurant_name_by_id,
                ),
            }
        )
    return types


def build_non_cash_totals_payload(
    consumption_by_type: Dict[str, Dict[str, Any]],
    *,
    mapped_non_cash_ids: set[str],
    restaurant_name_by_id: Dict[int, str],
) -> Dict[str, Any]:
    totals_by_restaurant_map: Dict[int, Dict[str, Any]] = {}
    for consumed in consumption_by_type.values():
        for rest_id, rest_stats in (consumed.get("restaurants") or {}).items():
            bucket = totals_by_restaurant_map.setdefault(
                int(rest_id),
                {
                    "consumed_amount": 0.0,
                    "consumed_qty": 0.0,
                    "orders_count": 0,
                    "items_count": 0,
                },
            )
            bucket["consumed_amount"] = float(bucket.get("consumed_amount") or 0) + float(
                rest_stats.get("consumed_amount") or 0
            )
            bucket["consumed_qty"] = float(bucket.get("consumed_qty") or 0) + float(rest_stats.get("consumed_qty") or 0)
            bucket["orders_count"] = int(bucket.get("orders_count") or 0) + int(rest_stats.get("orders_count") or 0)
            bucket["items_count"] = int(bucket.get("items_count") or 0) + int(rest_stats.get("items_count") or 0)

    mapped_consumed = round(
        sum(float(consumption_by_type.get(type_id, {}).get("consumed_amount") or 0) for type_id in mapped_non_cash_ids),
        2,
    )
    unmapped_consumed = round(
        sum(
            float(consumed.get("consumed_amount") or 0)
            for type_id, consumed in consumption_by_type.items()
            if type_id not in mapped_non_cash_ids
        ),
        2,
    )
    return {
        "totals_by_restaurant": serialize_non_cash_restaurant_stats(
            totals_by_restaurant_map,
            restaurant_name_by_id=restaurant_name_by_id,
        ),
        "totals": {
            "mapped_consumed": mapped_consumed,
            "unmapped_consumed": unmapped_consumed,
            "total_consumed": round(mapped_consumed + unmapped_consumed, 2),
        },
    }


def list_non_cash_consumption_payload(
    db: Session,
    current_user: User,
    *,
    from_date: str,
    to_date: str,
    restaurant_id: int | None,
    non_cash_type_id: str | None,
    user_id: int | None,
    include_inactive_limits: bool,
) -> Dict[str, Any]:
    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)

    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = [restaurant.id for restaurant in accessible_restaurants]
    restaurant_name_by_id = {restaurant.id: restaurant.name for restaurant in accessible_restaurants}
    if not accessible_ids:
        return {
            "from_date": to_iso_date(from_date),
            "to_date": to_iso_date(to_date),
            "items": [],
            "unmapped": [],
            "types": [],
            "totals_by_restaurant": [],
            "totals": {"mapped_consumed": 0.0, "unmapped_consumed": 0.0, "total_consumed": 0.0},
        }

    clean_non_cash_type_id = (non_cash_type_id or "").strip() or None
    start = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    end_excl = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)

    known_non_cash_rows = (
        non_cash_types_query(db, current_user)
        .with_entities(IikoNonCashPaymentType.id, IikoNonCashPaymentType.name)
        .all()
    )
    non_cash_id_by_name = build_non_cash_name_index(known_non_cash_rows)

    non_cash_id_expr = IikoSaleItem.raw_payload["NonCashPaymentType.Id"].astext
    non_cash_name_expr = IikoSaleItem.raw_payload["NonCashPaymentType"].astext
    base_items_q = (
        db.query(IikoSaleItem)
        .filter(IikoSaleItem.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleItem.open_date >= start)
        .filter(IikoSaleItem.open_date < end_excl)
        .filter(sa.or_(non_cash_id_expr.isnot(None), non_cash_name_expr.isnot(None)))
    )
    if restaurant_id is not None:
        base_items_q = base_items_q.filter(IikoSaleItem.restaurant_id == restaurant_id)

    consumption_rows = (
        base_items_q.with_entities(
            non_cash_id_expr.label("non_cash_type_id"),
            non_cash_name_expr.label("non_cash_type_name"),
            IikoSaleItem.restaurant_id.label("restaurant_id"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("consumed_amount"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("consumed_qty"),
            sa.func.count(sa.distinct(IikoSaleItem.order_id)).label("orders_count"),
            sa.func.count(IikoSaleItem.id).label("items_count"),
        )
        .group_by(non_cash_id_expr, non_cash_name_expr, IikoSaleItem.restaurant_id)
        .all()
    )
    consumption_by_type = accumulate_non_cash_consumption(
        consumption_rows,
        non_cash_id_by_name=non_cash_id_by_name,
        clean_non_cash_type_id=clean_non_cash_type_id,
    )

    category_expr = dish_category_sql_expr(with_fallback=True)
    category_rows = (
        base_items_q
        .outerjoin(IikoProduct, IikoProduct.id == IikoSaleItem.iiko_product_id)
        .outerjoin(IikoProductSetting, IikoProductSetting.product_id == IikoProduct.id)
        .with_entities(
            non_cash_id_expr.label("non_cash_type_id"),
            non_cash_name_expr.label("non_cash_type_name"),
            IikoSaleItem.restaurant_id.label("restaurant_id"),
            category_expr.label("category_name"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.sum), 0).label("consumed_amount"),
            sa.func.coalesce(sa.func.sum(IikoSaleItem.qty), 0).label("consumed_qty"),
            sa.func.count(sa.distinct(IikoSaleItem.order_id)).label("orders_count"),
            sa.func.count(IikoSaleItem.id).label("items_count"),
        )
        .group_by(non_cash_id_expr, non_cash_name_expr, IikoSaleItem.restaurant_id, category_expr)
        .all()
    )
    categories_by_type_by_restaurant = accumulate_non_cash_categories(
        category_rows,
        non_cash_id_by_name=non_cash_id_by_name,
        clean_non_cash_type_id=clean_non_cash_type_id,
    )

    limits_q = non_cash_limits_query(db, current_user)
    if not include_inactive_limits:
        limits_q = limits_q.filter(IikoNonCashEmployeeLimit.is_active.is_(True))
    if clean_non_cash_type_id:
        limits_q = limits_q.filter(IikoNonCashEmployeeLimit.non_cash_type_id == clean_non_cash_type_id)
    if user_id is not None:
        limits_q = limits_q.filter(IikoNonCashEmployeeLimit.user_id == user_id)

    limit_rows = limits_q.order_by(
        IikoNonCashEmployeeLimit.non_cash_type_id.asc(),
        IikoNonCashEmployeeLimit.user_id.asc(),
        IikoNonCashEmployeeLimit.period_type.asc(),
    ).all()

    non_cash_ids = {
        *(str(row.non_cash_type_id) for row in limit_rows if row.non_cash_type_id),
        *consumption_by_type.keys(),
    }
    user_ids = {int(row.user_id) for row in limit_rows if row.user_id is not None}
    non_cash_lookup = non_cash_lookup_by_id(db, current_user, set(non_cash_ids))
    user_name_by_id = user_names_by_ids(db, user_ids)

    user_workplace_restaurant_by_id: Dict[int, int | None] = {}
    if user_ids:
        workplace_rows = (
            db.query(User.id, User.workplace_restaurant_id)
            .filter(User.id.in_(sorted(user_ids)))
            .all()
        )
        user_workplace_restaurant_by_id = {
            int(found_user_id): int(found_restaurant_id) if found_restaurant_id is not None else None
            for found_user_id, found_restaurant_id in workplace_rows
        }

    limits_count_by_type: Dict[str, int] = {}
    for row in limit_rows:
        key = str(row.non_cash_type_id)
        limits_count_by_type[key] = int(limits_count_by_type.get(key) or 0) + 1

    items, mapped_non_cash_ids = build_non_cash_limits_payload(
        limit_rows,
        consumption_by_type=consumption_by_type,
        categories_by_type_by_restaurant=categories_by_type_by_restaurant,
        non_cash_lookup=non_cash_lookup,
        user_name_by_id=user_name_by_id,
        limits_count_by_type=limits_count_by_type,
        restaurant_name_by_id=restaurant_name_by_id,
        user_workplace_restaurant_by_id=user_workplace_restaurant_by_id,
        serialize_non_cash_limit=serialize_non_cash_limit,
    )
    unmapped = build_non_cash_unmapped_payload(
        consumption_by_type,
        mapped_non_cash_ids=mapped_non_cash_ids,
        non_cash_lookup=non_cash_lookup,
        restaurant_name_by_id=restaurant_name_by_id,
    )
    types = build_non_cash_types_payload(
        consumption_by_type,
        mapped_non_cash_ids=mapped_non_cash_ids,
        non_cash_lookup=non_cash_lookup,
        limits_count_by_type=limits_count_by_type,
        restaurant_name_by_id=restaurant_name_by_id,
    )
    totals_payload = build_non_cash_totals_payload(
        consumption_by_type,
        mapped_non_cash_ids=mapped_non_cash_ids,
        restaurant_name_by_id=restaurant_name_by_id,
    )

    return {
        "from_date": start.isoformat(),
        "to_date": (end_excl - timedelta(days=1)).isoformat(),
        "restaurant_id": restaurant_id,
        "items": items,
        "unmapped": unmapped,
        "types": types,
        "totals_by_restaurant": totals_payload["totals_by_restaurant"],
        "totals": totals_payload["totals"],
    }
