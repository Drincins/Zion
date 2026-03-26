from __future__ import annotations

from backend.bd.models import User
from backend.services.permissions import PermissionCode, has_permission

SALES_REPORT_VIEW_PERMISSIONS = (
    PermissionCode.SALES_REPORT_VIEW_QTY,
    PermissionCode.SALES_REPORT_VIEW_MONEY,
    PermissionCode.IIKO_VIEW,
    PermissionCode.IIKO_MANAGE,
)
SALES_REPORT_MONEY_PERMISSIONS = (
    PermissionCode.SALES_REPORT_VIEW_MONEY,
    PermissionCode.IIKO_VIEW,
    PermissionCode.IIKO_MANAGE,
)
SALES_TABLES_VIEW_PERMISSIONS = (
    PermissionCode.SALES_TABLES_VIEW,
    PermissionCode.SALES_TABLES_MANAGE,
    PermissionCode.IIKO_VIEW,
    PermissionCode.IIKO_MANAGE,
)
SALES_TABLES_MANAGE_PERMISSIONS = (
    PermissionCode.SALES_TABLES_MANAGE,
    PermissionCode.IIKO_MANAGE,
)


def can_view_sales_money(current_user: User) -> bool:
    return any(has_permission(current_user, code) for code in SALES_REPORT_MONEY_PERMISSIONS)
