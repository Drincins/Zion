from __future__ import annotations

from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.iiko_sales import (
    IikoSaleOrder,
    IikoSalesHall,
    IikoSalesHallTable,
    IikoSalesHallZone,
    IikoSalesLocationMapping,
)
from backend.bd.models import User
from backend.services.iiko_sales_scope import restrict_company_scoped_query


def normalize_location_token(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def sales_location_mappings_query(db: Session, current_user: User):
    return restrict_company_scoped_query(
        db.query(IikoSalesLocationMapping),
        IikoSalesLocationMapping.company_id,
        db,
        current_user,
    )


def serialize_sales_location_mapping(
    row: IikoSalesLocationMapping,
    *,
    source_restaurant_name: Optional[str] = None,
    target_restaurant_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "source_restaurant_id": row.source_restaurant_id,
        "source_restaurant_name": source_restaurant_name,
        "target_restaurant_id": row.target_restaurant_id,
        "target_restaurant_name": target_restaurant_name,
        "department": row.department,
        "table_num": row.table_num,
        "department_norm": row.department_norm,
        "table_num_norm": row.table_num_norm,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def sales_halls_query(db: Session, current_user: User):
    return restrict_company_scoped_query(
        db.query(IikoSalesHall),
        IikoSalesHall.company_id,
        db,
        current_user,
    )


def sales_hall_zones_query(db: Session, current_user: User):
    return restrict_company_scoped_query(
        db.query(IikoSalesHallZone),
        IikoSalesHallZone.company_id,
        db,
        current_user,
    )


def serialize_sales_hall(row: IikoSalesHall) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "name": row.name,
        "name_norm": row.name_norm,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_sales_hall_zone(
    row: IikoSalesHallZone,
    *,
    hall_name: Optional[str] = None,
    restaurant_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "hall_id": str(row.hall_id) if row.hall_id is not None else None,
        "hall_name": hall_name,
        "restaurant_id": row.restaurant_id,
        "restaurant_name": restaurant_name,
        "name": row.name,
        "name_norm": row.name_norm,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def sales_hall_tables_query(db: Session, current_user: User):
    return restrict_company_scoped_query(
        db.query(IikoSalesHallTable),
        IikoSalesHallTable.company_id,
        db,
        current_user,
    )


def serialize_sales_hall_table(
    row: IikoSalesHallTable,
    *,
    restaurant_name: Optional[str] = None,
    source_restaurant_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "company_id": row.company_id,
        "restaurant_id": row.restaurant_id,
        "restaurant_name": restaurant_name,
        "hall_id": str(row.hall_id) if getattr(row, "hall_id", None) is not None else None,
        "zone_id": str(row.zone_id) if getattr(row, "zone_id", None) is not None else None,
        "source_restaurant_id": row.source_restaurant_id,
        "source_restaurant_name": source_restaurant_name,
        "department": row.department,
        "table_num": row.table_num,
        "department_norm": row.department_norm,
        "table_num_norm": row.table_num_norm,
        "hall_name": row.hall_name,
        "hall_name_norm": row.hall_name_norm,
        "zone_name": getattr(row, "zone_name", None),
        "zone_name_norm": getattr(row, "zone_name_norm", None),
        "table_name": row.table_name,
        "capacity": row.capacity,
        "comment": row.comment,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def build_sales_hall_table_resolver(rows: List[IikoSalesHallTable]):
    sorted_rows = sorted(
        rows or [],
        key=lambda row: (
            row.company_id is None,
            row.source_restaurant_id is None,
        ),
    )

    by_exact: Dict[tuple[int, Optional[int], str, str], IikoSalesHallTable] = {}
    by_department: Dict[tuple[int, Optional[int], str], IikoSalesHallTable] = {}

    for row in sorted_rows:
        rest_id = int(row.restaurant_id) if row.restaurant_id is not None else None
        if rest_id is None:
            continue
        dep_norm = (row.department_norm or normalize_location_token(row.department)).strip()
        table_norm = (row.table_num_norm or normalize_location_token(row.table_num)).strip()
        if not dep_norm:
            continue
        source_key = int(row.source_restaurant_id) if row.source_restaurant_id is not None else None
        if table_norm:
            by_exact.setdefault((rest_id, source_key, dep_norm, table_norm), row)
        else:
            by_department.setdefault((rest_id, source_key, dep_norm), row)

    def _resolve(
        *,
        restaurant_id: Optional[int],
        source_restaurant_id: Optional[int],
        department: Any,
        table_num: Any,
    ) -> Dict[str, Any]:
        rest_id = int(restaurant_id) if restaurant_id is not None else None
        dep_norm = normalize_location_token(department)
        table_norm = normalize_location_token(table_num)
        source_key = (
            int(source_restaurant_id)
            if source_restaurant_id is not None
            else (rest_id if rest_id is not None else None)
        )

        if rest_id is not None and dep_norm:
            if table_norm:
                for maybe_source in (source_key, None):
                    row = by_exact.get((rest_id, maybe_source, dep_norm, table_norm))
                    if row is not None:
                        hall_name = (row.hall_name or "").strip() or (department or "Без зала")
                        return {
                            "hall_name": hall_name,
                            "hall_name_norm": normalize_location_token(hall_name),
                            "zone_name": (row.zone_name or "").strip() or None,
                            "zone_name_norm": normalize_location_token(row.zone_name),
                            "table_name": (row.table_name or "").strip() or (table_num or None),
                            "capacity": int(row.capacity) if row.capacity is not None else None,
                        }
            for maybe_source in (source_key, None):
                row = by_department.get((rest_id, maybe_source, dep_norm))
                if row is not None:
                    hall_name = (row.hall_name or "").strip() or (department or "Без зала")
                    return {
                        "hall_name": hall_name,
                        "hall_name_norm": normalize_location_token(hall_name),
                        "zone_name": (row.zone_name or "").strip() or None,
                        "zone_name_norm": normalize_location_token(row.zone_name),
                        "table_name": (row.table_name or "").strip() or (table_num or None),
                        "capacity": int(row.capacity) if row.capacity is not None else None,
                    }

        fallback_hall = str(department).strip() if department is not None and str(department).strip() else "Без зала"
        fallback_table = str(table_num).strip() if table_num is not None and str(table_num).strip() else None
        return {
            "hall_name": fallback_hall,
            "hall_name_norm": normalize_location_token(fallback_hall),
            "zone_name": None,
            "zone_name_norm": "",
            "table_name": fallback_table,
            "capacity": None,
        }

    return _resolve


def collect_halls_from_order_rows(
    db: Session,
    current_user: User,
    order_rows: List[Any],
) -> List[str]:
    if not order_rows:
        return []

    restaurant_ids = {
        int(row.restaurant_id)
        for row in order_rows
        if getattr(row, "restaurant_id", None) is not None
    }
    hall_rows_q = sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.is_active.is_(True))
    if restaurant_ids:
        hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.restaurant_id.in_(sorted(restaurant_ids)))
    resolve_hall = build_sales_hall_table_resolver(hall_rows_q.all())

    by_norm: Dict[str, str] = {}
    for row in order_rows:
        resolved = resolve_hall(
            restaurant_id=getattr(row, "restaurant_id", None),
            source_restaurant_id=getattr(row, "source_restaurant_id", None),
            department=getattr(row, "department", None),
            table_num=getattr(row, "table_num", None),
        )
        hall_name = str(resolved.get("hall_name") or "").strip()
        hall_norm = str(resolved.get("hall_name_norm") or "").strip()
        if not hall_name or not hall_norm or hall_norm in by_norm:
            continue
        by_norm[hall_norm] = hall_name

    return sorted(by_norm.values(), key=lambda value: str(value).casefold())


def apply_hall_filter_to_base_query(
    db: Session,
    current_user: User,
    base_q,
    include_halls_lower: List[str],
):
    include_set = {str(value or "").strip().casefold() for value in include_halls_lower if str(value or "").strip()}
    if not include_set:
        return base_q

    order_rows = (
        base_q.with_entities(
            IikoSaleOrder.id.label("order_id"),
            IikoSaleOrder.restaurant_id.label("restaurant_id"),
            IikoSaleOrder.source_restaurant_id.label("source_restaurant_id"),
            IikoSaleOrder.department.label("department"),
            IikoSaleOrder.table_num.label("table_num"),
        )
        .distinct()
        .all()
    )
    if not order_rows:
        return base_q.filter(sa.literal(False))

    restaurant_ids = {
        int(row.restaurant_id)
        for row in order_rows
        if row.restaurant_id is not None
    }
    hall_rows_q = sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.is_active.is_(True))
    if restaurant_ids:
        hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.restaurant_id.in_(sorted(restaurant_ids)))
    resolve_hall = build_sales_hall_table_resolver(hall_rows_q.all())

    selected_order_ids = []
    for row in order_rows:
        resolved = resolve_hall(
            restaurant_id=row.restaurant_id,
            source_restaurant_id=row.source_restaurant_id,
            department=row.department,
            table_num=row.table_num,
        )
        if str(resolved.get("hall_name_norm") or "").strip().casefold() in include_set:
            selected_order_ids.append(row.order_id)

    if not selected_order_ids:
        return base_q.filter(sa.literal(False))

    return base_q.filter(IikoSaleOrder.id.in_(selected_order_ids))
