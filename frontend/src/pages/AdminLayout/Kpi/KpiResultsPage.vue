<template>
    <div class="kpi-page">
        <section class="kpi-panel">
            <div class="kpi-panel__header">
                <div>
                    <h2 class="kpi-panel__title">{{ resultFormTitle }}</h2>
                    <p class="kpi-panel__subtitle">Фиксация фактических значений KPI.</p>
                </div>
            </div>
            <div class="kpi-panel__grid">
                <Select
                    v-model="resultForm.metricId"
                    label="Метрика"
                    :options="metricOptions"
                    placeholder="Выберите метрику"
                />
                <Select
                    v-model="resultForm.restaurantId"
                    label="Ресторан"
                    :options="restaurantOptions"
                    placeholder="Все рестораны"
                />
                <Select
                    v-model="resultForm.positionId"
                    label="Должность"
                    :options="positionOptions"
                    placeholder="Все должности"
                />
                <Input
                    v-model="resultForm.employeeId"
                    label="Сотрудник (ID)"
                    placeholder="Опционально"
                />
                <div class="kpi-panel__field">
                    <label class="kpi-panel__label">Период от</label>
                    <DateInput v-model="resultForm.periodStart" />
                </div>
                <div class="kpi-panel__field">
                    <label class="kpi-panel__label">Период до</label>
                    <DateInput v-model="resultForm.periodEnd" />
                </div>
                <Input
                    v-model="resultForm.factValue"
                    label="Факт"
                    type="number"
                    step="0.01"
                />
                <Select
                    v-model="resultForm.status"
                    label="Статус"
                    :options="statusOptions"
                />
                <Select
                    v-model="resultForm.source"
                    label="Источник"
                    :options="sourceOptions"
                />
                <div class="kpi-panel__field kpi-panel__field--full">
                    <label class="kpi-panel__label">Комментарий</label>
                    <textarea v-model="resultForm.comment" class="kpi-panel__textarea" rows="2" />
                </div>
            </div>
            <div class="kpi-panel__actions">
                <Button color="primary" :loading="resultSaving" @click="handleSaveResult">
                    {{ resultFormAction }}
                </Button>
                <Button
                    v-if="resultEditingId"
                    color="ghost"
                    :disabled="resultSaving"
                    @click="resetResultForm"
                >
                    Отменить
                </Button>
            </div>
        </section>

        <section class="kpi-panel">
            <div class="kpi-panel__header">
                <div>
                    <h2 class="kpi-panel__title">Результаты KPI</h2>
                    <p class="kpi-panel__subtitle">Всего: {{ results.length }}</p>
                </div>
                <Button color="outline" size="sm" :loading="resultsLoading" @click="loadResults">
                    Обновить
                </Button>
            </div>
            <div v-if="results.length" class="kpi-list">
                <div v-for="result in results" :key="result.id" class="kpi-card">
                    <div class="kpi-card__top">
                        <span class="kpi-card__id">№ {{ result.id }}</span>
                        <span class="kpi-card__status" :class="{ 'is-muted': result.status !== 'confirmed' }">
                            {{ statusLabel(result.status) }}
                        </span>
                    </div>
                    <div class="kpi-card__title">{{ metricName(result.metric) }}</div>
                    <div class="kpi-card__meta">
                        <span>{{ restaurantLabel(result.restaurant_id) }}</span>
                        <span>{{ positionLabel(result.position_id) }}</span>
                        <span>{{ formatDateRange(result.period_start, result.period_end) }}</span>
                        <span>Факт: {{ formatNumber(result.fact_value) }}</span>
                    </div>
                    <div class="kpi-card__footer">
                        <Button size="sm" @click="startEditResult(result)">Изменить</Button>
                        <Button
                            size="sm"
                            color="danger"
                            :loading="resultDeletingId === result.id"
                            @click="handleDeleteResult(result)"
                        >
                            Удалить
                        </Button>
                    </div>
                </div>
            </div>
            <p v-else class="kpi-list__empty">Результаты пока не добавлены.</p>
        </section>
    </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import {
    createKpiResult,
    deleteKpiResult,
    fetchAccessPositions,
    fetchKpiMetrics,
    fetchKpiResults,
    fetchRestaurants,
    updateKpiResult,
} from '@/api';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';

const toast = useToast();

const results = ref([]);
const resultsLoading = ref(false);
const resultSaving = ref(false);
const resultDeletingId = ref(null);
const resultEditingId = ref(null);

const metrics = ref([]);
const restaurants = ref([]);
const positions = ref([]);

const statusOptions = [
    { value: 'draft', label: 'Черновик' },
    { value: 'confirmed', label: 'Подтвержден' },
];
const sourceOptions = [
    { value: 'manual', label: 'Вручную' },
    { value: 'import', label: 'Импорт' },
    { value: 'calculated', label: 'Авто' },
];

const resultForm = ref(defaultResultForm());

function defaultResultForm() {
    const today = new Date().toISOString().slice(0, 10);
    return {
        metricId: null,
        restaurantId: null,
        positionId: null,
        employeeId: '',
        periodStart: today,
        periodEnd: today,
        factValue: '',
        status: 'draft',
        source: 'manual',
        comment: '',
    };
}

const resultFormTitle = computed(() =>
    resultEditingId.value ? 'Редактировать результат' : 'Создать результат',
);
const resultFormAction = computed(() => (resultEditingId.value ? 'Сохранить' : 'Создать'));

const metricOptions = computed(() =>
    metrics.value.map((metric) => ({
        value: metric.id,
        label: metric.name,
    })),
);
const restaurantOptions = computed(() => [
    { value: null, label: 'Все рестораны' },
    ...restaurants.value.map((rest) => ({ value: rest.id, label: rest.name })),
]);
const positionOptions = computed(() => [
    { value: null, label: 'Все должности' },
    ...positions.value.map((pos) => ({ value: pos.id, label: pos.name })),
]);

function metricName(metric) {
    return metric?.name || `Метрика ${metric?.id || ''}`.trim();
}

function restaurantLabel(id) {
    const rest = restaurants.value.find((item) => Number(item.id) === Number(id));
    return rest?.name || (id ? `Ресторан ${id}` : 'Все рестораны');
}

function positionLabel(id) {
    const pos = positions.value.find((item) => Number(item.id) === Number(id));
    return pos?.name || (id ? `Должность ${id}` : 'Все должности');
}

function formatDateRange(start, end) {
    if (!start && !end) return '';
    if (start && end && start === end) return start;
    return [start, end].filter(Boolean).join(' — ');
}

function formatNumber(value) {
    const num = Number(value || 0);
    return new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(num);
}

function statusLabel(status) {
    const option = statusOptions.find((item) => item.value === status);
    return option ? option.label : status;
}

async function loadOptions() {
    try {
        const [metricsData, restaurantsData, positionsData] = await Promise.all([
            fetchKpiMetrics(),
            fetchRestaurants(),
            fetchAccessPositions(),
        ]);
        metrics.value = Array.isArray(metricsData?.items) ? metricsData.items : metricsData || [];
        restaurants.value = Array.isArray(restaurantsData?.items)
            ? restaurantsData.items
            : restaurantsData || [];
        positions.value = Array.isArray(positionsData) ? positionsData : positionsData?.items || [];
    } catch (error) {
        toast.error('Не удалось загрузить справочники');
        console.error(error);
    }
}

async function loadResults() {
    resultsLoading.value = true;
    try {
        const data = await fetchKpiResults();
        results.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить результаты KPI');
        console.error(error);
    } finally {
        resultsLoading.value = false;
    }
}

function resetResultForm() {
    resultEditingId.value = null;
    resultForm.value = defaultResultForm();
}

function startEditResult(result) {
    resultEditingId.value = result.id;
    resultForm.value = {
        metricId: result.metric_id || null,
        restaurantId: result.restaurant_id ?? null,
        positionId: result.position_id ?? null,
        employeeId: result.employee_id || '',
        periodStart: result.period_start,
        periodEnd: result.period_end,
        factValue: result.fact_value ?? '',
        status: result.status || 'draft',
        source: result.source || 'manual',
        comment: result.comment || '',
    };
}

function parseNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(String(value).replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
}

async function handleSaveResult() {
    if (!resultForm.value.metricId) {
        toast.error('Выберите метрику');
        return;
    }
    if (!resultForm.value.periodStart || !resultForm.value.periodEnd) {
        toast.error('Укажите период');
        return;
    }
    const payload = {
        metric_id: Number(resultForm.value.metricId),
        restaurant_id: resultForm.value.restaurantId ? Number(resultForm.value.restaurantId) : null,
        position_id: resultForm.value.positionId ? Number(resultForm.value.positionId) : null,
        employee_id: resultForm.value.employeeId ? Number(resultForm.value.employeeId) : null,
        period_start: resultForm.value.periodStart,
        period_end: resultForm.value.periodEnd,
        fact_value: parseNumber(resultForm.value.factValue) ?? 0,
        status: resultForm.value.status,
        source: resultForm.value.source,
        comment: resultForm.value.comment || null,
    };
    resultSaving.value = true;
    try {
        if (resultEditingId.value) {
            await updateKpiResult(resultEditingId.value, payload);
            toast.success('Результат обновлен');
        } else {
            await createKpiResult(payload);
            toast.success('Результат создан');
        }
        await loadResults();
        resetResultForm();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить результат');
        console.error(error);
    } finally {
        resultSaving.value = false;
    }
}

async function handleDeleteResult(result) {
    if (!result?.id) return;
    if (!window.confirm('Удалить результат?')) return;
    resultDeletingId.value = result.id;
    try {
        await deleteKpiResult(result.id);
        toast.success('Результат удален');
        await loadResults();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить результат');
        console.error(error);
    } finally {
        resultDeletingId.value = null;
    }
}

onMounted(async () => {
    await loadOptions();
    await loadResults();
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kpi-results' as *;
</style>
