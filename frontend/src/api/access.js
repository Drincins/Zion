import { api, buildQueryParams, cachedGet, invalidateCacheScope } from './client';

const ACCESS_BOOTSTRAP_SCOPE = 'access-bootstrap';
const ACCESS_BOOTSTRAP_TTL_MS = 60 * 60 * 1000;
const ACCESS_ROLE_PERMISSIONS_SCOPE = 'access-role-permissions';
const ACCESS_ROLE_PERMISSIONS_MAP_SCOPE = 'access-role-permissions-map';
const ACCESS_POSITION_PERMISSIONS_SCOPE = 'access-position-permissions';
const ACCESS_POSITION_PERMISSIONS_MAP_SCOPE = 'access-position-permissions-map';
const ACCESS_PAYMENT_FORMATS_SCOPE = 'access-payment-formats';
const ACCESS_RESTAURANT_SUBDIVISIONS_SCOPE = 'access-restaurant-subdivisions';

async function readAccessBootstrapField(fieldName) {
    try {
        const data = await fetchAccessBootstrap();
        if (data && Array.isArray(data[fieldName])) {
            return data[fieldName];
        }
    } catch {
        // Fallback to dedicated endpoints on bootstrap errors.
    }
    return null;
}

export async function fetchAccessRoles() {
    const bootstrapRoles = await readAccessBootstrapField('roles');
    if (bootstrapRoles !== null) {
        return bootstrapRoles;
    }
    return await cachedGet('/api/access/roles', {
        cacheScope: 'access-roles',
        ttlMs: ACCESS_BOOTSTRAP_TTL_MS
    });
}

export async function fetchAccessBootstrap() {
    return await cachedGet('/api/access/bootstrap', {
        cacheScope: ACCESS_BOOTSTRAP_SCOPE,
        ttlMs: ACCESS_BOOTSTRAP_TTL_MS
    });
}

export async function fetchRolePermissions(roleId) {
    return await cachedGet(`/api/access/roles/${roleId}/permissions`, {
        cacheScope: ACCESS_ROLE_PERMISSIONS_SCOPE,
        ttlMs: 2 * 60 * 1000
    });
}

export async function fetchRolePermissionsMap(roleIds = []) {
    const params = buildQueryParams({ ids: roleIds });
    const query = params.toString();
    const path = query
        ? `/api/access/roles/permissions-map?${query}`
        : '/api/access/roles/permissions-map';
    return await cachedGet(path, {
        cacheScope: ACCESS_ROLE_PERMISSIONS_MAP_SCOPE,
        ttlMs: 2 * 60 * 1000
    });
}

export async function updateRolePermissions(roleId, permissionCodes = []) {
    const { data } = await api.put(`/api/access/roles/${roleId}/permissions`, {
        permission_codes: permissionCodes
    });
    invalidateCacheScope(ACCESS_ROLE_PERMISSIONS_SCOPE);
    invalidateCacheScope(ACCESS_ROLE_PERMISSIONS_MAP_SCOPE);
    return data;
}

export async function fetchAccessPositions() {
    const bootstrapPositions = await readAccessBootstrapField('positions');
    if (bootstrapPositions !== null) {
        return bootstrapPositions;
    }
    return await cachedGet('/api/access/positions', {
        cacheScope: 'access-positions',
        ttlMs: ACCESS_BOOTSTRAP_TTL_MS
    });
}

export async function fetchPaymentFormats() {
    const bootstrapPaymentFormats = await readAccessBootstrapField('payment_formats');
    if (bootstrapPaymentFormats !== null) {
        return bootstrapPaymentFormats;
    }
    return await cachedGet('/api/access/payment-formats', {
        cacheScope: ACCESS_PAYMENT_FORMATS_SCOPE,
        ttlMs: ACCESS_BOOTSTRAP_TTL_MS
    });
}

export async function fetchRestaurantSubdivisions() {
    const bootstrapSubdivisions = await readAccessBootstrapField('restaurant_subdivisions');
    if (bootstrapSubdivisions !== null) {
        return bootstrapSubdivisions;
    }
    return await cachedGet('/api/access/restaurant-subdivisions', {
        cacheScope: ACCESS_RESTAURANT_SUBDIVISIONS_SCOPE,
        ttlMs: ACCESS_BOOTSTRAP_TTL_MS
    });
}

export async function createRestaurantSubdivision(payload) {
    const { data } = await api.post('/api/access/restaurant-subdivisions', payload);
    invalidateCacheScope(ACCESS_BOOTSTRAP_SCOPE);
    invalidateCacheScope(ACCESS_RESTAURANT_SUBDIVISIONS_SCOPE);
    return data;
}

export async function updateRestaurantSubdivision(subdivisionId, payload) {
    const { data } = await api.patch(`/api/access/restaurant-subdivisions/${subdivisionId}`, payload);
    invalidateCacheScope(ACCESS_BOOTSTRAP_SCOPE);
    invalidateCacheScope(ACCESS_RESTAURANT_SUBDIVISIONS_SCOPE);
    return data;
}

export async function deleteRestaurantSubdivision(subdivisionId) {
    await api.delete(`/api/access/restaurant-subdivisions/${subdivisionId}`);
    invalidateCacheScope(ACCESS_BOOTSTRAP_SCOPE);
    invalidateCacheScope(ACCESS_RESTAURANT_SUBDIVISIONS_SCOPE);
}

export async function createAccessPosition(payload) {
    const { data } = await api.post('/api/access/positions', payload);
    invalidateCacheScope('access-positions');
    invalidateCacheScope(ACCESS_BOOTSTRAP_SCOPE);
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_SCOPE);
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_MAP_SCOPE);
    return data;
}

export async function updateAccessPosition(positionId, payload) {
    const { data } = await api.patch(`/api/access/positions/${positionId}`, payload);
    invalidateCacheScope('access-positions');
    invalidateCacheScope(ACCESS_BOOTSTRAP_SCOPE);
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_SCOPE);
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_MAP_SCOPE);
    return data;
}

export async function fetchPositionChangeOrders(positionId) {
    const { data } = await api.get(`/api/access/positions/${positionId}/change-orders`);
    return data;
}

export async function createPositionChangeOrder(positionId, payload) {
    const { data } = await api.post(`/api/access/positions/${positionId}/change-orders`, payload);
    invalidateCacheScope('access-positions');
    invalidateCacheScope(ACCESS_BOOTSTRAP_SCOPE);
    return data;
}

export async function cancelPositionChangeOrder(positionId, orderId) {
    const { data } = await api.post(`/api/access/positions/${positionId}/change-orders/${orderId}/cancel`);
    invalidateCacheScope('access-positions');
    invalidateCacheScope(ACCESS_BOOTSTRAP_SCOPE);
    return data;
}

export async function deleteAccessPosition(positionId) {
    await api.delete(`/api/access/positions/${positionId}`);
    invalidateCacheScope('access-positions');
    invalidateCacheScope(ACCESS_BOOTSTRAP_SCOPE);
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_SCOPE);
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_MAP_SCOPE);
}

export async function fetchAccessPermissions() {
    const bootstrapPermissions = await readAccessBootstrapField('permissions');
    if (bootstrapPermissions !== null) {
        return bootstrapPermissions;
    }
    const { data } = await api.get('/api/access/permissions');
    return data;
}

export async function fetchUserPermissions(userId) {
    const { data } = await api.get(`/api/access/users/${userId}/permissions`);
    return data;
}

export async function addUserPermission(userId, permissionCode) {
    const payload = { permission_code: permissionCode };
    const { data } = await api.post(`/api/access/users/${userId}/permissions`, payload);
    return data;
}

export async function removeUserPermission(userId, permissionCode) {
    await api.delete(`/api/access/users/${userId}/permissions/${encodeURIComponent(permissionCode)}`);
}

export async function fetchPositionPermissions(positionId) {
    return await cachedGet(`/api/access/positions/${positionId}/permissions`, {
        cacheScope: ACCESS_POSITION_PERMISSIONS_SCOPE,
        ttlMs: 2 * 60 * 1000
    });
}

export async function fetchPositionPermissionsMap(positionIds = []) {
    const params = buildQueryParams({ ids: positionIds });
    const query = params.toString();
    const path = query
        ? `/api/access/positions/permissions-map?${query}`
        : '/api/access/positions/permissions-map';
    return await cachedGet(path, {
        cacheScope: ACCESS_POSITION_PERMISSIONS_MAP_SCOPE,
        ttlMs: 2 * 60 * 1000
    });
}

export async function addPositionPermission(positionId, permissionCode) {
    const { data } = await api.post(`/api/access/positions/${positionId}/permissions`, {
        permission_code: permissionCode
    });
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_SCOPE);
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_MAP_SCOPE);
    return data;
}

export async function removePositionPermission(positionId, permissionCode) {
    await api.delete(
        `/api/access/positions/${positionId}/permissions/${encodeURIComponent(permissionCode)}`
    );
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_SCOPE);
    invalidateCacheScope(ACCESS_POSITION_PERMISSIONS_MAP_SCOPE);
}
