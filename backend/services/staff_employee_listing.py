from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, load_only, noload, selectinload

from backend.bd.models import Company, Position, Restaurant, RestaurantSubdivision, Role, User
from backend.schemas import (
    CompanyRead,
    PositionHierarchyNode,
    RestaurantRead,
    RoleRead,
    StaffEmployeesReferencePayload,
    StaffUserListPublic,
    StaffUserPublic,
)
from backend.services.permissions import PermissionCode, can_view_rate, ensure_permissions, has_permission
from backend.services.reference_cache import cached_reference_data
from backend.utils import get_user_restaurant_ids

_RATE_FULL_ACCESS_LEVEL = 5
STAFF_REFERENCES_CACHE_SCOPE = "staff_employees:references"
STAFF_REFERENCES_CACHE_TTL_SECONDS = 45


def ensure_staff_view(user: User) -> None:
    ensure_permissions(
        user,
        PermissionCode.STAFF_VIEW_SENSITIVE,
        PermissionCode.STAFF_MANAGE_SUBORDINATES,
        PermissionCode.STAFF_MANAGE_ALL,
        PermissionCode.STAFF_EMPLOYEES_VIEW,
        PermissionCode.EMPLOYEES_CARD_VIEW,
    )


def role_level_for_rate(user: Optional[User]) -> Optional[int]:
    if not user:
        return None
    role = getattr(user, "role", None)
    if role is None:
        role = getattr(getattr(user, "position", None), "role", None)
    if role is None or getattr(role, "level", None) is None:
        return None
    try:
        return int(role.level)
    except Exception:
        return None


def get_allowed_workplace_ids(db: Session, viewer: User) -> Optional[set[int]]:
    allowed_restaurants = get_user_restaurant_ids(db, viewer)
    if allowed_restaurants is None:
        return None
    allowed_workplaces = set(allowed_restaurants)
    if getattr(viewer, "workplace_restaurant_id", None):
        allowed_workplaces.add(viewer.workplace_restaurant_id)
    return allowed_workplaces


def to_staff_public(
    user: User,
    viewer: Optional[User] = None,
    can_see_rate_override: Optional[bool] = None,
) -> StaffUserPublic:
    if can_see_rate_override is not None:
        can_see_rate = bool(can_see_rate_override)
    else:
        can_see_rate = can_view_rate(viewer, user) if viewer else True
    restaurants = [
        {
            "id": r.id,
            "name": (r.name or f"Restaurant #{r.id}"),
            "department_code": getattr(r, "department_code", None),
        }
        for r in (user.restaurants or [])
        if r and r.id is not None
    ]
    restaurant_department_codes = [
        r.department_code for r in (user.restaurants or []) if getattr(r, "department_code", None)
    ]
    subdivision_id = getattr(getattr(user, "position", None), "restaurant_subdivision_id", None)
    subdivision_name = getattr(getattr(getattr(user, "position", None), "restaurant_subdivision", None), "name", None)
    subdivision_is_multi = bool(
        getattr(getattr(getattr(user, "position", None), "restaurant_subdivision", None), "is_multi", False)
    )
    return StaffUserPublic(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        iiko_id=user.iiko_id,
        iiko_code=user.iiko_code,
        staff_code=user.staff_code,
        phone_number=user.phone_number,
        email=user.email,
        company_id=user.company.id if user.company else None,
        company_name=user.company.name if user.company else None,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        position_id=user.position_id,
        position_name=user.position.name if user.position else None,
        position_code=user.position.code if getattr(user, "position", None) else None,
        gender=user.gender,
        rate=float(user.rate) if can_see_rate and user.rate is not None else None,
        position_rate=float(user.position.rate)
        if can_see_rate and getattr(user, "position", None) and user.position.rate is not None
        else None,
        hire_date=user.hire_date,
        fire_date=user.fire_date,
        birth_date=user.birth_date,
        photo_key=user.photo_key,
        fired=bool(user.fired),
        is_formalized=bool(getattr(user, "is_formalized", False)),
        is_cis_employee=bool(getattr(user, "is_cis_employee", False)),
        confidential_data_consent=bool(getattr(user, "confidential_data_consent", False)),
        restaurants=restaurants,
        restaurant_ids=[item["id"] for item in restaurants],
        restaurant_department_codes=restaurant_department_codes,
        workplace_restaurant_id=getattr(user, "workplace_restaurant_id", None),
        individual_rate=float(user.individual_rate) if can_see_rate and user.individual_rate is not None else None,
        has_full_restaurant_access=bool(getattr(user, "has_full_restaurant_access", False)),
        rate_hidden=not can_see_rate,
        has_fingerprint=bool(getattr(user, "has_fingerprint", False)),
        restaurant_subdivision_id=subdivision_id,
        restaurant_subdivision_name=subdivision_name,
        restaurant_subdivision_is_multi=subdivision_is_multi,
    )


def to_staff_list_public(
    user: User,
    viewer: Optional[User] = None,
    can_see_rate_override: Optional[bool] = None,
) -> StaffUserListPublic:
    if can_see_rate_override is not None:
        can_see_rate = bool(can_see_rate_override)
    else:
        can_see_rate = can_view_rate(viewer, user) if viewer else True
    restaurants = [
        {
            "id": r.id,
            "name": (r.name or f"Restaurant #{r.id}"),
        }
        for r in (user.restaurants or [])
        if r and r.id is not None
    ]
    return StaffUserListPublic(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        iiko_id=user.iiko_id,
        iiko_code=user.iiko_code,
        staff_code=user.staff_code,
        phone_number=user.phone_number,
        company_name=user.company.name if user.company else None,
        role_id=user.role_id,
        position_id=user.position_id,
        position_name=user.position.name if user.position else None,
        position_code=user.position.code if getattr(user, "position", None) else None,
        gender=user.gender,
        hire_date=user.hire_date,
        fire_date=user.fire_date,
        birth_date=user.birth_date,
        fired=bool(user.fired),
        is_formalized=bool(getattr(user, "is_formalized", False)),
        is_cis_employee=bool(getattr(user, "is_cis_employee", False)),
        restaurants=restaurants,
        restaurant_ids=[item["id"] for item in restaurants],
        workplace_restaurant_id=getattr(user, "workplace_restaurant_id", None),
        rate_hidden=not can_see_rate,
    )


def ids_scope_key(values: Optional[set[int]]) -> tuple:
    if values is None:
        return ("all",)
    if not values:
        return ("none",)
    return tuple(sorted(int(value) for value in values))


def _can_load_restaurant_references(user: User) -> bool:
    return any(
        has_permission(user, code)
        for code in (
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.RESTAURANTS_VIEW,
            PermissionCode.RESTAURANTS_MANAGE,
            PermissionCode.RESTAURANTS_SETTINGS_VIEW,
            PermissionCode.RESTAURANTS_SETTINGS_MANAGE,
            PermissionCode.STAFF_PORTAL_ACCESS,
        )
    )


def _can_load_company_references(user: User) -> bool:
    return any(
        has_permission(user, code)
        for code in (
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.COMPANIES_VIEW,
            PermissionCode.COMPANIES_MANAGE,
        )
    )


def _can_load_role_references(user: User) -> bool:
    return any(
        has_permission(user, code)
        for code in (
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.ROLES_MANAGE,
            PermissionCode.STAFF_ROLES_ASSIGN,
        )
    )


def _can_load_position_references(user: User) -> bool:
    return any(
        has_permission(user, code)
        for code in (
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.POSITIONS_MANAGE,
            PermissionCode.POSITIONS_EDIT,
            PermissionCode.POSITIONS_RATE_MANAGE,
        )
    )


def _position_hierarchy_payload(position: Position) -> PositionHierarchyNode:
    return PositionHierarchyNode(
        id=position.id,
        name=position.name,
        code=position.code,
        role_id=position.role_id,
        role_name=position.role.name if position.role else None,
        parent_id=position.parent_id,
        hierarchy_level=position.hierarchy_level,
        rate=position.rate,
        payment_format_id=position.payment_format_id,
        payment_format_name=position.payment_format.name if position.payment_format else None,
        hours_per_shift=position.hours_per_shift,
        monthly_shift_norm=position.monthly_shift_norm,
        restaurant_subdivision_id=position.restaurant_subdivision_id,
        restaurant_subdivision_name=position.restaurant_subdivision.name if position.restaurant_subdivision else None,
        night_bonus_enabled=bool(getattr(position, "night_bonus_enabled", False)),
        night_bonus_percent=getattr(position, "night_bonus_percent", None),
    )


def load_staff_references(
    db: Session,
    current_user: User,
    *,
    include_restaurants: bool = True,
    include_companies: bool = True,
    include_roles: bool = True,
    include_positions: bool = True,
) -> StaffEmployeesReferencePayload:
    can_load_restaurants = include_restaurants and _can_load_restaurant_references(current_user)
    can_load_companies = include_companies and _can_load_company_references(current_user)
    can_load_roles = include_roles and _can_load_role_references(current_user)
    can_load_positions = include_positions and _can_load_position_references(current_user)
    allowed_restaurants = get_user_restaurant_ids(db, current_user) if can_load_restaurants else None

    cache_key = (
        int(current_user.id),
        bool(can_load_restaurants),
        bool(can_load_companies),
        bool(can_load_roles),
        bool(can_load_positions),
        bool(include_restaurants),
        bool(include_companies),
        bool(include_roles),
        bool(include_positions),
        ids_scope_key(allowed_restaurants) if can_load_restaurants else ("skip",),
    )

    def _load_references() -> dict:
        restaurants_payload: list[RestaurantRead] = []
        companies_payload: list[CompanyRead] = []
        roles_payload: list[RoleRead] = []
        positions_payload: list[PositionHierarchyNode] = []

        if can_load_restaurants:
            restaurants_query = db.query(Restaurant)
            if allowed_restaurants is not None:
                if allowed_restaurants:
                    restaurants_query = restaurants_query.filter(Restaurant.id.in_(allowed_restaurants))
                else:
                    restaurants_query = restaurants_query.filter(False)
            restaurants = restaurants_query.order_by(Restaurant.id.asc()).all()
            restaurants_payload = [RestaurantRead.model_validate(item) for item in restaurants]

        if can_load_companies:
            companies = db.query(Company).order_by(Company.id.asc()).all()
            companies_payload = [CompanyRead.model_validate(item) for item in companies]

        if can_load_roles:
            roles = db.query(Role).order_by(func.lower(Role.name).nullslast(), Role.id.asc()).all()
            roles_payload = [RoleRead.model_validate(item) for item in roles]

        if can_load_positions:
            positions = (
                db.query(Position)
                .options(
                    joinedload(Position.role).load_only(Role.id, Role.name),
                    joinedload(Position.payment_format),
                    joinedload(Position.restaurant_subdivision).load_only(
                        RestaurantSubdivision.id,
                        RestaurantSubdivision.name,
                    ),
                )
                .order_by(Position.hierarchy_level.asc(), func.lower(Position.name).nullslast(), Position.id.asc())
                .all()
            )
            positions_payload = [_position_hierarchy_payload(item) for item in positions]

        return StaffEmployeesReferencePayload(
            restaurants=restaurants_payload,
            companies=companies_payload,
            roles=roles_payload,
            positions=positions_payload,
        ).model_dump(mode="json")

    payload = cached_reference_data(
        STAFF_REFERENCES_CACHE_SCOPE,
        cache_key,
        _load_references,
        ttl_seconds=STAFF_REFERENCES_CACHE_TTL_SECONDS,
    )
    return StaffEmployeesReferencePayload.model_validate(payload)


def _staff_employee_search_expr():
    return func.lower(
        func.coalesce(User.username, "")
        + " "
        + func.coalesce(User.first_name, "")
        + " "
        + func.coalesce(User.last_name, "")
        + " "
        + func.coalesce(User.middle_name, "")
        + " "
        + func.coalesce(User.staff_code, "")
        + " "
        + func.coalesce(User.phone_number, "")
    )


def _apply_order_direction(expression, direction: str):
    if (direction or "asc").lower() == "desc":
        return expression.desc().nullslast()
    return expression.asc().nullslast()


def _apply_staff_employee_sort(query, sort_by: Optional[str], sort_direction: str):
    normalized_sort = (sort_by or "").strip().lower()
    direction = (sort_direction or "asc").lower()
    order_clauses = []

    if normalized_sort == "staff_code":
        order_clauses.append(_apply_order_direction(func.lower(func.coalesce(User.staff_code, "")), direction))
    elif normalized_sort == "full_name":
        order_clauses.extend(
            [
                _apply_order_direction(func.lower(func.coalesce(User.last_name, "")), direction),
                _apply_order_direction(func.lower(func.coalesce(User.first_name, "")), direction),
                _apply_order_direction(func.lower(func.coalesce(User.middle_name, "")), direction),
            ]
        )
    elif normalized_sort == "phone_number":
        order_clauses.append(_apply_order_direction(func.lower(func.coalesce(User.phone_number, "")), direction))
    elif normalized_sort == "company_name":
        query = query.outerjoin(User.company)
        order_clauses.append(_apply_order_direction(func.lower(func.coalesce(Company.name, "")), direction))
    elif normalized_sort == "position_name":
        query = query.outerjoin(User.position)
        order_clauses.append(_apply_order_direction(func.lower(func.coalesce(Position.name, "")), direction))
    elif normalized_sort == "role_name":
        query = query.outerjoin(User.role)
        order_clauses.append(_apply_order_direction(func.lower(func.coalesce(Role.name, "")), direction))
    elif normalized_sort == "iiko_id":
        order_clauses.append(_apply_order_direction(func.lower(func.coalesce(User.iiko_id, "")), direction))
    elif normalized_sort == "gender":
        order_clauses.append(_apply_order_direction(func.lower(func.coalesce(User.gender, "")), direction))
    elif normalized_sort == "hire_date":
        order_clauses.append(_apply_order_direction(User.hire_date, direction))
    elif normalized_sort == "fire_date":
        order_clauses.append(_apply_order_direction(User.fire_date, direction))
    elif normalized_sort == "birth_date":
        order_clauses.append(_apply_order_direction(User.birth_date, direction))
    elif normalized_sort == "is_cis_employee":
        order_clauses.append(_apply_order_direction(User.is_cis_employee, direction))
    elif normalized_sort == "status":
        order_clauses.append(_apply_order_direction(User.fired, direction))

    if order_clauses:
        order_clauses.append(User.id.asc())
        return query.order_by(*order_clauses)

    return query.order_by(
        func.lower(User.last_name).nullslast(),
        func.lower(User.first_name).nullslast(),
        User.id.asc(),
    )


def list_staff_employee_items(
    db: Session,
    current_user: User,
    *,
    q: Optional[str] = None,
    include_fired: bool = False,
    only_fired: bool = False,
    only_formalized: bool = False,
    only_not_formalized: bool = False,
    only_cis: bool = False,
    only_not_cis: bool = False,
    position_ids: Optional[list[int]] = None,
    sort_by: Optional[str] = None,
    sort_direction: str = "asc",
    restaurant_id: Optional[int] = None,
    hire_date_from: Optional[date] = None,
    hire_date_to: Optional[date] = None,
    fire_date_from: Optional[date] = None,
    fire_date_to: Optional[date] = None,
    compact: bool = False,
    offset: int = 0,
    limit: int = 1000,
) -> tuple[list[StaffUserPublic], bool, Optional[int]]:
    ensure_staff_view(current_user)
    viewer_can_view_all_rates = has_permission(current_user, PermissionCode.STAFF_RATE_VIEW_ALL)
    viewer_rate_level = role_level_for_rate(current_user)

    def _can_see_rate_for_target(target: User) -> bool:
        if viewer_can_view_all_rates:
            return True
        if current_user.id == target.id:
            return True
        if viewer_rate_level is None:
            return False
        if viewer_rate_level >= _RATE_FULL_ACCESS_LEVEL:
            return True
        target_level = role_level_for_rate(target)
        if target_level is None:
            target_level = -1
        return viewer_rate_level > target_level

    base_user_fields = [
        User.id,
        User.username,
        User.first_name,
        User.last_name,
        User.middle_name,
        User.iiko_id,
        User.iiko_code,
        User.staff_code,
        User.phone_number,
        User.company_id,
        User.role_id,
        User.position_id,
        User.gender,
        User.hire_date,
        User.fire_date,
        User.birth_date,
        User.fired,
        User.is_cis_employee,
        User.is_formalized,
        User.workplace_restaurant_id,
    ]
    if compact:
        query_options = [
            noload(User.permission_links),
            noload(User.direct_permissions),
            noload(User.medical_check_records),
            noload(User.cis_document_records),
            noload(User.training_events),
            load_only(*base_user_fields),
            joinedload(User.company).load_only(Company.id, Company.name),
            joinedload(User.position).load_only(
                Position.id,
                Position.name,
                Position.code,
            ),
            joinedload(User.position).noload(Position.permission_links),
            joinedload(User.position).noload(Position.permissions),
            joinedload(User.position).noload(Position.training_requirements),
            selectinload(User.restaurants).load_only(Restaurant.id, Restaurant.name),
        ]
    else:
        query_options = [
            noload(User.permission_links),
            noload(User.direct_permissions),
            noload(User.medical_check_records),
            noload(User.cis_document_records),
            noload(User.training_events),
            load_only(
                *base_user_fields,
                User.email,
                User.rate,
                User.photo_key,
                User.confidential_data_consent,
                User.individual_rate,
                User.has_full_restaurant_access,
                User.has_fingerprint,
            ),
            joinedload(User.role).load_only(Role.id, Role.name, Role.level),
            joinedload(User.role).noload(Role.permission_links),
            joinedload(User.role).noload(Role.permissions),
            joinedload(User.company).load_only(Company.id, Company.name),
            joinedload(User.position).load_only(
                Position.id,
                Position.name,
                Position.code,
                Position.rate,
                Position.restaurant_subdivision_id,
                Position.role_id,
            ),
            joinedload(User.position).noload(Position.permission_links),
            joinedload(User.position).noload(Position.permissions),
            joinedload(User.position).noload(Position.training_requirements),
            joinedload(User.position).joinedload(Position.role).load_only(Role.id, Role.name, Role.level),
            joinedload(User.position).joinedload(Position.role).noload(Role.permission_links),
            joinedload(User.position).joinedload(Position.role).noload(Role.permissions),
            joinedload(User.position).joinedload(Position.restaurant_subdivision).load_only(
                RestaurantSubdivision.id,
                RestaurantSubdivision.name,
                RestaurantSubdivision.is_multi,
            ),
            selectinload(User.restaurants).load_only(Restaurant.id, Restaurant.name, Restaurant.department_code),
        ]
    query = db.query(User).options(*query_options)
    if only_fired:
        query = query.filter(User.fired == True)
    elif not include_fired:
        query = query.filter(User.fired == False)
    if only_formalized and not only_not_formalized:
        query = query.filter(User.is_formalized == True)
    elif only_not_formalized and not only_formalized:
        query = query.filter(or_(User.is_formalized == False, User.is_formalized.is_(None)))
    if only_cis and not only_not_cis:
        query = query.filter(User.is_cis_employee == True)
    elif only_not_cis and not only_cis:
        query = query.filter(or_(User.is_cis_employee == False, User.is_cis_employee.is_(None)))
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(_staff_employee_search_expr().like(like))
    if position_ids:
        normalized_position_ids: list[int] = []
        seen_position_ids: set[int] = set()
        for raw_position_id in position_ids:
            try:
                position_id = int(raw_position_id)
            except Exception:
                continue
            if position_id <= 0 or position_id in seen_position_ids:
                continue
            seen_position_ids.add(position_id)
            normalized_position_ids.append(position_id)
        if normalized_position_ids:
            query = query.filter(User.position_id.in_(normalized_position_ids))
    if hire_date_from:
        query = query.filter(User.hire_date >= hire_date_from)
    if hire_date_to:
        query = query.filter(User.hire_date <= hire_date_to)
    if fire_date_from:
        query = query.filter(User.fire_date >= fire_date_from)
    if fire_date_to:
        query = query.filter(User.fire_date <= fire_date_to)
    if restaurant_id is not None:
        query = query.filter(User.workplace_restaurant_id == restaurant_id)

    allowed_workplaces = get_allowed_workplace_ids(db, current_user)
    if allowed_workplaces is not None:
        if restaurant_id is not None and restaurant_id not in allowed_workplaces:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if allowed_workplaces:
            query = query.filter(
                or_(
                    User.id == current_user.id,
                    User.workplace_restaurant_id.in_(allowed_workplaces),
                )
            )
        else:
            query = query.filter(User.id == current_user.id)

    users_window = _apply_staff_employee_sort(query, sort_by, sort_direction).offset(offset).limit(limit + 1).all()
    has_more = len(users_window) > limit
    users = users_window[:limit]
    next_offset = (offset + len(users)) if has_more else None

    serializer = to_staff_list_public if compact else to_staff_public
    items = [serializer(user, current_user, can_see_rate_override=_can_see_rate_for_target(user)) for user in users]
    return items, has_more, next_offset
