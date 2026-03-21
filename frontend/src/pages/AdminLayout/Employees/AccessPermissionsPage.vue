<template>
    <div class="access-permissions">
        <div class="access-permissions__tabs">
            <button
                type="button"
                class="access-permissions__tab"
                :class="{ 'is-active': activeTab === 'roles' }"
                @click="setActiveTab('roles')"
            >
                Шаблон прав ролей
            </button>
            <button
                type="button"
                class="access-permissions__tab"
                :class="{ 'is-active': activeTab === 'positions' }"
                @click="setActiveTab('positions')"
            >
                Права должностей
            </button>
        </div>

        <section v-if="activeTab === 'roles'" class="access-permissions__card">
            <header class="access-permissions__card-header">
                <div>
                    <h3 class="access-permissions__card-title">Шаблон прав ролей</h3>
                </div>
            </header>
            <div v-if="permissionsLoading || rolesLoading" class="access-permissions__state">
                Загрузка матрицы прав ролей...
            </div>
            <div v-else-if="!permissionColumns.length" class="access-permissions__state">
                Каталог прав недоступен.
            </div>
            <div v-else-if="!roles.length" class="access-permissions__state">
                Роли не найдены.
            </div>
            <div v-else>
                <div class="access-permissions__filters">
                    <Input
                        v-model="roleFilter"
                        label="Фильтр по роли"
                        placeholder="Начните вводить название роли"
                    />
                    <Input
                        v-model="rolePermissionFilter"
                        label="Фильтр по правам"
                        placeholder="Введите код или название права"
                    />
                    <Select
                        v-model="rolePermissionGroupFilter"
                        label="Группа прав"
                        :options="permissionGroupOptions"
                    />
                </div>
                <div v-if="!filteredRoles.length" class="access-permissions__state">
                    Роли не найдены по такому запросу.
                </div>
                <div v-else-if="!filteredRolePermissionColumns.length" class="access-permissions__state">
                    Права не найдены по такому запросу.
                </div>
                <div v-else class="access-permissions__matrix-wrapper">
                    <table class="permissions-matrix">
                        <thead>
                            <tr>
                                <th class="permissions-matrix__row-header">Роль</th>
                                <th
                                    v-for="permission in filteredRolePermissionColumns"
                                    :key="permission.code"
                                    class="permissions-matrix__permission-header"
                                    :title="permissionHeaderTitle(permission)"
                                >
                                    {{ permission.label }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="role in pagedRoles" :key="role.id">
                                <th class="permissions-matrix__row-label" scope="row">
                                    <span class="permissions-matrix__row-name">{{ role.name }}</span>
                                    <span v-if="role.level !== undefined" class="permissions-matrix__row-meta">
                                        Уровень: {{ role.level }}
                                    </span>
                                </th>
                                <td
                                    v-for="permission in filteredRolePermissionColumns"
                                    :key="permission.code"
                                    class="permissions-matrix__cell"
                                >
                                    <Checkbox
                                        :model-value="roleHasPermission(role.id, permission.code)"
                                        :disabled="isRoleCellDisabled(role.id)"
                                        @update:model-value="
                                            (checked) => toggleRolePermission(role.id, permission.code, checked)
                                        "
                                    />
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-if="roleTotalPages > 1" class="access-permissions__pagination">
                    <Button
                        color="outline"
                        size="sm"
                        :disabled="rolePage <= 1"
                        @click="rolePage = Math.max(1, rolePage - 1)"
                    >
                        Назад
                    </Button>
                    <span class="access-permissions__pagination-info">
                        Страница {{ rolePage }} из {{ roleTotalPages }}
                    </span>
                    <Button
                        color="outline"
                        size="sm"
                        :disabled="rolePage >= roleTotalPages"
                        @click="rolePage = Math.min(roleTotalPages, rolePage + 1)"
                    >
                        Вперёд
                    </Button>
                </div>
            </div>
        </section>

        <section v-else class="access-permissions__card">
            <header class="access-permissions__card-header">
                <div>
                    <h3 class="access-permissions__card-title">Права должностей</h3>
                    <p class="access-permissions__card-subtitle">
                        Управляйте правами для каждой должности по аналогичному принципу.
                    </p>
                </div>
            </header>
            <div v-if="permissionsLoading || positionsLoading" class="access-permissions__state">
                Загрузка матрицы прав должностей...
            </div>
            <div v-else-if="!permissionColumns.length" class="access-permissions__state">
                Каталог прав недоступен.
            </div>
            <div v-else-if="!positions.length" class="access-permissions__state">
                Должности не найдены.
            </div>
            <div v-else>
                <div class="access-permissions__filters">
                    <Input
                        v-model="positionFilter"
                        label="Фильтр по должности"
                        placeholder="Введите название должности"
                    />
                    <Input
                        v-model="positionPermissionFilter"
                        label="Фильтр по правам"
                        placeholder="Введите код или название права"
                    />
                    <Select
                        v-model="positionPermissionGroupFilter"
                        label="Группа прав"
                        :options="permissionGroupOptions"
                    />
                </div>
                <div v-if="!filteredPositions.length" class="access-permissions__state">
                    Должности не найдены по такому запросу.
                </div>
                <div v-else-if="!filteredPositionPermissionColumns.length" class="access-permissions__state">
                    Права не найдены по такому запросу.
                </div>
                <div v-else class="access-permissions__matrix-wrapper">
                    <table class="permissions-matrix">
                        <thead>
                            <tr>
                                <th class="permissions-matrix__row-header">Должность</th>
                                <th
                                    v-for="permission in filteredPositionPermissionColumns"
                                    :key="permission.code"
                                    class="permissions-matrix__permission-header"
                                    :title="permissionHeaderTitle(permission)"
                                >
                                    {{ permission.label }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="position in pagedPositions" :key="position.id">
                                <th class="permissions-matrix__row-label" scope="row">
                                    <span class="permissions-matrix__row-name">{{ position.name }}</span>
                                    <span v-if="position.role_name" class="permissions-matrix__row-meta">
                                        Роль: {{ position.role_name }}
                                    </span>
                                </th>
                                <td
                                    v-for="permission in filteredPositionPermissionColumns"
                                    :key="permission.code"
                                    class="permissions-matrix__cell"
                                >
                                    <Checkbox
                                        :model-value="positionHasPermission(position.id, permission.code)"
                                        :disabled="isPositionCellDisabled(position.id, permission.code)"
                                        @update:model-value="
                                            (checked) => togglePositionPermission(position.id, permission.code, checked)
                                        "
                                    />
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-if="positionTotalPages > 1" class="access-permissions__pagination">
                    <Button
                        color="outline"
                        size="sm"
                        :disabled="positionPage <= 1"
                        @click="positionPage = Math.max(1, positionPage - 1)"
                    >
                        Назад
                    </Button>
                    <span class="access-permissions__pagination-info">
                        Страница {{ positionPage }} из {{ positionTotalPages }}
                    </span>
                    <Button
                        color="outline"
                        size="sm"
                        :disabled="positionPage >= positionTotalPages"
                        @click="positionPage = Math.min(positionTotalPages, positionPage + 1)"
                    >
                        Вперёд
                    </Button>
                </div>
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import {
    addPositionPermission,
    fetchAccessPermissions,
    fetchAccessPositions,
    fetchAccessRoles,
    fetchPositionPermissions,
    fetchPositionPermissionsMap,
    fetchRolePermissions,
    fetchRolePermissionsMap,
    removePositionPermission,
    updateRolePermissions,
} from '@/api';
import { extractApiErrorMessage } from '@/utils/apiErrors';

const PERMISSION_CODE_GROUP_FALLBACKS = [
    { pattern: /^system(\.|$)/, label: 'Система' },
    { pattern: /^staff(_|\.|$)/, label: 'Сотрудники' },
    { pattern: /^(roles|positions|users|companies|restaurants)(\.|$)/, label: 'Администрирование' },
    { pattern: /^(employees_card|staff_employees)(\.|$)/, label: 'Сотрудники' },
    { pattern: /^checklists(\.|$)/, label: 'Сотрудники' },
    { pattern: /^inventory(\.|$)/, label: 'Склад' },
    { pattern: /^payroll(\.|$)/, label: 'Зарплата' },
    { pattern: /^kpi(\.|$)/, label: 'KPI' },
    { pattern: /^training(\.|$)/, label: 'Обучение' },
    { pattern: /^iiko(\.|$)/, label: 'Продажи' },
    { pattern: /^sales(\.|$)/, label: 'Продажи' },
    { pattern: /^sections(\.|$)/, label: 'Доступ к разделам' },
    { pattern: /^(medical_checks|cis_documents)(\.|$)/, label: 'Кадры' },
    { pattern: /^access_control(\.|$)/, label: 'Доступ' },
    { pattern: /^kitchen(\.|$)/, label: 'Кухня' },
    { pattern: /^(time|timesheet)(_|\.|$)/, label: 'Табель смен' },
];

const toast = useToast();

const permissionsCatalog = ref([]);
const permissionsLoading = ref(false);

const roles = ref([]);
const rolesLoading = ref(false);
const rolePermissionsMap = ref({});
const roleUpdatingMap = ref({});

const positions = ref([]);
const positionsLoading = ref(false);
const positionPermissionsMap = ref({});
const positionCellUpdating = ref({});
const rolePermissionsInFlight = new Set();
const positionPermissionsInFlight = new Set();

const roleFilter = ref('');
const positionFilter = ref('');
const rolePermissionFilter = ref('');
const rolePermissionGroupFilter = ref('');
const positionPermissionFilter = ref('');
const positionPermissionGroupFilter = ref('');
const permissionGroups = ref([]);
const activeTab = ref('roles');
const ROLE_PAGE_SIZE = 20;
const POSITION_PAGE_SIZE = 20;
const rolePage = ref(1);
const positionPage = ref(1);

const permissionColumns = computed(() =>
    permissionsCatalog.value.map((permission) => ({
        code: permission.code,
        label: permission.display_name || permission.name || permission.code || '',
        description: permission.description?.trim() || '',
        group: resolvePermissionGroup(permission),
    })),
);

const permissionGroupOptions = computed(() => [
    { value: '', label: 'Все группы' },
    ...permissionGroups.value.map((group) => ({
        value: group,
        label: group,
    })),
]);

const sortedRoles = computed(() => {
    const list = [...roles.value];
    return list.sort((a, b) => {
        const levelA = Number.isFinite(Number(a?.level)) ? Number(a.level) : Number.POSITIVE_INFINITY;
        const levelB = Number.isFinite(Number(b?.level)) ? Number(b.level) : Number.POSITIVE_INFINITY;
        if (levelA !== levelB) {
            return levelA - levelB;
        }
        return (a?.name || '').localeCompare(b?.name || '', 'ru', { sensitivity: 'base' });
    });
});

function buildPermissionFilter(queryValue, groupValue) {
    const query = (queryValue || '').trim().toLowerCase();
    const groupQuery = (groupValue || '').trim().toLowerCase();
    return permissionColumns.value.filter((permission) => {
        const permissionGroup = (permission.group || '').toLowerCase();
        if (groupQuery && permissionGroup !== groupQuery) {
            return false;
        }
        if (!query) {
            return true;
        }
        const combined = `${permission.label} ${permission.code}`.toLowerCase();
        return combined.includes(query);
    });
}

const filteredRolePermissionColumns = computed(() =>
    buildPermissionFilter(rolePermissionFilter.value, rolePermissionGroupFilter.value),
);

const filteredPositionPermissionColumns = computed(() =>
    buildPermissionFilter(positionPermissionFilter.value, positionPermissionGroupFilter.value),
);

const filteredRoles = computed(() => {
    const query = roleFilter.value.trim().toLowerCase();
    if (!query) {
        return sortedRoles.value;
    }
    return sortedRoles.value.filter((role) => role?.name?.toLowerCase().includes(query));
});

const sortedPositions = computed(() => {
    const list = [...positions.value];
    return list.sort((a, b) => {
        const roleA = Number.isFinite(Number(a?.role_id)) ? Number(a.role_id) : Number.POSITIVE_INFINITY;
        const roleB = Number.isFinite(Number(b?.role_id)) ? Number(b.role_id) : Number.POSITIVE_INFINITY;
        if (roleA !== roleB) {
            return roleA - roleB;
        }
        return (a?.name || '').localeCompare(b?.name || '', 'ru', { sensitivity: 'base' });
    });
});

const filteredPositions = computed(() => {
    const query = positionFilter.value.trim().toLowerCase();
    const base = sortedPositions.value;
    if (!query) {
        return base;
    }
    return base.filter((position) => position?.name?.toLowerCase().includes(query));
});

const roleTotalPages = computed(() =>
    Math.max(1, Math.ceil(filteredRoles.value.length / ROLE_PAGE_SIZE)),
);

const positionTotalPages = computed(() =>
    Math.max(1, Math.ceil(filteredPositions.value.length / POSITION_PAGE_SIZE)),
);

const pagedRoles = computed(() => {
    const start = (rolePage.value - 1) * ROLE_PAGE_SIZE;
    return filteredRoles.value.slice(start, start + ROLE_PAGE_SIZE);
});

const pagedPositions = computed(() => {
    const start = (positionPage.value - 1) * POSITION_PAGE_SIZE;
    return filteredPositions.value.slice(start, start + POSITION_PAGE_SIZE);
});

function resolvePermissionGroup(permission) {
    const explicitZone = extractExplicitPermissionZone(permission);
    if (explicitZone) {
        return explicitZone;
    }
    return inferPermissionGroupFromCode(permission);
}

function extractExplicitPermissionZone(permission) {
    const candidates = [
        permission?.responsibility_zone,
        permission?.responsibilityZone,
    ];
    for (const candidate of candidates) {
        if (typeof candidate === 'string') {
            const trimmed = candidate.trim();
            if (trimmed) {
                return trimmed;
            }
        }
    }
    return '';
}

function inferPermissionGroupFromCode(permission) {
    const rawCode =
        typeof permission?.code === 'string'
            ? permission.code
            : typeof permission?.api_router === 'string'
            ? permission.api_router
            : '';
    const normalized = rawCode.trim().toLowerCase();
    if (!normalized) {
        return '';
    }
    for (const fallback of PERMISSION_CODE_GROUP_FALLBACKS) {
        if (fallback.pattern.test(normalized)) {
            return fallback.label;
        }
    }
    const prefix = normalized.split(/[._]/)[0]?.replace(/_/g, ' ').trim();
    if (!prefix) {
        return '';
    }
    return prefix.replace(/\b\w/g, (char) => char.toUpperCase());
}

function recomputePermissionGroups(catalog) {
    const groups = new Set();
    for (const permission of catalog || []) {
        const group = resolvePermissionGroup(permission);
        if (group) {
            groups.add(group);
        }
    }
    permissionGroups.value = Array.from(groups).sort((a, b) =>
        a.localeCompare(b, 'ru', { sensitivity: 'base' }),
    );
}

onMounted(() => {
    loadPermissionsCatalog();
    ensureRolesLoaded();
});

watch(
    () => activeTab.value,
    (tab) => {
        if (tab === 'roles') {
            ensureRolesLoaded();
        } else if (tab === 'positions') {
            ensurePositionsLoaded();
        }
    },
);

function setActiveTab(tab) {
    activeTab.value = tab;
}

watch([roleFilter, rolePermissionFilter, rolePermissionGroupFilter], () => {
    rolePage.value = 1;
});

watch([positionFilter, positionPermissionFilter, positionPermissionGroupFilter], () => {
    positionPage.value = 1;
});

watch(
    () => filteredRoles.value.length,
    () => {
        if (rolePage.value > roleTotalPages.value) {
            rolePage.value = roleTotalPages.value;
        }
    },
);

watch(
    () => filteredPositions.value.length,
    () => {
        if (positionPage.value > positionTotalPages.value) {
            positionPage.value = positionTotalPages.value;
        }
    },
);

watch(
    () => pagedRoles.value,
    (items) => {
        const ids = items.map((role) => role.id).filter((id) => id !== undefined && id !== null);
        loadRolePermissionsForIds(ids);
    },
    { immediate: true },
);

watch(
    () => pagedPositions.value,
    (items) => {
        const ids = items.map((pos) => pos.id).filter((id) => id !== undefined && id !== null);
        loadPositionPermissionsForIds(ids);
    },
    { immediate: true },
);

function permissionHeaderTitle(permission) {
    if (permission.description) {
        return `${permission.label} — ${permission.description}`;
    }
    return permission.label;
}

function chunkIds(ids, size = 200) {
    const chunks = [];
    for (let index = 0; index < ids.length; index += size) {
        chunks.push(ids.slice(index, index + size));
    }
    return chunks;
}

async function loadPermissionsCatalog() {
    permissionsLoading.value = true;
    try {
        const data = await fetchAccessPermissions();
        permissionsCatalog.value = Array.isArray(data) ? data : [];
        recomputePermissionGroups(permissionsCatalog.value);
    } catch (error) {
        permissionsCatalog.value = [];
        recomputePermissionGroups(permissionsCatalog.value);
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить каталог прав'));
        console.error(error);
    } finally {
        permissionsLoading.value = false;
    }
}

async function ensureRolesLoaded() {
    if (rolesLoading.value || roles.value.length) {
        return;
    }
    await loadRolesWithPermissions();
}

async function ensurePositionsLoaded() {
    if (positionsLoading.value || positions.value.length) {
        return;
    }
    await loadPositionsWithPermissions();
}

async function loadRolePermissionsForIds(ids) {
    const uniqueIds = Array.from(new Set((ids || []).map((id) => Number(id)).filter(Number.isFinite)));
    if (!uniqueIds.length) {
        return;
    }
    const missing = uniqueIds.filter(
        (id) => !rolePermissionsMap.value[id] && !rolePermissionsInFlight.has(id),
    );
    if (!missing.length) {
        return;
    }
    for (const id of missing) {
        rolePermissionsInFlight.add(id);
    }
    try {
        const merged = { ...rolePermissionsMap.value };
        const chunks = chunkIds(missing);
        const results = await Promise.all(chunks.map((chunk) => fetchRolePermissionsMap(chunk)));
        for (const data of results) {
            for (const [rawId, codes] of Object.entries(data || {})) {
                const roleId = Number(rawId);
                if (!Number.isFinite(roleId)) {
                    continue;
                }
                merged[roleId] = new Set(extractPermissionCodes(codes));
            }
        }
        for (const id of missing) {
            if (!merged[id]) {
                merged[id] = new Set();
            }
        }
        rolePermissionsMap.value = merged;
    } catch (error) {
        console.error(error);
        const fallback = {};
        const fallbackResults = await Promise.all(
            missing.map(async (roleId) => {
                try {
                    const permissions = await fetchRolePermissions(roleId);
                    return [roleId, new Set(extractPermissionCodes(permissions))];
                } catch (innerError) {
                    console.error(innerError);
                    return [roleId, new Set()];
                }
            }),
        );
        for (const [roleId, codes] of fallbackResults) {
            fallback[roleId] = codes;
        }
        rolePermissionsMap.value = {
            ...rolePermissionsMap.value,
            ...fallback,
        };
    } finally {
        for (const id of missing) {
            rolePermissionsInFlight.delete(id);
        }
    }
}

async function loadPositionPermissionsForIds(ids) {
    const uniqueIds = Array.from(new Set((ids || []).map((id) => Number(id)).filter(Number.isFinite)));
    if (!uniqueIds.length) {
        return;
    }
    const missing = uniqueIds.filter(
        (id) => !positionPermissionsMap.value[id] && !positionPermissionsInFlight.has(id),
    );
    if (!missing.length) {
        return;
    }
    for (const id of missing) {
        positionPermissionsInFlight.add(id);
    }
    try {
        const merged = { ...positionPermissionsMap.value };
        const chunks = chunkIds(missing);
        const results = await Promise.all(chunks.map((chunk) => fetchPositionPermissionsMap(chunk)));
        for (const data of results) {
            for (const [rawId, codes] of Object.entries(data || {})) {
                const positionId = Number(rawId);
                if (!Number.isFinite(positionId)) {
                    continue;
                }
                merged[positionId] = new Set(extractPermissionCodes(codes));
            }
        }
        for (const id of missing) {
            if (!merged[id]) {
                merged[id] = new Set();
            }
        }
        positionPermissionsMap.value = merged;
    } catch (error) {
        console.error(error);
        const fallback = {};
        const fallbackResults = await Promise.all(
            missing.map(async (positionId) => {
                try {
                    const permissions = await fetchPositionPermissions(positionId);
                    return [positionId, new Set(extractPermissionCodes(permissions))];
                } catch (innerError) {
                    console.error(innerError);
                    return [positionId, new Set()];
                }
            }),
        );
        for (const [positionId, codes] of fallbackResults) {
            fallback[positionId] = codes;
        }
        positionPermissionsMap.value = {
            ...positionPermissionsMap.value,
            ...fallback,
        };
    } finally {
        for (const id of missing) {
            positionPermissionsInFlight.delete(id);
        }
    }
}

async function loadRolesWithPermissions() {
    rolesLoading.value = true;
    try {
        const data = await fetchAccessRoles();
        const list = Array.isArray(data) ? data : [];
        roles.value = list;
        if (!list.length) {
            rolePermissionsMap.value = {};
            return;
        }
        rolePermissionsMap.value = {};
        await loadRolePermissionsForIds(list.map((role) => role.id));
    } catch (error) {
        roles.value = [];
        rolePermissionsMap.value = {};
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить роли'));
        console.error(error);
    } finally {
        rolesLoading.value = false;
    }
}

async function loadPositionsWithPermissions() {
    positionsLoading.value = true;
    try {
        const data = await fetchAccessPositions();
        const list = Array.isArray(data) ? data : [];
        positions.value = list;
        if (!list.length) {
            positionPermissionsMap.value = {};
            return;
        }
        positionPermissionsMap.value = {};
        await loadPositionPermissionsForIds(list.map((position) => position.id));
    } catch (error) {
        positions.value = [];
        positionPermissionsMap.value = {};
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить должности'));
        console.error(error);
    } finally {
        positionsLoading.value = false;
    }
}

function roleHasPermission(roleId, permissionCode) {
    return rolePermissionsMap.value[roleId]?.has(permissionCode) ?? false;
}

function positionHasPermission(positionId, permissionCode) {
    return positionPermissionsMap.value[positionId]?.has(permissionCode) ?? false;
}

function isRoleCellDisabled(roleId) {
    return (
        permissionsLoading.value ||
        rolesLoading.value ||
        Boolean(roleUpdatingMap.value[roleId])
    );
}

function isPositionCellDisabled(positionId, permissionCode) {
    return (
        permissionsLoading.value ||
        positionsLoading.value ||
        Boolean(positionCellUpdating.value[`${positionId}:${permissionCode}`])
    );
}

function setRoleUpdating(roleId, state) {
    roleUpdatingMap.value = {
        ...roleUpdatingMap.value,
        [roleId]: state,
    };
}

function setPositionCellUpdating(positionId, permissionCode, state) {
    const key = `${positionId}:${permissionCode}`;
    const next = { ...positionCellUpdating.value };
    if (state) {
        next[key] = true;
    } else {
        delete next[key];
    }
    positionCellUpdating.value = next;
}

function setRolePermissionCodes(roleId, codes) {
    rolePermissionsMap.value = {
        ...rolePermissionsMap.value,
        [roleId]: new Set(codes),
    };
}

function setPositionPermissionCodes(positionId, codes) {
    positionPermissionsMap.value = {
        ...positionPermissionsMap.value,
        [positionId]: new Set(codes),
    };
}

async function toggleRolePermission(roleId, permissionCode, checked) {
    if (!roleId || !permissionCode || isRoleCellDisabled(roleId)) {
        return;
    }
    const currentSet = new Set(rolePermissionsMap.value[roleId] ?? []);
    if (checked) {
        currentSet.add(permissionCode);
    } else {
        currentSet.delete(permissionCode);
    }

    setRoleUpdating(roleId, true);
    try {
        const updated = await updateRolePermissions(roleId, Array.from(currentSet));
        setRolePermissionCodes(roleId, extractPermissionCodes(updated));
        toast.success('Права роли обновлены');
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось обновить права роли'));
        console.error(error);
    } finally {
        setRoleUpdating(roleId, false);
    }
}

async function togglePositionPermission(positionId, permissionCode, checked) {
    if (!positionId || !permissionCode || isPositionCellDisabled(positionId, permissionCode)) {
        return;
    }
    setPositionCellUpdating(positionId, permissionCode, true);
    try {
        if (checked) {
            await addPositionPermission(positionId, permissionCode);
        } else {
            await removePositionPermission(positionId, permissionCode);
        }
        const currentSet = new Set(positionPermissionsMap.value[positionId] ?? []);
        if (checked) {
            currentSet.add(permissionCode);
        } else {
            currentSet.delete(permissionCode);
        }
        setPositionPermissionCodes(positionId, currentSet);
        toast.success('Права должности обновлены');
    } catch (error) {
        toast.error(
            extractApiErrorMessage(error, 'Не удалось обновить права должности'),
        );
        console.error(error);
    } finally {
        setPositionCellUpdating(positionId, permissionCode, false);
    }
}

function extractPermissionCodes(payload) {
    if (!Array.isArray(payload)) {
        return [];
    }
    return payload
        .map((item) => (typeof item === 'string' ? item : item?.code))
        .filter((code) => typeof code === 'string' && code.trim())
        .map((code) => code.trim());
}

</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-access-permissions' as *;
</style>
