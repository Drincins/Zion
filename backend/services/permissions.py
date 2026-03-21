"""Permission helpers used across the application."""
from __future__ import annotations

from typing import Iterable, Optional, Sequence, Set, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.dependencies.models import Dependant

from backend.bd.models import Role, User


class PermissionKey:
    """Canonical permission identifiers."""

    SYSTEM_ADMIN = "system.admin"
    STAFF_MANAGE_ALL = "staff.manage_all"
    STAFF_MANAGE_SUBORDINATES = "staff.manage_subordinates"
    STAFF_VIEW_SENSITIVE = "staff.view_sensitive"
    ROLES_MANAGE = "roles.manage"
    POSITIONS_MANAGE = "positions.manage"
    POSITIONS_EDIT = "positions.edit"
    POSITIONS_RATE_MANAGE = "positions.rate.manage"
    USERS_VIEW = "users.view"
    USERS_MANAGE = "users.manage"
    COMPANIES_VIEW = "companies.view"
    COMPANIES_MANAGE = "companies.manage"
    RESTAURANTS_VIEW = "restaurants.view"
    RESTAURANTS_MANAGE = "restaurants.manage"
    INVENTORY_VIEW = "inventory.view"
    INVENTORY_MANAGE = "inventory.manage"
    INVENTORY_BOT_ACCESS = "inventory.bot.access"
    INVENTORY_BALANCE_VIEW = "inventory.balance.view"
    INVENTORY_MOVEMENTS_VIEW = "inventory.movements.view"
    INVENTORY_MOVEMENTS_CREATE = "inventory.movements.create"
    INVENTORY_MOVEMENTS_EDIT = "inventory.movements.edit"
    INVENTORY_MOVEMENTS_MANAGE = "inventory.movements.manage"
    INVENTORY_MOVEMENTS_DELETE = "inventory.movements.delete"
    INVENTORY_NOMENCLATURE_VIEW = "inventory.nomenclature.view"
    INVENTORY_NOMENCLATURE_CREATE = "inventory.nomenclature.create"
    INVENTORY_NOMENCLATURE_EDIT = "inventory.nomenclature.edit"
    INVENTORY_NOMENCLATURE_MANAGE = "inventory.nomenclature.manage"
    INVENTORY_NOMENCLATURE_DELETE = "inventory.nomenclature.delete"
    PAYROLL_VIEW = "payroll.view"
    PAYROLL_MANAGE = "payroll.manage"
    PAYROLL_EXPORT = "payroll.export"
    PAYROLL_RESULTS_VIEW = "payroll.results.view"
    PAYROLL_RESULTS_MANAGE = "payroll.results.manage"
    PAYROLL_ADVANCE_VIEW = "payroll.advance.view"
    PAYROLL_ADVANCE_CREATE = "payroll.advance.create"
    PAYROLL_ADVANCE_EDIT = "payroll.advance.edit"
    PAYROLL_ADVANCE_STATUS_REVIEW = "payroll.advance.status.review"
    PAYROLL_ADVANCE_STATUS_CONFIRM = "payroll.advance.status.confirm"
    PAYROLL_ADVANCE_STATUS_READY = "payroll.advance.status.ready"
    PAYROLL_ADVANCE_STATUS_ALL = "payroll.advance.status.all"
    PAYROLL_ADVANCE_DOWNLOAD = "payroll.advance.download"
    PAYROLL_ADVANCE_POST = "payroll.advance.post"
    PAYROLL_ADVANCE_DELETE = "payroll.advance.delete"
    TIMESHEET_EXPORT = "timesheet.export"
    STAFF_EMPLOYEES_EXPORT = "staff_employees.export"
    KPI_VIEW = "kpi.view"
    KPI_MANAGE = "kpi.manage"
    KPI_METRICS_VIEW = "kpi.metrics.view"
    KPI_METRICS_MANAGE = "kpi.metrics.manage"
    KPI_METRIC_GROUPS_VIEW = "kpi.metric_groups.view"
    KPI_METRIC_GROUPS_MANAGE = "kpi.metric_groups.manage"
    KPI_RULES_ASSIGN = "kpi.rules.assign"
    KPI_FACTS_VIEW = "kpi.facts.view"
    KPI_FACTS_MANAGE = "kpi.facts.manage"
    KPI_RESULTS_VIEW = "kpi.results.view"
    KPI_PAYOUTS_VIEW = "kpi.payouts.view"
    KPI_PAYOUTS_MANAGE = "kpi.payouts.manage"
    TRAINING_VIEW = "training.view"
    TRAINING_MANAGE = "training.manage"
    IIKO_VIEW = "iiko.view"
    IIKO_MANAGE = "iiko.manage"
    IIKO_CATALOG_SYNC = "iiko.catalog.sync"
    SALES_REPORT_VIEW_QTY = "sales.report.view_qty"
    SALES_REPORT_VIEW_MONEY = "sales.report.view_money"
    SALES_TABLES_VIEW = "sales.tables.view"
    SALES_TABLES_MANAGE = "sales.tables.manage"
    SALES_DISHES_VIEW = "sales.dishes.view"
    SALES_DISHES_MANAGE = "sales.dishes.manage"
    RESTAURANTS_SETTINGS_VIEW = "restaurants.settings.view"
    RESTAURANTS_SETTINGS_MANAGE = "restaurants.settings.manage"
    STAFF_EMPLOYEES_VIEW = "staff_employees.view"
    STAFF_EMPLOYEES_MANAGE = "staff_employees.manage"
    STAFF_EMPLOYEES_RESTORE = "staff_employees.restore"
    STAFF_EMPLOYEES_IIKO_SYNC = "staff_employees.iiko_sync"
    STAFF_ROLES_ASSIGN = "staff.roles.assign"
    STAFF_RATE_MANAGE = "staff.rate.manage"
    STAFF_PORTAL_ACCESS = "staff_portal.access"
    EMPLOYEES_CARD_VIEW = "employees_card.view"
    EMPLOYEES_CARD_MANAGE = "employees_card.manage"
    ACCESS_CONTROL_READ = "access_control.read"
    ACCESS_CONTROL_MANAGE = "access_control.manage"
    IIKO_PRODUCTS_READ = "iiko_products.read"
    IIKO_OLAP_PRODUCT = "iiko_olap_product.manage"
    IIKO_OLAP_READ = "iiko_olap_read.view"
    STAFF_RATE_VIEW_ALL = "staff.rate.view_all"
    MEDICAL_CHECKS_VIEW = "medical_checks.view"
    MEDICAL_CHECKS_MANAGE = "medical_checks.manage"
    CIS_DOCUMENTS_VIEW = "cis_documents.view"
    CIS_DOCUMENTS_MANAGE = "cis_documents.manage"
    EMPLOYEE_CHANGES_VIEW = "employee_changes.view"
    EMPLOYEE_CHANGES_MANAGE = "employee_changes.manage"
    EMPLOYEE_CHANGES_DELETE = "employee_changes.delete"
    CHECKLISTS_EDIT_ALL = "checklists.edit_all"
    LABOR_SUMMARY_VIEW = "labor.summary.view"
    LABOR_SUMMARY_DASHBOARD_VIEW = "labor.summary.dashboard.view"
    LABOR_SUMMARY_VIEW_FACT = "labor.summary.view_cost"
    LABOR_SUMMARY_VIEW_COST = LABOR_SUMMARY_VIEW_FACT
    LABOR_SUMMARY_SETTINGS_MANAGE = "labor.summary.settings.manage"
    ACCOUNTING_INVOICES_VIEW = "accounting.invoices.view"
    ACCOUNTING_INVOICES_CREATE = "accounting.invoices.create"
    ACCOUNTING_INVOICES_EDIT = "accounting.invoices.edit"
    ACCOUNTING_INVOICES_STATUS = "accounting.invoices.status"
    ACCOUNTING_INVOICES_DELETE = "accounting.invoices.delete"
    KNOWLEDGE_BASE_SECTION = "knowledge_base.section"
    # Backward-compatible aliases for legacy codes.
    KNOWLEDGE_BASE_VIEW = KNOWLEDGE_BASE_SECTION
    KNOWLEDGE_BASE_MANAGE = KNOWLEDGE_BASE_SECTION
    KNOWLEDGE_BASE_UPLOAD = KNOWLEDGE_BASE_SECTION


class PermissionCode:
    """Backward-compatible permission names used across routers."""

    SYSTEM_ADMIN = PermissionKey.SYSTEM_ADMIN
    STAFF_MANAGE_ALL = PermissionKey.STAFF_MANAGE_ALL
    STAFF_MANAGE_SUBORDINATES = PermissionKey.STAFF_MANAGE_SUBORDINATES
    STAFF_VIEW_SENSITIVE = PermissionKey.STAFF_VIEW_SENSITIVE
    ROLES_MANAGE = PermissionKey.ROLES_MANAGE
    POSITIONS_MANAGE = PermissionKey.POSITIONS_MANAGE
    POSITIONS_EDIT = PermissionKey.POSITIONS_EDIT
    POSITIONS_RATE_MANAGE = PermissionKey.POSITIONS_RATE_MANAGE
    USERS_VIEW = PermissionKey.USERS_VIEW
    USERS_MANAGE = PermissionKey.USERS_MANAGE
    COMPANIES_VIEW = PermissionKey.COMPANIES_VIEW
    COMPANIES_MANAGE = PermissionKey.COMPANIES_MANAGE
    RESTAURANTS_VIEW = PermissionKey.RESTAURANTS_VIEW
    RESTAURANTS_MANAGE = PermissionKey.RESTAURANTS_MANAGE
    INVENTORY_VIEW = PermissionKey.INVENTORY_VIEW
    INVENTORY_MANAGE = PermissionKey.INVENTORY_MANAGE
    INVENTORY_BOT_ACCESS = PermissionKey.INVENTORY_BOT_ACCESS
    INVENTORY_BALANCE_VIEW = PermissionKey.INVENTORY_BALANCE_VIEW
    INVENTORY_MOVEMENTS_VIEW = PermissionKey.INVENTORY_MOVEMENTS_VIEW
    INVENTORY_MOVEMENTS_CREATE = PermissionKey.INVENTORY_MOVEMENTS_CREATE
    INVENTORY_MOVEMENTS_EDIT = PermissionKey.INVENTORY_MOVEMENTS_EDIT
    INVENTORY_MOVEMENTS_MANAGE = PermissionKey.INVENTORY_MOVEMENTS_MANAGE
    INVENTORY_MOVEMENTS_DELETE = PermissionKey.INVENTORY_MOVEMENTS_DELETE
    INVENTORY_NOMENCLATURE_VIEW = PermissionKey.INVENTORY_NOMENCLATURE_VIEW
    INVENTORY_NOMENCLATURE_CREATE = PermissionKey.INVENTORY_NOMENCLATURE_CREATE
    INVENTORY_NOMENCLATURE_EDIT = PermissionKey.INVENTORY_NOMENCLATURE_EDIT
    INVENTORY_NOMENCLATURE_MANAGE = PermissionKey.INVENTORY_NOMENCLATURE_MANAGE
    INVENTORY_NOMENCLATURE_DELETE = PermissionKey.INVENTORY_NOMENCLATURE_DELETE
    PAYROLL_VIEW = PermissionKey.PAYROLL_VIEW
    PAYROLL_MANAGE = PermissionKey.PAYROLL_MANAGE
    PAYROLL_EXPORT = PermissionKey.PAYROLL_EXPORT
    PAYROLL_RESULTS_VIEW = PermissionKey.PAYROLL_RESULTS_VIEW
    PAYROLL_RESULTS_MANAGE = PermissionKey.PAYROLL_RESULTS_MANAGE
    PAYROLL_ADVANCE_VIEW = PermissionKey.PAYROLL_ADVANCE_VIEW
    PAYROLL_ADVANCE_CREATE = PermissionKey.PAYROLL_ADVANCE_CREATE
    PAYROLL_ADVANCE_EDIT = PermissionKey.PAYROLL_ADVANCE_EDIT
    PAYROLL_ADVANCE_STATUS_REVIEW = PermissionKey.PAYROLL_ADVANCE_STATUS_REVIEW
    PAYROLL_ADVANCE_STATUS_CONFIRM = PermissionKey.PAYROLL_ADVANCE_STATUS_CONFIRM
    PAYROLL_ADVANCE_STATUS_READY = PermissionKey.PAYROLL_ADVANCE_STATUS_READY
    PAYROLL_ADVANCE_STATUS_ALL = PermissionKey.PAYROLL_ADVANCE_STATUS_ALL
    PAYROLL_ADVANCE_DOWNLOAD = PermissionKey.PAYROLL_ADVANCE_DOWNLOAD
    PAYROLL_ADVANCE_POST = PermissionKey.PAYROLL_ADVANCE_POST
    PAYROLL_ADVANCE_DELETE = PermissionKey.PAYROLL_ADVANCE_DELETE
    TIMESHEET_EXPORT = PermissionKey.TIMESHEET_EXPORT
    STAFF_EMPLOYEES_EXPORT = PermissionKey.STAFF_EMPLOYEES_EXPORT
    KPI_VIEW = PermissionKey.KPI_VIEW
    KPI_MANAGE = PermissionKey.KPI_MANAGE
    KPI_METRICS_VIEW = PermissionKey.KPI_METRICS_VIEW
    KPI_METRICS_MANAGE = PermissionKey.KPI_METRICS_MANAGE
    KPI_METRIC_GROUPS_VIEW = PermissionKey.KPI_METRIC_GROUPS_VIEW
    KPI_METRIC_GROUPS_MANAGE = PermissionKey.KPI_METRIC_GROUPS_MANAGE
    KPI_RULES_ASSIGN = PermissionKey.KPI_RULES_ASSIGN
    KPI_FACTS_VIEW = PermissionKey.KPI_FACTS_VIEW
    KPI_FACTS_MANAGE = PermissionKey.KPI_FACTS_MANAGE
    KPI_RESULTS_VIEW = PermissionKey.KPI_RESULTS_VIEW
    KPI_PAYOUTS_VIEW = PermissionKey.KPI_PAYOUTS_VIEW
    KPI_PAYOUTS_MANAGE = PermissionKey.KPI_PAYOUTS_MANAGE
    TRAINING_VIEW = PermissionKey.TRAINING_VIEW
    TRAINING_MANAGE = PermissionKey.TRAINING_MANAGE
    IIKO_VIEW = PermissionKey.IIKO_VIEW
    IIKO_MANAGE = PermissionKey.IIKO_MANAGE
    IIKO_CATALOG_SYNC = PermissionKey.IIKO_CATALOG_SYNC
    SALES_REPORT_VIEW_QTY = PermissionKey.SALES_REPORT_VIEW_QTY
    SALES_REPORT_VIEW_MONEY = PermissionKey.SALES_REPORT_VIEW_MONEY
    SALES_TABLES_VIEW = PermissionKey.SALES_TABLES_VIEW
    SALES_TABLES_MANAGE = PermissionKey.SALES_TABLES_MANAGE
    SALES_DISHES_VIEW = PermissionKey.SALES_DISHES_VIEW
    SALES_DISHES_MANAGE = PermissionKey.SALES_DISHES_MANAGE
    RESTAURANTS_SETTINGS_VIEW = PermissionKey.RESTAURANTS_SETTINGS_VIEW
    RESTAURANTS_SETTINGS_MANAGE = PermissionKey.RESTAURANTS_SETTINGS_MANAGE
    STAFF_EMPLOYEES_VIEW = PermissionKey.STAFF_EMPLOYEES_VIEW
    STAFF_EMPLOYEES_MANAGE = PermissionKey.STAFF_EMPLOYEES_MANAGE
    STAFF_EMPLOYEES_RESTORE = PermissionKey.STAFF_EMPLOYEES_RESTORE
    STAFF_EMPLOYEES_IIKO_SYNC = PermissionKey.STAFF_EMPLOYEES_IIKO_SYNC
    STAFF_ROLES_ASSIGN = PermissionKey.STAFF_ROLES_ASSIGN
    STAFF_RATE_MANAGE = PermissionKey.STAFF_RATE_MANAGE
    STAFF_PORTAL_ACCESS = PermissionKey.STAFF_PORTAL_ACCESS
    EMPLOYEES_CARD_VIEW = PermissionKey.EMPLOYEES_CARD_VIEW
    EMPLOYEES_CARD_MANAGE = PermissionKey.EMPLOYEES_CARD_MANAGE
    ACCESS_CONTROL_READ = PermissionKey.ACCESS_CONTROL_READ
    ACCESS_CONTROL_MANAGE = PermissionKey.ACCESS_CONTROL_MANAGE
    IIKO_PRODUCTS_READ = PermissionKey.IIKO_PRODUCTS_READ
    IIKO_OLAP_PRODUCT = PermissionKey.IIKO_OLAP_PRODUCT
    IIKO_OLAP_READ = PermissionKey.IIKO_OLAP_READ
    STAFF_RATE_VIEW_ALL = PermissionKey.STAFF_RATE_VIEW_ALL
    MEDICAL_CHECKS_VIEW = PermissionKey.MEDICAL_CHECKS_VIEW
    MEDICAL_CHECKS_MANAGE = PermissionKey.MEDICAL_CHECKS_MANAGE
    CIS_DOCUMENTS_VIEW = PermissionKey.CIS_DOCUMENTS_VIEW
    CIS_DOCUMENTS_MANAGE = PermissionKey.CIS_DOCUMENTS_MANAGE
    EMPLOYEE_CHANGES_VIEW = PermissionKey.EMPLOYEE_CHANGES_VIEW
    EMPLOYEE_CHANGES_MANAGE = PermissionKey.EMPLOYEE_CHANGES_MANAGE
    EMPLOYEE_CHANGES_DELETE = PermissionKey.EMPLOYEE_CHANGES_DELETE
    CHECKLISTS_EDIT_ALL = PermissionKey.CHECKLISTS_EDIT_ALL
    LABOR_SUMMARY_VIEW = PermissionKey.LABOR_SUMMARY_VIEW
    LABOR_SUMMARY_DASHBOARD_VIEW = PermissionKey.LABOR_SUMMARY_DASHBOARD_VIEW
    LABOR_SUMMARY_VIEW_FACT = PermissionKey.LABOR_SUMMARY_VIEW_FACT
    LABOR_SUMMARY_VIEW_COST = PermissionKey.LABOR_SUMMARY_VIEW_FACT
    LABOR_SUMMARY_SETTINGS_MANAGE = PermissionKey.LABOR_SUMMARY_SETTINGS_MANAGE
    ACCOUNTING_INVOICES_VIEW = PermissionKey.ACCOUNTING_INVOICES_VIEW
    ACCOUNTING_INVOICES_CREATE = PermissionKey.ACCOUNTING_INVOICES_CREATE
    ACCOUNTING_INVOICES_EDIT = PermissionKey.ACCOUNTING_INVOICES_EDIT
    ACCOUNTING_INVOICES_STATUS = PermissionKey.ACCOUNTING_INVOICES_STATUS
    ACCOUNTING_INVOICES_DELETE = PermissionKey.ACCOUNTING_INVOICES_DELETE
    KNOWLEDGE_BASE_SECTION = PermissionKey.KNOWLEDGE_BASE_SECTION
    KNOWLEDGE_BASE_VIEW = PermissionKey.KNOWLEDGE_BASE_VIEW
    KNOWLEDGE_BASE_MANAGE = PermissionKey.KNOWLEDGE_BASE_MANAGE
    KNOWLEDGE_BASE_UPLOAD = PermissionKey.KNOWLEDGE_BASE_UPLOAD


LEGACY_ADMIN_ROLE_NAMES = {
    "admin",
    "administrator",
    "technical administrator",
    "технический администратор",
}

_REQUIRED_PERMISSIONS_ATTR = "_required_permission_keys"
_SUPERUSER_PERMISSION_KEYS = {
    PermissionKey.SYSTEM_ADMIN,
    PermissionKey.STAFF_MANAGE_ALL,
}
_COMPATIBILITY_ALIASES = {
    "users": PermissionKey.USERS_VIEW,
    "companies": PermissionKey.COMPANIES_VIEW,
    "restaurants": PermissionKey.RESTAURANTS_VIEW,
    "inventory": PermissionKey.INVENTORY_VIEW,
    "payroll": PermissionKey.PAYROLL_VIEW,
    "payroll_export": PermissionKey.PAYROLL_EXPORT,
    "payroll_results": PermissionKey.PAYROLL_RESULTS_VIEW,
    "payroll_advances": PermissionKey.PAYROLL_ADVANCE_VIEW,
    "kpi": PermissionKey.KPI_VIEW,
    "training": PermissionKey.TRAINING_VIEW,
    "training_events": PermissionKey.TRAINING_VIEW,
    "iiko": PermissionKey.IIKO_VIEW,
    "iiko_products_read": PermissionKey.SALES_DISHES_VIEW,
    "iiko_olap_product": PermissionKey.IIKO_CATALOG_SYNC,
    "iiko_olap_read": PermissionKey.SALES_REPORT_VIEW_QTY,
    "iiko_products.read": PermissionKey.SALES_DISHES_VIEW,
    "iiko_olap_product.manage": PermissionKey.IIKO_CATALOG_SYNC,
    "iiko_olap_read.view": PermissionKey.SALES_REPORT_VIEW_QTY,
    "staff_employees": PermissionKey.STAFF_EMPLOYEES_VIEW,
    "staff_portal": PermissionKey.STAFF_PORTAL_ACCESS,
    "employees_card": PermissionKey.EMPLOYEES_CARD_VIEW,
    "access_control": PermissionKey.ACCESS_CONTROL_READ,
    "medical_checks": PermissionKey.MEDICAL_CHECKS_VIEW,
    "cis_documents": PermissionKey.CIS_DOCUMENTS_VIEW,
    "checklists": PermissionKey.CHECKLISTS_EDIT_ALL,
    "knowledge_base": PermissionKey.KNOWLEDGE_BASE_SECTION,
    "knowledge_base.view": PermissionKey.KNOWLEDGE_BASE_SECTION,
    "knowledge_base.manage": PermissionKey.KNOWLEDGE_BASE_SECTION,
    "knowledge_base.upload": PermissionKey.KNOWLEDGE_BASE_SECTION,
}


def _normalize_key(key: Optional[str]) -> Optional[str]:
    if not key or not isinstance(key, str):
        return None
    normalized = key.strip().lower()
    return _COMPATIBILITY_ALIASES.get(normalized, normalized)


def _collect_codes_from_permissions(permissions: Sequence) -> Set[str]:
    collected: Set[str] = set()
    for perm in permissions or []:
        key = _normalize_key(getattr(perm, "api_router", None))
        if key:
            collected.add(key)
            continue
        # Backwards compatibility for legacy attributes
        legacy = _normalize_key(getattr(perm, "code", None))
        if legacy:
            collected.add(legacy)
    return collected


def _collect_position_permission_codes(user: Optional[User]) -> Set[str]:
    if not user:
        return set()
    position = getattr(user, "position", None)
    if not position:
        return set()
    return _collect_codes_from_permissions(getattr(position, "permissions", []) or [])


def _collect_role_permission_codes(user: Optional[User]) -> Set[str]:
    if not user:
        return set()
    # Roles act as templates for positions. If a user has a position,
    # we rely on position permissions only.
    if getattr(user, "position_id", None):
        return set()
    role = getattr(user, "role", None)
    if not role:
        return set()
    return _collect_codes_from_permissions(getattr(role, "permissions", []) or [])


def _collect_user_permission_codes(user: Optional[User]) -> Set[str]:
    if not user:
        return set()
    return _collect_codes_from_permissions(getattr(user, "direct_permissions", []) or [])


def get_user_permission_codes(user: Optional[User]) -> Set[str]:
    """Return a set of permission keys available to the user."""
    if not user:
        return set()

    cached = getattr(user, "_permission_codes_cache", None)
    if isinstance(cached, set):
        return set(cached)

    codes: Set[str] = set()
    codes.update(_collect_user_permission_codes(user))
    codes.update(_collect_position_permission_codes(user))
    codes.update(_collect_role_permission_codes(user))
    # Cache on ORM instance for the current request to avoid rebuilding
    # permission sets in tight loops (e.g. employee lists).
    try:
        setattr(user, "_permission_codes_cache", set(codes))
    except Exception:
        pass
    return codes


def has_permission(user: Optional[User], code: str) -> bool:
    """Check whether a user has the specific permission key."""
    normalized = _normalize_key(code)
    if not normalized:
        return False
    codes = get_user_permission_codes(user)
    if normalized in codes:
        return True
    # Superuser check
    return bool(codes.intersection(_SUPERUSER_PERMISSION_KEYS))


def has_any_permission(user: Optional[User], codes: Iterable[str]) -> bool:
    """Check whether a user has at least one permission from the iterable."""
    target = {_normalize_key(code) for code in codes if _normalize_key(code)}
    if not target:
        return False
    user_codes = get_user_permission_codes(user)
    if user_codes.intersection(target):
        return True
    return bool(user_codes.intersection(_SUPERUSER_PERMISSION_KEYS))


_RATE_FULL_ACCESS_LEVEL = 5


def _get_user_role(user: Optional[User]) -> Optional[Role]:
    if not user:
        return None
    role = getattr(user, "role", None)
    if role:
        return role
    position = getattr(user, "position", None)
    return getattr(position, "role", None) if position else None


def can_view_rate(viewer: Optional[User], target: Optional[User]) -> bool:
    if not viewer or not target:
        return False
    if has_permission(viewer, PermissionKey.STAFF_RATE_VIEW_ALL):
        return True
    if getattr(viewer, "id", None) == getattr(target, "id", None):
        return True
    viewer_role = _get_user_role(viewer)
    if not viewer_role:
        return False
    viewer_level = viewer_role.level if viewer_role.level is not None else 0
    if viewer_level >= _RATE_FULL_ACCESS_LEVEL:
        return True
    target_role = _get_user_role(target)
    target_level = target_role.level if target_role and target_role.level is not None else -1
    return viewer_level > target_level


def has_global_access(user: Optional[User]) -> bool:
    """Return True if user is considered to have system-wide access."""
    if not user:
        return False
    codes = get_user_permission_codes(user)
    if codes.intersection(_SUPERUSER_PERMISSION_KEYS):
        return True
    role = getattr(user, "role", None)
    name = getattr(role, "name", None)
    if not name:
        username = getattr(user, "username", "") or ""
        # Fallback for default admin accounts without explicit role/permissions.
        if username.strip().lower() in {"admin", "administrator", "technical administrator"}:
            return True
        return False
    return name.strip().lower() in LEGACY_ADMIN_ROLE_NAMES


def ensure_permissions(user: Optional[User], *codes: str) -> None:
    """Raise HTTP 403 if the user lacks required permissions."""
    if not codes:
        return
    if has_global_access(user):
        return
    if has_any_permission(user, codes):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав для выполнения операции.",
    )


def ensure_permission(user: Optional[User], code: str) -> None:
    """Shortcut for single permission check."""
    ensure_permissions(user, code)


def _current_user_dependency():
    from backend.utils import get_current_user  # Imported lazily to avoid circular references

    return get_current_user


def require_permissions(*codes: str):
    """FastAPI dependency that ensures current user has at least one of the given permissions."""

    async def dependency(user: User = Depends(_current_user_dependency())) -> User:
        ensure_permissions(user, *codes)
        return user

    normalized = tuple(dict.fromkeys(filter(None, (_normalize_key(code) for code in codes))))
    setattr(dependency, _REQUIRED_PERMISSIONS_ATTR, normalized)
    return dependency


def require_permission(code: str):
    """FastAPI dependency that ensures current user has the given permission."""
    return require_permissions(code)


def get_required_permission_codes(callable_obj) -> Tuple[str, ...]:
    """Return permission codes attached to a dependency created via require_permissions."""
    codes = getattr(callable_obj, _REQUIRED_PERMISSIONS_ATTR, ())
    if isinstance(codes, tuple):
        return codes
    if isinstance(codes, (list, set)):
        return tuple(codes)
    return ()


def collect_permission_codes(dependant: Optional[Dependant]) -> Set[str]:
    """Recursively collect permission codes from a FastAPI dependant tree."""
    collected: Set[str] = set()
    if dependant is None:
        return collected

    stack = [dependant]
    seen: Set[int] = set()
    while stack:
        current = stack.pop()
        if current is None:
            continue
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        if current.call is not None:
            collected.update(get_required_permission_codes(current.call))
        stack.extend(current.dependencies or [])
        stack.extend(getattr(current, "sub_dependants", []) or [])
    return collected


def can_manage_user(viewer: Optional[User], target: Optional[User]) -> bool:
    """Return True if viewer can manage target based on role permissions (no position hierarchy)."""
    if not viewer or not target:
        return False
    if viewer.id == target.id:
        return True
    if has_global_access(viewer):
        return True
    if has_permission(viewer, PermissionKey.STAFF_MANAGE_ALL):
        return True
    if not has_permission(viewer, PermissionKey.STAFF_MANAGE_SUBORDINATES):
        return False

    # Сравниваем уровни ролей (level); большее/равное значение — выше или равный ранг.
    viewer_role = _get_user_role(viewer)
    target_role = _get_user_role(target)
    if viewer_role:
        if not target_role:
            return True
        try:
            if viewer_role.level is not None and target_role.level is not None:
                return viewer_role.level >= target_role.level
        except Exception:
            pass

    return False


def ensure_can_manage_user(viewer: User, target: User) -> None:
    """Raise HTTP 403 if viewer cannot manage target."""
    if not can_manage_user(viewer, target):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления выбранным пользователем.",
        )


def require_router_permission(router_key: str):
    """Convenience dependency for router-level permission checks."""
    return require_permission(router_key)
