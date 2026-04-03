from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from . import common as c
from backend.services.employee_attendance_updates import apply_employee_updates_to_attendances
from backend.services.image_uploads import normalize_uploaded_image

router = APIRouter()


@router.post("/{user_id}/photo", response_model=c.PhotoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_employee_photo(
    user_id: int,
    file: UploadFile = File(...),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    db_user = db.query(c.User).filter(c.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    c._ensure_can_edit_user(db, current_user, db_user)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image uploads are allowed")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    old_photo_key = db_user.photo_key

    try:
        upload_filename, upload_content, upload_content_type = normalize_uploaded_image(
            filename=file.filename,
            content=content,
            content_type=file.content_type,
        )
    except HTTPException:
        raise
    except Exception:
        c.logger.warning("Failed to normalize employee photo; uploading original", exc_info=True)
        upload_filename = file.filename or "photo.jpg"
        upload_content = content
        upload_content_type = file.content_type or "application/octet-stream"

    photo_key, photo_url = c.upload_employee_photo_with_url(
        user_id,
        upload_filename,
        upload_content,
        upload_content_type,
    )
    db_user.photo_key = photo_key
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            c.delete_object(photo_key)
        except Exception:
            c.logger.warning("Failed to delete uploaded employee photo after DB rollback", exc_info=True)
        raise
    db.refresh(db_user)
    if old_photo_key and old_photo_key != photo_key:
        try:
            c.delete_object(old_photo_key)
        except Exception:
            c.logger.warning("Failed to delete previous employee photo %s", old_photo_key, exc_info=True)
    return c.PhotoUploadResponse(photo_key=photo_key, photo_url=photo_url)


@router.put("/{user_id}", response_model=c.EmployeeCardPublic)
def update_employee(
    user_id: int,
    payload: c.EmployeeUpdateRequest,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
):
    db_user = (
        db.query(c.User)
        .options(
            c.joinedload(c.User.company),
            c.joinedload(c.User.role),
            c.joinedload(c.User.position).joinedload(c.Position.payment_format),
            c.joinedload(c.User.position).joinedload(c.Position.restaurant_subdivision),
            c.joinedload(c.User.restaurants),
        )
        .filter(c.User.id == user_id)
        .first()
    )
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    original_values = {
        "first_name": db_user.first_name,
        "last_name": db_user.last_name,
        "company": db_user.company,
        "position": db_user.position,
        "workplace": db_user.workplace_restaurant,
        "restaurants": list(db_user.restaurants or []),
        "rate": db_user.rate,
        "fired": db_user.fired,
    }
    original_position_id = getattr(db_user.position, "id", None)
    original_workplace_id = getattr(db_user.workplace_restaurant, "id", None)

    fields_set = getattr(payload, "model_fields_set", set())
    sync_only_allowed_fields = {
        "first_name",
        "last_name",
        "middle_name",
        "staff_code",
        "iiko_code",
        "workplace_restaurant_id",
        "add_to_iiko",
        "iiko_sync_restaurant_id",
        "iiko_department_restaurant_ids",
    }
    can_edit_employee = c._can_edit_user(db, current_user, db_user)
    if not can_edit_employee:
        if not payload.add_to_iiko:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient permissions to manage this employee",
            )
        c._ensure_can_sync_user_iiko(db, current_user, db_user)
        disallowed_sync_fields = {field for field in fields_set if field not in sync_only_allowed_fields}
        if disallowed_sync_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient permissions to edit employee fields",
            )

    rate_fields_requested = "rate" in fields_set or "individual_rate" in fields_set
    if rate_fields_requested and not c.has_permission(current_user, c.PermissionCode.STAFF_RATE_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient permissions to edit rate",
        )
    can_edit_rate = c.can_view_rate(current_user, db_user) and c.has_permission(
        current_user,
        c.PermissionCode.STAFF_RATE_MANAGE,
    )
    rate_was_provided = "rate" in fields_set and can_edit_rate
    individual_rate_was_provided = "individual_rate" in fields_set and can_edit_rate

    if (
        "role_id" in fields_set
        and "position_id" not in fields_set
        and db_user.position is None
        and not c.has_permission(current_user, c.PermissionCode.STAFF_ROLES_ASSIGN)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient permissions to edit role",
        )
    iiko_sync_restaurant_id = None
    if payload.iiko_sync_restaurant_id is not None:
        try:
            parsed_sync_restaurant_id = int(payload.iiko_sync_restaurant_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid iiko_sync_restaurant_id")
        if parsed_sync_restaurant_id > 0:
            iiko_sync_restaurant_id = parsed_sync_restaurant_id

    iiko_department_restaurant_ids = None
    if payload.iiko_department_restaurant_ids is not None:
        iiko_department_restaurant_ids = []
        seen_department_restaurant_ids = set()
        for raw_id in payload.iiko_department_restaurant_ids:
            try:
                parsed_id = int(raw_id)
            except Exception:
                continue
            if parsed_id <= 0 or parsed_id in seen_department_restaurant_ids:
                continue
            seen_department_restaurant_ids.add(parsed_id)
            iiko_department_restaurant_ids.append(parsed_id)

    if payload.add_to_iiko:
        c.ensure_permissions(
            current_user,
            c.PermissionCode.STAFF_EMPLOYEES_IIKO_SYNC,
            c.PermissionCode.IIKO_MANAGE,
        )
        c._validate_iiko_restaurant_scope(
            db,
            current_user,
            sync_restaurant_id=iiko_sync_restaurant_id,
            department_restaurant_ids=iiko_department_restaurant_ids,
        )

    if payload.first_name is not None:
        db_user.first_name = payload.first_name
    if payload.last_name is not None:
        db_user.last_name = payload.last_name
    if payload.middle_name is not None:
        db_user.middle_name = payload.middle_name
    if payload.gender is not None:
        db_user.gender = payload.gender
    if payload.staff_code is not None:
        db_user.staff_code = payload.staff_code
    if payload.iiko_code is not None:
        db_user.iiko_code = payload.iiko_code
    if payload.iiko_id is not None:
        if not c._can_edit_iiko_id(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient permissions to edit iiko_id",
            )
        db_user.iiko_id = (payload.iiko_id or "").strip() or None
    if payload.phone_number is not None:
        db_user.phone_number = (payload.phone_number or "").strip() or None
    if payload.email is not None:
        db_user.email = (payload.email or "").strip() or None
    if rate_was_provided:
        db_user.rate = payload.rate
    if "hire_date" in fields_set:
        db_user.hire_date = payload.hire_date
    if "fire_date" in fields_set:
        db_user.fire_date = payload.fire_date
    if payload.fired is not None:
        db_user.fired = payload.fired
    if "birth_date" in fields_set:
        db_user.birth_date = payload.birth_date
    if payload.photo_key is not None:
        db_user.photo_key = payload.photo_key
    if payload.is_cis_employee is not None:
        db_user.is_cis_employee = payload.is_cis_employee
    if payload.is_formalized is not None:
        db_user.is_formalized = payload.is_formalized
    if payload.confidential_data_consent is not None:
        db_user.confidential_data_consent = bool(payload.confidential_data_consent)
    if payload.password:
        db_user.hashed_password = c.hash_password(payload.password)

    if payload.company_id is not None:
        if payload.company_id:
            company = db.query(c.Company).filter(c.Company.id == payload.company_id).first()
            if not company:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
            db_user.company = company
        else:
            db_user.company = None

    if payload.position_id is not None:
        if payload.position_id:
            position = (
                db.query(c.Position)
                .options(c.joinedload(c.Position.payment_format))
                .filter(c.Position.id == payload.position_id)
                .first()
            )
            if not position:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
            db_user.position = position
            if not rate_was_provided:
                db_user.rate = position.rate
        else:
            db_user.position = None
            if not rate_was_provided:
                db_user.rate = None
            db_user.role = None

    if payload.role_id is not None and "position_id" not in fields_set and db_user.position is None:
        if payload.role_id:
            role = db.query(c.Role).filter(c.Role.id == payload.role_id).first()
            if not role:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
            db_user.role = role
        else:
            db_user.role = None

    if db_user.position is not None:
        db_user.role = db_user.position.role

    if individual_rate_was_provided:
        if payload.individual_rate is None:
            db_user.individual_rate = None
            if not rate_was_provided:
                position = db_user.position
                if position and position.rate is not None:
                    db_user.rate = position.rate
                else:
                    db_user.rate = None
        else:
            db_user.individual_rate = payload.individual_rate
            db_user.rate = payload.individual_rate

    if payload.workplace_restaurant_id is not None:
        if payload.workplace_restaurant_id:
            workplace_restaurant = (
                db.query(c.Restaurant)
                .filter(c.Restaurant.id == payload.workplace_restaurant_id)
                .first()
            )
            if not workplace_restaurant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
            db_user.workplace_restaurant = workplace_restaurant
        else:
            db_user.workplace_restaurant = None

    if payload.restaurant_ids is not None:
        if payload.restaurant_ids:
            restaurants = db.query(c.Restaurant).filter(c.Restaurant.id.in_(payload.restaurant_ids)).all()
            db_user.restaurants = restaurants
        else:
            if getattr(payload, "clear_restaurants", False):
                db_user.restaurants = []
            else:
                if db_user.restaurants:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="restaurant_ids is empty; set clear_restaurants=true to remove access",
                    )

    if "company_id" not in fields_set:
        inferred_company_id = None
        workplace_company_id = getattr(db_user.workplace_restaurant, "company_id", None)
        if workplace_company_id:
            inferred_company_id = workplace_company_id
        elif db_user.restaurants:
            company_ids = {
                getattr(item, "company_id", None)
                for item in (db_user.restaurants or [])
                if getattr(item, "company_id", None)
            }
            if len(company_ids) == 1:
                inferred_company_id = next(iter(company_ids))
        if inferred_company_id:
            company = db.query(c.Company).filter(c.Company.id == inferred_company_id).first()
            if company:
                db_user.company = company

    updated_position = db_user.position
    updated_workplace = db_user.workplace_restaurant
    updated_position_id = getattr(updated_position, "id", None)
    updated_workplace_id = getattr(updated_workplace, "id", None)
    position_changed = original_position_id != updated_position_id
    workplace_changed = original_workplace_id != updated_workplace_id
    rate_changed = c._normalize_rate_value(original_values["rate"]) != c._normalize_rate_value(db_user.rate)

    if payload.update_attendances:
        attendance_date_from = payload.attendance_date_from
        attendance_date_to = payload.attendance_date_to
        if attendance_date_from is None or attendance_date_to is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для обновления смен укажите диапазон дат",
            )
        if attendance_date_from > attendance_date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Дата начала периода не может быть позже даты окончания",
            )
        apply_employee_updates_to_attendances(
            db=db,
            user_id=db_user.id,
            date_from=attendance_date_from,
            date_to=attendance_date_to,
            position_changed=position_changed,
            restaurant_changed=workplace_changed,
            rate_changed=rate_changed,
            position=updated_position,
            restaurant=updated_workplace,
            rate=float(db_user.rate) if db_user.rate is not None else None,
        )

    new_row_id = c.build_employee_row_id(
        last_name=db_user.last_name,
        first_name=db_user.first_name,
        middle_name=db_user.middle_name,
        birth_date=db_user.birth_date,
    )
    if new_row_id != getattr(db_user, "employee_row_id", None):
        if new_row_id:
            conflict_id = (
                db.query(c.User.id)
                .filter(c.User.employee_row_id == new_row_id, c.User.id != db_user.id)
                .scalar()
            )
            if conflict_id:
                conflict_user = (
                    db.query(c.User)
                    .options(
                        c.joinedload(c.User.position),
                        c.joinedload(c.User.workplace_restaurant),
                    )
                    .filter(c.User.id == conflict_id)
                    .first()
                )
                detail = {"code": "employee_duplicate"}
                if conflict_user:
                    can_open_card = c._can_view_duplicate_employee(db, current_user, conflict_user)
                    detail["can_open_card"] = can_open_card
                    detail["employee"] = c._build_duplicate_employee_payload(
                        db,
                        conflict_user,
                        include_id=can_open_card,
                    )
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        db_user.employee_row_id = new_row_id

    changes = []
    if original_values["first_name"] != db_user.first_name:
        changes.append({"field": "first_name", "old_value": original_values["first_name"], "new_value": db_user.first_name})
    if original_values["last_name"] != db_user.last_name:
        changes.append({"field": "last_name", "old_value": original_values["last_name"], "new_value": db_user.last_name})
    if getattr(original_values["company"], "id", None) != getattr(db_user.company, "id", None):
        changes.append({"field": "company", "old_value": c.format_ref(original_values["company"]), "new_value": c.format_ref(db_user.company)})
    if getattr(original_values["position"], "id", None) != getattr(db_user.position, "id", None):
        changes.append({"field": "position", "old_value": c.format_ref(original_values["position"]), "new_value": c.format_ref(db_user.position)})
    if getattr(original_values["workplace"], "id", None) != getattr(db_user.workplace_restaurant, "id", None):
        changes.append({"field": "workplace_restaurant", "old_value": c.format_ref(original_values["workplace"]), "new_value": c.format_ref(db_user.workplace_restaurant)})
    if rate_changed:
        changes.append({"field": "rate", "old_value": original_values["rate"], "new_value": db_user.rate})
    original_restaurant_ids = {item.id for item in (original_values["restaurants"] or []) if item and item.id is not None}
    updated_restaurant_ids = {item.id for item in (db_user.restaurants or []) if item and item.id is not None}
    if original_restaurant_ids != updated_restaurant_ids:
        changes.append(
            {
                "field": "restaurants",
                "old_value": c._format_restaurant_refs(original_values["restaurants"]),
                "new_value": c._format_restaurant_refs(db_user.restaurants),
            }
        )
    if original_values["fired"] != db_user.fired:
        changes.append({"field": "fired", "old_value": original_values["fired"], "new_value": db_user.fired})

    c.log_employee_changes(
        db,
        user_id=db_user.id,
        changed_by_id=current_user.id,
        changes=changes,
    )

    db.commit()
    db.refresh(db_user)
    if payload.add_to_iiko:
        try:
            previous_iiko_code = (getattr(db_user, "iiko_code", None) or "").strip() or None
            previous_iiko_id = (getattr(db_user, "iiko_id", None) or "").strip() or None
            iiko_uid = c.add_user_to_iiko(
                db,
                db_user,
                sync_restaurant_id=iiko_sync_restaurant_id,
                department_restaurant_ids=iiko_department_restaurant_ids,
            )
            if iiko_uid:
                db_user.iiko_id = iiko_uid
            updated_iiko_code = (getattr(db_user, "iiko_code", None) or "").strip() or None
            updated_iiko_id = (getattr(db_user, "iiko_id", None) or "").strip() or None
            if updated_iiko_code != previous_iiko_code or updated_iiko_id != previous_iiko_id:
                db.commit()
                db.refresh(db_user)
            setattr(db_user, "iiko_sync_error", None)
        except c.IikoIntegrationError as exc:
            setattr(db_user, "iiko_sync_error", exc.detail)
            c.logger.warning("iiko sync failed for user %s: %s", db_user.id, exc.detail)
        except Exception as exc:
            setattr(db_user, "iiko_sync_error", f"Unexpected iiko error: {exc}")
            c.logger.exception("Failed to add user %s to iiko", db_user.id)
    return c._to_employee_card(db_user, current_user)


@router.delete("/{user_id}")
async def delete_employee(
    user_id: int,
    request: Request,
    delete_from_iiko: bool = Query(False),
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> dict[str, Any]:
    db_user = db.query(c.User).filter(c.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    c._ensure_can_edit_user(db, current_user, db_user)
    iiko_error = None
    if delete_from_iiko:
        try:
            c.fire_user_in_iiko(db, db_user)
        except c.IikoIntegrationError as exc:
            iiko_error = exc.detail
            c.logger.warning("iiko delete failed for user %s: %s", db_user.id, exc.detail)
        except Exception as exc:
            iiko_error = f"Unexpected iiko error: {exc}"
            c.logger.exception("Failed to delete user %s from iiko", db_user.id)
    try:
        payload = await request.json()
        comment = (payload or {}).get("comment") or ""
    except Exception:
        comment = ""
    comment = comment.strip()
    if not comment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Комментарий обязателен")

    if not db_user.fired:
        old_value = db_user.fired
        db_user.fired = True
        c.log_employee_changes(
            db,
            user_id=db_user.id,
            changed_by_id=current_user.id,
            changes=[
                {
                    "field": "fired",
                    "old_value": old_value,
                    "new_value": True,
                    "comment": comment,
                    "source": "delete_employee",
                }
            ],
        )
    db_user.fire_date = date.today()
    db.commit()
    return {"ok": True, "iiko_sync_error": iiko_error}


@router.post("/{user_id}/restore", response_model=c.EmployeeCardPublic)
async def restore_employee(
    user_id: int,
    request: Request,
    db: c.Session = Depends(c.get_db),
    current_user: c.User = Depends(c.get_current_user),
) -> c.EmployeeCardPublic:
    c.ensure_permissions(current_user, c.PermissionCode.STAFF_EMPLOYEES_RESTORE)
    db_user = db.query(c.User).filter(c.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    c._ensure_can_edit_user(db, current_user, db_user)

    try:
        payload = await request.json()
        comment = (payload or {}).get("comment") or ""
    except Exception:
        comment = ""
    comment = comment.strip()

    if db_user.fired:
        old_value = db_user.fired
        db_user.fired = False
        c.log_employee_changes(
            db,
            user_id=db_user.id,
            changed_by_id=current_user.id,
            changes=[
                {
                    "field": "fired",
                    "old_value": old_value,
                    "new_value": False,
                    "comment": comment,
                    "source": "restore_employee",
                }
            ],
        )
    if db_user.fire_date is not None:
        db_user.fire_date = None
    db.commit()
    db.refresh(db_user)
    return c._to_employee_card(db_user, current_user)
