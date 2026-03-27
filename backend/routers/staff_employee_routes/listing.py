from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from . import common as c

router = APIRouter()


@router.get("/", response_model=c.StaffEmployeeListResponse)
def list_staff_employees(
    q: Optional[str] = Query(None, description="Search by username/first_name/last_name/staff_code"),
    include_fired: bool = Query(False),
    only_fired: bool = Query(False),
    only_formalized: bool = Query(False),
    only_not_formalized: bool = Query(False),
    only_cis: bool = Query(False),
    only_not_cis: bool = Query(False),
    position_ids: Optional[List[int]] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_direction: str = Query("asc"),
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
        only_formalized=only_formalized,
        only_not_formalized=only_not_formalized,
        only_cis=only_cis,
        only_not_cis=only_not_cis,
        position_ids=position_ids,
        sort_by=sort_by,
        sort_direction=sort_direction,
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
    only_formalized: bool = Query(False),
    only_not_formalized: bool = Query(False),
    only_cis: bool = Query(False),
    only_not_cis: bool = Query(False),
    position_ids: Optional[List[int]] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_direction: str = Query("asc"),
    restaurant_id: Optional[int] = Query(None, ge=1),
    hire_date_from: Optional[date] = Query(None),
    hire_date_to: Optional[date] = Query(None),
    fire_date_from: Optional[date] = Query(None),
    fire_date_to: Optional[date] = Query(None),
    include_restaurants: bool = Query(True),
    include_companies: bool = Query(True),
    include_roles: bool = Query(True),
    include_positions: bool = Query(True),
    include_items: bool = Query(True),
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> c.StaffEmployeesBootstrapResponse:
    items: List[c.StaffUserPublic] = []
    has_more = False
    next_offset = None
    response_offset = 0
    response_limit = 0
    if include_items:
        items, has_more, next_offset = c._list_staff_employee_items(
            db,
            current_user,
            q=q,
            include_fired=include_fired,
            only_fired=only_fired,
            only_formalized=only_formalized,
            only_not_formalized=only_not_formalized,
            only_cis=only_cis,
            only_not_cis=only_not_cis,
            position_ids=position_ids,
            sort_by=sort_by,
            sort_direction=sort_direction,
            restaurant_id=restaurant_id,
            hire_date_from=hire_date_from,
            hire_date_to=hire_date_to,
            fire_date_from=fire_date_from,
            fire_date_to=fire_date_to,
            offset=offset,
            limit=limit,
        )
        response_offset = offset
        response_limit = limit
    references = c._load_staff_references(
        db,
        current_user,
        include_restaurants=include_restaurants,
        include_companies=include_companies,
        include_roles=include_roles,
        include_positions=include_positions,
    )
    return c.StaffEmployeesBootstrapResponse(
        items=items,
        references=references,
        offset=response_offset,
        limit=response_limit,
        has_more=has_more,
        next_offset=next_offset,
    )
