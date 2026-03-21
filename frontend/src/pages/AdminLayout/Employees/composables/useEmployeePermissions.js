import { computed, ref } from 'vue';
import { useToast } from 'vue-toastification';
import {
    addUserPermission,
    fetchAccessPermissions,
    fetchPositionPermissions,
    fetchUserPermissions,
    removeUserPermission,
} from '@/api';

export function useEmployeePermissions({
    activeEmployee,
    canManageUserPermissions,
}) {
    const toast = useToast();

    const userPermissionCatalog = ref([]);
    const userPermissionCatalogLoading = ref(false);
    const userPermissions = ref([]);
    const userPositionPermissions = ref([]);
    const userPermissionsLoading = ref(false);
    const userPermissionUpdating = ref({});
    const loadedPermissionsEmployeeId = ref(null);
    const loadedPermissionsPositionId = ref(null);
    let loadUserPermissionsPromise = null;

    const userAssignedPermissionCodes = computed(() => {
        const set = new Set();
        const combined = []
            .concat(userPermissions.value || [])
            .concat(userPositionPermissions.value || []);
        for (const permission of combined) {
            const code =
                typeof permission?.code === 'string'
                    ? permission.code
                    : typeof permission?.api_router === 'string'
                    ? permission.api_router
                    : '';
            if (code && typeof code === 'string') {
                set.add(code);
            }
        }
        return Array.from(set);
    });

    const userExplicitPermissionSet = computed(() => {
        const set = new Set();
        for (const permission of userPermissions.value || []) {
            const code =
                typeof permission?.code === 'string'
                    ? permission.code
                    : typeof permission?.api_router === 'string'
                    ? permission.api_router
                    : '';
            if (code && typeof code === 'string') {
                set.add(code);
            }
        }
        return set;
    });

    async function loadUserPermissionCatalog() {
        if (
            !canManageUserPermissions.value ||
            userPermissionCatalogLoading.value ||
            userPermissionCatalog.value.length
        ) {
            return;
        }
        userPermissionCatalogLoading.value = true;
        try {
            const data = await fetchAccessPermissions();
            userPermissionCatalog.value = Array.isArray(data) ? data : [];
        } catch (error) {
            const detail = error?.response?.data?.detail;
            userPermissionCatalog.value = [];
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            userPermissionCatalogLoading.value = false;
        }
    }

    async function loadUserPermissions(options = {}) {
        const force = Boolean(options?.force);
        if (!activeEmployee.value || !canManageUserPermissions.value) {
            userPermissions.value = [];
            userPositionPermissions.value = [];
            loadedPermissionsEmployeeId.value = null;
            loadedPermissionsPositionId.value = null;
            return;
        }

        const employeeId = Number(activeEmployee.value.id);
        if (!Number.isFinite(employeeId) || employeeId <= 0) {
            userPermissions.value = [];
            userPositionPermissions.value = [];
            loadedPermissionsEmployeeId.value = null;
            loadedPermissionsPositionId.value = null;
            return;
        }
        const positionId = Number(activeEmployee.value.position_id);
        const normalizedPositionId = Number.isFinite(positionId) && positionId > 0 ? positionId : null;
        if (
            !force &&
            loadedPermissionsEmployeeId.value === employeeId &&
            loadedPermissionsPositionId.value === normalizedPositionId
        ) {
            return;
        }
        if (loadUserPermissionsPromise && !force) {
            return await loadUserPermissionsPromise;
        }

        userPermissionsLoading.value = true;
        const currentPromise = (async () => {
            const [userData, positionData] = await Promise.all([
                fetchUserPermissions(employeeId),
                activeEmployee.value.position_id
                    ? fetchPositionPermissions(activeEmployee.value.position_id)
                    : Promise.resolve([]),
            ]);
            userPermissions.value = Array.isArray(userData) ? userData : [];
            userPositionPermissions.value = Array.isArray(positionData) ? positionData : [];
            loadedPermissionsEmployeeId.value = employeeId;
            loadedPermissionsPositionId.value = normalizedPositionId;
        })();
        loadUserPermissionsPromise = currentPromise;
        try {
            await currentPromise;
        } catch (error) {
            const detail = error?.response?.data?.detail;
            userPermissions.value = [];
            userPositionPermissions.value = [];
            loadedPermissionsEmployeeId.value = null;
            loadedPermissionsPositionId.value = null;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            if (loadUserPermissionsPromise === currentPromise) {
                loadUserPermissionsPromise = null;
            }
            userPermissionsLoading.value = false;
        }
    }

    function setUserPermissionUpdating(code, state) {
        if (!code) {
            return;
        }
        if (state) {
            userPermissionUpdating.value = {
                ...userPermissionUpdating.value,
                [code]: true,
            };
            return;
        }
        const next = { ...userPermissionUpdating.value };
        delete next[code];
        userPermissionUpdating.value = next;
    }

    async function handleToggleUserPermission(payload) {
        const code = typeof payload?.code === 'string' ? payload.code : '';
        const checked = Boolean(payload?.checked);
        if (!code || !activeEmployee.value || !canManageUserPermissions.value) {
            return;
        }
        if (userPermissionUpdating.value[code]) {
            return;
        }
        setUserPermissionUpdating(code, true);
        try {
            if (checked) {
                const permission = await addUserPermission(activeEmployee.value.id, code);
                userPermissions.value = [
                    ...userPermissions.value.filter((item) => item?.code !== permission.code),
                    permission,
                ];
            } else {
                if (!userExplicitPermissionSet.value.has(code)) {
                    toast.info('Эта привилегия назначена через должность/роль и не может быть убрана здесь');
                } else {
                    await removeUserPermission(activeEmployee.value.id, code);
                    userPermissions.value = userPermissions.value.filter(
                        (item) => (item?.code || item?.api_router) !== code,
                    );
                }
            }
            loadedPermissionsEmployeeId.value = Number(activeEmployee.value.id) || null;
            const positionId = Number(activeEmployee.value.position_id);
            loadedPermissionsPositionId.value =
                Number.isFinite(positionId) && positionId > 0 ? positionId : null;
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
            await loadUserPermissions({ force: true });
        } finally {
            setUserPermissionUpdating(code, false);
        }
    }

    function resetUserPermissionState() {
        userPermissions.value = [];
        userPositionPermissions.value = [];
        userPermissionUpdating.value = {};
        loadedPermissionsEmployeeId.value = null;
        loadedPermissionsPositionId.value = null;
        loadUserPermissionsPromise = null;
    }

    return {
        userPermissionCatalog,
        userPermissionCatalogLoading,
        userPermissions,
        userPositionPermissions,
        userPermissionsLoading,
        userPermissionUpdating,
        userAssignedPermissionCodes,
        userExplicitPermissionSet,
        loadUserPermissionCatalog,
        loadUserPermissions,
        handleToggleUserPermission,
        resetUserPermissionState,
    };
}
