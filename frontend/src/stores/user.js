import { defineStore } from 'pinia';
import { fetchUser } from '@/api';
import { logoutUser } from '@/api/auth';

export const useUserStore = defineStore('user', {
    state: () => ({
        id: null,
        login: '',
        firstName: '',
        lastName: '',
        fullName: '',
        roleName: '',
        positionName: '',
        positionId: null,
        token: '',
        rate: null,
        permissions: [],
        hasFullRestaurantAccess: false,
        hasGlobalAccess: false,
        restaurantIds: [],
        workplaceRestaurantId: null,
        restaurantSubdivisionId: null,
        restaurantSubdivisionName: '',
        restaurantSubdivisionIsMulti: false,
        isFired: false,
    }),
    actions: {
        setUser(data = {}) {
            if ('id' in data) {
                this.id = data.id ?? null;
            }
            if ('login' in data) {
                this.login = data.login ?? '';
            }
            if ('firstName' in data) {
                this.firstName = data.firstName ?? '';
            }
            if ('lastName' in data) {
                this.lastName = data.lastName ?? '';
            }
            if ('fullName' in data) {
                this.fullName = (data.fullName ?? '').trim();
            } else if ('firstName' in data || 'lastName' in data) {
                this.fullName = `${this.firstName} ${this.lastName}`.trim();
            }
            if ('roleName' in data) {
                this.roleName = data.roleName ?? '';
            }
            if ('positionName' in data) {
                this.positionName = data.positionName ?? '';
            }
            if ('positionId' in data) {
                const parsed = Number(data.positionId);
                this.positionId = Number.isFinite(parsed) ? parsed : null;
            }
            if ('rate' in data) {
                this.rate = typeof data.rate === 'number' ? data.rate : null;
            }
            if ('token' in data) {
                this.token = data.token ?? '';
            }
            if ('permissions' in data) {
                const normalized = Array.isArray(data.permissions)
                    ? Array.from(
                          new Set(
                              data.permissions
                                  .filter((code) => typeof code === 'string')
                                  .map((code) => code.trim().toLowerCase())
                                  .filter(Boolean),
                          ),
                      )
                    : [];
                this.permissions = normalized;
            }
            if ('hasFullRestaurantAccess' in data) {
                this.hasFullRestaurantAccess = Boolean(data.hasFullRestaurantAccess);
            }
            if ('hasGlobalAccess' in data) {
                this.hasGlobalAccess = Boolean(data.hasGlobalAccess);
            }
            if ('restaurantIds' in data) {
                this.restaurantIds = Array.isArray(data.restaurantIds)
                    ? data.restaurantIds
                          .map((id) => Number(id))
                          .filter((id) => Number.isFinite(id))
                    : [];
            }
            if ('workplaceRestaurantId' in data) {
                const parsed = Number(data.workplaceRestaurantId);
                this.workplaceRestaurantId = Number.isFinite(parsed) ? parsed : null;
            }
            if ('restaurantSubdivisionId' in data) {
                const parsed = Number(data.restaurantSubdivisionId);
                this.restaurantSubdivisionId = Number.isFinite(parsed) ? parsed : null;
            }
            if ('restaurantSubdivisionName' in data) {
                this.restaurantSubdivisionName = data.restaurantSubdivisionName || '';
            }
            if ('restaurantSubdivisionIsMulti' in data) {
                this.restaurantSubdivisionIsMulti = Boolean(data.restaurantSubdivisionIsMulti);
            }
            if ('isFired' in data) {
                this.isFired = Boolean(data.isFired);
            }
        },
        clearUser() {
            this.id = null;
            this.login = '';
            this.firstName = '';
            this.lastName = '';
            this.fullName = '';
            this.roleName = '';
            this.positionName = '';
            this.positionId = null;
            this.rate = null;
            this.token = '';
            this.permissions = [];
            this.hasFullRestaurantAccess = false;
            this.hasGlobalAccess = false;
            this.restaurantIds = [];
            this.workplaceRestaurantId = null;
            this.restaurantSubdivisionId = null;
            this.restaurantSubdivisionName = '';
            this.restaurantSubdivisionIsMulti = false;
            this.isFired = false;
        },
        async logout() {
            try {
                await logoutUser();
            } catch {
                // local cleanup should still happen even if the backend cookie is already gone
            }
            this.clearUser();
            localStorage.removeItem('pinia-user');
            sessionStorage.removeItem('pinia-user');
        },
        setFiredFromDetail(detail) {
            if (typeof detail !== 'string') {
                return false;
            }
            const normalized = detail.toLowerCase();
            if (normalized.includes('fired') || normalized.includes('\u0443\u0432\u043e\u043b\u0435\u043d')) {
                this.isFired = true;
                return true;
            }
            return false;
        },
        async fetchUserFromApi() {
            if (!this.id) return;

            try {
                const user = await fetchUser(this.id);
                const permissions = collectPermissionCodes(user);
                const restaurants = Array.isArray(user?.restaurants)
                    ? user.restaurants
                          .map((restaurant) => Number(restaurant?.id))
                          .filter((id) => Number.isFinite(id))
                    : Array.isArray(user?.restaurant_ids)
                        ? user.restaurant_ids
                              .map((id) => Number(id))
                              .filter((id) => Number.isFinite(id))
                        : [];
                this.setUser({
                    id: user.id,
                    login: user.username ?? '',
                    firstName: user.first_name ?? '',
                    lastName: user.last_name ?? '',
                    fullName: `${user.first_name ?? ''} ${user.last_name ?? ''}`.trim(),
                    roleName: user.role?.name ?? '',
                    positionName: user.position?.name ?? '',
                    rate: typeof user.rate === 'number' ? user.rate : null,
                    token: this.token,
                    permissions,
                    hasFullRestaurantAccess: Boolean(user?.has_full_restaurant_access),
                    hasGlobalAccess: Boolean(user?.has_global_access),
                    restaurantIds: restaurants,
                    workplaceRestaurantId: user?.workplace_restaurant_id ?? null,
                    isFired: Boolean(user?.fired ?? user?.is_fired),
                });
            } catch (e) {
                this.setFiredFromDetail(e?.response?.data?.detail);
                console.error('Ошибка загрузки данных пользователя:', e);
            }
        },
    },
    getters: {
        permissionSet(state) {
            return new Set(state.permissions.map((code) => code.trim().toLowerCase()));
        },
        hasPermission(state) {
            return (code) => {
                if (!code || typeof code !== 'string') {
                    return false;
                }
                const normalized = code.trim().toLowerCase();
                if (!normalized) {
                    return false;
                }
                const set = this.permissionSet;
                if (set.has(normalized)) {
                    return true;
                }
                if (state.hasGlobalAccess) {
                    return true;
                }
                if (set.has('system.admin') || set.has('staff.manage_all')) {
                    return true;
                }
                return false;
            };
        },
        hasAnyPermission() {
            return (...codes) => {
                if (!codes || !codes.length) {
                    return false;
                }
                return codes.some((code) => this.hasPermission(code));
            };
        },
        isAuthenticated(state) {
            return Boolean(state.id);
        },
    },
});

function collectPermissionCodes(user) {
    const set = new Set();
    const add = (value) => {
        if (!value) {
            return;
        }
        if (Array.isArray(value)) {
            value.forEach((item) => add(item));
            return;
        }
        if (typeof value === 'string') {
            const normalized = value.trim().toLowerCase();
            if (normalized) {
                set.add(normalized);
            }
            return;
        }
        if (typeof value === 'object') {
            const direct = value.permission_code || value.code || value.api_router;
            if (typeof direct === 'string') {
                add(direct);
            }
        }
    };

    add(user?.permission_codes);
    add(user?.permissions);
    add(user?.direct_permissions);
    add(user?.role?.permission_codes);
    add(user?.role?.permissions);
    add(user?.position?.permission_codes);
    add(user?.position?.permissions);

    return Array.from(set);
}
