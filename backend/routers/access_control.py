from __future__ import annotations

from typing import Iterable, List, Optional, Dict
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.bd.database import get_db
from backend.bd.models import (
    Position,
    PositionChangeOrder,
    Permission,
    Role,
    User,
    PositionPermission,
    UserPermission,
    RolePermission,
    PaymentFormat,
    RestaurantSubdivision,
)
from backend.schemas import (
    PermissionCreate,
    PermissionRead,
    PermissionUpdate,
    RolePermissionsCreate,
    RolePermissionsUpdate,
    RoleWithPermissions,
    PositionHierarchyCreate,
    PositionHierarchyNode,
    PositionHierarchyUpdate,
    PositionChangeOrderCreate,
    PositionChangeOrderPublic,
    PositionChangeOrderListResponse,
    PaymentFormatRead,
    RestaurantSubdivisionRead,
    RestaurantSubdivisionCreate,
    RestaurantSubdivisionUpdate,
    PermissionRouteInfo,
    PermissionRouteListResponse,
    PermissionCodeList,
    PermissionCodeSingle,
)
from backend.services.permissions import (
    PermissionCode,
    has_any_permission,
    has_permission,
    collect_permission_codes,
)
from backend.services.employee_changes import log_employee_changes
from backend.services.position_change_orders import apply_position_change_order
from backend.services.reference_cache import cached_reference_data, invalidate_reference_scope
from backend.utils import get_current_user, now_local, today_local, user_has_global_access

router = APIRouter(prefix="/access", tags=["Access control"])

DEPRECATED_PERMISSION_CODES = {
    "inventory.bot.access",
    "iiko_products.read",
    "iiko_olap_read.view",
    "iiko_olap_product.manage",
}
ACCESS_PERMISSIONS_CACHE_SCOPE = "access:permissions"
ACCESS_POSITIONS_CACHE_SCOPE = "access:positions"
ACCESS_BOOTSTRAP_CACHE_SCOPE = "access:bootstrap"
ACCESS_ROLES_CACHE_SCOPE = "access:roles"
ACCESS_PAYMENT_FORMATS_CACHE_SCOPE = "access:payment_formats"
ACCESS_RESTAURANT_SUBDIVISIONS_CACHE_SCOPE = "access:restaurant_subdivisions"
ACCESS_ROLE_PERMISSIONS_MAP_CACHE_SCOPE = "access:role_permissions_map"
ACCESS_POSITION_PERMISSIONS_MAP_CACHE_SCOPE = "access:position_permissions_map"
ACCESS_REFERENCE_CACHE_TTL_SECONDS = 60


# ----- Helpers ----------------------------------------------------------------

def _require_permissions(user: User, codes: Iterable[str]) -> None:
    if user_has_global_access(user):
        return
    if has_any_permission(user, codes):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _permission_not_found(code: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Permission '{code}' not found")


def _role_response(role: Role) -> RoleWithPermissions:
    return RoleWithPermissions(
        id=role.id,
        name=role.name,
        level=role.level,
        comment=role.comment,
    )


def _position_response(position: Position) -> PositionHierarchyNode:
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
        restaurant_subdivision_name=position.restaurant_subdivision.name
        if position.restaurant_subdivision
        else None,
        night_bonus_enabled=position.night_bonus_enabled,
        night_bonus_percent=position.night_bonus_percent,
    )


def _require_position_change_orders_manage(current_user: User) -> None:
    _require_permissions(
        current_user,
        [
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.POSITIONS_CHANGE_ORDERS_MANAGE,
        ],
    )


def _load_position_change_order(
    db: Session,
    *,
    position_id: int,
    order_id: int,
) -> PositionChangeOrder:
    order = (
        db.query(PositionChangeOrder)
        .options(
            selectinload(PositionChangeOrder.position).selectinload(Position.payment_format),
            selectinload(PositionChangeOrder.created_by),
            selectinload(PositionChangeOrder.cancelled_by),
        )
        .filter(
            PositionChangeOrder.id == order_id,
            PositionChangeOrder.position_id == position_id,
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position change order not found")
    return order


class AccessBootstrapResponse(BaseModel):
    roles: List[RoleWithPermissions] = Field(default_factory=list)
    permissions: List[PermissionRead] = Field(default_factory=list)
    positions: List[PositionHierarchyNode] = Field(default_factory=list)
    payment_formats: List[PaymentFormatRead] = Field(default_factory=list)
    restaurant_subdivisions: List[RestaurantSubdivisionRead] = Field(default_factory=list)


def _validate_parent(db: Session, position_id: Optional[int], parent_id: Optional[int]) -> Optional[Position]:
    if parent_id is None:
        return None
    if position_id is not None and parent_id == position_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position cannot be its own parent")

    parent = db.query(Position).options(selectinload(Position.parent)).filter(Position.id == parent_id).first()
    if not parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent position not found")

    ancestor = parent
    while ancestor:
        if ancestor.id == position_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent cycle detected")
        if ancestor.parent_id is None:
            break
        ancestor = db.query(Position).filter(Position.id == ancestor.parent_id).first()
    return parent


def _resolve_role(db: Session, role_id: Optional[int]) -> Optional[Role]:
    if role_id is None:
        return None
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


def _resolve_payment_format(db: Session, payment_format_id: Optional[int]) -> Optional[PaymentFormat]:
    if payment_format_id is None:
        return None
    payment_format = db.query(PaymentFormat).filter(PaymentFormat.id == payment_format_id).first()
    if not payment_format:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment format not found")
    return payment_format


def _resolve_subdivision(db: Session, subdivision_id: Optional[int]) -> Optional[RestaurantSubdivision]:
    if subdivision_id is None:
        return None
    subdivision = (
        db.query(RestaurantSubdivision).filter(RestaurantSubdivision.id == subdivision_id).first()
    )
    if not subdivision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant subdivision not found")
    return subdivision


def _fetch_permissions(db: Session, codes: Iterable[str]) -> List[Permission]:
    normalized: List[str] = []
    for code in codes:
        if code is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission code cannot be empty",
            )
        normalized_code = code.strip().lower()
        if not normalized_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission code cannot be empty",
            )
        normalized.append(normalized_code)

    if not normalized:
        return []

    permissions = (
        db.query(Permission)
        .filter(Permission.api_router.in_(normalized))
        .all()
    )

    found_codes = {permission.code for permission in permissions}
    missing = [code for code in normalized if code not in found_codes]
    if missing:
        raise _permission_not_found(missing[0])

    permission_map = {permission.code: permission for permission in permissions}
    return [permission_map[code] for code in normalized]


def _can_read_permissions_catalog(user: User) -> bool:
    return user_has_global_access(user) or has_any_permission(
        user,
        [
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.ROLES_MANAGE,
            PermissionCode.POSITIONS_MANAGE,
        ],
    )


def _can_read_roles(user: User) -> bool:
    return user_has_global_access(user) or has_any_permission(
        user,
        [
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.ROLES_MANAGE,
        ],
    )


def _can_read_positions(user: User) -> bool:
    return user_has_global_access(user) or has_any_permission(
        user,
        [
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.POSITIONS_MANAGE,
            PermissionCode.POSITIONS_EDIT,
            PermissionCode.POSITIONS_RATE_MANAGE,
            PermissionCode.POSITIONS_CHANGE_ORDERS_MANAGE,
        ],
    )


def _can_manage_positions_catalog(user: User) -> bool:
    return user_has_global_access(user) or has_any_permission(
        user,
        [
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.POSITIONS_MANAGE,
        ],
    )


def _get_position_or_404(db: Session, position_id: int) -> Position:
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return position


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _role_permissions_query(db: Session, role_id: int):
    return (
        db.query(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == role_id)
        .order_by(Permission.api_router.asc())
    )


def _sync_position_permissions_from_role(db: Session, position: Position, *, replace: bool = False) -> None:
    """Seed position permissions from its role template."""
    if not position or not position.role_id:
        return

    if replace:
        db.query(PositionPermission).filter(PositionPermission.position_id == position.id).delete(
            synchronize_session=False
        )
        db.flush()

    existing = db.query(PositionPermission.permission_id).filter(
        PositionPermission.position_id == position.id
    )
    existing_ids = {row[0] for row in existing.all()}

    role_permission_ids = (
        db.query(RolePermission.permission_id)
        .filter(RolePermission.role_id == position.role_id)
        .all()
    )
    if not role_permission_ids:
        return

    objects = [
        PositionPermission(position_id=position.id, permission_id=permission_id)
        for (permission_id,) in role_permission_ids
        if permission_id not in existing_ids
    ]
    if objects:
        db.bulk_save_objects(objects)


@router.get("/bootstrap", response_model=AccessBootstrapResponse)
def access_bootstrap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccessBootstrapResponse:
    can_read_permissions = _can_read_permissions_catalog(current_user)
    can_read_roles = _can_read_roles(current_user)
    can_read_positions = _can_read_positions(current_user)
    can_manage_positions = _can_manage_positions_catalog(current_user)

    if not any((can_read_permissions, can_read_roles, can_read_positions, can_manage_positions)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    cache_key = (
        int(current_user.id),
        bool(can_read_permissions),
        bool(can_read_roles),
        bool(can_read_positions),
        bool(can_manage_positions),
    )

    def _load_bootstrap() -> dict:
        roles_payload: list[RoleWithPermissions] = []
        permissions_payload: list[PermissionRead] = []
        positions_payload: list[PositionHierarchyNode] = []
        payment_formats_payload: list[PaymentFormatRead] = []
        subdivisions_payload: list[RestaurantSubdivisionRead] = []

        if can_read_roles:
            roles = db.query(Role).order_by(Role.name.asc()).all()
            roles_payload = [_role_response(role) for role in roles]

        if can_read_permissions:
            permissions = (
                db.query(Permission)
                .filter(~Permission.api_router.in_(DEPRECATED_PERMISSION_CODES))
                .order_by(
                    func.coalesce(Permission.responsibility_zone, "").asc(),
                    func.coalesce(Permission.display_name, Permission.router_description, Permission.api_router).asc(),
                    Permission.api_router.asc(),
                )
                .all()
            )
            permissions_payload = [PermissionRead.model_validate(permission) for permission in permissions]

        if can_read_positions:
            positions = (
                db.query(Position)
                .options(
                    selectinload(Position.role),
                    selectinload(Position.payment_format),
                    selectinload(Position.restaurant_subdivision),
                )
                .order_by(Position.hierarchy_level.asc(), Position.name.asc())
                .all()
            )
            positions_payload = [_position_response(position) for position in positions]

        if can_manage_positions:
            payment_formats = db.query(PaymentFormat).order_by(PaymentFormat.name.asc()).all()
            payment_formats_payload = [PaymentFormatRead.model_validate(item) for item in payment_formats]
            subdivisions = db.query(RestaurantSubdivision).order_by(RestaurantSubdivision.name.asc()).all()
            subdivisions_payload = [RestaurantSubdivisionRead.model_validate(item) for item in subdivisions]

        return AccessBootstrapResponse(
            roles=roles_payload,
            permissions=permissions_payload,
            positions=positions_payload,
            payment_formats=payment_formats_payload,
            restaurant_subdivisions=subdivisions_payload,
        ).model_dump(mode="json")

    payload = cached_reference_data(
        ACCESS_BOOTSTRAP_CACHE_SCOPE,
        cache_key,
        _load_bootstrap,
        ttl_seconds=ACCESS_REFERENCE_CACHE_TTL_SECONDS,
    )
    return AccessBootstrapResponse.model_validate(payload)


# ----- Permission catalogue ---------------------------------------------------


@router.get("/permission-map", response_model=PermissionRouteListResponse)
def get_permission_map(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> PermissionRouteListResponse:
    _require_permissions(
        current_user,
        [
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.ROLES_MANAGE,
            PermissionCode.POSITIONS_MANAGE,
        ],
    )

    routes: List[PermissionRouteInfo] = []
    for route in request.app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = sorted(route.methods or [])
        permission_codes = sorted(collect_permission_codes(route.dependant))
        tags = list(route.tags or [])
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes.append(
                PermissionRouteInfo(
                    method=method,
                    path=route.path,
                    name=route.name,
                    summary=route.summary,
                    tags=tags,
                    permission_codes=permission_codes,
                    include_in_schema=route.include_in_schema,
                )
            )

    routes.sort(key=lambda item: (item.path, item.method))
    return PermissionRouteListResponse(routes=routes)


@router.get("/permissions", response_model=List[PermissionRead])
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PermissionRead]:
    _require_permissions(
        current_user,
        [
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.ROLES_MANAGE,
            PermissionCode.POSITIONS_MANAGE,
        ],
    )
    def _load_permissions() -> list[dict]:
        permissions = (
            db.query(Permission)
            .filter(~Permission.api_router.in_(DEPRECATED_PERMISSION_CODES))
            .order_by(
                func.coalesce(Permission.responsibility_zone, "").asc(),
                func.coalesce(Permission.display_name, Permission.router_description, Permission.api_router).asc(),
                Permission.api_router.asc(),
            )
            .all()
        )
        return [
            PermissionRead.model_validate(permission).model_dump(mode="json")
            for permission in permissions
        ]

    return cached_reference_data(
        ACCESS_PERMISSIONS_CACHE_SCOPE,
        "all",
        _load_permissions,
        ttl_seconds=ACCESS_REFERENCE_CACHE_TTL_SECONDS,
    )


@router.post("/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
def create_permission(
    payload: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Permission:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])

    code = payload.code.strip().lower()
    name = payload.name.strip()
    description = payload.description.strip() if isinstance(payload.description, str) else payload.description

    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Permission code cannot be empty")
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Permission name cannot be empty")

    existing = db.query(Permission).filter(Permission.api_router == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Permission with this code already exists")

    display_name = payload.display_name.strip() if isinstance(payload.display_name, str) else None
    responsibility_zone = (
        payload.responsibility_zone.strip() if isinstance(payload.responsibility_zone, str) else None
    )
    permission = Permission(
        code=code,
        name=name,
        description=description,
        display_name=display_name,
        responsibility_zone=responsibility_zone,
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)
    invalidate_reference_scope(ACCESS_PERMISSIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return permission


@router.patch("/permissions/{permission_id}", response_model=PermissionRead)
def update_permission(
    permission_id: int,
    payload: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Permission:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])

    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Permission name cannot be empty")
        permission.name = name
    if payload.description is not None:
        permission.description = (
            payload.description.strip() if isinstance(payload.description, str) and payload.description.strip() else None
        )
    if payload.display_name is not None:
        permission.display_name = (
            payload.display_name.strip() if isinstance(payload.display_name, str) and payload.display_name.strip() else None
        )
    if payload.responsibility_zone is not None:
        permission.responsibility_zone = (
            payload.responsibility_zone.strip()
            if isinstance(payload.responsibility_zone, str) and payload.responsibility_zone.strip()
            else None
        )

    db.commit()
    db.refresh(permission)
    invalidate_reference_scope(ACCESS_PERMISSIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return permission


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])

    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    linked_roles = db.query(RolePermission.id).filter(RolePermission.permission_id == permission_id).first()
    if linked_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete permission that is assigned to roles",
        )

    db.delete(permission)
    db.commit()
    invalidate_reference_scope(ACCESS_PERMISSIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----- Roles ------------------------------------------------------------------


@router.get("/roles", response_model=List[RoleWithPermissions])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[RoleWithPermissions]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])
    def _load_roles() -> list[dict]:
        roles = (
            db.query(Role)
            .order_by(Role.name.asc())
            .all()
        )
        return [
            _role_response(role).model_dump(mode="json")
            for role in roles
        ]

    payload = cached_reference_data(
        ACCESS_ROLES_CACHE_SCOPE,
        "all",
        _load_roles,
        ttl_seconds=ACCESS_REFERENCE_CACHE_TTL_SECONDS,
    )
    return [RoleWithPermissions.model_validate(item) for item in payload]


@router.post("/roles", response_model=RoleWithPermissions, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RolePermissionsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoleWithPermissions:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role name cannot be empty")

    existing = db.query(Role).filter(Role.name == name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role with this name already exists")

    level = payload.level if payload.level is not None else 0
    if level < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role level cannot be negative")
    comment = (
        payload.comment.strip()
        if isinstance(payload.comment, str) and payload.comment.strip()
        else None
    )

    role = Role(name=name, level=level, comment=comment)

    db.add(role)
    db.commit()
    db.refresh(role)
    db.refresh(role)
    invalidate_reference_scope(ACCESS_ROLES_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_ROLE_PERMISSIONS_MAP_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_POSITIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return _role_response(role)


@router.patch("/roles/{role_id}", response_model=RoleWithPermissions)
def update_role(
    role_id: int,
    payload: RolePermissionsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoleWithPermissions:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])

    role = (
        db.query(Role)
        .filter(Role.id == role_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if payload.name is not None:
        new_name = payload.name.strip()
        if not new_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role name cannot be empty")
        duplicate = (
            db.query(Role)
            .filter(Role.name == new_name)
            .filter(Role.id != role_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role with this name already exists")
        role.name = new_name

    if payload.level is not None:
        if payload.level < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role level cannot be negative")
        role.level = payload.level
    if payload.comment is not None:
        role.comment = payload.comment.strip() if payload.comment.strip() else None

    db.commit()
    db.refresh(role)
    invalidate_reference_scope(ACCESS_ROLES_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_ROLE_PERMISSIONS_MAP_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_POSITIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return _role_response(role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    usage_exists = db.query(User.id).filter(User.role_id == role_id).first()
    if usage_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete role that is assigned to users",
        )

    db.delete(role)
    db.commit()
    invalidate_reference_scope(ACCESS_ROLES_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_ROLE_PERMISSIONS_MAP_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_POSITIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----- Role permissions -------------------------------------------------------


@router.get("/roles/{role_id}/permissions", response_model=List[PermissionRead])
def list_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PermissionRead]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])
    role = _resolve_role(db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    permissions = _role_permissions_query(db, role_id).all()
    return [PermissionRead.model_validate(perm) for perm in permissions]


@router.get("/roles/permissions-map", response_model=Dict[int, List[str]])
def list_role_permissions_map(
    ids: Optional[List[int]] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[int, List[str]]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])
    requested_ids = sorted({int(value) for value in (ids or []) if value is not None})
    cache_key: tuple = tuple(requested_ids) if requested_ids else ("all",)

    def _load_permissions_map() -> dict[int, list[str]]:
        query = (
            db.query(RolePermission.role_id, Permission.api_router)
            .join(Permission, RolePermission.permission_id == Permission.id)
            .order_by(RolePermission.role_id.asc(), Permission.api_router.asc())
        )
        if requested_ids:
            query = query.filter(RolePermission.role_id.in_(requested_ids))
        rows = query.all()
        result: dict[int, List[str]] = defaultdict(list)
        for role_id, code in rows:
            result[int(role_id)].append(code)
        if requested_ids:
            for role_id in requested_ids:
                result.setdefault(int(role_id), [])
        return dict(result)

    return cached_reference_data(
        ACCESS_ROLE_PERMISSIONS_MAP_CACHE_SCOPE,
        cache_key,
        _load_permissions_map,
        ttl_seconds=ACCESS_REFERENCE_CACHE_TTL_SECONDS,
    )


@router.put("/roles/{role_id}/permissions", response_model=List[PermissionRead])
def replace_role_permissions(
    role_id: int,
    payload: PermissionCodeList,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PermissionRead]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])
    _resolve_role(db, role_id)
    permissions = _fetch_permissions(db, payload.permission_codes)

    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete(synchronize_session=False)
    db.flush()

    objects = [
        RolePermission(role_id=role_id, permission_id=perm.id)
        for perm in permissions
    ]
    if objects:
        db.bulk_save_objects(objects)
    db.commit()
    invalidate_reference_scope(ACCESS_ROLE_PERMISSIONS_MAP_CACHE_SCOPE)

    return [
        PermissionRead.model_validate(perm)
        for perm in _role_permissions_query(db, role_id).all()
    ]


# ----- Positions --------------------------------------------------------------


@router.get("/positions", response_model=List[PositionHierarchyNode])
def list_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PositionHierarchyNode]:
    _require_permissions(
        current_user,
        [
            PermissionCode.SYSTEM_ADMIN,
            PermissionCode.POSITIONS_MANAGE,
            PermissionCode.POSITIONS_EDIT,
            PermissionCode.POSITIONS_RATE_MANAGE,
            PermissionCode.POSITIONS_CHANGE_ORDERS_MANAGE,
        ],
    )

    def _load_positions() -> list[dict]:
        positions = (
            db.query(Position)
            .options(
                selectinload(Position.role),
                selectinload(Position.payment_format),
                selectinload(Position.restaurant_subdivision),
            )
            .order_by(Position.hierarchy_level.asc(), Position.name.asc())
            .all()
        )
        return [
            _position_response(position).model_dump(mode="json")
            for position in positions
        ]

    return cached_reference_data(
        ACCESS_POSITIONS_CACHE_SCOPE,
        "all",
        _load_positions,
        ttl_seconds=ACCESS_REFERENCE_CACHE_TTL_SECONDS,
    )


@router.get("/payment-formats", response_model=List[PaymentFormatRead])
def list_payment_formats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PaymentFormatRead]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    def _load_payment_formats() -> list[dict]:
        items = db.query(PaymentFormat).order_by(PaymentFormat.name.asc()).all()
        return [PaymentFormatRead.model_validate(item).model_dump(mode="json") for item in items]

    payload = cached_reference_data(
        ACCESS_PAYMENT_FORMATS_CACHE_SCOPE,
        "all",
        _load_payment_formats,
        ttl_seconds=ACCESS_REFERENCE_CACHE_TTL_SECONDS,
    )
    return [PaymentFormatRead.model_validate(item) for item in payload]


@router.get("/restaurant-subdivisions", response_model=List[RestaurantSubdivisionRead])
def list_restaurant_subdivisions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[RestaurantSubdivisionRead]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    def _load_subdivisions() -> list[dict]:
        items = db.query(RestaurantSubdivision).order_by(RestaurantSubdivision.name.asc()).all()
        return [RestaurantSubdivisionRead.model_validate(item).model_dump(mode="json") for item in items]

    payload = cached_reference_data(
        ACCESS_RESTAURANT_SUBDIVISIONS_CACHE_SCOPE,
        "all",
        _load_subdivisions,
        ttl_seconds=ACCESS_REFERENCE_CACHE_TTL_SECONDS,
    )
    return [RestaurantSubdivisionRead.model_validate(item) for item in payload]


@router.post("/restaurant-subdivisions", response_model=RestaurantSubdivisionRead, status_code=status.HTTP_201_CREATED)
def create_restaurant_subdivision(
    payload: RestaurantSubdivisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RestaurantSubdivisionRead:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subdivision name cannot be empty")

    existing = db.query(RestaurantSubdivision).filter(RestaurantSubdivision.name == name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subdivision with this name already exists")

    subdivision = RestaurantSubdivision(name=name, is_multi=bool(payload.is_multi))
    db.add(subdivision)
    db.commit()
    db.refresh(subdivision)
    invalidate_reference_scope(ACCESS_RESTAURANT_SUBDIVISIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_POSITIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return RestaurantSubdivisionRead.model_validate(subdivision)


@router.patch("/restaurant-subdivisions/{subdivision_id}", response_model=RestaurantSubdivisionRead)
def update_restaurant_subdivision(
    subdivision_id: int,
    payload: RestaurantSubdivisionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RestaurantSubdivisionRead:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    subdivision = db.query(RestaurantSubdivision).filter(RestaurantSubdivision.id == subdivision_id).first()
    if not subdivision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subdivision not found")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subdivision name cannot be empty")
        duplicate = (
            db.query(RestaurantSubdivision)
            .filter(RestaurantSubdivision.name == name)
            .filter(RestaurantSubdivision.id != subdivision_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subdivision with this name already exists")
        subdivision.name = name
    if payload.is_multi is not None:
        subdivision.is_multi = bool(payload.is_multi)

    db.commit()
    db.refresh(subdivision)
    invalidate_reference_scope(ACCESS_RESTAURANT_SUBDIVISIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_POSITIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return RestaurantSubdivisionRead.model_validate(subdivision)


@router.delete("/restaurant-subdivisions/{subdivision_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_restaurant_subdivision(
    subdivision_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    subdivision = db.query(RestaurantSubdivision).filter(RestaurantSubdivision.id == subdivision_id).first()
    if not subdivision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subdivision not found")

    in_use = db.query(Position.id).filter(Position.restaurant_subdivision_id == subdivision_id).first()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete subdivision that is assigned to positions",
        )

    db.delete(subdivision)
    db.commit()
    invalidate_reference_scope(ACCESS_RESTAURANT_SUBDIVISIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_POSITIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/positions", response_model=PositionHierarchyNode, status_code=status.HTTP_201_CREATED)
def create_position(
    payload: PositionHierarchyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionHierarchyNode:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])

    if db.query(Position).filter(Position.name == payload.name).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Position with this name already exists")

    role = _resolve_role(db, payload.role_id)
    parent = _validate_parent(db, None, payload.parent_id)

    hierarchy_level = payload.hierarchy_level
    if hierarchy_level is None:
        hierarchy_level = (parent.hierarchy_level + 1) if parent else 0

    code = payload.code.strip() if payload.code else None
    if code:
        existing_code = db.query(Position).filter(Position.code == code).first()
        if existing_code:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Должность с таким названием уже существует")

    position = Position(
        name=payload.name.strip(),
        code=code,
        role=role,
        parent=parent,
        hierarchy_level=hierarchy_level,
        rate=payload.rate,
        payment_format=_resolve_payment_format(db, payload.payment_format_id),
        hours_per_shift=payload.hours_per_shift,
        monthly_shift_norm=payload.monthly_shift_norm,
        restaurant_subdivision=_resolve_subdivision(db, payload.restaurant_subdivision_id),
        night_bonus_enabled=payload.night_bonus_enabled,
        night_bonus_percent=payload.night_bonus_percent or 0,
    )

    db.add(position)
    db.flush()
    _sync_position_permissions_from_role(db, position, replace=True)
    db.commit()
    db.refresh(position)
    invalidate_reference_scope(ACCESS_POSITION_PERMISSIONS_MAP_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_POSITIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    position = (
        db.query(Position)
        .options(
            selectinload(Position.role),
            selectinload(Position.payment_format),
            selectinload(Position.restaurant_subdivision),
        )
        .filter(Position.id == position.id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found after creation")
    return _position_response(position)


@router.patch("/positions/{position_id}", response_model=PositionHierarchyNode)
def update_position(
    position_id: int,
    payload: PositionHierarchyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionHierarchyNode:
    position = (
        db.query(Position)
        .options(
            selectinload(Position.role),
            selectinload(Position.payment_format),
            selectinload(Position.restaurant_subdivision),
        )
        .filter(Position.id == position_id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    fields_set = getattr(payload, "model_fields_set", set())
    non_rate_fields = {field for field in fields_set if field != "rate"}
    if non_rate_fields:
        _require_permissions(
            current_user,
            [
                PermissionCode.SYSTEM_ADMIN,
                PermissionCode.POSITIONS_MANAGE,
                PermissionCode.POSITIONS_EDIT,
            ],
        )
    if "rate" in fields_set:
        _require_permissions(
            current_user,
            [
                PermissionCode.SYSTEM_ADMIN,
                PermissionCode.POSITIONS_MANAGE,
                PermissionCode.POSITIONS_RATE_MANAGE,
            ],
        )
    rate_changed = False
    role_changed = False

    if payload.name is not None:
        duplicate = (
            db.query(Position)
            .filter(Position.name == payload.name)
            .filter(Position.id != position_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Position with this name already exists")
        position.name = payload.name.strip()

    if "code" in fields_set:
        code = payload.code.strip() if payload.code else None
        if code:
            duplicate_code = (
                db.query(Position)
                .filter(Position.code == code)
                .filter(Position.id != position_id)
                .first()
            )
            if duplicate_code:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Должность с таким названием уже существует",
                )
        position.code = code

    if "role_id" in fields_set:
        if payload.role_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role id cannot be null")
        position.role = _resolve_role(db, payload.role_id)
        role_changed = True

    if "parent_id" in fields_set:
        if payload.parent_id is None:
            position.parent = None
            if "hierarchy_level" not in fields_set:
                position.hierarchy_level = 0
        else:
            parent = _validate_parent(db, position_id, payload.parent_id)
            position.parent = parent
            if "hierarchy_level" not in fields_set:
                position.hierarchy_level = parent.hierarchy_level + 1 if parent else 0

    if "hierarchy_level" in fields_set:
        if payload.hierarchy_level is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hierarchy level cannot be null")
        if payload.hierarchy_level < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hierarchy level cannot be negative")
        position.hierarchy_level = payload.hierarchy_level

    if "payment_format_id" in fields_set:
        if payload.payment_format_id is None:
            position.payment_format = None
        else:
            position.payment_format = _resolve_payment_format(db, payload.payment_format_id)

    if "hours_per_shift" in fields_set:
        position.hours_per_shift = payload.hours_per_shift

    if "monthly_shift_norm" in fields_set:
        position.monthly_shift_norm = payload.monthly_shift_norm

    if "night_bonus_enabled" in fields_set and payload.night_bonus_enabled is not None:
        position.night_bonus_enabled = payload.night_bonus_enabled

    if "night_bonus_percent" in fields_set:
        position.night_bonus_percent = payload.night_bonus_percent or 0

    if "rate" in fields_set:
        position.rate = payload.rate
        rate_changed = True

    if "restaurant_subdivision_id" in fields_set:
        if payload.restaurant_subdivision_id is None:
            position.restaurant_subdivision = None
        else:
            position.restaurant_subdivision = _resolve_subdivision(db, payload.restaurant_subdivision_id)

    if rate_changed:
        db.query(User).filter(
            User.position_id == position.id,
            User.individual_rate.is_(None),
        ).update(
            {User.rate: position.rate},
            synchronize_session=False,
        )
    if role_changed:
        db.query(User).filter(User.position_id == position.id).update(
            {User.role_id: position.role_id},
            synchronize_session=False,
        )
        _sync_position_permissions_from_role(db, position, replace=True)

    db.commit()
    invalidate_reference_scope(ACCESS_POSITION_PERMISSIONS_MAP_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_POSITIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    position = (
        db.query(Position)
        .options(
            selectinload(Position.role),
            selectinload(Position.payment_format),
            selectinload(Position.restaurant_subdivision),
        )
        .filter(Position.id == position_id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found after update")
    return _position_response(position)


@router.get(
    "/positions/{position_id}/change-orders",
    response_model=PositionChangeOrderListResponse,
    response_model_exclude_none=True,
)
def list_position_change_orders(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionChangeOrderListResponse:
    _require_position_change_orders_manage(current_user)

    position = db.query(Position.id).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    items = (
        db.query(PositionChangeOrder)
        .options(
            selectinload(PositionChangeOrder.position).selectinload(Position.payment_format),
            selectinload(PositionChangeOrder.created_by),
            selectinload(PositionChangeOrder.cancelled_by),
        )
        .filter(PositionChangeOrder.position_id == position_id)
        .order_by(
            PositionChangeOrder.effective_date.desc(),
            PositionChangeOrder.created_at.desc(),
            PositionChangeOrder.id.desc(),
        )
        .all()
    )
    return PositionChangeOrderListResponse(
        items=[PositionChangeOrderPublic.model_validate(item) for item in items]
    )


@router.post(
    "/positions/{position_id}/change-orders",
    response_model=PositionChangeOrderPublic,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create_position_change_order(
    position_id: int,
    payload: PositionChangeOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionChangeOrderPublic:
    _require_position_change_orders_manage(current_user)

    position = (
        db.query(Position)
        .options(selectinload(Position.payment_format))
        .filter(Position.id == position_id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    if payload.effective_date < today_local():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Effective date must be today or in the future",
        )
    if payload.rate_new is None or payload.rate_new < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите корректную новую ставку",
        )

    existing_pending = (
        db.query(PositionChangeOrder.id)
        .filter(
            PositionChangeOrder.position_id == position_id,
            PositionChangeOrder.effective_date == payload.effective_date,
            PositionChangeOrder.status == "pending",
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending change order already exists for this date",
        )

    order = PositionChangeOrder(
        position_id=position_id,
        effective_date=payload.effective_date,
        rate_new=payload.rate_new,
        apply_to_attendances=bool(payload.apply_to_attendances),
        comment=(payload.comment or "").strip() or None,
        created_by_id=current_user.id,
    )
    db.add(order)
    db.commit()

    order = _load_position_change_order(db, position_id=position_id, order_id=order.id)
    if order.effective_date <= today_local():
        try:
            apply_position_change_order(db, order)
            db.commit()
            order = _load_position_change_order(db, position_id=position_id, order_id=order.id)
        except Exception:
            db.rollback()
            raise
    return PositionChangeOrderPublic.model_validate(order)


@router.post(
    "/positions/{position_id}/change-orders/{order_id}/cancel",
    response_model=PositionChangeOrderPublic,
    response_model_exclude_none=True,
)
def cancel_position_change_order(
    position_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PositionChangeOrderPublic:
    _require_position_change_orders_manage(current_user)

    position = db.query(Position.id).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    order = _load_position_change_order(db, position_id=position_id, order_id=order_id)
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending position change orders can be cancelled",
        )

    order.status = "cancelled"
    order.cancelled_at = now_local()
    order.cancelled_by_id = current_user.id
    order.error_message = None
    db.commit()

    order = _load_position_change_order(db, position_id=position_id, order_id=order_id)
    return PositionChangeOrderPublic.model_validate(order)


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])

    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    has_children = db.query(Position.id).filter(Position.parent_id == position_id).first()
    if has_children:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete position that has child positions",
        )

    has_users = db.query(User.id).filter(User.position_id == position_id).first()
    if has_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete position that is assigned to users",
        )

    db.delete(position)
    db.commit()
    invalidate_reference_scope(ACCESS_POSITION_PERMISSIONS_MAP_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_POSITIONS_CACHE_SCOPE)
    invalidate_reference_scope(ACCESS_BOOTSTRAP_CACHE_SCOPE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----- Position permissions ----------------------------------------------------


def _position_permissions_query(db: Session, position_id: int):
    return (
        db.query(Permission)
        .join(PositionPermission, PositionPermission.permission_id == Permission.id)
        .filter(PositionPermission.position_id == position_id)
        .order_by(Permission.api_router.asc())
    )


@router.get("/positions/{position_id}/permissions", response_model=List[PermissionRead])
def list_position_permissions(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PermissionRead]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    _get_position_or_404(db, position_id)
    permissions = _position_permissions_query(db, position_id).all()
    return [PermissionRead.model_validate(perm) for perm in permissions]


@router.get("/positions/permissions-map", response_model=Dict[int, List[str]])
def list_position_permissions_map(
    ids: Optional[List[int]] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[int, List[str]]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    requested_ids = sorted({int(value) for value in (ids or []) if value is not None})
    cache_key: tuple = tuple(requested_ids) if requested_ids else ("all",)

    def _load_permissions_map() -> dict[int, list[str]]:
        query = (
            db.query(PositionPermission.position_id, Permission.api_router)
            .join(Permission, PositionPermission.permission_id == Permission.id)
            .order_by(PositionPermission.position_id.asc(), Permission.api_router.asc())
        )
        if requested_ids:
            query = query.filter(PositionPermission.position_id.in_(requested_ids))
        rows = query.all()
        result: dict[int, List[str]] = defaultdict(list)
        for position_id, code in rows:
            result[int(position_id)].append(code)
        if requested_ids:
            for position_id in requested_ids:
                result.setdefault(int(position_id), [])
        return dict(result)

    return cached_reference_data(
        ACCESS_POSITION_PERMISSIONS_MAP_CACHE_SCOPE,
        cache_key,
        _load_permissions_map,
        ttl_seconds=ACCESS_REFERENCE_CACHE_TTL_SECONDS,
    )


@router.put("/positions/{position_id}/permissions", response_model=List[PermissionRead])
def replace_position_permissions(
    position_id: int,
    payload: PermissionCodeList,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PermissionRead]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    _get_position_or_404(db, position_id)
    permissions = _fetch_permissions(db, payload.permission_codes)

    db.query(PositionPermission).filter(PositionPermission.position_id == position_id).delete(synchronize_session=False)
    db.flush()

    objects = [
        PositionPermission(position_id=position_id, permission_id=perm.id)
        for perm in permissions
    ]
    if objects:
        db.bulk_save_objects(objects)
    db.commit()
    invalidate_reference_scope(ACCESS_POSITION_PERMISSIONS_MAP_CACHE_SCOPE)

    return [
        PermissionRead.model_validate(perm)
        for perm in _position_permissions_query(db, position_id).all()
    ]


@router.post("/positions/{position_id}/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
def add_position_permission(
    position_id: int,
    payload: PermissionCodeSingle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PermissionRead:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    _get_position_or_404(db, position_id)
    permission = _fetch_permissions(db, [payload.permission_code])[0]

    exists = (
        db.query(PositionPermission)
        .filter(
            PositionPermission.position_id == position_id,
            PositionPermission.permission_id == permission.id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Permission already assigned to position")

    db.add(PositionPermission(position_id=position_id, permission_id=permission.id))
    db.commit()
    invalidate_reference_scope(ACCESS_POSITION_PERMISSIONS_MAP_CACHE_SCOPE)
    return PermissionRead.model_validate(permission)


@router.delete("/positions/{position_id}/permissions/{permission_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_position_permission(
    position_id: int,
    permission_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.POSITIONS_MANAGE])
    _get_position_or_404(db, position_id)
    permission = _fetch_permissions(db, [permission_code])[0]
    link = (
        db.query(PositionPermission)
        .filter(
            PositionPermission.position_id == position_id,
            PositionPermission.permission_id == permission.id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not assigned to position")
    db.delete(link)
    db.commit()
    invalidate_reference_scope(ACCESS_POSITION_PERMISSIONS_MAP_CACHE_SCOPE)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----- User permissions --------------------------------------------------------


def _user_permissions_query(db: Session, user_id: int):
    return (
        db.query(Permission)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .filter(UserPermission.user_id == user_id)
        .order_by(Permission.api_router.asc())
    )


def _permission_codes(perms: Iterable[Permission]) -> list[str]:
    codes = [perm.code for perm in perms if getattr(perm, "code", None)]
    return sorted(set(codes))


@router.get("/users/{user_id}/permissions", response_model=List[PermissionRead])
def list_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PermissionRead]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])
    _get_user_or_404(db, user_id)
    permissions = _user_permissions_query(db, user_id).all()
    return [PermissionRead.model_validate(perm) for perm in permissions]


@router.put("/users/{user_id}/permissions", response_model=List[PermissionRead])
def replace_user_permissions(
    user_id: int,
    payload: PermissionCodeList,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PermissionRead]:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])
    _get_user_or_404(db, user_id)
    old_codes = _permission_codes(_user_permissions_query(db, user_id).all())
    permissions = _fetch_permissions(db, payload.permission_codes)
    new_codes = _permission_codes(permissions)

    db.query(UserPermission).filter(UserPermission.user_id == user_id).delete(synchronize_session=False)
    db.flush()
    objects = [
        UserPermission(user_id=user_id, permission_id=perm.id)
        for perm in permissions
    ]
    if objects:
        db.bulk_save_objects(objects)
    if old_codes != new_codes:
        log_employee_changes(
            db,
            user_id=user_id,
            changed_by_id=current_user.id,
            changes=[
                {
                    "field": "permissions",
                    "old_value": old_codes,
                    "new_value": new_codes,
                    "source": "user_permissions",
                    "comment": "Обновлены права доступа",
                }
            ],
        )
    db.commit()
    return [
        PermissionRead.model_validate(perm)
        for perm in _user_permissions_query(db, user_id).all()
    ]


@router.post("/users/{user_id}/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
def add_user_permission(
    user_id: int,
    payload: PermissionCodeSingle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PermissionRead:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])
    _get_user_or_404(db, user_id)
    old_codes = _permission_codes(_user_permissions_query(db, user_id).all())
    permission = _fetch_permissions(db, [payload.permission_code])[0]

    exists = (
        db.query(UserPermission)
        .filter(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == permission.id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Permission already assigned to user")

    db.add(UserPermission(user_id=user_id, permission_id=permission.id))
    new_codes = sorted(set(old_codes + [permission.code]))
    if old_codes != new_codes:
        log_employee_changes(
            db,
            user_id=user_id,
            changed_by_id=current_user.id,
            changes=[
                {
                    "field": "permissions",
                    "old_value": old_codes,
                    "new_value": new_codes,
                    "source": "user_permissions",
                    "comment": "Добавлено право доступа",
                }
            ],
        )
    db.commit()
    return PermissionRead.model_validate(permission)


@router.delete("/users/{user_id}/permissions/{permission_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_permission(
    user_id: int,
    permission_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _require_permissions(current_user, [PermissionCode.SYSTEM_ADMIN, PermissionCode.ROLES_MANAGE])
    _get_user_or_404(db, user_id)
    old_codes = _permission_codes(_user_permissions_query(db, user_id).all())
    permission = _fetch_permissions(db, [permission_code])[0]
    link = (
        db.query(UserPermission)
        .filter(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == permission.id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not assigned to user")
    db.delete(link)
    new_codes = [code for code in old_codes if code != permission.code]
    if old_codes != new_codes:
        log_employee_changes(
            db,
            user_id=user_id,
            changed_by_id=current_user.id,
            changes=[
                {
                    "field": "permissions",
                    "old_value": old_codes,
                    "new_value": new_codes,
                    "source": "user_permissions",
                    "comment": "Удалено право доступа",
                }
            ],
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
