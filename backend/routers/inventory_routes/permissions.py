from __future__ import annotations

from backend.bd.models import User
from backend.services.permissions import PermissionCode, PermissionKey, ensure_permissions

INVENTORY_NOMENCLATURE_VIEW_PERMISSION_CODES = (
    PermissionCode.INVENTORY_VIEW,
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_VIEW,
    PermissionKey.INVENTORY_NOMENCLATURE_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_CREATE,
    PermissionKey.INVENTORY_NOMENCLATURE_EDIT,
    PermissionKey.INVENTORY_NOMENCLATURE_DELETE,
)
INVENTORY_NOMENCLATURE_CREATE_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_CREATE,
)
INVENTORY_NOMENCLATURE_EDIT_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_EDIT,
)
INVENTORY_NOMENCLATURE_DELETE_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_MANAGE,
    PermissionKey.INVENTORY_NOMENCLATURE_DELETE,
)
INVENTORY_MOVEMENTS_VIEW_PERMISSION_CODES = (
    PermissionCode.INVENTORY_VIEW,
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_VIEW,
    PermissionKey.INVENTORY_MOVEMENTS_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_CREATE,
    PermissionKey.INVENTORY_MOVEMENTS_EDIT,
    PermissionKey.INVENTORY_MOVEMENTS_DELETE,
)
INVENTORY_MOVEMENTS_CREATE_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_CREATE,
)
INVENTORY_MOVEMENTS_EDIT_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_EDIT,
)
INVENTORY_MOVEMENTS_DELETE_PERMISSION_CODES = (
    PermissionCode.INVENTORY_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_MANAGE,
    PermissionKey.INVENTORY_MOVEMENTS_DELETE,
)
INVENTORY_LOOKUP_PERMISSION_CODES = tuple(
    dict.fromkeys(INVENTORY_NOMENCLATURE_VIEW_PERMISSION_CODES + INVENTORY_MOVEMENTS_VIEW_PERMISSION_CODES)
)


def _ensure_inventory_nomenclature_view(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_NOMENCLATURE_VIEW_PERMISSION_CODES)


def _ensure_inventory_nomenclature_create(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_NOMENCLATURE_CREATE_PERMISSION_CODES)


def _ensure_inventory_nomenclature_edit(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_NOMENCLATURE_EDIT_PERMISSION_CODES)


def _ensure_inventory_nomenclature_delete(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_NOMENCLATURE_DELETE_PERMISSION_CODES)


def _ensure_inventory_movements_view(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_MOVEMENTS_VIEW_PERMISSION_CODES)


def _ensure_inventory_movements_create(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_MOVEMENTS_CREATE_PERMISSION_CODES)


def _ensure_inventory_movements_edit(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_MOVEMENTS_EDIT_PERMISSION_CODES)


def _ensure_inventory_movements_delete(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_MOVEMENTS_DELETE_PERMISSION_CODES)


def _ensure_inventory_lookup_access(current_user: User) -> None:
    ensure_permissions(current_user, *INVENTORY_LOOKUP_PERMISSION_CODES)


def _ensure_inventory_balance_view(current_user: User) -> None:
    ensure_permissions(
        current_user,
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_MANAGE,
        PermissionKey.INVENTORY_BALANCE_VIEW,
    )
