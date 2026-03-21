<template>
    <div class="admin-page kitchen-revenue-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Выручка</h1>
                <p class="admin-page__subtitle">
                    Таблица выручки по реальным методам оплаты: строки - методы оплаты, столбцы - даты.
                </p>
            </div>
            <div class="admin-page__header-actions">
                <Button :loading="loading" :disabled="loading || !canViewMoney" @click="buildReport">
                    {{ loading ? 'Загрузка...' : 'Сформировать' }}
                </Button>
            </div>
        </header>

        <section v-if="!canViewMoney" class="admin-page__section">
            <div class="admin-page__empty">Недостаточно прав для просмотра выручки.</div>
        </section>

        <section v-if="canViewMoney" class="kitchen-revenue-page__filters-panel">
            <button
                type="button"
                class="kitchen-revenue-page__filters-toggle"
                @click="isFiltersOpen = !isFiltersOpen"
            >
                Фильтры
                <span :class="['kitchen-revenue-page__filters-icon', { 'is-open': isFiltersOpen }]">
                    ▼
                </span>
            </button>

            <div v-if="isFiltersOpen" class="kitchen-revenue-page__filters-content">
                <div class="kitchen-revenue-page__filters-grid">
                    <div class="kitchen-revenue-page__filter-block">
                        <p class="kitchen-revenue-page__filter-title">Рестораны</p>
                        <div v-if="restaurantOptions.length" class="kitchen-revenue-page__restaurants-list">
                            <Checkbox
                                label="Выбрать все"
                                :model-value="isAllRestaurantsSelected"
                                @update:model-value="toggleAllRestaurants"
                            />
                            <Checkbox
                                v-for="option in restaurantOptions"
                                :key="option.value"
                                :label="option.label"
                                :model-value="isRestaurantSelected(option.value)"
                                @update:model-value="(checked) => toggleRestaurantSelection(option.value, checked)"
                            />
                        </div>
                        <p v-else class="kitchen-revenue-page__empty-hint">
                            Нет доступных ресторанов.
                        </p>
                    </div>

                    <div class="kitchen-revenue-page__filter-block">
                        <p class="kitchen-revenue-page__filter-title">Период</p>
                        <div class="kitchen-revenue-page__dates-grid">
                            <DateInput v-model="fromDate" label="С даты" />
                            <DateInput v-model="toDate" label="По дату" />
                        </div>
                    </div>
                </div>
            </div>

            <p class="kitchen-revenue-page__summary">
                Период: {{ fromDate }} - {{ toDate }} | Итого: {{ formatMoney(totalAmount) }}
            </p>
        </section>

        <section v-if="canViewMoney" class="admin-page__section">
            <div v-if="loading" class="admin-page__empty">
                Загрузка выручки...
            </div>

            <div v-else-if="!reportDates.length || !reportMethods.length" class="admin-page__empty">
                Нет данных по выбранным фильтрам.
            </div>

            <div v-else class="kitchen-revenue-page__table-wrap">
                <Table class="kitchen-revenue-page__table">
                    <thead>
                        <tr>
                            <th class="kitchen-revenue-page__sticky-col">Метод оплаты</th>
                            <th v-for="dateKey in reportDates" :key="dateKey">
                                {{ formatDateLabel(dateKey) }}
                            </th>
                            <th>Итого</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="method in reportMethods" :key="method.method_guid">
                            <td class="kitchen-revenue-page__sticky-col">
                                {{ method.method_name || method.method_guid }}
                            </td>
                            <td v-for="dateKey in reportDates" :key="`${method.method_guid}:${dateKey}`">
                                {{ formatMoney(method.by_date?.[dateKey] || 0) }}
                            </td>
                            <td class="kitchen-revenue-page__cell-total">
                                {{ formatMoney(method.total_amount || 0) }}
                            </td>
                        </tr>
                    </tbody>
                    <tfoot>
                        <tr>
                            <th class="kitchen-revenue-page__sticky-col">Итого</th>
                            <th v-for="dateKey in reportDates" :key="`total:${dateKey}`">
                                {{ formatMoney(totalsByDate[dateKey] || 0) }}
                            </th>
                            <th class="kitchen-revenue-page__cell-total">
                                {{ formatMoney(totalAmount) }}
                            </th>
                        </tr>
                    </tfoot>
                </Table>
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { fetchKitchenRestaurants, fetchKitchenRevenueByPaymentMethods } from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Table from '@/components/UI-components/Table.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import { formatNumberValue } from '@/utils/format';

const userStore = useUserStore();
const toast = useToast();
const canViewMoney = computed(() =>
    userStore.hasAnyPermission('sales.report.view_money', 'iiko.view', 'iiko.manage'),
);

const loading = ref(false);
const isFiltersOpen = ref(true);
let revenueReportAbortController = null;
let revenueReportRequestSeq = 0;

const restaurants = ref([]);
const selectedRestaurantIds = ref([]);
const fromDate = ref(defaultMonthStart());
const toDate = ref(defaultToday());

const reportDates = ref([]);
const reportMethods = ref([]);
const totalsByDate = ref({});
const totalAmount = ref(0);

const restaurantOptions = computed(() =>
    (restaurants.value || [])
        .map((row) => ({
            value: Number(row.id),
            label: row.name || `#${row.id}`,
        }))
        .filter((row) => Number.isFinite(row.value)),
);

const selectedRestaurantIdsNormalized = computed(() =>
    Array.from(
        new Set(
            (selectedRestaurantIds.value || [])
                .map((value) => Number(value))
                .filter((value) => Number.isFinite(value)),
        ),
    ).sort((a, b) => a - b),
);

const isAllRestaurantsSelected = computed(() => {
    const allCount = restaurantOptions.value.length;
    if (!allCount) {
        return false;
    }
    return selectedRestaurantIdsNormalized.value.length === allCount;
});

function defaultToday() {
    return formatDateInputLocal(new Date());
}

function defaultMonthStart() {
    const dt = new Date();
    dt.setDate(1);
    return formatDateInputLocal(dt);
}

function formatDateInputLocal(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
        return '';
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function isRestaurantSelected(value) {
    const id = Number(value);
    return selectedRestaurantIdsNormalized.value.includes(id);
}

function toggleRestaurantSelection(value, checked) {
    const id = Number(value);
    if (!Number.isFinite(id)) {
        return;
    }
    if (checked) {
        selectedRestaurantIds.value = Array.from(new Set([...selectedRestaurantIdsNormalized.value, id]));
    } else {
        selectedRestaurantIds.value = selectedRestaurantIdsNormalized.value.filter((item) => item !== id);
    }
}

function toggleAllRestaurants(checked) {
    if (checked) {
        selectedRestaurantIds.value = restaurantOptions.value.map((item) => Number(item.value));
        return;
    }
    selectedRestaurantIds.value = [];
}

function formatMoney(value) {
    return formatNumberValue(value, {
        emptyValue: '-',
        invalidValue: '-',
        locale: 'ru-RU',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function formatDateLabel(dateValue) {
    if (!dateValue) {
        return '-';
    }
    const parsed = new Date(`${dateValue}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
        return dateValue;
    }
    return parsed.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
    });
}

function ensureValidFilters() {
    if (!canViewMoney.value) {
        toast.error('Недостаточно прав для просмотра выручки');
        return false;
    }
    if (!fromDate.value || !toDate.value) {
        toast.error('Укажи период дат');
        return false;
    }
    if (fromDate.value > toDate.value) {
        toast.error('Дата "С" не может быть позже даты "По"');
        return false;
    }
    if (!selectedRestaurantIdsNormalized.value.length) {
        toast.error('Выбери хотя бы один ресторан');
        return false;
    }
    return true;
}

function isRequestCanceled(error) {
    return (
        error?.code === 'ERR_CANCELED' ||
        error?.name === 'CanceledError' ||
        error?.message === 'canceled' ||
        error?.message === 'Request canceled'
    );
}

function getDefaultRestaurantSelectionIds() {
    const availableIds = restaurantOptions.value
        .map((item) => Number(item.value))
        .filter((value) => Number.isFinite(value));
    if (!availableIds.length) {
        return [];
    }

    const workplaceRestaurantId = Number(userStore.workplaceRestaurantId);
    if (Number.isFinite(workplaceRestaurantId) && availableIds.includes(workplaceRestaurantId)) {
        return [workplaceRestaurantId];
    }

    return [availableIds[0]];
}

async function loadRestaurants() {
    if (!canViewMoney.value) {
        return;
    }
    const data = await fetchKitchenRestaurants({ sales_participants_only: true });
    restaurants.value = Array.isArray(data) ? data : [];

    const available = new Set(restaurantOptions.value.map((item) => Number(item.value)));
    const selectedAvailableIds = selectedRestaurantIdsNormalized.value.filter((value) => available.has(value));
    if (selectedAvailableIds.length) {
        selectedRestaurantIds.value = selectedAvailableIds;
        return;
    }

    selectedRestaurantIds.value = getDefaultRestaurantSelectionIds();
}

async function buildReport() {
    if (!canViewMoney.value) {
        return;
    }
    if (!ensureValidFilters()) {
        return;
    }

    if (revenueReportAbortController) {
        revenueReportAbortController.abort();
        revenueReportAbortController = null;
    }
    const abortController = new AbortController();
    revenueReportAbortController = abortController;
    const requestSeq = ++revenueReportRequestSeq;
    loading.value = true;
    try {
        const params = new URLSearchParams();
        params.append('from_date', fromDate.value);
        params.append('to_date', toDate.value);
        for (const restId of selectedRestaurantIdsNormalized.value) {
            params.append('restaurant_ids', String(restId));
        }

        const payload = await fetchKitchenRevenueByPaymentMethods(params, {
            signal: abortController.signal,
        });
        if (requestSeq !== revenueReportRequestSeq || abortController.signal.aborted) {
            return;
        }

        reportDates.value = Array.isArray(payload.dates) ? payload.dates : [];
        totalsByDate.value = payload.totals_by_date && typeof payload.totals_by_date === 'object'
            ? payload.totals_by_date
            : {};
        totalAmount.value = Number(payload.total_amount || 0);

        const methods = Array.isArray(payload.methods) ? payload.methods : [];
        reportMethods.value = methods.map((row) => ({
            method_guid: row.method_guid,
            method_name: row.method_name,
            by_date: row.by_date && typeof row.by_date === 'object' ? row.by_date : {},
            total_amount: Number(row.total_amount || 0),
        }));
    } catch (error) {
        if (isRequestCanceled(error) || requestSeq !== revenueReportRequestSeq) {
            return;
        }
        toast.error(`Ошибка построения отчета: ${error.response?.data?.detail || error.message}`);
    } finally {
        if (requestSeq === revenueReportRequestSeq) {
            loading.value = false;
        }
        if (revenueReportAbortController === abortController) {
            revenueReportAbortController = null;
        }
    }
}

onMounted(async () => {
    if (!canViewMoney.value) {
        return;
    }
    try {
        await loadRestaurants();
        await buildReport();
    } catch (error) {
        toast.error(`Ошибка загрузки данных: ${error.response?.data?.detail || error.message}`);
    }
});

onBeforeUnmount(() => {
    if (revenueReportAbortController) {
        revenueReportAbortController.abort();
        revenueReportAbortController = null;
    }
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-revenue-report' as *;
</style>
