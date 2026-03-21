<template>
    <div class="kpi-page">
        <section class="kpi-panel kpi-panel--hero">
            <div class="kpi-panel__header">
                <div>
                    <p class="kpi-panel__eyebrow">KPI</p>
                    <h2 class="kpi-panel__title">Фактические значения</h2>
                </div>
            </div>
            <div class="kpi-facts__hero-actions">
                <div class="kpi-facts__year-field">
                    <DateInput
                        v-model="yearPicker"
                        label="Год"
                        type="month"
                        min="2000-01"
                        max="2100-12"
                        :disabled="loading"
                    />
                </div>
                <div
                    class="kpi-facts__mode-switch"
                    :class="{ 'is-restaurant': viewMode === 'restaurant' }"
                    role="tablist"
                    aria-label="Режим отображения фактических значений KPI"
                >
                    <span class="kpi-facts__mode-indicator" aria-hidden="true"></span>
                    <button
                        v-for="option in viewModeOptions"
                        :key="option.value"
                        type="button"
                        class="kpi-facts__mode-button"
                        :class="{ 'is-active': viewMode === option.value }"
                        :aria-pressed="(viewMode === option.value).toString()"
                        :disabled="loading"
                        @click="viewMode = option.value"
                    >
                        {{ option.label }}
                    </button>
                </div>
                <Select
                    v-if="viewMode === 'restaurant'"
                    v-model="restaurantId"
                    class="kpi-facts__restaurant-field"
                    label="Ресторан"
                    :options="restaurantOptions"
                    placeholder="Выберите ресторан"
                    :disabled="loading"
                />
            </div>
        </section>

        <section class="kpi-panel">
            <div v-if="!metrics.length" class="kpi-empty">
                <p class="kpi-empty__title">Показателей пока нет</p>
                <p class="kpi-empty__subtitle">Создайте KPI-показатели, чтобы фиксировать фактические значения.</p>
            </div>
            <div v-else-if="editableRows.length" class="kpi-table-wrapper">
                <table class="kpi-table kpi-table--facts">
                    <colgroup>
                        <col class="kpi-table__col kpi-table__col--metric" />
                        <col class="kpi-table__col kpi-table__col--restaurant" />
                        <col
                            v-for="month in months"
                            :key="`fact-col-${month.month}`"
                            class="kpi-table__col kpi-table__col--month"
                        />
                    </colgroup>
                    <thead>
                        <tr>
                            <th>Показатель</th>
                            <th>Ресторан</th>
                            <th v-for="month in months" :key="month.month">{{ month.short }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="row in editableRows" :key="row.key">
                            <td class="kpi-fact__metric">
                                <div class="kpi-fact__metric-name">{{ row.metricName }}</div>
                                <div v-if="row.metricUnit" class="kpi-fact__metric-unit">{{ row.metricUnit }}</div>
                            </td>
                            <td class="kpi-fact__restaurant">{{ row.restaurantName }}</td>
                            <td
                                v-for="month in months"
                                :key="`${row.key}-${month.month}`"
                                class="kpi-fact__cell"
                                :class="{ 'is-editing': isCellEditing(row.key, month.month) }"
                            >
                                <div v-if="isCellEditing(row.key, month.month)" class="kpi-fact__editor">
                                    <input
                                        v-model="editingCellValue"
                                        class="kpi-fact__input"
                                        type="number"
                                        step="0.01"
                                        :disabled="loading || isCellSaving(row.key, month.month)"
                                        @keydown.enter.prevent="commitEditingCell(row, month.month)"
                                        @keydown.esc.prevent="cancelEditingCell()"
                                        @blur="commitEditingCell(row, month.month)"
                                    >
                                </div>
                                <button
                                    v-else-if="canManageFacts"
                                    type="button"
                                    class="kpi-fact__value-button"
                                    :class="{ 'is-empty': !hasCellFactValue(row.key, month.month) }"
                                    :disabled="loading || isCellSaving(row.key, month.month)"
                                    @click="startEditingCell(row, month.month)"
                                >
                                    {{ cellDisplayValue(row.key, month.month) }}
                                </button>
                                <span v-else class="kpi-fact__placeholder">
                                    {{ cellDisplayValue(row.key, month.month) }}
                                </span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p v-else class="kpi-list__empty">Для выбранных ресторанов нет доступных показателей.</p>
        </section>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { fetchKpiMetrics, fetchKpiPlanFactsBulk, fetchRestaurants, upsertKpiPlanFactsBulk } from '@/api';
import { useDebounce } from '@/composables/useDebounce';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';

const toast = useToast();
const userStore = useUserStore();

const metrics = ref([]);
const loading = ref(false);
const year = ref(new Date().getFullYear());
const yearPicker = ref(toYearPickerValue(year.value));
const restaurants = ref([]);
const restaurantId = ref(null);
const viewMode = ref('overall');
const viewModeOptions = [
    { value: 'overall', label: 'Все рестораны' },
    { value: 'restaurant', label: 'По ресторану' },
];

const planFactsByRow = ref({});
const factsRequestSeq = ref(0);
const editingCell = ref(null);
const cellSaving = ref({});

const months = [
    { month: 1, short: 'Янв' },
    { month: 2, short: 'Фев' },
    { month: 3, short: 'Мар' },
    { month: 4, short: 'Апр' },
    { month: 5, short: 'Май' },
    { month: 6, short: 'Июн' },
    { month: 7, short: 'Июл' },
    { month: 8, short: 'Авг' },
    { month: 9, short: 'Сен' },
    { month: 10, short: 'Окт' },
    { month: 11, short: 'Ноя' },
    { month: 12, short: 'Дек' },
];

const restaurantOptions = computed(() =>
    restaurants.value.map((rest) => ({ value: Number(rest.id), label: rest.name })),
);

const selectedRestaurants = computed(() => {
    if (viewMode.value !== 'restaurant') return restaurants.value;
    if (!restaurantId.value) return [];
    return restaurants.value.filter((rest) => Number(rest.id) === Number(restaurantId.value));
});

const editableRows = computed(() => {
    const rows = [];
    metrics.value.forEach((metric) => {
        selectedRestaurants.value.forEach((rest) => {
            if (!metricMatchesRestaurant(metric, Number(rest.id))) {
                return;
            }
            rows.push({
                key: rowKey(metric.id, rest.id),
                metricId: Number(metric.id),
                metricName: metric.name,
                metricUnit: metric.unit || '',
                restaurantId: Number(rest.id),
                restaurantName: rest.name,
            });
        });
    });
    return rows.sort(
        (a, b) =>
            a.metricName.localeCompare(b.metricName, 'ru-RU') ||
            a.restaurantName.localeCompare(b.restaurantName, 'ru-RU'),
    );
});

const canManageFacts = computed(() =>
    userStore.hasAnyPermission('kpi.facts.manage', 'kpi.manage', 'system.admin'),
);

function parseNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(String(value).replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value) {
    if (value === null || value === undefined) return '—';
    const num = Number(value);
    if (!Number.isFinite(num)) return '—';
    return new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(num);
}

function toYearPickerValue(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '';
    return `${Math.trunc(numeric)}-01`;
}

function parseYearFromPicker(value) {
    const raw = String(value ?? '').trim();
    if (!raw) return null;

    const isoMatch = raw.match(/^(\d{4})(?:-\d{2}(?:-\d{2})?)?$/);
    if (isoMatch) {
        return Number(isoMatch[1]);
    }

    const dotMonthMatch = raw.match(/^\d{2}\.(\d{4})$/);
    if (dotMonthMatch) {
        return Number(dotMonthMatch[1]);
    }

    const dotDateMatch = raw.match(/^\d{2}\.\d{2}\.(\d{4})$/);
    if (dotDateMatch) {
        return Number(dotDateMatch[1]);
    }

    return null;
}

function rowKey(metricId, restId) {
    return `${Number(metricId)}:${Number(restId)}`;
}

function cellKey(rowKeyValue, month) {
    return `${String(rowKeyValue)}:${Number(month)}`;
}

function metricMatchesRestaurant(metric, restId) {
    if (!metric) return false;
    if (metric.all_restaurants !== false) return true;
    const ids = Array.isArray(metric.restaurant_ids) ? metric.restaurant_ids.map((id) => Number(id)) : [];
    return ids.includes(Number(restId));
}

function factCellEntry(rowKeyValue, month) {
    return planFactsByRow.value?.[String(rowKeyValue)]?.months?.[Number(month)] || null;
}

function hasCellFactValue(rowKeyValue, month) {
    return parseNumber(factCellEntry(rowKeyValue, month)?.fact_value) !== null;
}

function cellDisplayValue(rowKeyValue, month) {
    return formatNumber(factCellEntry(rowKeyValue, month)?.fact_value);
}

function isCellSaving(rowKeyValue, month) {
    return Boolean(cellSaving.value[cellKey(rowKeyValue, month)]);
}

function isCellEditing(rowKeyValue, month) {
    if (!editingCell.value) return false;
    return (
        editingCell.value.rowKey === String(rowKeyValue) &&
        Number(editingCell.value.month) === Number(month)
    );
}

const editingCellValue = computed({
    get() {
        return editingCell.value?.value ?? '';
    },
    set(value) {
        if (!editingCell.value) return;
        editingCell.value = {
            ...editingCell.value,
            value,
        };
    },
});

function startEditingCell(row, month) {
    if (loading.value || !canManageFacts.value || !row?.key) return;
    const monthValue = Number(month);
    const current = factCellEntry(row.key, monthValue)?.fact_value;
    editingCell.value = {
        rowKey: String(row.key),
        month: monthValue,
        value: current === null || current === undefined ? '' : String(current),
    };
}

function cancelEditingCell() {
    editingCell.value = null;
}

function numbersEqual(a, b) {
    if (a === null && b === null) return true;
    if (a === null || b === null) return false;
    return Math.abs(a - b) < 1e-9;
}

async function loadMetrics() {
    try {
        const data = await fetchKpiMetrics();
        metrics.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить показатели KPI');
        console.error(error);
    }
}

async function loadRestaurants() {
    try {
        const data = await fetchRestaurants();
        restaurants.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить рестораны');
        console.error(error);
    }
}

async function loadFacts() {
    const requestSeq = ++factsRequestSeq.value;
    cancelEditingCell();
    loading.value = true;
    try {
        if (!metrics.value.length) {
            await loadMetrics();
        }
        if (!restaurants.value.length) {
            await loadRestaurants();
        }

        const yearValue = Number(year.value);
        const params = { year: yearValue };
        if (viewMode.value === 'restaurant' && restaurantId.value) {
            params.restaurant_id = Number(restaurantId.value);
        }
        const data = await fetchKpiPlanFactsBulk(params);
        const items = Array.isArray(data?.items) ? data.items : data || [];

        const nextFacts = {};
        items.forEach((item) => {
            const metricId = Number(item.metric_id);
            const restId = Number(item.restaurant_id);
            const key = rowKey(metricId, restId);
            if (!nextFacts[key]) {
                nextFacts[key] = {
                    metricId,
                    restaurantId: restId,
                    months: {},
                };
            }
            nextFacts[key].months[Number(item.month)] = {
                plan_value: item.plan_value ?? null,
                fact_value: item.fact_value ?? null,
            };
        });

        if (requestSeq !== factsRequestSeq.value) {
            return;
        }
        planFactsByRow.value = nextFacts;
    } catch (error) {
        if (requestSeq !== factsRequestSeq.value) {
            return;
        }
        toast.error('Не удалось загрузить фактические значения');
        console.error(error);
    } finally {
        if (requestSeq === factsRequestSeq.value) {
            loading.value = false;
        }
    }
}

const scheduleFactsReload = useDebounce(() => {
    loadFacts();
}, 250);

async function saveFactCell(row, month, rawValue) {
    if (!row?.key) {
        cancelEditingCell();
        return;
    }

    const rowKeyValue = String(row.key);
    const monthValue = Number(month);
    const saveKey = cellKey(rowKeyValue, monthValue);
    if (isCellSaving(rowKeyValue, monthValue)) {
        return;
    }
    cellSaving.value = {
        ...cellSaving.value,
        [saveKey]: true,
    };

    const nextFactValue = parseNumber(rawValue);
    const existingEntry = factCellEntry(rowKeyValue, monthValue);
    const existingFactValue = parseNumber(existingEntry?.fact_value);
    if (numbersEqual(existingFactValue, nextFactValue)) {
        const nextSavingMap = { ...cellSaving.value };
        delete nextSavingMap[saveKey];
        cellSaving.value = nextSavingMap;
        cancelEditingCell();
        return;
    }

    if (nextFactValue === null && !existingEntry) {
        const nextSavingMap = { ...cellSaving.value };
        delete nextSavingMap[saveKey];
        cellSaving.value = nextSavingMap;
        cancelEditingCell();
        return;
    }

    try {
        await upsertKpiPlanFactsBulk([
            {
                metric_id: Number(row.metricId),
                restaurant_id: Number(row.restaurantId),
                year: Number(year.value),
                month: monthValue,
                fact_value: nextFactValue,
            },
        ]);

        const nextFacts = { ...planFactsByRow.value };
        const rowFacts = nextFacts[rowKeyValue]
            ? { ...nextFacts[rowKeyValue] }
            : {
                metricId: Number(row.metricId),
                restaurantId: Number(row.restaurantId),
                months: {},
            };
        const nextMonths = { ...(rowFacts.months || {}) };
        const prev = nextMonths[monthValue] || existingEntry || {};
        nextMonths[monthValue] = {
            ...prev,
            plan_value: prev?.plan_value ?? null,
            fact_value: nextFactValue,
        };
        rowFacts.months = nextMonths;
        nextFacts[rowKeyValue] = rowFacts;
        planFactsByRow.value = nextFacts;
        cancelEditingCell();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить значение');
        console.error(error);
    } finally {
        const nextSavingMap = { ...cellSaving.value };
        delete nextSavingMap[saveKey];
        cellSaving.value = nextSavingMap;
    }
}

async function commitEditingCell(row, month) {
    if (!isCellEditing(row?.key, month) || !editingCell.value) {
        return;
    }
    await saveFactCell(row, month, editingCell.value.value);
}

watch(
    () => yearPicker.value,
    (value) => {
        const parsedYear = parseYearFromPicker(value);
        if (parsedYear !== null && parsedYear !== Number(year.value)) {
            year.value = parsedYear;
        }
    },
);

watch(
    () => year.value,
    (value) => {
        const pickerValue = toYearPickerValue(value);
        if (pickerValue && yearPicker.value !== pickerValue) {
            yearPicker.value = pickerValue;
        }
        cancelEditingCell();
        scheduleFactsReload();
    },
);

watch(
    () => restaurantId.value,
    () => {
        cancelEditingCell();
        scheduleFactsReload();
    },
);

watch(
    () => viewMode.value,
    (nextMode) => {
        if (nextMode !== 'restaurant') {
            restaurantId.value = null;
        }
        cancelEditingCell();
        scheduleFactsReload();
    },
);

onMounted(async () => {
    await loadRestaurants();
    await loadMetrics();
    await loadFacts();
});

onBeforeUnmount(() => {
    scheduleFactsReload.cancel?.();
    cancelEditingCell();
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kpi-facts' as *;
</style>
