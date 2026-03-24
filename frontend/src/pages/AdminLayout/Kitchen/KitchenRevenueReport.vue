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

        <section
            v-if="canViewMoney && !loading && reportDates.length && reportMethods.length"
            class="admin-page__section"
        >
            <div class="kitchen-revenue-page__dashboard-header">
                <div>
                    <h3 class="kitchen-revenue-page__dashboard-title">Дашборд выручки</h3>
                    <p class="kitchen-revenue-page__dashboard-subtitle">
                        Управленческий обзор по выбранному периоду: динамика, структура методов
                        оплаты и лидеры по объёму выручки.
                    </p>
                </div>
            </div>

            <div class="kitchen-revenue-page__stats">
                <article class="kitchen-revenue-page__stat-card">
                    <p>Выручка периода</p>
                    <strong>{{ formatMoney(totalAmount) }}</strong>
                </article>
                <article class="kitchen-revenue-page__stat-card">
                    <p>Среднее за день</p>
                    <strong>{{ formatMoney(averageRevenuePerDay) }}</strong>
                </article>
                <article class="kitchen-revenue-page__stat-card">
                    <p>Активных дней</p>
                    <strong>{{ formatNumber(activeRevenueDaysCount) }}</strong>
                </article>
                <article class="kitchen-revenue-page__stat-card">
                    <p>Главный метод оплаты</p>
                    <strong>{{ topRevenueMethodLabel }}</strong>
                    <span>{{ formatMoney(topRevenueMethodAmount) }}</span>
                </article>
            </div>

            <div class="kitchen-revenue-page__dashboard-grid">
                <div class="kitchen-revenue-page__chart-card kitchen-revenue-page__chart-card--wide">
                    <div class="kitchen-revenue-page__chart-head">
                        <div>
                            <p class="kitchen-revenue-page__chart-title">Динамика по дням</p>
                            <p class="kitchen-revenue-page__chart-note">
                                Дневная выручка и средний уровень по периоду
                            </p>
                        </div>
                    </div>
                    <VChart
                        class="kitchen-revenue-page__chart"
                        :option="revenueDailyTrendOption"
                        autoresize
                    />
                </div>

                <div class="kitchen-revenue-page__chart-card">
                    <div class="kitchen-revenue-page__chart-head">
                        <div>
                            <p class="kitchen-revenue-page__chart-title">Структура оплат</p>
                            <p class="kitchen-revenue-page__chart-note">
                                Доля каждого метода оплаты в итоговой выручке
                            </p>
                        </div>
                    </div>
                    <VChart
                        class="kitchen-revenue-page__chart"
                        :option="revenueMethodShareOption"
                        autoresize
                    />
                </div>

                <div class="kitchen-revenue-page__chart-card">
                    <div class="kitchen-revenue-page__chart-head">
                        <div>
                            <p class="kitchen-revenue-page__chart-title">Методы-лидеры</p>
                            <p class="kitchen-revenue-page__chart-note">
                                Основной вклад в выручку по способам оплаты
                            </p>
                        </div>
                    </div>
                    <VChart
                        class="kitchen-revenue-page__chart"
                        :option="revenueMethodRankingOption"
                        autoresize
                    />
                </div>
            </div>
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
import { use } from 'echarts/core';
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import { CanvasRenderer } from 'echarts/renderers';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import { fetchKitchenRestaurants, fetchKitchenRevenueByPaymentMethods } from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Table from '@/components/UI-components/Table.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import VChart from 'vue-echarts';
import { formatNumberValue } from '@/utils/format';

use([CanvasRenderer, BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent]);

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

const averageRevenuePerDay = computed(() =>
    reportDates.value.length ? totalAmount.value / reportDates.value.length : 0,
);

const activeRevenueDaysCount = computed(
    () =>
        reportDates.value.filter((dateKey) => Number(totalsByDate.value?.[dateKey] || 0) > 0)
            .length,
);

const revenueMethodRows = computed(() =>
    [...reportMethods.value].sort((left, right) => Number(right.total_amount || 0) - Number(left.total_amount || 0)),
);

const topRevenueMethod = computed(() => revenueMethodRows.value[0] || null);
const topRevenueMethodLabel = computed(
    () => topRevenueMethod.value?.method_name || topRevenueMethod.value?.method_guid || 'Нет данных',
);
const topRevenueMethodAmount = computed(() => Number(topRevenueMethod.value?.total_amount || 0));

const revenueDailyTrendOption = computed(() => ({
    color: ['#c79b63', '#5ea1ff'],
    tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(16, 13, 10, 0.94)',
        borderColor: 'rgba(199, 155, 99, 0.35)',
        textStyle: { color: '#f8f3ec' },
        formatter(params) {
            const lines = [`<strong>${params[0]?.axisValue || '-'}</strong>`];
            for (const item of params) {
                lines.push(`${item.marker}${item.seriesName}: ${formatMoney(item.value)}`);
            }
            return lines.join('<br/>');
        },
    },
    grid: { left: 56, right: 24, top: 24, bottom: 48 },
    xAxis: {
        type: 'category',
        data: reportDates.value.map((dateKey) => formatDateLabel(dateKey)),
        axisLabel: { color: '#b9aa95' },
        axisLine: { lineStyle: { color: 'rgba(185, 170, 149, 0.2)' } },
    },
    yAxis: {
        type: 'value',
        axisLabel: {
            color: '#b9aa95',
            formatter: (value) => formatAxisShortValue(value),
        },
        splitLine: { lineStyle: { color: 'rgba(185, 170, 149, 0.12)' } },
    },
    series: [
        {
            name: 'Выручка',
            type: 'bar',
            barMaxWidth: 28,
            data: reportDates.value.map((dateKey) => Number(totalsByDate.value?.[dateKey] || 0)),
            itemStyle: { borderRadius: [10, 10, 0, 0] },
        },
        {
            name: 'Среднее за день',
            type: 'line',
            smooth: true,
            showSymbol: false,
            data: reportDates.value.map(() => averageRevenuePerDay.value),
            lineStyle: { width: 3, type: 'dashed' },
        },
    ],
}));

const revenueMethodShareOption = computed(() => ({
    color: ['#c79b63', '#5ea1ff', '#54c38f', '#d97ab0', '#e07c68', '#9f7aea', '#606a7b'],
    tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(16, 13, 10, 0.94)',
        borderColor: 'rgba(199, 155, 99, 0.35)',
        textStyle: { color: '#f8f3ec' },
        formatter(params) {
            return `<strong>${params.name}</strong><br/>Выручка: ${formatMoney(params.value)}<br/>Доля: ${formatNumber(params.percent)}%`;
        },
    },
    legend: {
        bottom: 0,
        textStyle: { color: '#b9aa95' },
    },
    series: [
        {
            name: 'Методы оплаты',
            type: 'pie',
            radius: ['48%', '72%'],
            center: ['50%', '44%'],
            label: {
                color: '#f4ede3',
                formatter: ({ percent }) => `${formatNumber(percent)}%`,
            },
            labelLine: { lineStyle: { color: 'rgba(185, 170, 149, 0.4)' } },
            data: collapseRevenueMethods(revenueMethodRows.value, 6),
        },
    ],
}));

const revenueMethodRankingOption = computed(() => {
    const rows = revenueMethodRows.value.slice(0, 8).reverse();
    return {
        color: ['#c79b63'],
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(16, 13, 10, 0.94)',
            borderColor: 'rgba(199, 155, 99, 0.35)',
            textStyle: { color: '#f8f3ec' },
            formatter(params) {
                const item = params[0];
                return `<strong>${item?.name || '-'}</strong><br/>Выручка: ${formatMoney(item?.value)}`;
            },
        },
        grid: { left: 150, right: 24, top: 20, bottom: 20 },
        xAxis: {
            type: 'value',
            axisLabel: {
                color: '#b9aa95',
                formatter: (value) => formatAxisShortValue(value),
            },
            splitLine: { lineStyle: { color: 'rgba(185, 170, 149, 0.12)' } },
        },
        yAxis: {
            type: 'category',
            data: rows.map((row) => row.method_name || row.method_guid || 'Не указано'),
            axisLabel: { color: '#d7c8b4' },
            axisLine: { show: false },
            axisTick: { show: false },
        },
        series: [
            {
                name: 'Выручка',
                type: 'bar',
                barMaxWidth: 22,
                data: rows.map((row) => Number(row.total_amount || 0)),
                itemStyle: { borderRadius: [0, 10, 10, 0] },
            },
        ],
    };
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

function formatNumber(value) {
    return formatNumberValue(value, {
        emptyValue: '-',
        invalidValue: '-',
        locale: 'ru-RU',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    });
}

function formatAxisShortValue(value) {
    const numeric = Number(value || 0);
    if (!Number.isFinite(numeric)) {
        return '-';
    }
    if (Math.abs(numeric) >= 1000000) {
        return `${formatNumber(numeric / 1000000)}м`;
    }
    if (Math.abs(numeric) >= 1000) {
        return `${formatNumber(numeric / 1000)}к`;
    }
    return formatNumber(numeric);
}

function collapseRevenueMethods(rows, limit = 6) {
    const top = (rows || []).slice(0, limit).map((row) => ({
        name: row.method_name || row.method_guid || 'Не указано',
        value: Number(row.total_amount || 0),
    }));
    const rest = (rows || [])
        .slice(limit)
        .reduce((sum, row) => sum + Number(row.total_amount || 0), 0);
    if (rest > 0) {
        top.push({ name: 'Прочее', value: rest });
    }
    return top.filter((item) => item.value > 0);
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
