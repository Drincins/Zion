from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException
import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.bd.models import Restaurant, User
from backend.services.permissions import PermissionCode, has_global_access, has_permission
from backend.utils import get_user_company_ids


def get_user_company_scope_ids(db: Session, current_user: User) -> Optional[List[int]]:
    company_ids = get_user_company_ids(db, current_user)
    if company_ids is None:
        return None
    return sorted(int(company_id) for company_id in company_ids if company_id is not None)


def restrict_company_scoped_query(query, company_column, db: Session, current_user: User):
    company_ids = get_user_company_scope_ids(db, current_user)
    if company_ids is None:
        return query
    if not company_ids:
        return query.filter(sa.literal(False))
    if len(company_ids) == 1:
        return query.filter(company_column == int(company_ids[0]))
    return query.filter(company_column.in_(company_ids))


def resolve_scoped_company_id(
    db: Session,
    current_user: User,
    requested_company_id: Optional[int] = None,
) -> int:
    if requested_company_id is not None:
        requested = int(requested_company_id)
        if not has_global_access(current_user):
            company_ids = get_user_company_scope_ids(db, current_user) or []
            if requested not in company_ids:
                raise HTTPException(status_code=403, detail="Company is outside of your scope")
        return requested

    direct_company_id = getattr(current_user, "company_id", None)
    if direct_company_id is not None:
        return int(direct_company_id)

    if has_global_access(current_user):
        raise HTTPException(status_code=400, detail="company_id is required")

    company_ids = get_user_company_scope_ids(db, current_user) or []
    if not company_ids:
        raise HTTPException(status_code=403, detail="Company scope is unavailable for the current user")
    if len(company_ids) == 1:
        return int(company_ids[0])
    raise HTTPException(
        status_code=400,
        detail="Multiple companies available; pass company_id explicitly.",
    )


def ensure_user_access_to_restaurant(
    db: Session,
    current_user: User,
    restaurant_id: int,
    *,
    require_credentials: bool = True,
) -> Restaurant:
    query = db.query(Restaurant).filter(Restaurant.id == restaurant_id)
    if not has_global_access(current_user):
        company_ids = get_user_company_scope_ids(db, current_user) or []
        if company_ids:
            query = query.filter(Restaurant.company_id.in_(company_ids))
            if not has_permission(current_user, PermissionCode.IIKO_MANAGE):
                query = query.filter(Restaurant.users.contains(current_user))
        else:
            query = query.filter(Restaurant.users.contains(current_user))
    restaurant = query.first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found or unavailable")
    if require_credentials and (not restaurant.server or not restaurant.iiko_login or not restaurant.iiko_password_sha1):
        raise HTTPException(status_code=400, detail="Restaurant has no iiko credentials configured")
    return restaurant


def list_accessible_restaurants(db: Session, current_user: User) -> List[Restaurant]:
    q = db.query(Restaurant)
    if not has_global_access(current_user):
        company_ids = get_user_company_scope_ids(db, current_user) or []
        if company_ids:
            q = q.filter(Restaurant.company_id.in_(company_ids))
            if not has_permission(current_user, PermissionCode.IIKO_MANAGE):
                q = q.filter(Restaurant.users.contains(current_user))
        else:
            q = q.filter(Restaurant.users.contains(current_user))
    q = q.filter(Restaurant.participates_in_sales.is_(True))
    return q.order_by(Restaurant.id.asc()).all()
