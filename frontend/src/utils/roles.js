const SUPER_ADMIN_ROLE_NAMES = new Set([
    'суперадмин',
    'супер админ',
    'супер-админ',
    'superadmin',
    'super admin'
]);

const SYSTEM_LEVEL_ROLE_NAMES = new Set([
    ...SUPER_ADMIN_ROLE_NAMES,
    'системный админ',
    'системный администратор'
]);

export function isSuperAdminRole(roleName = '') {
    return SUPER_ADMIN_ROLE_NAMES.has(String(roleName).trim().toLowerCase());
}

export function isSystemLevelRole(roleName = '') {
    return SYSTEM_LEVEL_ROLE_NAMES.has(String(roleName).trim().toLowerCase());
}
