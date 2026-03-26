from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.bd.database import get_db
from backend.bd.models import User
from backend.schemas.iiko_sales import (
    AssignIikoSalesZoneTablesRequest,
    CreateIikoSalesHallRequest,
    CreateIikoSalesHallZoneRequest,
    UpdateIikoSalesHallRequest,
    UpdateIikoSalesHallTableRequest,
    UpdateIikoSalesHallZoneRequest,
    UpdateIikoSalesLocationMappingRequest,
    UpsertIikoSalesHallTableRequest,
    UpsertIikoSalesLocationMappingRequest,
)
from backend.services.iiko_sales_layouts import (
    assign_tables_to_sales_hall_zone as _assign_tables_to_sales_hall_zone,
    create_sales_hall as _create_sales_hall,
    create_sales_hall_zone as _create_sales_hall_zone,
    delete_sales_hall as _delete_sales_hall,
    delete_sales_hall_table as _delete_sales_hall_table,
    delete_sales_hall_zone as _delete_sales_hall_zone,
    delete_sales_location_mapping as _delete_sales_location_mapping,
    list_sales_halls_payload as _list_sales_halls_payload,
    list_sales_hall_table_candidates_payload as _list_sales_hall_table_candidates_payload,
    list_sales_hall_tables_payload as _list_sales_hall_tables_payload,
    list_sales_hall_zones_payload as _list_sales_hall_zones_payload,
    list_sales_location_candidates_payload as _list_sales_location_candidates_payload,
    list_sales_location_mappings_payload as _list_sales_location_mappings_payload,
    serialize_sales_hall as _serialize_sales_hall,
    serialize_sales_hall_table as _serialize_sales_hall_table,
    serialize_sales_hall_zone as _serialize_sales_hall_zone,
    serialize_sales_location_mapping as _serialize_sales_location_mapping,
    update_sales_hall as _update_sales_hall,
    update_sales_hall_table as _update_sales_hall_table,
    update_sales_hall_zone as _update_sales_hall_zone,
    update_sales_location_mapping as _update_sales_location_mapping,
    upsert_sales_hall_table as _upsert_sales_hall_table,
    upsert_sales_location_mapping as _upsert_sales_location_mapping,
)
from backend.services.permissions import ensure_permissions
from backend.utils import get_current_user

from .common import SALES_TABLES_MANAGE_PERMISSIONS, SALES_TABLES_VIEW_PERMISSIONS

router = APIRouter()


@router.get("/sales-location-mappings")
def list_sales_location_mappings(
    include_inactive: bool = Query(True),
    source_restaurant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    return _list_sales_location_mappings_payload(
        db,
        current_user,
        include_inactive=include_inactive,
        source_restaurant_id=source_restaurant_id,
    )


@router.put("/sales-location-mappings")
def upsert_sales_location_mapping(
    payload: UpsertIikoSalesLocationMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row, source_restaurant_name, target_restaurant_name = _upsert_sales_location_mapping(
        db,
        current_user,
        payload,
    )
    return _serialize_sales_location_mapping(
        row,
        source_restaurant_name=source_restaurant_name,
        target_restaurant_name=target_restaurant_name,
    )


@router.patch("/sales-location-mappings/{mapping_id}")
def update_sales_location_mapping(
    mapping_id: str,
    payload: UpdateIikoSalesLocationMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row, source_restaurant_name, target_restaurant_name = _update_sales_location_mapping(
        db,
        current_user,
        mapping_id=mapping_id,
        payload=payload,
    )
    return _serialize_sales_location_mapping(
        row,
        source_restaurant_name=source_restaurant_name,
        target_restaurant_name=target_restaurant_name,
    )


@router.delete("/sales-location-mappings/{mapping_id}")
def delete_sales_location_mapping(
    mapping_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    deleted_id = _delete_sales_location_mapping(db, current_user, mapping_id=mapping_id)
    return {"status": "ok", "id": deleted_id}


@router.get("/sales-location-candidates")
def list_sales_location_candidates(
    source_restaurant_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    return _list_sales_location_candidates_payload(
        db,
        current_user,
        source_restaurant_id=source_restaurant_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )


@router.get("/sales-halls")
def list_sales_halls(
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    return _list_sales_halls_payload(db, current_user, include_inactive=include_inactive)


@router.post("/sales-halls")
def create_sales_hall(
    payload: CreateIikoSalesHallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row = _create_sales_hall(db, current_user, payload)
    return _serialize_sales_hall(row)


@router.patch("/sales-halls/{hall_id}")
def update_sales_hall(
    hall_id: UUID,
    payload: UpdateIikoSalesHallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row = _update_sales_hall(db, current_user, hall_id=hall_id, payload=payload)
    return _serialize_sales_hall(row)


@router.delete("/sales-halls/{hall_id}")
def delete_sales_hall(
    hall_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    deleted_id = _delete_sales_hall(db, current_user, hall_id=hall_id)
    return {"status": "ok", "id": deleted_id}


@router.get("/sales-hall-zones")
def list_sales_hall_zones(
    include_inactive: bool = Query(True),
    hall_id: Optional[UUID] = Query(None),
    restaurant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    return _list_sales_hall_zones_payload(
        db,
        current_user,
        include_inactive=include_inactive,
        hall_id=hall_id,
        restaurant_id=restaurant_id,
    )


@router.post("/sales-hall-zones")
def create_sales_hall_zone(
    payload: CreateIikoSalesHallZoneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row, hall_name, restaurant_name = _create_sales_hall_zone(db, current_user, payload)
    return _serialize_sales_hall_zone(
        row,
        hall_name=hall_name,
        restaurant_name=restaurant_name,
    )


@router.patch("/sales-hall-zones/{zone_id}")
def update_sales_hall_zone(
    zone_id: UUID,
    payload: UpdateIikoSalesHallZoneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row, hall_name, restaurant_name = _update_sales_hall_zone(
        db,
        current_user,
        zone_id=zone_id,
        payload=payload,
    )
    return _serialize_sales_hall_zone(
        row,
        hall_name=hall_name,
        restaurant_name=restaurant_name,
    )


@router.delete("/sales-hall-zones/{zone_id}")
def delete_sales_hall_zone(
    zone_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    deleted_id = _delete_sales_hall_zone(db, current_user, zone_id=zone_id)
    return {"status": "ok", "id": deleted_id}


@router.post("/sales-hall-zones/{zone_id}/assign-tables")
def assign_tables_to_sales_hall_zone(
    zone_id: UUID,
    payload: AssignIikoSalesZoneTablesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    return _assign_tables_to_sales_hall_zone(
        db,
        current_user,
        zone_id=zone_id,
        payload=payload,
    )


@router.get("/sales-hall-tables")
def list_sales_hall_tables(
    include_inactive: bool = Query(True),
    restaurant_id: Optional[int] = Query(None),
    source_restaurant_id: Optional[int] = Query(None),
    hall_id: Optional[UUID] = Query(None),
    zone_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    return _list_sales_hall_tables_payload(
        db,
        current_user,
        include_inactive=include_inactive,
        restaurant_id=restaurant_id,
        source_restaurant_id=source_restaurant_id,
        hall_id=hall_id,
        zone_id=zone_id,
    )


@router.put("/sales-hall-tables")
def upsert_sales_hall_table(
    payload: UpsertIikoSalesHallTableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row, restaurant_name, source_restaurant_name = _upsert_sales_hall_table(
        db,
        current_user,
        payload,
    )
    return _serialize_sales_hall_table(
        row,
        restaurant_name=restaurant_name,
        source_restaurant_name=source_restaurant_name,
    )


@router.patch("/sales-hall-tables/{row_id}")
def update_sales_hall_table(
    row_id: str,
    payload: UpdateIikoSalesHallTableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    row, restaurant_name, source_restaurant_name = _update_sales_hall_table(
        db,
        current_user,
        row_id=row_id,
        payload=payload,
    )
    return _serialize_sales_hall_table(
        row,
        restaurant_name=restaurant_name,
        source_restaurant_name=source_restaurant_name,
    )


@router.delete("/sales-hall-tables/{row_id}")
def delete_sales_hall_table(
    row_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_MANAGE_PERMISSIONS)
    deleted_id = _delete_sales_hall_table(db, current_user, row_id=row_id)
    return {"status": "ok", "id": deleted_id}


@router.get("/sales-hall-table-candidates")
def list_sales_hall_table_candidates(
    restaurant_id: Optional[int] = Query(None),
    source_restaurant_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_permissions(current_user, *SALES_TABLES_VIEW_PERMISSIONS)
    return _list_sales_hall_table_candidates_payload(
        db,
        current_user,
        restaurant_id=restaurant_id,
        source_restaurant_id=source_restaurant_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )
