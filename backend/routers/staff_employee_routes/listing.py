from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from . import common as c

router = APIRouter()


@router.get("/", response_model=c.StaffEmployeeListResponse)
def list_staff_employees(
    q: Optional[str] = Query(None, description="Search by username/first_name/last_name/staff_code"),
    include_fired: bool = Query(False),
    only_fired: bool = Query(False),
    restaurant_id: Optional[int] = Query(None, ge=1),
    hire_date_from: Optional[date] = Query(None),
    hire_date_to: Optional[date] = Query(None),
    fire_date_from: Optional[date] = Query(None),
    fire_date_to: Optional[date] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> c.StaffEmployeeListResponse:
    items, has_more, next_offset = c._list_staff_employee_items(
        db,
        current_user,
        q=q,
        include_fired=include_fired,
        only_fired=only_fired,
        restaurant_id=restaurant_id,
        hire_date_from=hire_date_from,
        hire_date_to=hire_date_to,
        fire_date_from=fire_date_from,
        fire_date_to=fire_date_to,
        offset=offset,
        limit=limit,
    )
    return c.StaffEmployeeListResponse(
        items=items,
        offset=offset,
        limit=limit,
        has_more=has_more,
        next_offset=next_offset,
    )


@router.get("/bootstrap", response_model=c.StaffEmployeesBootstrapResponse)
def staff_employees_bootstrap(
    q: Optional[str] = Query(None, description="Search by username/first_name/last_name/staff_code"),
    include_fired: bool = Query(False),
    only_fired: bool = Query(False),
    restaurant_id: Optional[int] = Query(None, ge=1),
    hire_date_from: Optional[date] = Query(None),
    hire_date_to: Optional[date] = Query(None),
    fire_date_from: Optional[date] = Query(None),
    fire_date_to: Optional[date] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> c.StaffEmployeesBootstrapResponse:
    items, has_more, next_offset = c._list_staff_employee_items(
        db,
        current_user,
        q=q,
        include_fired=include_fired,
        only_fired=only_fired,
        restaurant_id=restaurant_id,
        hire_date_from=hire_date_from,
        hire_date_to=hire_date_to,
        fire_date_from=fire_date_from,
        fire_date_to=fire_date_to,
        offset=offset,
        limit=limit,
    )
    references = c._load_staff_references(db, current_user)
    return c.StaffEmployeesBootstrapResponse(
        items=items,
        references=references,
        offset=offset,
        limit=limit,
        has_more=has_more,
        next_offset=next_offset,
    )
