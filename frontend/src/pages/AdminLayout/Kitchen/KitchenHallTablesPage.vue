<template>
    <div class="admin-page kitchen-hall-tables-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Столы и залы</h1>
                <p class="admin-page__subtitle">
                    Управление через иерархию: <strong>Ресторан -> Зал -> Зона -> Столы</strong>.
                    Столы без привязки выводятся в разделе «Нераспределенные».
                </p>
            </div>
            <div class="admin-page__header-actions">
                <Button :loading="loading" :disabled="loading" @click="reloadAll">Обновить</Button>
                <Button :disabled="!canManage" @click="openHallModal">Создать зал</Button>
                <Button :disabled="!canManage || !selectedRestaurantId" @click="openZoneModal">Создать зону</Button>
            </div>
        </header>

        <section class="admin-page__section">
            <h3 class="kitchen-hall-tables-page__section-title">Рестораны</h3>
            <div class="kitchen-hall-tables-page__restaurant-grid">
                <button
                    v-for="restaurant in restaurants"
                    :key="restaurant.id"
                    type="button"
                    class="kitchen-hall-tables-page__restaurant-tile"
                    :class="{ 'is-active': String(restaurant.id) === String(selectedRestaurantId || '') }"
                    @click="selectRestaurant(restaurant.id)"
                >
                    <strong>{{ restaurant.name }}</strong>
                    <span>Зон: {{ restaurantZoneCount(restaurant.id) }}</span>
                </button>
            </div>
        </section>

        <section v-if="selectedRestaurantId" class="admin-page__section kitchen-hall-tables-page__workspace">
            <aside class="kitchen-hall-tables-page__tree">
                <h3 class="kitchen-hall-tables-page__section-title">Структура</h3>

                <button
                    type="button"
                    class="kitchen-hall-tables-page__node"
                    :class="{ 'is-active': activeNode === 'unassigned' }"
                    @click="selectUnassignedNode"
                >
                    <span>Нераспределенные</span>
                    <span class="kitchen-hall-tables-page__node-count">{{ unassignedRows.length }}</span>
                </button>

                <div v-for="hallNode in hallTreeNodes" :key="hallNode.id" class="kitchen-hall-tables-page__hall-block">
                    <button type="button" class="kitchen-hall-tables-page__node" @click="toggleHallExpanded(hallNode.id)">
                        <span>{{ hallNode.name }}</span>
                        <span class="kitchen-hall-tables-page__node-count">{{ hallNode.table_count }}</span>
                    </button>

                    <div v-if="isHallExpanded(hallNode.id)" class="kitchen-hall-tables-page__zone-list">
                        <button
                            v-for="zoneNode in hallNode.zones"
                            :key="zoneNode.id"
                            type="button"
                            class="kitchen-hall-tables-page__node"
                            :class="{ 'is-active': activeNode === `zone:${zoneNode.id}` }"
                            @click="selectZoneNode(zoneNode.id)"
                        >
                            <span>{{ zoneNode.name }}</span>
                            <span class="kitchen-hall-tables-page__node-count">{{ zoneNode.table_count }}</span>
                        </button>
                        <p v-if="!hallNode.zones.length" class="kitchen-hall-tables-page__tree-empty">В этом зале пока нет зон.</p>
                    </div>
                </div>
            </aside>

            <div class="kitchen-hall-tables-page__content">
                <article v-if="activeNode === 'unassigned'" class="kitchen-hall-tables-page__panel">
                    <h3 class="kitchen-hall-tables-page__section-title">Нераспределенные столы</h3>
                    <div class="kitchen-hall-tables-page__filters-grid">
                        <Input v-model="filters.department" label="Подразделение iiko" placeholder="Поиск по подразделению" />
                        <Input v-model="filters.table_num" label="Стол iiko" placeholder="Поиск по столу" />
                        <Select
                            v-model="filters.source_restaurant_id"
                            label="Источник iiko"
                            :options="sourceFilterOptions"
                            placeholder="Все"
                        />
                    </div>

                    <div class="kitchen-hall-tables-page__actions kitchen-hall-tables-page__actions--inline">
                        <Select
                            v-model="targetZoneId"
                            label="Куда назначить"
                            :options="zoneAssignOptions"
                            placeholder="Выберите зону"
                        />
                        <Button :disabled="!canAssignSelected || assigning" :loading="assigning" @click="assignSelectedRowsToZone">
                            Назначить выбранные
                        </Button>
                        <Button color="ghost" :disabled="assigning" @click="clearSelection">Сбросить выбор</Button>
                        <span class="kitchen-hall-tables-page__hint">Выбрано: {{ selectedRowKeys.length }}</span>
                    </div>

                    <Table v-if="filteredUnassignedRows.length" class="kitchen-hall-tables-page__table">
                        <thead>
                            <tr>
                                <th class="kitchen-hall-tables-page__check-col"></th>
                                <th>Источник</th>
                                <th>Подразделение</th>
                                <th>Стол iiko</th>
                                <th>Название стола</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in filteredUnassignedRows" :key="row.scope_key">
                                <td class="kitchen-hall-tables-page__check-col">
                                    <input v-model="selectedRowKeys" type="checkbox" :value="row.scope_key" />
                                </td>
                                <td>{{ row.source_restaurant_name || 'Любой источник' }}</td>
                                <td>{{ row.department || '-' }}</td>
                                <td>{{ row.table_num || '-' }}</td>
                                <td>{{ row.table_name || '-' }}</td>
                            </tr>
                        </tbody>
                    </Table>
                    <div v-else-if="loadingCandidates" class="admin-page__empty">Загрузка столов...</div>
                    <div v-else class="admin-page__empty">Нераспределенных столов нет.</div>
                </article>

                <article v-else class="kitchen-hall-tables-page__panel">
                    <h3 class="kitchen-hall-tables-page__section-title">
                        {{ selectedZone?.hall_name || 'Зал' }} / {{ selectedZone?.name || 'Зона' }}
                    </h3>
                    <div class="kitchen-hall-tables-page__actions">
                        <Button color="ghost" @click="selectUnassignedNode">Показать нераспределенные</Button>
                    </div>
                    <Table v-if="zoneRows.length" class="kitchen-hall-tables-page__table">
                        <thead>
                            <tr>
                                <th>Источник</th>
                                <th>Подразделение</th>
                                <th>Стол iiko</th>
                                <th>Название стола</th>
                                <th>Вместимость</th>
                                <th class="admin-page__actions">Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in zoneRows" :key="row.id || row.scope_key">
                                <td>{{ row.source_restaurant_name || 'Любой источник' }}</td>
                                <td>{{ row.department || '-' }}</td>
                                <td>{{ row.table_num || '-' }}</td>
                                <td>{{ row.table_name || '-' }}</td>
                                <td>{{ row.capacity ?? '-' }}</td>
                                <td class="admin-page__actions">
                                    <Button
                                        size="sm"
                                        color="danger"
                                        :disabled="!canManage || !row.id || deletingIds.includes(String(row.id))"
                                        :loading="deletingIds.includes(String(row.id))"
                                        @click="removeRowFromZone(row)"
                                    >
                                        В нераспределенные
                                    </Button>
                                </td>
                            </tr>
                        </tbody>
                    </Table>
                    <div v-else-if="loadingRows" class="admin-page__empty">Загрузка столов зоны...</div>
                    <div v-else class="admin-page__empty">В этой зоне пока нет столов.</div>
                </article>
            </div>
        </section>

        <Modal v-if="hallModalOpen" @close="closeHallModal">
            <template #header><h3 class="kitchen-hall-tables-page__modal-title">Создать зал</h3></template>
            <form class="kitchen-hall-tables-page__modal-grid" @submit.prevent="createHall">
                <Input v-model="hallDraft.name" label="Название зала" placeholder="Например: Основной зал" />
                <Input v-model="hallDraft.comment" label="Комментарий" placeholder="Опционально" />
                <Checkbox v-model="hallDraft.is_active" label="Активен" />
            </form>
            <template #footer>
                <Button :disabled="savingHall || !canManage" :loading="savingHall" @click="createHall">Создать</Button>
                <Button color="ghost" :disabled="savingHall" @click="closeHallModal">Закрыть</Button>
            </template>
        </Modal>

        <Modal v-if="zoneModalOpen" @close="closeZoneModal">
            <template #header><h3 class="kitchen-hall-tables-page__modal-title">Создать зону</h3></template>
            <form class="kitchen-hall-tables-page__modal-grid" @submit.prevent="createZone">
                <Select v-model="zoneDraft.restaurant_id" label="Ресторан" :options="restaurantOptions" placeholder="Выберите ресторан" />
                <Select v-model="zoneDraft.hall_id" label="Зал" :options="hallOptions" placeholder="Выберите зал" />
                <Input v-model="zoneDraft.name" label="Название зоны" placeholder="Например: Веранда" />
                <Input v-model="zoneDraft.comment" label="Комментарий" placeholder="Опционально" />
                <Checkbox v-model="zoneDraft.is_active" label="Активна" />
            </form>
            <template #footer>
                <Button :disabled="savingZone || !canManage" :loading="savingZone" @click="createZone">Создать</Button>
                <Button color="ghost" :disabled="savingZone" @click="closeZoneModal">Закрыть</Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import {
    assignKitchenSalesHallZoneTables,
    createKitchenSalesHall,
    createKitchenSalesHallZone,
    deleteKitchenSalesHallTable,
    fetchKitchenRestaurants,
    fetchKitchenSalesHallTableCandidates,
    fetchKitchenSalesHallTables,
    fetchKitchenSalesHallZones,
    fetchKitchenSalesHalls,
} from "@/api";
import { useToast } from "vue-toastification";
import { useUserStore } from "@/stores/user";
import Button from "@/components/UI-components/Button.vue";
import Table from "@/components/UI-components/Table.vue";
import Select from "@/components/UI-components/Select.vue";
import Input from "@/components/UI-components/Input.vue";
import Checkbox from "@/components/UI-components/Checkbox.vue";
import Modal from "@/components/UI-components/Modal.vue";

const toast = useToast();
const userStore = useUserStore();

const loading = ref(false);
const loadingRows = ref(false);
const loadingCandidates = ref(false);
const savingHall = ref(false);
const savingZone = ref(false);
const assigning = ref(false);

const restaurants = ref([]);
const halls = ref([]);
const zones = ref([]);
const candidates = ref([]);
const restaurantRows = ref([]);

const selectedRestaurantId = ref("");
const activeNode = ref("unassigned");
const expandedHallIds = ref([]);
const selectedRowKeys = ref([]);
const targetZoneId = ref("");
const deletingIds = ref([]);

const hallModalOpen = ref(false);
const zoneModalOpen = ref(false);

const hallDraft = reactive({ name: "", comment: "", is_active: true });
const zoneDraft = reactive({ restaurant_id: "", hall_id: "", name: "", comment: "", is_active: true });
const filters = reactive({ department: "", table_num: "", source_restaurant_id: "" });

const canManage = computed(() =>
    userStore.hasAnyPermission("sales.tables.manage", "iiko.manage"),
);

const restaurantOptions = computed(() => [
    { value: "", label: "Не выбрано" },
    ...(restaurants.value || []).map((row) => ({ value: String(row.id), label: row.name })),
]);

const hallOptions = computed(() => [
    { value: "", label: "Не выбрано" },
    ...(halls.value || []).map((row) => ({ value: String(row.id), label: row.is_active ? row.name : `${row.name} (неактивен)` })),
]);

const selectedRestaurant = computed(() =>
    (restaurants.value || []).find((row) => String(row.id) === String(selectedRestaurantId.value || "")) || null,
);

const zonesForSelectedRestaurant = computed(() =>
    (zones.value || []).filter((row) => String(row.restaurant_id || "") === String(selectedRestaurantId.value || "")),
);
const zoneAssignOptions = computed(() => [
    { value: "", label: "Выберите зону" },
    ...zonesForSelectedRestaurant.value.map((row) => ({
        value: String(row.id),
        label: row.hall_name ? `${row.hall_name} / ${row.name}` : row.name,
    })),
]);

const selectedZoneId = computed(() => {
    if (!activeNode.value.startsWith("zone:")) {
        return "";
    }
    return activeNode.value.slice("zone:".length);
});

const selectedZone = computed(() =>
    (zonesForSelectedRestaurant.value || []).find((row) => String(row.id) === String(selectedZoneId.value || "")) || null,
);

const settingsByScope = computed(() => {
    const map = new Map();
    for (const row of restaurantRows.value || []) {
        map.set(scopeKeyFromRow(row), row);
    }
    return map;
});

const mergedRows = computed(() => {
    const map = new Map();
    for (const candidate of candidates.value || []) {
        const scopeKey = scopeKeyFromRow(candidate);
        const setting = settingsByScope.value.get(scopeKey);
        map.set(scopeKey, {
            scope_key: scopeKey,
            id: setting?.id || "",
            restaurant_id: candidate.restaurant_id ?? setting?.restaurant_id ?? null,
            restaurant_name: candidate.restaurant_name || setting?.restaurant_name || selectedRestaurant.value?.name || "",
            source_restaurant_id: candidate.source_restaurant_id ?? setting?.source_restaurant_id ?? null,
            source_restaurant_name: candidate.source_restaurant_name || setting?.source_restaurant_name || "",
            department: candidate.department || setting?.department || "",
            table_num: candidate.table_num || setting?.table_num || "",
            hall_id: setting?.hall_id || null,
            hall_name: setting?.hall_name || candidate.hall_name || "",
            zone_id: setting?.zone_id || null,
            zone_name: setting?.zone_name || candidate.zone_name || "",
            table_name: setting?.table_name || candidate.table_name || "",
            capacity: setting?.capacity ?? candidate?.capacity ?? null,
            is_active: setting?.is_active ?? null,
        });
    }

    for (const setting of restaurantRows.value || []) {
        const scopeKey = scopeKeyFromRow(setting);
        if (map.has(scopeKey)) {
            continue;
        }
        map.set(scopeKey, {
            scope_key: scopeKey,
            id: setting.id || "",
            restaurant_id: setting.restaurant_id ?? null,
            restaurant_name: setting.restaurant_name || selectedRestaurant.value?.name || "",
            source_restaurant_id: setting.source_restaurant_id ?? null,
            source_restaurant_name: setting.source_restaurant_name || "",
            department: setting.department || "",
            table_num: setting.table_num || "",
            hall_id: setting.hall_id || null,
            hall_name: setting.hall_name || "",
            zone_id: setting.zone_id || null,
            zone_name: setting.zone_name || "",
            table_name: setting.table_name || "",
            capacity: setting.capacity ?? null,
            is_active: setting.is_active ?? null,
        });
    }

    return Array.from(map.values());
});

const unassignedRows = computed(() =>
    mergedRows.value.filter((row) => !String(row.zone_id || "").trim()).sort((a, b) => sortRowsByLocation(a, b)),
);

const filteredUnassignedRows = computed(() => {
    const dep = normalizeText(filters.department);
    const table = normalizeText(filters.table_num);
    return unassignedRows.value.filter((row) => {
        if (filters.source_restaurant_id) {
            if (filters.source_restaurant_id === "__any__") {
                if (row.source_restaurant_id !== null && row.source_restaurant_id !== undefined) {
                    return false;
                }
            } else if (String(row.source_restaurant_id || "") !== String(filters.source_restaurant_id)) {
                return false;
            }
        }
        if (dep && !normalizeText(row.department).includes(dep)) {
            return false;
        }
        if (table && !normalizeText(row.table_num).includes(table)) {
            return false;
        }
        return true;
    });
});

const zoneRows = computed(() => {
    const zoneId = String(selectedZoneId.value || "");
    if (!zoneId) {
        return [];
    }
    return mergedRows.value.filter((row) => String(row.zone_id || "") === zoneId).sort((a, b) => sortRowsByLocation(a, b));
});

const sourceFilterOptions = computed(() => {
    const map = new Map();
    for (const row of unassignedRows.value) {
        const sourceId = row.source_restaurant_id;
        const key = sourceId === null || sourceId === undefined ? "__any__" : String(sourceId);
        if (map.has(key)) {
            continue;
        }
        map.set(key, sourceId === null || sourceId === undefined ? "Любой источник" : row.source_restaurant_name || `#${sourceId}`);
    }
    return [{ value: "", label: "Все" }, ...Array.from(map.entries()).map(([value, label]) => ({ value, label }))];
});

const tableCountByZone = computed(() => {
    const map = new Map();
    for (const row of mergedRows.value) {
        const zoneId = String(row.zone_id || "").trim();
        if (!zoneId) {
            continue;
        }
        map.set(zoneId, (map.get(zoneId) || 0) + 1);
    }
    return map;
});

const hallTreeNodes = computed(() => {
    const zonesByHall = new Map();
    for (const zone of zonesForSelectedRestaurant.value) {
        const hallId = String(zone.hall_id || "");
        if (!hallId) {
            continue;
        }
        const list = zonesByHall.get(hallId) || [];
        list.push({
            id: String(zone.id),
            name: zone.name,
            hall_name: zone.hall_name || "",
            table_count: tableCountByZone.value.get(String(zone.id)) || 0,
        });
        zonesByHall.set(hallId, list);
    }

    const result = [];
    for (const hall of halls.value || []) {
        const hallId = String(hall.id || "");
        const zonesList = (zonesByHall.get(hallId) || []).sort((a, b) =>
            String(a.name || "").localeCompare(String(b.name || ""), "ru", { sensitivity: "base" }),
        );
        const tableCount = zonesList.reduce((sum, zone) => sum + Number(zone.table_count || 0), 0);
        result.push({ id: hallId, name: hall.name, zones: zonesList, table_count: tableCount });
    }
    return result;
});

const canAssignSelected = computed(() => Boolean(canManage.value && targetZoneId.value && selectedRowKeys.value.length > 0));

watch(
    selectedRestaurantId,
    async (value) => {
        selectedRowKeys.value = [];
        targetZoneId.value = "";
        activeNode.value = "unassigned";

        if (!String(value || "").trim()) {
            candidates.value = [];
            restaurantRows.value = [];
            return;
        }
        await Promise.all([loadRestaurantRows(), loadCandidates()]);
    },
    { immediate: false },
);

watch(
    zonesForSelectedRestaurant,
    () => {
        const zoneIds = new Set(zonesForSelectedRestaurant.value.map((row) => String(row.id)));
        if (selectedZoneId.value && !zoneIds.has(String(selectedZoneId.value))) {
            activeNode.value = "unassigned";
        }
        if (targetZoneId.value && !zoneIds.has(String(targetZoneId.value))) {
            targetZoneId.value = "";
        }
    },
    { deep: true },
);

watch(
    filteredUnassignedRows,
    () => {
        const allowed = new Set((filteredUnassignedRows.value || []).map((row) => row.scope_key));
        selectedRowKeys.value = (selectedRowKeys.value || []).filter((key) => allowed.has(key));
    },
    { deep: true },
);

function normalizeText(value) {
    return String(value || "").trim().toLowerCase();
}

function scopeKeyFromRow(row) {
    return [
        row?.restaurant_id ?? "none",
        row?.source_restaurant_id ?? "none",
        normalizeText(row?.department_norm || row?.department),
        normalizeText(row?.table_num_norm || row?.table_num),
    ].join(":");
}

function sortRowsByLocation(a, b) {
    const aSource = normalizeText(a.source_restaurant_name || a.source_restaurant_id);
    const bSource = normalizeText(b.source_restaurant_name || b.source_restaurant_id);
    const sourceCmp = aSource.localeCompare(bSource, "ru", { sensitivity: "base" });
    if (sourceCmp !== 0) {
        return sourceCmp;
    }
    const depCmp = normalizeText(a.department).localeCompare(normalizeText(b.department), "ru", { sensitivity: "base" });
    if (depCmp !== 0) {
        return depCmp;
    }
    return normalizeText(a.table_num).localeCompare(normalizeText(b.table_num), "ru", { sensitivity: "base" });
}

function restaurantZoneCount(restaurantId) {
    return zones.value.filter((row) => String(row.restaurant_id || "") === String(restaurantId)).length;
}

function selectRestaurant(restaurantId) {
    selectedRestaurantId.value = String(restaurantId);
}

function selectUnassignedNode() {
    activeNode.value = "unassigned";
}

function selectZoneNode(zoneId) {
    activeNode.value = `zone:${zoneId}`;
}

function isHallExpanded(hallId) {
    return expandedHallIds.value.includes(String(hallId));
}

function toggleHallExpanded(hallId) {
    const key = String(hallId);
    if (expandedHallIds.value.includes(key)) {
        expandedHallIds.value = expandedHallIds.value.filter((id) => id !== key);
        return;
    }
    expandedHallIds.value = [...expandedHallIds.value, key];
}

function clearSelection() {
    selectedRowKeys.value = [];
}

function openHallModal() {
    hallDraft.name = "";
    hallDraft.comment = "";
    hallDraft.is_active = true;
    hallModalOpen.value = true;
}

function closeHallModal() {
    hallModalOpen.value = false;
}

function openZoneModal() {
    zoneDraft.restaurant_id = String(selectedRestaurantId.value || "");
    zoneDraft.hall_id = "";
    zoneDraft.name = "";
    zoneDraft.comment = "";
    zoneDraft.is_active = true;
    zoneModalOpen.value = true;
}

function closeZoneModal() {
    zoneModalOpen.value = false;
}
async function loadRestaurants() {
    const data = await fetchKitchenRestaurants();
    restaurants.value = Array.isArray(data) ? data : [];
    if (!selectedRestaurantId.value && restaurants.value.length) {
        selectedRestaurantId.value = String(restaurants.value[0].id);
    }
}

async function loadHalls() {
    const data = await fetchKitchenSalesHalls({ include_inactive: true });
    halls.value = Array.isArray(data) ? data : [];
    expandedHallIds.value = Array.from(
        new Set([...(expandedHallIds.value || []), ...halls.value.map((row) => String(row.id))]),
    );
}

async function loadZones() {
    const data = await fetchKitchenSalesHallZones({ include_inactive: true });
    zones.value = Array.isArray(data) ? data : [];
}

async function loadRestaurantRows() {
    if (!selectedRestaurantId.value) {
        restaurantRows.value = [];
        return;
    }
    loadingRows.value = true;
    try {
        const data = await fetchKitchenSalesHallTables({
            include_inactive: true,
            restaurant_id: Number(selectedRestaurantId.value),
        });
        restaurantRows.value = Array.isArray(data) ? data : [];
    } catch (error) {
        toast.error(`Ошибка загрузки привязанных столов: ${error.response?.data?.detail || error.message}`);
    } finally {
        loadingRows.value = false;
    }
}

async function loadCandidates() {
    if (!selectedRestaurantId.value) {
        candidates.value = [];
        return;
    }
    loadingCandidates.value = true;
    try {
        const data = await fetchKitchenSalesHallTableCandidates({
            restaurant_id: Number(selectedRestaurantId.value),
            limit: 5000,
        });
        candidates.value = Array.isArray(data) ? data : [];
    } catch (error) {
        toast.error(`Ошибка загрузки кандидатов: ${error.response?.data?.detail || error.message}`);
    } finally {
        loadingCandidates.value = false;
    }
}

async function createHall() {
    if (!canManage.value) {
        return;
    }
    const name = String(hallDraft.name || "").trim();
    if (!name) {
        toast.error("Укажите название зала");
        return;
    }

    savingHall.value = true;
    try {
        await createKitchenSalesHall({
            name,
            comment: String(hallDraft.comment || "").trim() || null,
            is_active: Boolean(hallDraft.is_active),
        });
        await loadHalls();
        toast.success("Зал создан");
        closeHallModal();
    } catch (error) {
        toast.error(`Ошибка создания зала: ${error.response?.data?.detail || error.message}`);
    } finally {
        savingHall.value = false;
    }
}

async function createZone() {
    if (!canManage.value) {
        return;
    }
    if (!zoneDraft.restaurant_id) {
        toast.error("Выберите ресторан");
        return;
    }
    if (!zoneDraft.hall_id) {
        toast.error("Выберите зал");
        return;
    }
    const name = String(zoneDraft.name || "").trim();
    if (!name) {
        toast.error("Укажите название зоны");
        return;
    }

    savingZone.value = true;
    try {
        const created = await createKitchenSalesHallZone({
            restaurant_id: Number(zoneDraft.restaurant_id),
            hall_id: String(zoneDraft.hall_id),
            name,
            comment: String(zoneDraft.comment || "").trim() || null,
            is_active: Boolean(zoneDraft.is_active),
        });
        await loadZones();
        toast.success("Зона создана");
        closeZoneModal();
        if (created?.id) {
            activeNode.value = `zone:${created.id}`;
        }
    } catch (error) {
        toast.error(`Ошибка создания зоны: ${error.response?.data?.detail || error.message}`);
    } finally {
        savingZone.value = false;
    }
}

async function assignSelectedRowsToZone() {
    if (!canAssignSelected.value) {
        return;
    }
    const rowsByKey = new Map((filteredUnassignedRows.value || []).map((row) => [row.scope_key, row]));
    const selectedRows = (selectedRowKeys.value || []).map((key) => rowsByKey.get(key)).filter(Boolean);
    if (!selectedRows.length) {
        toast.error("Выберите столы для назначения");
        return;
    }

    assigning.value = true;
    try {
        await assignKitchenSalesHallZoneTables(targetZoneId.value, {
            items: selectedRows.map((row) => ({
                source_restaurant_id: row.source_restaurant_id ?? null,
                department: String(row.department || "").trim(),
                table_num: String(row.table_num || "").trim() || null,
                table_name: String(row.table_name || row.table_num || "").trim() || null,
                capacity: row.capacity ?? null,
                comment: null,
                is_active: true,
            })),
            replace_zone_tables: false,
        });
        toast.success("Столы назначены в зону");
        selectedRowKeys.value = [];
        await Promise.all([loadRestaurantRows(), loadCandidates()]);
    } catch (error) {
        toast.error(`Ошибка назначения столов: ${error.response?.data?.detail || error.message}`);
    } finally {
        assigning.value = false;
    }
}

async function removeRowFromZone(row) {
    if (!row?.id || !canManage.value) {
        return;
    }
    if (!window.confirm("Переместить стол в нераспределенные?")) {
        return;
    }

    const id = String(row.id);
    deletingIds.value = [...deletingIds.value, id];
    try {
        await deleteKitchenSalesHallTable(id);
        toast.success("Стол перемещен в нераспределенные");
        await Promise.all([loadRestaurantRows(), loadCandidates()]);
        activeNode.value = "unassigned";
    } catch (error) {
        toast.error(`Ошибка удаления привязки: ${error.response?.data?.detail || error.message}`);
    } finally {
        deletingIds.value = deletingIds.value.filter((value) => value !== id);
    }
}

async function reloadAll() {
    loading.value = true;
    try {
        await Promise.all([loadRestaurants(), loadHalls(), loadZones()]);
        if (selectedRestaurantId.value) {
            await Promise.all([loadRestaurantRows(), loadCandidates()]);
        }
    } catch (error) {
        toast.error(`Ошибка загрузки: ${error.response?.data?.detail || error.message}`);
    } finally {
        loading.value = false;
    }
}

reloadAll();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-hall-tables' as *;
</style>
