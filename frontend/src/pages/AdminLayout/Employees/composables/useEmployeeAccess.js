import { computed } from 'vue';
import { isSuperAdminRole as isSuperAdminRoleByName, isSystemLevelRole } from '@/utils/roles';
import {
    PAYROLL_EXPORT_PERMISSION,
    PAYROLL_MANAGE_PERMISSION,
    STAFF_AUTH_CREDENTIALS_VIEW_PERMISSIONS,
    STAFF_CIS_DOCUMENTS_VIEW_PERMISSIONS,
    STAFF_CHANGES_VIEW_PERMISSIONS,
    STAFF_EMPLOYEE_ORDERS_MANAGE_PERMISSIONS,
    STAFF_CIS_DOCUMENTS_MANAGE_PERMISSIONS,
    STAFF_CREATE_PERMISSIONS,
    STAFF_DOCUMENTS_VIEW_PERMISSIONS,
    STAFF_EDIT_RATES_PERMISSIONS,
    STAFF_EDIT_ROLES_PERMISSIONS,
    STAFF_IIKO_SYNC_PERMISSIONS,
    STAFF_LOAD_COMPANIES_PERMISSIONS,
    STAFF_LOAD_POSITIONS_PERMISSIONS,
    STAFF_LOAD_RESTAURANTS_PERMISSIONS,
    STAFF_LOAD_ROLES_PERMISSIONS,
    STAFF_MANAGE_PERMISSIONS,
    STAFF_MEDICAL_CHECKS_VIEW_PERMISSIONS,
    STAFF_MEDICAL_CHECKS_MANAGE_PERMISSIONS,
    STAFF_RESTORE_PERMISSIONS,
    STAFF_USER_PERMISSIONS_MANAGE_PERMISSIONS,
    STAFF_VIEW_WITH_SYSTEM_PERMISSIONS,
    SYSTEM_ADMIN_PERMISSION,
    STAFF_EMPLOYEES_EXPORT_PERMISSION,
    TIMESHEET_EXPORT_PERMISSION,
    TRAININGS_MANAGE_PERMISSIONS,
    TRAININGS_VIEW_PERMISSIONS,
} from '@/accessPolicy';

const RESTRICTED_CREDENTIAL_ROLES = new Set([
    'тайм контроль',
    'тайм-контроль',
    'time control'
]);

export function useEmployeeAccess(userStore) {
    const normalizedUserRole = computed(() => (userStore.roleName || '').trim().toLowerCase());

    const isSuperAdminRole = computed(() => isSuperAdminRoleByName(userStore.roleName));
    const isSystemRole = computed(() => isSystemLevelRole(userStore.roleName));

    const canViewSensitiveStaffFields = computed(
        () =>
            userStore.hasPermission(SYSTEM_ADMIN_PERMISSION) ||
            isSystemRole.value
    );

    const canEditIikoId = computed(
        () =>
            userStore.hasPermission(SYSTEM_ADMIN_PERMISSION) ||
            isSystemRole.value
    );

    const canViewAuthCredentials = computed(() => {
        if (isSuperAdminRole.value) {
            return true;
        }
        if (RESTRICTED_CREDENTIAL_ROLES.has(normalizedUserRole.value)) {
            return false;
        }
        return userStore.hasAnyPermission(...STAFF_AUTH_CREDENTIALS_VIEW_PERMISSIONS);
    });

    const canViewEmployees = computed(() =>
        userStore.hasAnyPermission(...STAFF_VIEW_WITH_SYSTEM_PERMISSIONS)
    );

    const canManageEmployees = computed(() =>
        userStore.hasAnyPermission(...STAFF_MANAGE_PERMISSIONS)
    );

    const canEditRoles = computed(() =>
        userStore.hasAnyPermission(...STAFF_EDIT_ROLES_PERMISSIONS)
    );

    const canEditRates = computed(() =>
        userStore.hasAnyPermission(...STAFF_EDIT_RATES_PERMISSIONS)
    );

    const canCreateEmployees = computed(() =>
        userStore.hasAnyPermission(...STAFF_CREATE_PERMISSIONS)
    );

    const canSyncEmployeeToIiko = computed(() =>
        userStore.hasAnyPermission(...STAFF_IIKO_SYNC_PERMISSIONS)
    );

    const canEditFullAccess = computed(() =>
        userStore.hasAnyPermission(...STAFF_CREATE_PERMISSIONS)
    );

    const canManageUserPermissions = computed(() =>
        userStore.hasAnyPermission(...STAFF_USER_PERMISSIONS_MANAGE_PERMISSIONS)
    );

    const canLoadRoles = computed(() =>
        userStore.hasAnyPermission(...STAFF_LOAD_ROLES_PERMISSIONS)
    );

    const canLoadRestaurants = computed(() =>
        userStore.hasAnyPermission(...STAFF_LOAD_RESTAURANTS_PERMISSIONS)
    );

    const canLoadCompanies = computed(() =>
        userStore.hasAnyPermission(...STAFF_LOAD_COMPANIES_PERMISSIONS)
    );

    const canLoadPositions = computed(() =>
        userStore.hasAnyPermission(...STAFF_LOAD_POSITIONS_PERMISSIONS)
    );

    const canExportPayroll = computed(() => {
        const set = userStore.permissionSet;
        return set.has(PAYROLL_EXPORT_PERMISSION) || userStore.hasGlobalAccess || set.has(SYSTEM_ADMIN_PERMISSION);
    });

    const canBulkPayrollAdjust = computed(() => {
        const set = userStore.permissionSet;
        return set.has(SYSTEM_ADMIN_PERMISSION) || set.has(PAYROLL_MANAGE_PERMISSION) || userStore.hasGlobalAccess;
    });

    const canExportTimesheet = computed(() => {
        const set = userStore.permissionSet;
        return set.has(TIMESHEET_EXPORT_PERMISSION) || userStore.hasGlobalAccess || set.has(SYSTEM_ADMIN_PERMISSION);
    });

    const canDownloadEmployeesList = computed(
        () => {
            const set = userStore.permissionSet;
            return (
                canViewEmployees.value &&
                (
                    set.has(STAFF_EMPLOYEES_EXPORT_PERMISSION) ||
                    userStore.hasGlobalAccess ||
                    set.has(SYSTEM_ADMIN_PERMISSION)
                )
            );
        }
    );

    const canViewTrainings = computed(() => {
        const set = userStore.permissionSet;
        return (
            TRAININGS_VIEW_PERMISSIONS.some((code) => set.has(code)) ||
            userStore.hasGlobalAccess ||
            set.has(SYSTEM_ADMIN_PERMISSION)
        );
    });

    const canManageTrainings = computed(() => {
        const set = userStore.permissionSet;
        return (
            TRAININGS_MANAGE_PERMISSIONS.some((code) => set.has(code)) ||
            userStore.hasGlobalAccess ||
            set.has(SYSTEM_ADMIN_PERMISSION)
        );
    });

    const canViewDocuments = computed(() =>
        userStore.hasAnyPermission(...STAFF_DOCUMENTS_VIEW_PERMISSIONS)
    );

    const canViewMedicalChecks = computed(() =>
        userStore.hasAnyPermission(...STAFF_MEDICAL_CHECKS_VIEW_PERMISSIONS)
    );

    const canViewCisDocuments = computed(() =>
        userStore.hasAnyPermission(...STAFF_CIS_DOCUMENTS_VIEW_PERMISSIONS)
    );

    const canManageMedicalChecks = computed(() =>
        userStore.hasAnyPermission(...STAFF_MEDICAL_CHECKS_MANAGE_PERMISSIONS)
    );

    const canManageCisDocuments = computed(() =>
        userStore.hasAnyPermission(...STAFF_CIS_DOCUMENTS_MANAGE_PERMISSIONS)
    );

    const canManageDocuments = computed(
        () => canManageMedicalChecks.value || canManageCisDocuments.value
    );

    const canViewEmployeeChanges = computed(() =>
        userStore.hasAnyPermission(...STAFF_CHANGES_VIEW_PERMISSIONS)
    );

    const canManageEmployeeChangeOrders = computed(() =>
        userStore.hasAnyPermission(...STAFF_EMPLOYEE_ORDERS_MANAGE_PERMISSIONS)
    );

    const canRestoreEmployees = computed(() =>
        userStore.hasAnyPermission(...STAFF_RESTORE_PERMISSIONS)
    );

    return {
        isSuperAdminRole,
        canViewSensitiveStaffFields,
        canEditIikoId,
        canViewAuthCredentials,
        canViewEmployees,
        canManageEmployees,
        canEditRoles,
        canEditRates,
        canCreateEmployees,
        canSyncEmployeeToIiko,
        canEditFullAccess,
        canManageUserPermissions,
        canLoadRoles,
        canLoadRestaurants,
        canLoadCompanies,
        canLoadPositions,
        canExportPayroll,
        canBulkPayrollAdjust,
        canExportTimesheet,
        canDownloadEmployeesList,
        canViewTrainings,
        canManageTrainings,
        canViewDocuments,
        canViewMedicalChecks,
        canViewCisDocuments,
        canManageMedicalChecks,
        canManageCisDocuments,
        canManageDocuments,
        canViewEmployeeChanges,
        canManageEmployeeChangeOrders,
        canRestoreEmployees
    };
}
