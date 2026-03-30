from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from . import common as c

router = APIRouter()


@router.get("/{user_id}", response_model=c.StaffEmployeeDetailResponse)
def get_staff_employee_detail(
    user_id: int,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> c.StaffEmployeeDetailResponse:
    target = (
        db.query(c.User)
        .options(
            c.joinedload(c.User.role),
            c.joinedload(c.User.company),
            c.joinedload(c.User.position).joinedload(c.Position.payment_format),
            c.joinedload(c.User.position).joinedload(c.Position.restaurant_subdivision),
            c.joinedload(c.User.restaurants),
        )
        .filter(c.User.id == user_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.id != user_id:
        c._ensure_staff_view(current_user)
        if not c.users_share_restaurant(db, current_user, user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if not date_from or not date_to:
        start, end = c._month_bounds(date.today())
        date_from = date_from or start
        date_to = date_to or end
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be before or equal to date_to",
        )

    condition = c._attendance_range_condition(date_from, date_to)
    attendance_query = (
        db.query(c.Attendance)
        .options(
            c.joinedload(c.Attendance.position),
            c.joinedload(c.Attendance.restaurant),
        )
        .filter(c.Attendance.user_id == user_id)
        .filter(condition)
    )

    if current_user.id != user_id:
        allowed_restaurants = c.get_user_restaurant_ids(db, current_user)
        if allowed_restaurants is not None:
            if allowed_restaurants:
                attendance_query = attendance_query.filter(c.Attendance.restaurant_id.in_(allowed_restaurants))
            else:
                attendance_query = attendance_query.filter(False)

    rows = attendance_query.order_by(c.Attendance.open_date.asc(), c.Attendance.open_time.asc()).all()

    attendances = [c._attendance_to_public(a, current_user, target) for a in rows]
    return c.StaffEmployeeDetailResponse(
        user=c._to_staff_public(target, current_user),
        attendances=attendances,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{user_id}/iiko-sync-preview", response_model=c.EmployeeIikoSyncPreviewResponse)
def get_employee_iiko_sync_preview(
    user_id: int,
    sync_restaurant_id: Optional[int] = Query(None, ge=1),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> c.EmployeeIikoSyncPreviewResponse:
    db_user = (
        db.query(c.User)
        .options(
            c.joinedload(c.User.workplace_restaurant),
            c.joinedload(c.User.position),
            c.selectinload(c.User.restaurants),
        )
        .filter(c.User.id == user_id)
        .first()
    )
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    c._ensure_can_sync_user_iiko(db, current_user, db_user)
    c.ensure_permissions(
        current_user,
        c.PermissionCode.STAFF_EMPLOYEES_IIKO_SYNC,
        c.PermissionCode.IIKO_MANAGE,
    )
    c._validate_iiko_restaurant_scope(
        db,
        current_user,
        sync_restaurant_id=sync_restaurant_id,
        department_restaurant_ids=None,
    )

    local_restaurants = [row for row in (db_user.restaurants or []) if row and row.id is not None]
    if getattr(db_user, "workplace_restaurant", None) is not None and getattr(db_user.workplace_restaurant, "id", None):
        workplace_id = int(db_user.workplace_restaurant.id)
        if not any(int(row.id) == workplace_id for row in local_restaurants):
            local_restaurants.append(db_user.workplace_restaurant)
    local_department_codes: list[str] = []
    for row in local_restaurants:
        code = (getattr(row, "department_code", None) or "").strip()
        if code and code not in local_department_codes:
            local_department_codes.append(code)

    local_snapshot = c.IikoSyncEmployeeSnapshot(
        first_name=db_user.first_name,
        middle_name=db_user.middle_name,
        last_name=db_user.last_name,
        position_name=getattr(getattr(db_user, "position", None), "name", None),
        position_code=getattr(getattr(db_user, "position", None), "code", None),
        staff_code=db_user.staff_code,
        iiko_code=db_user.iiko_code,
        iiko_id=db_user.iiko_id,
        workplace_restaurant_id=getattr(db_user, "workplace_restaurant_id", None),
        workplace_restaurant_name=getattr(getattr(db_user, "workplace_restaurant", None), "name", None),
        department_code=getattr(getattr(db_user, "workplace_restaurant", None), "department_code", None),
        restaurant_ids=[int(row.id) for row in local_restaurants],
        restaurant_names=[row.name or f"Restaurant #{row.id}" for row in local_restaurants],
        department_codes=local_department_codes,
    )

    iiko_snapshot = None
    iiko_error = None
    try:
        raw_iiko_snapshot = c.fetch_iiko_employee_snapshot(
            db,
            db_user,
            sync_restaurant_id=sync_restaurant_id,
        )
        if raw_iiko_snapshot:
            iiko_position_code = (raw_iiko_snapshot.get("main_role_code") or "").strip() or None
            iiko_position_name = None
            if iiko_position_code:
                iiko_position = (
                    db.query(c.Position)
                    .filter(c.func.lower(c.Position.code) == iiko_position_code.lower())
                    .first()
                )
                if iiko_position:
                    iiko_position_name = iiko_position.name

            department_code = (raw_iiko_snapshot.get("department_code") or "").strip() or None
            raw_department_codes = raw_iiko_snapshot.get("department_codes") or []
            if not isinstance(raw_department_codes, list):
                raw_department_codes = [raw_department_codes]

            department_codes: list[str] = []
            for raw_code in raw_department_codes:
                text = str(raw_code or "").strip()
                if text and text not in department_codes:
                    department_codes.append(text)
            if department_code and department_code not in department_codes:
                department_codes.insert(0, department_code)

            iiko_restaurants: list[c.Restaurant] = []
            for code in department_codes:
                restaurant = db.query(c.Restaurant).filter(c.Restaurant.department_code == code).first()
                if not restaurant:
                    restaurant = (
                        db.query(c.Restaurant)
                        .filter(c.func.lower(c.Restaurant.department_code) == code.lower())
                        .first()
                    )
                if not restaurant:
                    continue
                if any(existing.id == restaurant.id for existing in iiko_restaurants):
                    continue
                iiko_restaurants.append(restaurant)

            primary_restaurant = None
            if department_code:
                primary_restaurant = next(
                    (
                        row
                        for row in iiko_restaurants
                        if (getattr(row, "department_code", None) or "").strip() == department_code
                    ),
                    None,
                )
            if primary_restaurant is None and iiko_restaurants:
                primary_restaurant = iiko_restaurants[0]

            iiko_snapshot = c.IikoSyncEmployeeSnapshot(
                first_name=raw_iiko_snapshot.get("first_name") or None,
                middle_name=raw_iiko_snapshot.get("middle_name") or None,
                last_name=raw_iiko_snapshot.get("last_name") or None,
                position_name=iiko_position_name,
                position_code=iiko_position_code,
                staff_code=raw_iiko_snapshot.get("pin_code") or None,
                iiko_code=raw_iiko_snapshot.get("code") or None,
                iiko_id=raw_iiko_snapshot.get("id") or None,
                workplace_restaurant_id=getattr(primary_restaurant, "id", None),
                workplace_restaurant_name=getattr(primary_restaurant, "name", None),
                department_code=department_code,
                restaurant_ids=[int(row.id) for row in iiko_restaurants if row.id is not None],
                restaurant_names=[
                    row.name or f"Restaurant #{row.id}"
                    for row in iiko_restaurants
                    if row.id is not None
                ],
                department_codes=department_codes,
            )
    except c.IikoIntegrationError as exc:
        iiko_error = str(exc.detail)
    except Exception as exc:
        iiko_error = f"Unexpected iiko error: {exc}"
        c.logger.exception("Failed to load iiko sync preview for user %s", db_user.id)

    return c.EmployeeIikoSyncPreviewResponse(
        local=local_snapshot,
        iiko=iiko_snapshot,
        iiko_error=iiko_error,
    )
