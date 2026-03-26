from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.iiko_sales import (
    IikoSaleOrder,
    IikoSalesHall,
    IikoSalesHallTable,
    IikoSalesHallZone,
    IikoSalesLocationMapping,
)
from backend.bd.models import Restaurant, User
from backend.services.iiko_api import to_iso_date
from backend.services.iiko_sales_scope import (
    ensure_user_access_to_restaurant,
    list_accessible_restaurants,
    resolve_scoped_company_id,
    restrict_company_scoped_query,
)
from backend.utils import now_local

HALL_TABLE_DEFAULT_LOOKBACK_DAYS = 365


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


def list_sales_location_mappings_payload(
    db: Session,
    current_user: User,
    *,
    include_inactive: bool = True,
    source_restaurant_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    if source_restaurant_id is not None:
        ensure_user_access_to_restaurant(
            db,
            current_user,
            int(source_restaurant_id),
            require_credentials=False,
        )

    q = sales_location_mappings_query(db, current_user)
    if not include_inactive:
        q = q.filter(IikoSalesLocationMapping.is_active.is_(True))
    if source_restaurant_id is not None:
        q = q.filter(IikoSalesLocationMapping.source_restaurant_id == int(source_restaurant_id))

    rows = q.order_by(
        IikoSalesLocationMapping.source_restaurant_id.asc().nullsfirst(),
        IikoSalesLocationMapping.department_norm.asc(),
        IikoSalesLocationMapping.table_num_norm.asc(),
    ).all()

    restaurant_ids = {
        int(row.source_restaurant_id)
        for row in rows
        if row.source_restaurant_id is not None
    }.union(
        {
            int(row.target_restaurant_id)
            for row in rows
            if row.target_restaurant_id is not None
        }
    )
    restaurant_name_by_id = restaurant_name_map(db, restaurant_ids)

    return [
        serialize_sales_location_mapping(
            row,
            source_restaurant_name=restaurant_name_by_id.get(int(row.source_restaurant_id))
            if row.source_restaurant_id is not None
            else None,
            target_restaurant_name=restaurant_name_by_id.get(int(row.target_restaurant_id))
            if row.target_restaurant_id is not None
            else None,
        )
        for row in rows
    ]


def delete_sales_location_mapping(
    db: Session,
    current_user: User,
    *,
    mapping_id: str,
) -> str:
    row = sales_location_mappings_query(db, current_user).filter(IikoSalesLocationMapping.id == mapping_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sales location mapping not found")
    db.delete(row)
    db.commit()
    return str(row.id)


def upsert_sales_location_mapping(
    db: Session,
    current_user: User,
    payload: Any,
) -> tuple[IikoSalesLocationMapping, Optional[str], Optional[str]]:
    source_restaurant: Optional[Restaurant] = None
    if getattr(payload, "source_restaurant_id", None) is not None:
        source_restaurant = ensure_user_access_to_restaurant(
            db,
            current_user,
            int(getattr(payload, "source_restaurant_id")),
            require_credentials=False,
        )

    target_restaurant = ensure_user_access_to_restaurant(
        db,
        current_user,
        int(getattr(payload, "target_restaurant_id")),
        require_credentials=False,
    )

    company_candidates = [target_restaurant.company_id]
    if source_restaurant is not None:
        company_candidates.append(source_restaurant.company_id)
    company_id = resolve_scoped_company_id(
        db,
        current_user,
        next((int(candidate) for candidate in company_candidates if candidate is not None), None),
    )
    if source_restaurant is not None and source_restaurant.company_id != company_id:
        raise HTTPException(status_code=400, detail="Source restaurant is outside of your company scope")
    if target_restaurant.company_id != company_id:
        raise HTTPException(status_code=400, detail="Target restaurant is outside of your company scope")

    department = str(getattr(payload, "department", "") or "").strip() or None
    table_num = str(getattr(payload, "table_num", "") or "").strip() or None
    department_norm = normalize_location_token(department)
    table_num_norm = normalize_location_token(table_num)
    if not department_norm:
        raise HTTPException(status_code=400, detail="department is required")

    source_restaurant_id_value = (
        int(getattr(payload, "source_restaurant_id"))
        if getattr(payload, "source_restaurant_id", None) is not None
        else None
    )

    row = (
        sales_location_mappings_query(db, current_user)
        .filter(IikoSalesLocationMapping.source_restaurant_id == source_restaurant_id_value)
        .filter(IikoSalesLocationMapping.department_norm == department_norm)
        .filter(IikoSalesLocationMapping.table_num_norm == table_num_norm)
        .first()
    )

    if row is None:
        row = IikoSalesLocationMapping(
            company_id=company_id,
            source_restaurant_id=source_restaurant_id_value,
            department=department,
            table_num=table_num,
            department_norm=department_norm,
            table_num_norm=table_num_norm,
            target_restaurant_id=int(getattr(payload, "target_restaurant_id")),
            comment=(str(getattr(payload, "comment", "") or "").strip() or None),
            is_active=bool(getattr(payload, "is_active", True)),
        )
    else:
        row.company_id = company_id
        row.source_restaurant_id = source_restaurant_id_value
        row.department = department
        row.table_num = table_num
        row.department_norm = department_norm
        row.table_num_norm = table_num_norm
        row.target_restaurant_id = int(getattr(payload, "target_restaurant_id"))
        row.comment = str(getattr(payload, "comment", "") or "").strip() or None
        row.is_active = bool(getattr(payload, "is_active", True))

    db.add(row)
    db.commit()
    db.refresh(row)
    return row, source_restaurant.name if source_restaurant is not None else None, target_restaurant.name


def update_sales_location_mapping(
    db: Session,
    current_user: User,
    *,
    mapping_id: str,
    payload: Any,
) -> tuple[IikoSalesLocationMapping, Optional[str], Optional[str]]:
    row = sales_location_mappings_query(db, current_user).filter(IikoSalesLocationMapping.id == mapping_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sales location mapping not found")

    source_restaurant: Optional[Restaurant] = None
    if getattr(payload, "source_restaurant_id", None) is not None:
        source_restaurant = ensure_user_access_to_restaurant(
            db,
            current_user,
            int(getattr(payload, "source_restaurant_id")),
            require_credentials=False,
        )
        row.source_restaurant_id = int(getattr(payload, "source_restaurant_id"))

    target_restaurant: Optional[Restaurant] = None
    if getattr(payload, "target_restaurant_id", None) is not None:
        target_restaurant = ensure_user_access_to_restaurant(
            db,
            current_user,
            int(getattr(payload, "target_restaurant_id")),
            require_credentials=False,
        )
        row.target_restaurant_id = int(getattr(payload, "target_restaurant_id"))

    if getattr(payload, "department", None) is not None:
        row.department = str(getattr(payload, "department", "") or "").strip() or None
        row.department_norm = normalize_location_token(row.department)
    if getattr(payload, "table_num", None) is not None:
        row.table_num = str(getattr(payload, "table_num", "") or "").strip() or None
        row.table_num_norm = normalize_location_token(row.table_num)
    if not row.department_norm:
        raise HTTPException(status_code=400, detail="department is required")

    if getattr(payload, "comment", None) is not None:
        row.comment = str(getattr(payload, "comment", "") or "").strip() or None
    if getattr(payload, "is_active", None) is not None:
        row.is_active = bool(getattr(payload, "is_active"))

    db.add(row)
    db.commit()
    db.refresh(row)

    if source_restaurant is None and row.source_restaurant_id is not None:
        source_restaurant = (
            db.query(Restaurant)
            .filter(Restaurant.id == int(row.source_restaurant_id))
            .first()
        )
    if target_restaurant is None:
        target_restaurant = (
            db.query(Restaurant)
            .filter(Restaurant.id == int(row.target_restaurant_id))
            .first()
        )
    return (
        row,
        source_restaurant.name if source_restaurant is not None else None,
        target_restaurant.name if target_restaurant is not None else None,
    )


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


def list_sales_halls_payload(
    db: Session,
    current_user: User,
    *,
    include_inactive: bool = True,
) -> List[Dict[str, Any]]:
    query = sales_halls_query(db, current_user)
    if not include_inactive:
        query = query.filter(IikoSalesHall.is_active.is_(True))
    rows = query.order_by(
        IikoSalesHall.is_active.desc(),
        IikoSalesHall.name_norm.asc(),
        IikoSalesHall.created_at.asc(),
    ).all()
    return [serialize_sales_hall(row) for row in rows]


def create_sales_hall(db: Session, current_user: User, payload: Any) -> IikoSalesHall:
    name = str(getattr(payload, "name", "") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    name_norm = normalize_location_token(name)

    company_id = resolve_scoped_company_id(db, current_user)

    dup_q = db.query(IikoSalesHall).filter(IikoSalesHall.name_norm == name_norm)
    dup_q = dup_q.filter(IikoSalesHall.company_id == company_id)
    if dup_q.first() is not None:
        raise HTTPException(status_code=400, detail="Hall with this name already exists")

    row = IikoSalesHall(
        company_id=company_id,
        name=name,
        name_norm=name_norm,
        comment=(str(getattr(payload, "comment", "") or "").strip() or None),
        is_active=bool(getattr(payload, "is_active", True)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_sales_hall(
    db: Session,
    current_user: User,
    *,
    hall_id: UUID,
    payload: Any,
) -> IikoSalesHall:
    row = sales_halls_query(db, current_user).filter(IikoSalesHall.id == hall_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Hall not found")

    if getattr(payload, "name", None) is not None:
        name = str(getattr(payload, "name", "") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        name_norm = normalize_location_token(name)
        dup_q = (
            db.query(IikoSalesHall)
            .filter(IikoSalesHall.id != row.id)
            .filter(IikoSalesHall.name_norm == name_norm)
        )
        if row.company_id is None:
            dup_q = dup_q.filter(IikoSalesHall.company_id.is_(None))
        else:
            dup_q = dup_q.filter(IikoSalesHall.company_id == row.company_id)
        if dup_q.first() is not None:
            raise HTTPException(status_code=400, detail="Hall with this name already exists")
        row.name = name
        row.name_norm = name_norm
    if getattr(payload, "comment", None) is not None:
        row.comment = str(getattr(payload, "comment", "") or "").strip() or None
    if getattr(payload, "is_active", None) is not None:
        row.is_active = bool(getattr(payload, "is_active"))

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_sales_hall(
    db: Session,
    current_user: User,
    *,
    hall_id: UUID,
) -> str:
    row = sales_halls_query(db, current_user).filter(IikoSalesHall.id == hall_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Hall not found")
    db.delete(row)
    db.commit()
    return str(row.id)


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


def list_sales_hall_zones_payload(
    db: Session,
    current_user: User,
    *,
    include_inactive: bool = True,
    hall_id: Optional[UUID] = None,
    restaurant_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
    if hall_id is not None:
        hall_exists = sales_halls_query(db, current_user).filter(IikoSalesHall.id == hall_id).first()
        if hall_exists is None:
            raise HTTPException(status_code=404, detail="Hall not found")

    query = sales_hall_zones_query(db, current_user)
    if not include_inactive:
        query = query.filter(IikoSalesHallZone.is_active.is_(True))
    if hall_id is not None:
        query = query.filter(IikoSalesHallZone.hall_id == hall_id)
    if restaurant_id is not None:
        query = query.filter(IikoSalesHallZone.restaurant_id == int(restaurant_id))

    rows = query.order_by(
        IikoSalesHallZone.restaurant_id.asc(),
        IikoSalesHallZone.name_norm.asc(),
        IikoSalesHallZone.created_at.asc(),
    ).all()
    if not rows:
        return []

    hall_ids = {row.hall_id for row in rows if row.hall_id is not None}
    hall_name_by_id = hall_name_map(db, hall_ids)
    restaurant_ids = {int(row.restaurant_id) for row in rows if row.restaurant_id is not None}
    restaurant_name_by_id = restaurant_name_map(db, restaurant_ids)
    return serialize_sales_hall_zone_rows(
        rows,
        hall_name_by_id=hall_name_by_id,
        restaurant_name_by_id=restaurant_name_by_id,
    )


def create_sales_hall_zone(
    db: Session,
    current_user: User,
    payload: Any,
) -> tuple[IikoSalesHallZone, Optional[str], Optional[str]]:
    hall = sales_halls_query(db, current_user).filter(IikoSalesHall.id == getattr(payload, "hall_id", None)).first()
    if hall is None:
        raise HTTPException(status_code=404, detail="Hall not found")

    restaurant = ensure_user_access_to_restaurant(
        db,
        current_user,
        int(getattr(payload, "restaurant_id")),
        require_credentials=False,
    )

    name = str(getattr(payload, "name", "") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    name_norm = normalize_location_token(name)

    requested_company_id = next(
        (int(candidate) for candidate in (restaurant.company_id, hall.company_id) if candidate is not None),
        None,
    )
    company_id = resolve_scoped_company_id(
        db,
        current_user,
        requested_company_id,
    )
    if restaurant.company_id != company_id:
        raise HTTPException(status_code=400, detail="Restaurant is outside of your company scope")
    if hall.company_id != company_id:
        raise HTTPException(status_code=400, detail="Hall is outside of your company scope")

    dup_q = (
        db.query(IikoSalesHallZone)
        .filter(IikoSalesHallZone.hall_id == hall.id)
        .filter(IikoSalesHallZone.restaurant_id == int(restaurant.id))
        .filter(IikoSalesHallZone.name_norm == name_norm)
        .filter(IikoSalesHallZone.company_id == company_id)
    )
    if dup_q.first() is not None:
        raise HTTPException(status_code=400, detail="Zone with this name already exists for this hall and restaurant")

    row = IikoSalesHallZone(
        company_id=company_id,
        hall_id=hall.id,
        restaurant_id=int(restaurant.id),
        name=name,
        name_norm=name_norm,
        comment=(str(getattr(payload, "comment", "") or "").strip() or None),
        is_active=bool(getattr(payload, "is_active", True)),
    )
    db.add(hall)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, hall.name, restaurant.name


def update_sales_hall_zone(
    db: Session,
    current_user: User,
    *,
    zone_id: UUID,
    payload: Any,
) -> tuple[IikoSalesHallZone, Optional[str], Optional[str]]:
    row = sales_hall_zones_query(db, current_user).filter(IikoSalesHallZone.id == zone_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    if getattr(payload, "name", None) is not None:
        name = str(getattr(payload, "name", "") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        name_norm = normalize_location_token(name)
        dup_q = (
            db.query(IikoSalesHallZone)
            .filter(IikoSalesHallZone.id != row.id)
            .filter(IikoSalesHallZone.hall_id == row.hall_id)
            .filter(IikoSalesHallZone.restaurant_id == row.restaurant_id)
            .filter(IikoSalesHallZone.name_norm == name_norm)
        )
        if row.company_id is None:
            dup_q = dup_q.filter(IikoSalesHallZone.company_id.is_(None))
        else:
            dup_q = dup_q.filter(IikoSalesHallZone.company_id == row.company_id)
        if dup_q.first() is not None:
            raise HTTPException(status_code=400, detail="Zone with this name already exists for this hall and restaurant")
        row.name = name
        row.name_norm = name_norm
    if getattr(payload, "comment", None) is not None:
        row.comment = str(getattr(payload, "comment", "") or "").strip() or None
    if getattr(payload, "is_active", None) is not None:
        row.is_active = bool(getattr(payload, "is_active"))

    db.add(row)
    db.commit()
    db.refresh(row)

    hall_row = db.query(IikoSalesHall.id, IikoSalesHall.name).filter(IikoSalesHall.id == row.hall_id).first()
    restaurant_row = db.query(Restaurant.id, Restaurant.name).filter(Restaurant.id == row.restaurant_id).first()
    hall_name = str(hall_row.name) if hall_row is not None and hall_row.name is not None else None
    restaurant_name = (
        str(restaurant_row.name)
        if restaurant_row is not None and restaurant_row.name is not None
        else None
    )
    return row, hall_name, restaurant_name


def delete_sales_hall_zone(
    db: Session,
    current_user: User,
    *,
    zone_id: UUID,
) -> str:
    row = sales_hall_zones_query(db, current_user).filter(IikoSalesHallZone.id == zone_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    db.delete(row)
    db.commit()
    return str(row.id)


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


def list_sales_hall_tables_payload(
    db: Session,
    current_user: User,
    *,
    include_inactive: bool = True,
    restaurant_id: Optional[int] = None,
    source_restaurant_id: Optional[int] = None,
    hall_id: Optional[UUID] = None,
    zone_id: Optional[UUID] = None,
) -> List[Dict[str, Any]]:
    if restaurant_id is not None:
        ensure_user_access_to_restaurant(
            db,
            current_user,
            int(restaurant_id),
            require_credentials=False,
        )
    if source_restaurant_id is not None:
        ensure_user_access_to_restaurant(
            db,
            current_user,
            int(source_restaurant_id),
            require_credentials=False,
        )
    if hall_id is not None:
        hall_exists = sales_halls_query(db, current_user).filter(IikoSalesHall.id == hall_id).first()
        if hall_exists is None:
            raise HTTPException(status_code=404, detail="Hall not found")
    if zone_id is not None:
        zone_exists = sales_hall_zones_query(db, current_user).filter(IikoSalesHallZone.id == zone_id).first()
        if zone_exists is None:
            raise HTTPException(status_code=404, detail="Zone not found")

    q = sales_hall_tables_query(db, current_user)
    if not include_inactive:
        q = q.filter(IikoSalesHallTable.is_active.is_(True))
    if restaurant_id is not None:
        q = q.filter(IikoSalesHallTable.restaurant_id == int(restaurant_id))
    if source_restaurant_id is not None:
        q = q.filter(IikoSalesHallTable.source_restaurant_id == int(source_restaurant_id))
    if hall_id is not None:
        q = q.filter(IikoSalesHallTable.hall_id == hall_id)
    if zone_id is not None:
        q = q.filter(IikoSalesHallTable.zone_id == zone_id)

    rows = q.order_by(
        IikoSalesHallTable.restaurant_id.asc(),
        IikoSalesHallTable.hall_name_norm.asc(),
        IikoSalesHallTable.department_norm.asc(),
        IikoSalesHallTable.table_num_norm.asc(),
    ).all()

    restaurant_ids = {
        int(row.restaurant_id)
        for row in rows
        if row.restaurant_id is not None
    }.union(
        {
            int(row.source_restaurant_id)
            for row in rows
            if row.source_restaurant_id is not None
        }
    )
    restaurant_name_by_id = restaurant_name_map(db, restaurant_ids)
    return serialize_sales_hall_table_rows(rows, restaurant_name_by_id=restaurant_name_by_id)


def upsert_sales_hall_table(
    db: Session,
    current_user: User,
    payload: Any,
) -> tuple[IikoSalesHallTable, Optional[str], Optional[str]]:
    restaurant = ensure_user_access_to_restaurant(
        db,
        current_user,
        int(getattr(payload, "restaurant_id")),
        require_credentials=False,
    )
    source_restaurant: Optional[Restaurant] = None
    if getattr(payload, "source_restaurant_id", None) is not None:
        source_restaurant = ensure_user_access_to_restaurant(
            db,
            current_user,
            int(getattr(payload, "source_restaurant_id")),
            require_credentials=False,
        )

    company_id = resolve_scoped_company_id(
        db,
        current_user,
        int(restaurant.company_id) if restaurant.company_id is not None else None,
    )
    if restaurant.company_id != company_id:
        raise HTTPException(status_code=400, detail="Restaurant is outside of your company scope")
    if source_restaurant is not None and source_restaurant.company_id != company_id:
        raise HTTPException(status_code=400, detail="Source restaurant is outside of your company scope")

    department = str(getattr(payload, "department", "") or "").strip() or None
    table_num = str(getattr(payload, "table_num", "") or "").strip() or None
    hall_name = str(getattr(payload, "hall_name", "") or "").strip()
    table_name = str(getattr(payload, "table_name", "") or "").strip() or None
    comment = str(getattr(payload, "comment", "") or "").strip() or None
    if not department:
        raise HTTPException(status_code=400, detail="department is required")
    if not hall_name:
        raise HTTPException(status_code=400, detail="hall_name is required")
    capacity = getattr(payload, "capacity", None)
    if capacity is not None and int(capacity) < 0:
        raise HTTPException(status_code=400, detail="capacity cannot be negative")

    department_norm = normalize_location_token(department)
    table_num_norm = normalize_location_token(table_num)
    hall_name_norm = normalize_location_token(hall_name)
    source_restaurant_id_value = (
        int(getattr(payload, "source_restaurant_id"))
        if getattr(payload, "source_restaurant_id", None) is not None
        else None
    )

    row = (
        sales_hall_tables_query(db, current_user)
        .filter(IikoSalesHallTable.restaurant_id == int(getattr(payload, "restaurant_id")))
        .filter(IikoSalesHallTable.source_restaurant_id == source_restaurant_id_value)
        .filter(IikoSalesHallTable.department_norm == department_norm)
        .filter(IikoSalesHallTable.table_num_norm == table_num_norm)
        .first()
    )

    if row is None:
        row = IikoSalesHallTable(
            company_id=company_id,
            restaurant_id=int(getattr(payload, "restaurant_id")),
            source_restaurant_id=source_restaurant_id_value,
            department=department,
            table_num=table_num,
            department_norm=department_norm,
            table_num_norm=table_num_norm,
            hall_name=hall_name,
            hall_name_norm=hall_name_norm,
            table_name=table_name,
            capacity=int(capacity) if capacity is not None else None,
            comment=comment,
            is_active=bool(getattr(payload, "is_active", True)),
        )
    else:
        row.company_id = company_id
        row.restaurant_id = int(getattr(payload, "restaurant_id"))
        row.source_restaurant_id = source_restaurant_id_value
        row.department = department
        row.table_num = table_num
        row.department_norm = department_norm
        row.table_num_norm = table_num_norm
        row.hall_name = hall_name
        row.hall_name_norm = hall_name_norm
        row.table_name = table_name
        row.capacity = int(capacity) if capacity is not None else None
        row.comment = comment
        row.is_active = bool(getattr(payload, "is_active", True))

    db.add(row)
    db.commit()
    db.refresh(row)
    return row, restaurant.name, source_restaurant.name if source_restaurant is not None else None


def update_sales_hall_table(
    db: Session,
    current_user: User,
    *,
    row_id: str,
    payload: Any,
) -> tuple[IikoSalesHallTable, Optional[str], Optional[str]]:
    row = sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Hall table mapping not found")

    restaurant: Optional[Restaurant] = None
    source_restaurant: Optional[Restaurant] = None
    if getattr(payload, "restaurant_id", None) is not None:
        restaurant = ensure_user_access_to_restaurant(
            db,
            current_user,
            int(getattr(payload, "restaurant_id")),
            require_credentials=False,
        )
        row.restaurant_id = int(getattr(payload, "restaurant_id"))
    if getattr(payload, "source_restaurant_id", None) is not None:
        source_restaurant = ensure_user_access_to_restaurant(
            db,
            current_user,
            int(getattr(payload, "source_restaurant_id")),
            require_credentials=False,
        )
        row.source_restaurant_id = int(getattr(payload, "source_restaurant_id"))

    requested_company_id = (
        int(restaurant.company_id)
        if restaurant is not None and restaurant.company_id is not None
        else int(row.company_id)
        if row.company_id is not None
        else None
    )
    company_id = resolve_scoped_company_id(db, current_user, requested_company_id)
    row.company_id = company_id

    if getattr(payload, "department", None) is not None:
        row.department = str(getattr(payload, "department", "") or "").strip() or None
        row.department_norm = normalize_location_token(row.department)
    if getattr(payload, "table_num", None) is not None:
        row.table_num = str(getattr(payload, "table_num", "") or "").strip() or None
        row.table_num_norm = normalize_location_token(row.table_num)
    if getattr(payload, "hall_name", None) is not None:
        row.hall_name = str(getattr(payload, "hall_name", "") or "").strip()
        row.hall_name_norm = normalize_location_token(row.hall_name)
    if getattr(payload, "table_name", None) is not None:
        row.table_name = str(getattr(payload, "table_name", "") or "").strip() or None
    if getattr(payload, "capacity", None) is not None:
        if int(getattr(payload, "capacity")) < 0:
            raise HTTPException(status_code=400, detail="capacity cannot be negative")
        row.capacity = int(getattr(payload, "capacity"))
    if getattr(payload, "comment", None) is not None:
        row.comment = str(getattr(payload, "comment", "") or "").strip() or None
    if getattr(payload, "is_active", None) is not None:
        row.is_active = bool(getattr(payload, "is_active"))

    if not row.department_norm:
        raise HTTPException(status_code=400, detail="department is required")
    if not str(row.hall_name or "").strip():
        raise HTTPException(status_code=400, detail="hall_name is required")
    row.hall_name_norm = normalize_location_token(row.hall_name)

    db.add(row)
    db.commit()
    db.refresh(row)

    if restaurant is None:
        restaurant = db.query(Restaurant).filter(Restaurant.id == int(row.restaurant_id)).first()
    if source_restaurant is None and row.source_restaurant_id is not None:
        source_restaurant = db.query(Restaurant).filter(Restaurant.id == int(row.source_restaurant_id)).first()

    return (
        row,
        restaurant.name if restaurant is not None else None,
        source_restaurant.name if source_restaurant is not None else None,
    )


def delete_sales_hall_table(
    db: Session,
    current_user: User,
    *,
    row_id: str,
) -> str:
    row = sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Hall table mapping not found")
    db.delete(row)
    db.commit()
    return str(row.id)


def assign_tables_to_sales_hall_zone(
    db: Session,
    current_user: User,
    *,
    zone_id: UUID,
    payload: Any,
) -> Dict[str, Any]:
    zone = sales_hall_zones_query(db, current_user).filter(IikoSalesHallZone.id == zone_id).first()
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    hall = sales_halls_query(db, current_user).filter(IikoSalesHall.id == zone.hall_id).first()
    if hall is None:
        raise HTTPException(status_code=404, detail="Hall not found")
    restaurant = ensure_user_access_to_restaurant(
        db,
        current_user,
        int(zone.restaurant_id),
        require_credentials=False,
    )

    requested_company_id = next(
        (
            int(candidate)
            for candidate in (zone.company_id, restaurant.company_id, hall.company_id)
            if candidate is not None
        ),
        None,
    )
    company_id = resolve_scoped_company_id(db, current_user, requested_company_id)

    if bool(getattr(payload, "replace_zone_tables", False)):
        old_rows = (
            sales_hall_tables_query(db, current_user)
            .filter(IikoSalesHallTable.restaurant_id == int(zone.restaurant_id))
            .filter(IikoSalesHallTable.zone_id == zone.id)
            .all()
        )
        for old_row in old_rows:
            db.delete(old_row)

    items = list(getattr(payload, "items", None) or [])
    source_restaurant_ids = sorted(
        {
            int(getattr(item, "source_restaurant_id"))
            for item in items
            if getattr(item, "source_restaurant_id", None) is not None
        }
    )
    for source_restaurant_id in source_restaurant_ids:
        ensure_user_access_to_restaurant(
            db,
            current_user,
            source_restaurant_id,
            require_credentials=False,
        )

    upserted = 0
    for index, item in enumerate(items):
        department = str(getattr(item, "department", "") or "").strip()
        if not department:
            raise HTTPException(status_code=400, detail=f"items[{index}].department is required")
        table_num = str(getattr(item, "table_num", "") or "").strip() or None
        table_name = str(getattr(item, "table_name", "") or "").strip() or table_num
        comment = str(getattr(item, "comment", "") or "").strip() or None
        if getattr(item, "capacity", None) is not None and int(getattr(item, "capacity")) < 0:
            raise HTTPException(status_code=400, detail=f"items[{index}].capacity cannot be negative")
        capacity = int(getattr(item, "capacity")) if getattr(item, "capacity", None) is not None else None
        source_restaurant_id_value = (
            int(getattr(item, "source_restaurant_id"))
            if getattr(item, "source_restaurant_id", None) is not None
            else None
        )

        department_norm = normalize_location_token(department)
        table_num_norm = normalize_location_token(table_num)
        row = (
            sales_hall_tables_query(db, current_user)
            .filter(IikoSalesHallTable.restaurant_id == int(zone.restaurant_id))
            .filter(IikoSalesHallTable.source_restaurant_id == source_restaurant_id_value)
            .filter(IikoSalesHallTable.department_norm == department_norm)
            .filter(IikoSalesHallTable.table_num_norm == table_num_norm)
            .first()
        )

        if row is None:
            row = IikoSalesHallTable(
                company_id=company_id,
                restaurant_id=int(zone.restaurant_id),
                hall_id=hall.id,
                zone_id=zone.id,
                source_restaurant_id=source_restaurant_id_value,
                department=department,
                table_num=table_num,
                department_norm=department_norm,
                table_num_norm=table_num_norm,
                hall_name=hall.name,
                hall_name_norm=normalize_location_token(hall.name),
                zone_name=zone.name,
                zone_name_norm=normalize_location_token(zone.name),
                table_name=table_name,
                capacity=capacity,
                comment=comment,
                is_active=bool(getattr(item, "is_active", True)),
            )
        else:
            row.company_id = company_id
            row.restaurant_id = int(zone.restaurant_id)
            row.hall_id = hall.id
            row.zone_id = zone.id
            row.source_restaurant_id = source_restaurant_id_value
            row.department = department
            row.table_num = table_num
            row.department_norm = department_norm
            row.table_num_norm = table_num_norm
            row.hall_name = hall.name
            row.hall_name_norm = normalize_location_token(hall.name)
            row.zone_name = zone.name
            row.zone_name_norm = normalize_location_token(zone.name)
            row.table_name = table_name
            row.capacity = capacity
            row.comment = comment
            row.is_active = bool(getattr(item, "is_active", True))
        db.add(row)
        upserted += 1

    db.commit()
    return {"status": "ok", "zone_id": str(zone.id), "upserted": upserted}


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


def restaurant_name_map(
    db: Session,
    restaurant_ids: set[int],
) -> Dict[int, str]:
    if not restaurant_ids:
        return {}
    rows = (
        db.query(Restaurant.id, Restaurant.name)
        .filter(Restaurant.id.in_(sorted(restaurant_ids)))
        .all()
    )
    return {
        int(rest_id): str(rest_name)
        for rest_id, rest_name in rows
        if rest_id is not None and rest_name is not None
    }


def hall_name_map(
    db: Session,
    hall_ids: set[Any],
) -> Dict[str, str]:
    if not hall_ids:
        return {}
    rows = (
        db.query(IikoSalesHall.id, IikoSalesHall.name)
        .filter(IikoSalesHall.id.in_(list(hall_ids)))
        .all()
    )
    return {
        str(hall_id): str(hall_name)
        for hall_id, hall_name in rows
        if hall_id is not None and hall_name is not None
    }


def serialize_sales_hall_zone_rows(
    rows: List[IikoSalesHallZone],
    *,
    hall_name_by_id: Dict[str, str],
    restaurant_name_by_id: Dict[int, str],
) -> List[Dict[str, Any]]:
    return [
        serialize_sales_hall_zone(
            row,
            hall_name=hall_name_by_id.get(str(row.hall_id)) if row.hall_id is not None else None,
            restaurant_name=restaurant_name_by_id.get(int(row.restaurant_id))
            if row.restaurant_id is not None
            else None,
        )
        for row in rows
    ]


def serialize_sales_hall_table_rows(
    rows: List[IikoSalesHallTable],
    *,
    restaurant_name_by_id: Dict[int, str],
) -> List[Dict[str, Any]]:
    return [
        serialize_sales_hall_table(
            row,
            restaurant_name=restaurant_name_by_id.get(int(row.restaurant_id))
            if row.restaurant_id is not None
            else None,
            source_restaurant_name=restaurant_name_by_id.get(int(row.source_restaurant_id))
            if row.source_restaurant_id is not None
            else None,
        )
        for row in rows
    ]


def serialize_sales_location_candidate_rows(
    rows: List[Any],
    *,
    restaurant_name_by_id: Dict[int, str],
) -> List[Dict[str, Any]]:
    return [
        {
            "source_restaurant_id": int(row.source_restaurant_id) if row.source_restaurant_id is not None else None,
            "source_restaurant_name": (
                restaurant_name_by_id.get(int(row.source_restaurant_id))
                if row.source_restaurant_id is not None
                else None
            ),
            "department": row.department,
            "table_num": row.table_num,
            "department_norm": normalize_location_token(row.department),
            "table_num_norm": normalize_location_token(row.table_num),
            "orders_count": int(row.orders_count or 0),
            "last_open_date": row.last_open_date.isoformat() if row.last_open_date else None,
        }
        for row in rows
    ]


def build_sales_hall_table_candidate_items(
    sales_rows: List[Any],
    *,
    restaurant_name_by_id: Dict[int, str],
    resolve_hall,
    limit: int,
) -> List[Dict[str, Any]]:
    items_by_scope: Dict[tuple[int, Optional[int], str, str], Dict[str, Any]] = {}
    for row in sales_rows:
        resolved_restaurant_id = int(row.restaurant_id) if row.restaurant_id is not None else None
        source_restaurant_id_value = int(row.source_restaurant_id) if row.source_restaurant_id is not None else None
        if resolved_restaurant_id is None:
            continue

        department = str(row.department or "").strip()
        table_num = str(row.table_num or "").strip()
        department_norm = normalize_location_token(department)
        table_num_norm = normalize_location_token(table_num)
        if not department_norm and not table_num_norm:
            continue

        scope_key = (
            resolved_restaurant_id,
            source_restaurant_id_value,
            department_norm,
            table_num_norm,
        )
        resolved = resolve_hall(
            restaurant_id=resolved_restaurant_id,
            source_restaurant_id=source_restaurant_id_value,
            department=department,
            table_num=table_num,
        )
        items_by_scope[scope_key] = {
            "restaurant_id": resolved_restaurant_id,
            "restaurant_name": restaurant_name_by_id.get(resolved_restaurant_id),
            "source_restaurant_id": source_restaurant_id_value,
            "source_restaurant_name": (
                restaurant_name_by_id.get(source_restaurant_id_value)
                if source_restaurant_id_value is not None
                else None
            ),
            "department": department,
            "table_num": table_num,
            "department_norm": department_norm,
            "table_num_norm": table_num_norm,
            "orders_count": int(row.orders_count or 0),
            "guests_count": int(row.guests_count or 0),
            "last_open_date": row.last_open_date.isoformat() if row.last_open_date is not None else None,
            "hall_name": resolved.get("hall_name"),
            "zone_name": resolved.get("zone_name"),
            "table_name": resolved.get("table_name"),
            "capacity": resolved.get("capacity"),
        }

    items = list(items_by_scope.values())
    for item in items:
        restaurant_id_value = item.get("restaurant_id")
        source_id_value = item.get("source_restaurant_id")
        if restaurant_id_value is not None and not item.get("restaurant_name"):
            item["restaurant_name"] = restaurant_name_by_id.get(int(restaurant_id_value))
        if source_id_value is not None and not item.get("source_restaurant_name"):
            item["source_restaurant_name"] = restaurant_name_by_id.get(int(source_id_value))

    items.sort(
        key=lambda item: (
            normalize_location_token(item.get("restaurant_name") or item.get("restaurant_id")),
            normalize_location_token(item.get("source_restaurant_name") or item.get("source_restaurant_id")),
            normalize_location_token(item.get("department")),
            normalize_location_token(item.get("table_num")),
        )
    )
    return items[:limit]


def resolve_hall_table_candidates_window(
    from_date: Optional[str],
    to_date: Optional[str],
) -> tuple[str, str]:
    today = now_local().date()
    if from_date:
        start_date = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
    elif to_date:
        end_hint = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date()
        start_date = end_hint - timedelta(days=HALL_TABLE_DEFAULT_LOOKBACK_DAYS)
    else:
        start_date = today - timedelta(days=HALL_TABLE_DEFAULT_LOOKBACK_DAYS)

    end_date = (
        datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date()
        if to_date
        else today
    )
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="from_date cannot be later than to_date")
    return start_date.isoformat(), end_date.isoformat()


def list_sales_location_candidates_payload(
    db: Session,
    current_user: User,
    *,
    source_restaurant_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    if source_restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)

    accessible_restaurants = list_accessible_restaurants(db, current_user)
    accessible_ids = [int(r.id) for r in accessible_restaurants]
    restaurant_name_by_id = {int(r.id): r.name for r in accessible_restaurants}
    if not accessible_ids:
        return []

    q = (
        db.query(
            sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id).label("source_restaurant_id"),
            IikoSaleOrder.department.label("department"),
            IikoSaleOrder.table_num.label("table_num"),
            sa.func.count(sa.distinct(IikoSaleOrder.iiko_order_id)).label("orders_count"),
            sa.func.max(IikoSaleOrder.open_date).label("last_open_date"),
        )
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
    )

    if from_date:
        from_value = datetime.strptime(to_iso_date(from_date), "%Y-%m-%d").date()
        q = q.filter(IikoSaleOrder.open_date >= from_value)
    if to_date:
        to_value = datetime.strptime(to_iso_date(to_date), "%Y-%m-%d").date() + timedelta(days=1)
        q = q.filter(IikoSaleOrder.open_date < to_value)
    if source_restaurant_id is not None:
        q = q.filter(
            sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id) == int(source_restaurant_id)
        )

    rows = (
        q.group_by(
            sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id),
            IikoSaleOrder.department,
            IikoSaleOrder.table_num,
        )
        .order_by(
            sa.func.count(sa.distinct(IikoSaleOrder.iiko_order_id)).desc(),
            sa.func.max(IikoSaleOrder.open_date).desc().nullslast(),
            IikoSaleOrder.department.asc().nullslast(),
            IikoSaleOrder.table_num.asc().nullslast(),
        )
        .limit(limit)
        .all()
    )

    return serialize_sales_location_candidate_rows(
        rows,
        restaurant_name_by_id=restaurant_name_by_id,
    )


def list_sales_hall_table_candidates_payload(
    db: Session,
    current_user: User,
    *,
    restaurant_id: Optional[int] = None,
    source_restaurant_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    if restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, restaurant_id, require_credentials=False)
    if source_restaurant_id is not None:
        ensure_user_access_to_restaurant(db, current_user, source_restaurant_id, require_credentials=False)

    accessible_restaurants = list_accessible_restaurants(db, current_user)
    restaurant_name_by_id = {int(row.id): row.name for row in accessible_restaurants if row.id is not None}
    if not accessible_restaurants:
        return []
    accessible_ids = [int(row.id) for row in accessible_restaurants if row.id is not None]
    if not accessible_ids:
        return []

    hall_rows_q = sales_hall_tables_query(db, current_user).filter(IikoSalesHallTable.is_active.is_(True))
    if restaurant_id is not None:
        hall_rows_q = hall_rows_q.filter(IikoSalesHallTable.restaurant_id == int(restaurant_id))
    resolve_hall = build_sales_hall_table_resolver(hall_rows_q.all())

    from_date_value, to_date_value = resolve_hall_table_candidates_window(from_date, to_date)
    start_date = datetime.strptime(from_date_value, "%Y-%m-%d").date()
    end_date = datetime.strptime(to_date_value, "%Y-%m-%d").date()
    source_restaurant_expr = sa.func.coalesce(IikoSaleOrder.source_restaurant_id, IikoSaleOrder.restaurant_id)

    sales_rows_q = (
        db.query(
            IikoSaleOrder.restaurant_id.label("restaurant_id"),
            source_restaurant_expr.label("source_restaurant_id"),
            IikoSaleOrder.department.label("department"),
            IikoSaleOrder.table_num.label("table_num"),
            sa.func.count(IikoSaleOrder.id).label("orders_count"),
            sa.func.coalesce(sa.func.sum(sa.func.coalesce(IikoSaleOrder.guest_num, 0)), 0).label("guests_count"),
            sa.func.max(IikoSaleOrder.open_date).label("last_open_date"),
        )
        .filter(IikoSaleOrder.restaurant_id.in_(accessible_ids))
        .filter(IikoSaleOrder.open_date.isnot(None))
        .filter(IikoSaleOrder.open_date >= start_date)
        .filter(IikoSaleOrder.open_date <= end_date)
    )
    if restaurant_id is not None:
        sales_rows_q = sales_rows_q.filter(IikoSaleOrder.restaurant_id == int(restaurant_id))
    if source_restaurant_id is not None:
        sales_rows_q = sales_rows_q.filter(source_restaurant_expr == int(source_restaurant_id))
    sales_rows = (
        sales_rows_q.group_by(
            IikoSaleOrder.restaurant_id,
            source_restaurant_expr,
            IikoSaleOrder.department,
            IikoSaleOrder.table_num,
        ).all()
    )

    return build_sales_hall_table_candidate_items(
        sales_rows,
        restaurant_name_by_id=restaurant_name_by_id,
        resolve_hall=resolve_hall,
        limit=limit,
    )
