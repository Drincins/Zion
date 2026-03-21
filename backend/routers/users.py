from datetime import date
from decimal import Decimal
from typing import Optional
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from backend.bd.database import get_db
from backend.bd.models import User, Restaurant, Role, Company, Position, EmployeeChangeEvent
from backend.utils import hash_password, get_current_user, get_user_restaurant_ids, users_share_restaurant
from backend.schemas import UserCreate, UserRead, RoleRead, UserUpdate
from backend.services.permissions import (
    PermissionCode,
    ensure_permissions,
    has_permission,
    require_permissions,
)
from backend.services.employee_codes import generate_unique_numeric_code
from backend.services.employee_identity import build_employee_row_id
from backend.services.employee_changes import log_employee_changes, format_ref
from backend.services.iiko_staff import add_user_to_iiko, IikoIntegrationError
from backend.services.s3 import generate_presigned_url


router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)


def _generate_unique_username(db: Session, base: str) -> str:
    """
    Build a unique username using the provided base (trimmed) and a numeric suffix when needed.
    Falls back to a random prefix if base is empty.
    """
    candidate = (base or "").strip() or f"user_{uuid.uuid4().hex[:8]}"
    unique_username = candidate
    suffix = 1
    while db.query(User.id).filter(User.username == unique_username).first():
        unique_username = f"{candidate}_{suffix}"
        suffix += 1
    return unique_username


def _normalize_rate_value(value):
    if value is None:
        return None
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01")))
    except Exception:
        return str(value)


def _format_restaurant_refs(restaurants):
    if not restaurants:
        return []
    return [format_ref(item) for item in restaurants if item]


def _get_duplicate_photo_url(user: User) -> Optional[str]:
    if not user.photo_key:
        return None
    try:
        return generate_presigned_url(user.photo_key)
    except Exception:
        logger.warning("Failed to build photo URL for duplicate employee %s", user.id, exc_info=True)
        return None


def _get_duplicate_fired_comment(db: Session, user: User) -> Optional[str]:
    if not user.fired:
        return None
    event = (
        db.query(EmployeeChangeEvent)
        .filter(
            EmployeeChangeEvent.user_id == user.id,
            EmployeeChangeEvent.field == "fired",
            EmployeeChangeEvent.new_value.in_(["True", "true", "1"]),
        )
        .order_by(EmployeeChangeEvent.created_at.desc(), EmployeeChangeEvent.id.desc())
        .first()
    )
    return event.comment if event else None


def _can_view_duplicate_employee(db: Session, viewer: User, target: User) -> bool:
    if viewer.id == target.id:
        return True
    if not users_share_restaurant(db, viewer, target.id):
        return False
    return any(
        has_permission(viewer, code)
        for code in (
            PermissionCode.STAFF_VIEW_SENSITIVE,
            PermissionCode.STAFF_EMPLOYEES_VIEW,
            PermissionCode.EMPLOYEES_CARD_VIEW,
            PermissionCode.STAFF_MANAGE_ALL,
            PermissionCode.STAFF_MANAGE_SUBORDINATES,
            PermissionCode.USERS_VIEW,
            PermissionCode.USERS_MANAGE,
        )
    )


def _build_duplicate_employee_payload(db: Session, user: User, *, include_id: bool) -> dict:
    position_name = user.position.name if user.position else None
    workplace_name = user.workplace_restaurant.name if user.workplace_restaurant else None
    payload = {
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "middle_name": user.middle_name or "",
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "hire_date": user.hire_date.isoformat() if user.hire_date else None,
        "fire_date": user.fire_date.isoformat() if user.fire_date else None,
        "position": position_name,
        "workplace": workplace_name,
        "fired": bool(user.fired),
        "fired_comment": _get_duplicate_fired_comment(db, user),
        "photo_url": _get_duplicate_photo_url(user),
    }
    if include_id:
        payload["id"] = user.id
    return payload


@router.get("/", response_model=list[UserRead])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions(
            PermissionCode.USERS_VIEW,
            PermissionCode.STAFF_VIEW_SENSITIVE,
            PermissionCode.STAFF_MANAGE_ALL,
        )
    ),
):
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    query = db.query(User).options(
        selectinload(User.role),
        selectinload(User.company),
        selectinload(User.position).selectinload(Position.payment_format),
        selectinload(User.position).selectinload(Position.restaurant_subdivision),
        selectinload(User.restaurants)
    )
    query = query.outerjoin(User.restaurants)

    if allowed_restaurants is None:
        return query.distinct().all()
    if not allowed_restaurants:
        query = query.filter(User.id == current_user.id)
    else:
        query = query.filter(
            or_(
                User.id == current_user.id,
                Restaurant.id.in_(allowed_restaurants),
            )
        )
    return query.distinct().all()

@router.get("/roles", response_model=list[RoleRead])
def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions(PermissionCode.ROLES_MANAGE, PermissionCode.STAFF_ROLES_ASSIGN)
    ),
):
    _ = current_user
    roles = db.query(Role).order_by(Role.name).all()
    return roles

@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        ensure_permissions(
            current_user,
            PermissionCode.USERS_VIEW,
            PermissionCode.STAFF_VIEW_SENSITIVE,
            PermissionCode.STAFF_MANAGE_ALL,
        )
    user = db.query(User).options(
        selectinload(User.role),
        selectinload(User.company),
        selectinload(User.position).selectinload(Position.payment_format),
        selectinload(User.position).selectinload(Position.restaurant_subdivision),
        selectinload(User.restaurants)
    ).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if current_user.id != user_id:
        if not users_share_restaurant(db, current_user, user_id):
            raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")
    return user

@router.post("/", response_model=UserRead)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions(
            PermissionCode.USERS_MANAGE,
            PermissionCode.STAFF_MANAGE_ALL,
        )
    ),
):
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    requested_restaurants = set(user.restaurant_ids or [])
    if allowed_restaurants is not None:
        if not allowed_restaurants and requested_restaurants:
            raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")
        invalid = requested_restaurants.difference(allowed_restaurants)
        if invalid:
            raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")

    first_name = (user.first_name or "").strip()
    last_name = (user.last_name or "").strip()
    middle_name = (user.middle_name or "").strip() or None
    phone_number = (user.phone_number or "").strip() or None
    photo_key = (user.photo_key or "").strip() or None
    staff_code_input = (user.staff_code or "").strip() or None
    if not first_name or not last_name or not user.birth_date:
        raise HTTPException(status_code=400, detail="first_name, last_name and birth_date are required")

    row_id = build_employee_row_id(
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name,
        birth_date=user.birth_date,
    )
    if row_id:
        normalized_first = first_name.lower()
        normalized_last = last_name.lower()
        conflict_query = (
            db.query(User)
            .options(
                selectinload(User.position),
                selectinload(User.workplace_restaurant),
            )
            .filter(
                or_(
                    User.employee_row_id == row_id,
                    and_(
                        User.birth_date == user.birth_date,
                        func.lower(func.coalesce(User.first_name, "")) == normalized_first,
                        func.lower(func.coalesce(User.last_name, "")) == normalized_last,
                    ),
                )
            )
        )
        conflict_user = conflict_query.first()
        if conflict_user:
            can_open_card = _can_view_duplicate_employee(db, current_user, conflict_user)
            detail = {
                "code": "employee_duplicate",
                "can_open_card": can_open_card,
                "employee": _build_duplicate_employee_payload(db, conflict_user, include_id=can_open_card),
            }
            raise HTTPException(status_code=409, detail=detail)

    if user.role_id is not None and user.position_id is None and not has_permission(
        current_user, PermissionCode.STAFF_ROLES_ASSIGN
    ):
        raise HTTPException(status_code=403, detail="Access denied: insufficient permissions to edit role")
    if (user.individual_rate is not None or user.rate is not None) and not has_permission(
        current_user, PermissionCode.STAFF_RATE_MANAGE
    ):
        raise HTTPException(status_code=403, detail="Access denied: insufficient permissions to edit rate")

    iiko_sync_restaurant_id = None
    if user.iiko_sync_restaurant_id is not None:
        try:
            parsed_sync_restaurant_id = int(user.iiko_sync_restaurant_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid iiko_sync_restaurant_id")
        if parsed_sync_restaurant_id > 0:
            iiko_sync_restaurant_id = parsed_sync_restaurant_id

    iiko_department_restaurant_ids = None
    if user.iiko_department_restaurant_ids is not None:
        iiko_department_restaurant_ids = []
        seen_department_restaurant_ids = set()
        for raw_id in user.iiko_department_restaurant_ids:
            try:
                parsed_id = int(raw_id)
            except Exception:
                continue
            if parsed_id <= 0 or parsed_id in seen_department_restaurant_ids:
                continue
            seen_department_restaurant_ids.add(parsed_id)
            iiko_department_restaurant_ids.append(parsed_id)

    if user.add_to_iiko:
        ensure_permissions(
            current_user,
            PermissionCode.STAFF_EMPLOYEES_IIKO_SYNC,
            PermissionCode.IIKO_MANAGE,
        )
        if allowed_restaurants is not None:
            requested_iiko_restaurants = set(iiko_department_restaurant_ids or [])
            if iiko_sync_restaurant_id:
                requested_iiko_restaurants.add(iiko_sync_restaurant_id)
            invalid_iiko_restaurants = requested_iiko_restaurants.difference(allowed_restaurants)
            if invalid_iiko_restaurants:
                raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")

    role: Role | None = None
    position: Position | None = None
    if user.position_id:
        position = db.query(Position).filter(Position.id == user.position_id).first()
        if position:
            role = position.role
    elif user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()

    role_norm = (role.name or "").strip().lower().replace(" ", "") if role else ""
    is_time_control = bool(role and (role.id == 10 or role_norm in {"таймконтроль", "тайм-контроль", "timecontrol", "time_control"}))

    requested_iiko_code = (user.iiko_code or "").strip() or None
    if requested_iiko_code:
        if db.query(User.id).filter(User.iiko_code == requested_iiko_code).first():
            raise HTTPException(status_code=409, detail="iiko_code already exists")
        resolved_iiko_code = requested_iiko_code
    else:
        try:
            resolved_iiko_code = generate_unique_numeric_code(db, "iiko_code", max_width=6)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if staff_code_input:
        if db.query(User.id).filter(User.staff_code == staff_code_input).first():
            raise HTTPException(status_code=409, detail="staff_code already exists")
        staff_code = staff_code_input
    else:
        try:
            staff_code = generate_unique_numeric_code(db, "staff_code", max_width=5)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if is_time_control:
        base_username = (user.username or resolved_iiko_code or f"timecontrol_{uuid.uuid4().hex[:8]}").strip()
        username = _generate_unique_username(db, base_username or f"timecontrol_{uuid.uuid4().hex[:8]}")
        raw_password = user.password or uuid.uuid4().hex
    else:
        provided_username = (user.username or "").strip()
        provided_password_raw = user.password or ""
        provided_password = provided_password_raw.strip()
        if provided_username or provided_password:
            if not provided_username or not provided_password:
                raise HTTPException(status_code=400, detail="username and password must be provided together")
            if db.query(User.id).filter(User.username == provided_username).first():
                raise HTTPException(status_code=409, detail="User with this username already exists")
            username = provided_username
            raw_password = provided_password
        else:
            username = _generate_unique_username(db, resolved_iiko_code or f"user_{uuid.uuid4().hex[:8]}")
            raw_password = uuid.uuid4().hex

    db_user = User(
        username=username,
        hashed_password=hash_password(raw_password),
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        email=(user.email or "").strip() or None,
        iiko_code=resolved_iiko_code,
        staff_code=staff_code,
        phone_number=phone_number,
        gender=user.gender,
        is_cis_employee=user.is_cis_employee,
        is_formalized=user.is_formalized,
        confidential_data_consent=bool(user.confidential_data_consent) if user.confidential_data_consent is not None else False,
        hire_date=user.hire_date or date.today(),
        fire_date=user.fire_date,
        fired=bool(user.fired) if user.fired is not None else False,
        birth_date=user.birth_date,
        photo_key=photo_key,
    )
    if row_id:
        db_user.employee_row_id = row_id
    if user.has_full_restaurant_access:
        if allowed_restaurants is not None:
            raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")
        db_user.has_full_restaurant_access = True

    # Role
    if role:
        db_user.role = role

    # Company
    if user.company_id:
        company = db.query(Company).filter(Company.id == user.company_id).first()
        if company:
            db_user.company = company

    # Position
    if position is None and user.position_id:
        position = db.query(Position).filter(Position.id == user.position_id).first()
    if position:
        db_user.position = position
        db_user.rate = position.rate

    if user.rate is not None:
        db_user.rate = user.rate
    if user.individual_rate is not None:
        db_user.individual_rate = user.individual_rate
        db_user.rate = user.individual_rate

    if db_user.fired and db_user.fire_date is None:
        db_user.fire_date = date.today()

    # Workplace restaurant
    if user.workplace_restaurant_id is not None:
        if user.workplace_restaurant_id:
            if allowed_restaurants is not None and user.workplace_restaurant_id not in allowed_restaurants:
                raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")
            workplace_restaurant = (
                db.query(Restaurant)
                .filter(Restaurant.id == user.workplace_restaurant_id)
                .first()
            )
            if not workplace_restaurant:
                raise HTTPException(status_code=404, detail="Restaurant not found")
            db_user.workplace_restaurant = workplace_restaurant
        else:
            db_user.workplace_restaurant = None

    # Restaurants
    if user.restaurant_ids:
        restaurant_ids = list(requested_restaurants)
        db_user.restaurants = db.query(Restaurant).filter(Restaurant.id.in_(restaurant_ids)).all()
    elif (not user.has_full_restaurant_access) and db_user.workplace_restaurant:
        # Default access to the workplace restaurant when no explicit scope is provided.
        db_user.restaurants = [db_user.workplace_restaurant]

    if user.company_id is None and db_user.company is None:
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
            company = db.query(Company).filter(Company.id == inferred_company_id).first()
            if company:
                db_user.company = company

    db.add(db_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="???????????? ? ????? ??????? ??? ??????????.",
        ) from exc
    db.refresh(db_user)

    iiko_error = None
    if user.add_to_iiko:
        try:
            previous_iiko_code = (getattr(db_user, "iiko_code", None) or "").strip() or None
            previous_iiko_id = (getattr(db_user, "iiko_id", None) or "").strip() or None
            iiko_uid = add_user_to_iiko(
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
        except IikoIntegrationError as exc:
            iiko_error = exc.detail
            logger.warning("iiko sync failed for user %s: %s", db_user.id, exc.detail)
        except Exception as exc:
            iiko_error = f"Unexpected iiko error: {exc}"
            logger.exception("Failed to add user %s to iiko", db_user.id)

    setattr(db_user, "iiko_sync_error", iiko_error)
    return db_user

@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions(
            PermissionCode.USERS_MANAGE,
            PermissionCode.STAFF_MANAGE_ALL,
        )
    ),
):
    allowed_restaurants = get_user_restaurant_ids(db, current_user)
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(404, "User not found")
    if current_user.id != user_id and not users_share_restaurant(db, current_user, user_id):
        raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")
    original_values = {
        "first_name": db_user.first_name,
        "last_name": db_user.last_name,
        "company": db_user.company,
        "position": db_user.position,
        "workplace": db_user.workplace_restaurant,
        "restaurants": list(db_user.restaurants or []),
        "rate": db_user.rate,
        "fired": db_user.fired,
        "has_full_restaurant_access": db_user.has_full_restaurant_access,
    }
    fields_set = getattr(user, "model_fields_set", set())

    if (
        "role_id" in fields_set
        and user.position_id is None
        and db_user.position is None
        and not has_permission(current_user, PermissionCode.STAFF_ROLES_ASSIGN)
    ):
        raise HTTPException(status_code=403, detail="Access denied: insufficient permissions to edit role")
    if "individual_rate" in fields_set and not has_permission(
        current_user, PermissionCode.STAFF_RATE_MANAGE
    ):
        raise HTTPException(status_code=403, detail="Access denied: insufficient permissions to edit rate")

    if user.first_name is not None:
        db_user.first_name = user.first_name
    if user.last_name is not None:
        db_user.last_name = user.last_name
    if "username" in fields_set:
        new_username = (user.username or "").strip()
        if not new_username:
            raise HTTPException(status_code=400, detail="username cannot be empty")
        if new_username != db_user.username and db.query(User.id).filter(
            User.username == new_username, User.id != db_user.id
        ).first():
            raise HTTPException(status_code=409, detail="User with this username already exists")
        db_user.username = new_username
    if user.iiko_code is not None:
        db_user.iiko_code = user.iiko_code
    if user.gender is not None:
        db_user.gender = user.gender
    if "email" in fields_set:
        db_user.email = (user.email or "").strip() or None
    if user.is_cis_employee is not None:
        db_user.is_cis_employee = user.is_cis_employee
    if user.fired is not None:
        db_user.fired = user.fired
    if user.is_formalized is not None:
        db_user.is_formalized = user.is_formalized
    if user.password:
        db_user.hashed_password = hash_password(user.password)

    if "role_id" in fields_set and user.position_id is None and db_user.position is None:
        if user.role_id:
            role = db.query(Role).filter(Role.id == user.role_id).first()
            if role:
                db_user.role = role
        else:
            db_user.role = None

    if user.company_id is not None:
        company = db.query(Company).filter(Company.id == user.company_id).first()
        if company:
            db_user.company = company

    if user.position_id is not None:
        if user.position_id:
            position = db.query(Position).filter(Position.id == user.position_id).first()
            if position:
                db_user.position = position
                db_user.rate = position.rate
        else:
            db_user.position = None
            db_user.rate = None
            db_user.role = None

    if "individual_rate" in fields_set:
        if user.individual_rate is None:
            db_user.individual_rate = None
            position = db_user.position
            if position and position.rate is not None:
                db_user.rate = position.rate
        else:
            db_user.individual_rate = user.individual_rate
            db_user.rate = user.individual_rate

    if db_user.position is not None:
        db_user.role = db_user.position.role

    if user.workplace_restaurant_id is not None:
        if user.workplace_restaurant_id:
            if allowed_restaurants is not None and user.workplace_restaurant_id not in allowed_restaurants:
                raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")
            workplace_restaurant = (
                db.query(Restaurant)
                .filter(Restaurant.id == user.workplace_restaurant_id)
                .first()
            )
            if not workplace_restaurant:
                raise HTTPException(status_code=404, detail="Restaurant not found")
            db_user.workplace_restaurant = workplace_restaurant
        else:
            db_user.workplace_restaurant = None

    if user.restaurant_ids is not None:
        requested_list = list(user.restaurant_ids or [])
        if not requested_list:
            if getattr(user, "clear_restaurants", False):
                db_user.restaurants = []
            else:
                if db_user.restaurants:
                    raise HTTPException(
                        status_code=400,
                        detail="restaurant_ids is empty; set clear_restaurants=true to remove access",
                    )
        else:
            requested = set(requested_list)
            if allowed_restaurants is not None:
                if not allowed_restaurants and requested:
                    raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")
                invalid = requested.difference(allowed_restaurants)
                if invalid:
                    raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")
            db_user.restaurants = db.query(Restaurant).filter(
                Restaurant.id.in_(list(requested))
            ).all()
    if user.has_full_restaurant_access is not None:
        if user.has_full_restaurant_access:
            if allowed_restaurants is not None:
                raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")
            db_user.has_full_restaurant_access = True
        else:
            db_user.has_full_restaurant_access = False

    new_row_id = build_employee_row_id(
        last_name=db_user.last_name,
        first_name=db_user.first_name,
        middle_name=db_user.middle_name,
        birth_date=db_user.birth_date,
    )
    if new_row_id != getattr(db_user, "employee_row_id", None):
        if new_row_id:
            conflict_id = (
                db.query(User.id)
                .filter(User.employee_row_id == new_row_id, User.id != db_user.id)
                .scalar()
            )
            if conflict_id:
                conflict_user = (
                    db.query(User)
                    .options(
                        selectinload(User.position),
                        selectinload(User.workplace_restaurant),
                    )
                    .filter(User.id == conflict_id)
                    .first()
                )
                detail = {"code": "employee_duplicate"}
                if conflict_user:
                    can_open_card = _can_view_duplicate_employee(db, current_user, conflict_user)
                    detail["can_open_card"] = can_open_card
                    detail["employee"] = _build_duplicate_employee_payload(
                        db,
                        conflict_user,
                        include_id=can_open_card,
                    )
                raise HTTPException(status_code=409, detail=detail)
        db_user.employee_row_id = new_row_id

    changes = []
    if original_values["first_name"] != db_user.first_name:
        changes.append(
            {
                "field": "first_name",
                "old_value": original_values["first_name"],
                "new_value": db_user.first_name,
            }
        )
    if original_values["last_name"] != db_user.last_name:
        changes.append(
            {
                "field": "last_name",
                "old_value": original_values["last_name"],
                "new_value": db_user.last_name,
            }
        )
    if getattr(original_values["company"], "id", None) != getattr(db_user.company, "id", None):
        changes.append(
            {
                "field": "company",
                "old_value": format_ref(original_values["company"]),
                "new_value": format_ref(db_user.company),
            }
        )
    if getattr(original_values["position"], "id", None) != getattr(db_user.position, "id", None):
        changes.append(
            {
                "field": "position",
                "old_value": format_ref(original_values["position"]),
                "new_value": format_ref(db_user.position),
            }
        )
    if getattr(original_values["workplace"], "id", None) != getattr(db_user.workplace_restaurant, "id", None):
        changes.append(
            {
                "field": "workplace_restaurant",
                "old_value": format_ref(original_values["workplace"]),
                "new_value": format_ref(db_user.workplace_restaurant),
            }
        )
    if _normalize_rate_value(original_values["rate"]) != _normalize_rate_value(db_user.rate):
        changes.append(
            {
                "field": "rate",
                "old_value": original_values["rate"],
                "new_value": db_user.rate,
            }
        )
    original_restaurant_ids = {
        item.id for item in (original_values["restaurants"] or []) if item and item.id is not None
    }
    updated_restaurant_ids = {
        item.id for item in (db_user.restaurants or []) if item and item.id is not None
    }
    if original_restaurant_ids != updated_restaurant_ids:
        changes.append(
            {
                "field": "restaurants",
                "old_value": _format_restaurant_refs(original_values["restaurants"]),
                "new_value": _format_restaurant_refs(db_user.restaurants),
            }
        )
    if (
        original_values["has_full_restaurant_access"]
        != db_user.has_full_restaurant_access
    ):
        changes.append(
            {
                "field": "has_full_restaurant_access",
                "old_value": original_values["has_full_restaurant_access"],
                "new_value": db_user.has_full_restaurant_access,
            }
        )
    if original_values["fired"] != db_user.fired:
        changes.append(
            {
                "field": "fired",
                "old_value": original_values["fired"],
                "new_value": db_user.fired,
            }
        )

    log_employee_changes(
        db,
        user_id=db_user.id,
        changed_by_id=current_user.id,
        changes=changes,
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Пользователь с такими данными уже существует.",
        ) from exc
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    request: "Request",
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions(
            PermissionCode.USERS_MANAGE,
            PermissionCode.STAFF_MANAGE_ALL,
        )
    ),
):
    """
    Soft-delete: ставим fired=True, логируем комментарий из тела запроса.
    Тело: { "comment": "..." } (необязательно)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if current_user.id != user_id and not users_share_restaurant(db, current_user, user_id):
        raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")

    try:
        payload = await request.json()
        comment = (payload or {}).get("comment") or ""
    except Exception:
        comment = ""
    comment = comment.strip()

    if not user.fired:
        if not comment:
            raise HTTPException(status_code=400, detail="Комментарий обязателен")
        old_value = user.fired
        user.fired = True
        log_employee_changes(
            db,
            user_id=user.id,
            changed_by_id=current_user.id,
            changes=[
                {
                    "field": "fired",
                    "old_value": old_value,
                    "new_value": True,
                    "comment": comment,
                    "source": "delete_user",
                }
            ],
        )

    user.fire_date = date.today()
    db.commit()
    db.refresh(user)
    return {"ok": True}


@router.post("/{user_id}/restore", response_model=UserRead)
async def restore_user(
    user_id: int,
    request: "Request",
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions(
            PermissionCode.STAFF_EMPLOYEES_RESTORE,
        )
    ),
):
    """Восстановление: fired=False, логируем комментарий."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if current_user.id != user_id and not users_share_restaurant(db, current_user, user_id):
        raise HTTPException(status_code=403, detail="Access to the selected restaurants is not allowed")

    try:
        payload = await request.json()
        comment = (payload or {}).get("comment") or ""
    except Exception:
        comment = ""

    if user.fired:
        old_value = user.fired
        user.fired = False
        log_employee_changes(
            db,
            user_id=user.id,
            changed_by_id=current_user.id,
            changes=[
                {
                    "field": "fired",
                    "old_value": old_value,
                    "new_value": False,
                    "comment": comment,
                    "source": "restore_user",
                }
            ],
        )
    if user.fire_date is not None:
        user.fire_date = None
    db.commit()
    db.refresh(user)
    return user
