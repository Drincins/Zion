import { api, cachedGet } from './client';

export async function fetchCompanies(options = {}) {
    return await cachedGet('/api/companies/', {
        cacheScope: 'companies',
        ttlMs: 60 * 60 * 1000,
        skipGlobalLoading: options?.skipGlobalLoading === true,
    });
}

export async function fetchRoles(options = {}) {
    return await cachedGet('/api/users/roles', {
        cacheScope: 'roles',
        ttlMs: 6 * 60 * 60 * 1000,
        skipGlobalLoading: options?.skipGlobalLoading === true,
    });
}

export async function fetchRestaurants(params = {}, options = {}) {
    return await cachedGet('/api/restaurants/', {
        params,
        cacheScope: 'restaurants',
        ttlMs: 10 * 60 * 1000,
        skipGlobalLoading: options?.skipGlobalLoading === true,
    });
}

export async function fetchUser(userId) {
    const { data } = await api.get(`/api/users/${userId}`);
    return data;
}

export async function createUser(payload) {
    const { data } = await api.post('/api/users/', payload);
    return data;
}

export async function updateUser(userId, payload) {
    const { data } = await api.put(`/api/users/${userId}`, payload);
    return data;
}
