<template>
    <div class="kpi-page">
        <section class="kpi-panel">
            <div class="kpi-panel__header">
                <div>
                    <h2 class="kpi-panel__title">Настройка KPI</h2>
                    <p class="kpi-panel__subtitle">Метрики и правила начисления KPI.</p>
                </div>
                <div class="kpi-panel__header-actions">
                    <Button color="outline" size="sm" :loading="loading" @click="loadKpiData">
                        Обновить
                    </Button>
                    <Button color="primary" size="sm" @click="openCreateModal">
                        Добавить KPI
                    </Button>
                </div>
            </div>
            <div v-if="loading" class="kpi-empty">
                <p class="kpi-empty__title">Загрузка KPI...</p>
            </div>
            <div v-else-if="metricRows.length" class="kpi-list">
                <button
                    v-for="metric in metricRows"
                    :key="metric.id"
                    type="button"
                    class="kpi-card kpi-card--button"
                    @click="openEditModal(metric)"
                >
                    <div class="kpi-card__top">
                        <span class="kpi-card__id">{{ metric.code }}</span>
                        <span class="kpi-card__status" :class="{ 'is-muted': !metric.is_active }">
                            {{ metric.is_active ? 'Активна' : 'Отключена' }}
                        </span>
                    </div>
                    <div class="kpi-card__title">{{ metric.name }}</div>
                    <div class="kpi-card__meta">
                        <span v-if="metric.unit">Ед.: {{ metric.unit }}</span>
                        <span>База: {{ calculationBaseLabel(metric.calculation_base) }}</span>
                        <span>Правил: {{ metric.rulesCount }}</span>
                        <span v-if="metric.rulesCount">Активных: {{ metric.activeRulesCount }}</span>
                    </div>
                </button>
            </div>
            <div v-else class="kpi-empty">
                <p class="kpi-empty__title">Метрик пока нет</p>
                <p class="kpi-empty__subtitle">Создайте первую KPI-метрику и сразу задайте правила.</p>
                <Button color="primary" size="sm" @click="openCreateModal">Добавить KPI</Button>
            </div>

        </section>

        <Modal v-if="isModalOpen" class="kpi-settings__modal" @close="closeModal">
            <template #header>
                <div>
                    <h3 class="kpi-settings__modal-title">
                        {{ isEditing ? 'Редактировать KPI' : 'Новый KPI' }}
                    </h3>
                    <p class="kpi-settings__modal-subtitle">
                        Заполните базовые данные и задайте правила начисления.
                    </p>
                </div>
            </template>

            <div class="kpi-settings__section">
                <h4 class="kpi-settings__section-title">Базовые данные</h4>
                <div class="kpi-panel__grid">
                    <Input
                        v-model="metricForm.code"
                        label="Код метрики"
                        placeholder="sales_rate"
                        required
                    />
                    <Input
                        v-model="metricForm.name"
                        label="Название"
                        placeholder="Выручка"
                        required
                    />
                    <Input
                        v-model="metricForm.unit"
                        label="Единица измерения"
                        placeholder="₽, %, шт"
                    />
                    <Select
                        v-model="metricForm.calculationBase"
                        label="База расчета"
                        :options="calculationBaseOptions"
                    />
                    <div class="kpi-panel__field">
                        <label class="kpi-panel__label">Активна</label>
                        <input v-model="metricForm.isActive" type="checkbox" class="kpi-panel__checkbox">
                    </div>
                    <div class="kpi-panel__field kpi-panel__field--full">
                        <label class="kpi-panel__label">Описание</label>
                        <textarea v-model="metricForm.description" class="kpi-panel__textarea" rows="3" />
                    </div>
                </div>
            </div>

            <div class="kpi-settings__section">
                <div class="kpi-settings__section-header">
                    <h4 class="kpi-settings__section-title">Правила KPI</h4>
                    <Button color="outline" size="sm" @click="addRule">Добавить правило</Button>
                </div>
                <div class="kpi-settings__rule-list">
                    <div v-for="(rule, index) in ruleForms" :key="rule.localId" class="kpi-settings__rule-card">
                        <div class="kpi-settings__rule-header">
                            <div>
                                <h5 class="kpi-settings__rule-title">Правило {{ index + 1 }}</h5>
                                <p class="kpi-settings__rule-subtitle">
                                    {{ rule.isActive ? 'Активно' : 'Отключено' }}
                                </p>
                            </div>
                            <Button
                                color="ghost"
                                size="sm"
                                :disabled="saving"
                                @click="removeRule(index)"
                            >
                                Удалить правило
                            </Button>
                        </div>
                        <div class="kpi-panel__grid">
                            <Select
                                v-model="rule.restaurantId"
                                label="Ресторан"
                                :options="restaurantOptions"
                                placeholder="Все рестораны"
                            />
                            <Select
                                v-model="rule.positionId"
                                label="Должность"
                                :options="positionOptions"
                                placeholder="Все должности"
                            />
                            <Input
                                v-model="rule.departmentCode"
                                label="Код отдела"
                                placeholder="Опционально"
                            />
                            <Input
                                v-model="rule.employeeId"
                                label="Сотрудник (ID)"
                                placeholder="Опционально"
                            />
                            <div class="kpi-panel__field">
                                <label class="kpi-panel__label">Период от</label>
                                <DateInput v-model="rule.periodStart" />
                            </div>
                            <div class="kpi-panel__field">
                                <label class="kpi-panel__label">Период до</label>
                                <DateInput v-model="rule.periodEnd" />
                            </div>
                            <Select
                                v-model="rule.thresholdType"
                                label="Тип порога"
                                :options="thresholdOptions"
                            />
                            <Input
                                v-model="rule.targetValue"
                                label="Цель"
                                type="number"
                                step="0.01"
                            />
                            <Input
                                v-model="rule.warningValue"
                                label="Нижний порог"
                                type="number"
                                step="0.01"
                                :disabled="rule.thresholdType !== 'dual'"
                            />
                            <Select
                                v-model="rule.bonusCondition"
                                label="Условие бонуса"
                                :options="comparisonOptions"
                            />
                            <Select
                                v-model="rule.bonusType"
                                label="Тип бонуса"
                                :options="effectTypeOptions"
                            />
                            <Input
                                v-model="rule.bonusValue"
                                label="Значение бонуса"
                                type="number"
                                step="0.01"
                            />
                            <Select
                                v-model="rule.bonusBase"
                                label="База бонуса"
                                :options="valueBaseOptions"
                            />
                            <Select
                                v-model="rule.penaltyCondition"
                                label="Условие штрафа"
                                :options="comparisonOptions"
                            />
                            <Select
                                v-model="rule.penaltyType"
                                label="Тип штрафа"
                                :options="effectTypeOptions"
                            />
                            <Input
                                v-model="rule.penaltyValue"
                                label="Значение штрафа"
                                type="number"
                                step="0.01"
                            />
                            <Select
                                v-model="rule.penaltyBase"
                                label="База штрафа"
                                :options="valueBaseOptions"
                            />
                            <div class="kpi-panel__field">
                                <label class="kpi-panel__label">Активно</label>
                                <input v-model="rule.isActive" type="checkbox" class="kpi-panel__checkbox">
                            </div>
                            <div class="kpi-panel__field kpi-panel__field--full">
                                <label class="kpi-panel__label">Комментарий</label>
                                <textarea v-model="rule.comment" class="kpi-panel__textarea" rows="2" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <template #footer>
                <div class="kpi-settings__modal-actions">
                    <Button color="primary" :loading="saving" @click="handleSave">
                        {{ isEditing ? 'Сохранить' : 'Создать KPI' }}
                    </Button>
                    <Button color="ghost" :disabled="saving" @click="closeModal">
                        Отмена
                    </Button>
                    <Button
                        v-if="isEditing"
                        color="danger"
                        :disabled="saving"
                        @click="handleDeleteMetric"
                    >
                        Удалить KPI
                    </Button>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import {
    createKpiMetric,
    createKpiRule,
    deleteKpiMetric,
    deleteKpiRule,
    fetchAccessPositions,
    fetchKpiMetrics,
    fetchKpiRules,
    fetchRestaurants,
    updateKpiMetric,
    updateKpiRule,
} from '@/api';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import Modal from '@/components/UI-components/Modal.vue';

const toast = useToast();

const metrics = ref([]);
const rules = ref([]);
const restaurants = ref([]);
const positions = ref([]);

const loading = ref(false);
const saving = ref(false);
const isModalOpen = ref(false);
const editingMetricId = ref(null);
const removedRuleIds = ref([]);

const calculationBaseOptions = [
    { value: 'none', label: 'Нет' },
    { value: 'salary', label: 'Оклад/зарплата' },
    { value: 'hours_sum', label: 'Часы' },
    { value: 'rate', label: 'Ставка' },
];
const thresholdOptions = [
    { value: 'single', label: 'Один порог' },
    { value: 'dual', label: 'Два порога' },
];
const comparisonOptions = [
    { value: 'gte', label: '≥' },
    { value: 'gt', label: '>' },
    { value: 'lte', label: '≤' },
    { value: 'lt', label: '<' },
];
const effectTypeOptions = [
    { value: 'none', label: 'Нет' },
    { value: 'fixed', label: 'Фикс' },
    { value: 'percent', label: '%' },
];
const valueBaseOptions = [
    { value: 'none', label: 'Нет' },
    { value: 'salary', label: 'Оклад/зарплата' },
    { value: 'hours_sum', label: 'Часы' },
    { value: 'rate', label: 'Ставка' },
];

let ruleCounter = 0;

function defaultMetricForm() {
    return {
        code: '',
        name: '',
        description: '',
        unit: '',
        calculationBase: 'none',
        isActive: true,
    };
}

function defaultRuleForm() {
    const today = new Date().toISOString().slice(0, 10);
    ruleCounter += 1;
    return {
        localId: `rule-${Date.now()}-${ruleCounter}`,
        id: null,
        restaurantId: null,
        positionId: null,
        departmentCode: '',
        employeeId: '',
        periodStart: today,
        periodEnd: today,
        thresholdType: 'single',
        targetValue: '',
        warningValue: '',
        bonusCondition: 'gte',
        bonusType: 'none',
        bonusValue: '',
        bonusBase: 'none',
        penaltyCondition: 'lte',
        penaltyType: 'none',
        penaltyValue: '',
        penaltyBase: 'none',
        isActive: true,
        comment: '',
    };
}

const metricForm = ref(defaultMetricForm());
const ruleForms = ref([defaultRuleForm()]);

const isEditing = computed(() => Boolean(editingMetricId.value));

const metricRows = computed(() =>
    metrics.value.map((metric) => {
        const metricRules = rules.value.filter((rule) => Number(rule.metric_id) === Number(metric.id));
        return {
            ...metric,
            rulesCount: metricRules.length,
            activeRulesCount: metricRules.filter((rule) => rule.is_active).length,
        };
    }),
);

const restaurantOptions = computed(() => [
    { value: null, label: 'Все рестораны' },
    ...restaurants.value.map((rest) => ({ value: rest.id, label: rest.name })),
]);
const positionOptions = computed(() => [
    { value: null, label: 'Все должности' },
    ...positions.value.map((pos) => ({ value: pos.id, label: pos.name })),
]);

function calculationBaseLabel(value) {
    const option = calculationBaseOptions.find((item) => item.value === value);
    return option ? option.label : value || '—';
}

function parseNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(String(value).replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
}

function openCreateModal() {
    editingMetricId.value = null;
    metricForm.value = defaultMetricForm();
    ruleForms.value = [defaultRuleForm()];
    removedRuleIds.value = [];
    isModalOpen.value = true;
}

function mapRuleToForm(rule) {
    return {
        localId: `rule-${rule.id}`,
        id: rule.id,
        restaurantId: rule.restaurant_id ?? null,
        positionId: rule.position_id ?? null,
        departmentCode: rule.department_code || '',
        employeeId: rule.employee_id || '',
        periodStart: rule.period_start,
        periodEnd: rule.period_end,
        thresholdType: rule.threshold_type || 'single',
        targetValue: rule.target_value ?? '',
        warningValue: rule.warning_value ?? '',
        bonusCondition: rule.bonus_condition || 'gte',
        bonusType: rule.bonus_type || 'none',
        bonusValue: rule.bonus_value ?? '',
        bonusBase: rule.bonus_base || 'none',
        penaltyCondition: rule.penalty_condition || 'lte',
        penaltyType: rule.penalty_type || 'none',
        penaltyValue: rule.penalty_value ?? '',
        penaltyBase: rule.penalty_base || 'none',
        isActive: Boolean(rule.is_active),
        comment: rule.comment || '',
    };
}

function openEditModal(metric) {
    editingMetricId.value = metric.id;
    metricForm.value = {
        code: metric.code || '',
        name: metric.name || '',
        description: metric.description || '',
        unit: metric.unit || '',
        calculationBase: metric.calculation_base || 'none',
        isActive: Boolean(metric.is_active),
    };
    const metricRules = rules.value
        .filter((rule) => Number(rule.metric_id) === Number(metric.id))
        .map((rule) => mapRuleToForm(rule));
    ruleForms.value = metricRules.length ? metricRules : [defaultRuleForm()];
    removedRuleIds.value = [];
    isModalOpen.value = true;
}

function closeModal() {
    isModalOpen.value = false;
    saving.value = false;
}

function addRule() {
    ruleForms.value.push(defaultRuleForm());
}

function removeRule(index) {
    if (ruleForms.value.length <= 1) {
        toast.error('Нужно хотя бы одно правило');
        return;
    }
    const rule = ruleForms.value[index];
    if (rule?.id && !window.confirm('Удалить правило?')) {
        return;
    }
    const [removed] = ruleForms.value.splice(index, 1);
    if (removed?.id) {
        removedRuleIds.value = [...removedRuleIds.value, removed.id];
    }
}

function validateRules() {
    for (const rule of ruleForms.value) {
        if (!rule.periodStart || !rule.periodEnd) {
            toast.error('Укажите период для всех правил');
            return false;
        }
        if (rule.thresholdType === 'dual') {
            const warning = parseNumber(rule.warningValue);
            if (warning === null) {
                toast.error('Для двух порогов укажите нижний порог');
                return false;
            }
        }
    }
    return true;
}

function buildRulePayload(rule, metricId) {
    return {
        metric_id: metricId,
        restaurant_id: rule.restaurantId ? Number(rule.restaurantId) : null,
        position_id: rule.positionId ? Number(rule.positionId) : null,
        department_code: rule.departmentCode?.trim() || null,
        employee_id: rule.employeeId ? Number(rule.employeeId) : null,
        period_start: rule.periodStart,
        period_end: rule.periodEnd,
        threshold_type: rule.thresholdType,
        target_value: parseNumber(rule.targetValue) ?? 0,
        warning_value: parseNumber(rule.warningValue),
        bonus_condition: rule.bonusCondition,
        bonus_type: rule.bonusType,
        bonus_value: parseNumber(rule.bonusValue) ?? 0,
        bonus_base: rule.bonusBase,
        penalty_condition: rule.penaltyCondition,
        penalty_type: rule.penaltyType,
        penalty_value: parseNumber(rule.penaltyValue) ?? 0,
        penalty_base: rule.penaltyBase,
        is_active: Boolean(rule.isActive),
        comment: rule.comment?.trim() || null,
    };
}

async function loadOptions() {
    try {
        const [restaurantsData, positionsData] = await Promise.all([
            fetchRestaurants(),
            fetchAccessPositions(),
        ]);
        restaurants.value = Array.isArray(restaurantsData?.items)
            ? restaurantsData.items
            : restaurantsData || [];
        positions.value = Array.isArray(positionsData) ? positionsData : positionsData?.items || [];
    } catch (error) {
        toast.error('Не удалось загрузить справочники');
        console.error(error);
    }
}

async function loadKpiData() {
    loading.value = true;
    try {
        const [metricsData, rulesData] = await Promise.all([
            fetchKpiMetrics(),
            fetchKpiRules(),
        ]);
        metrics.value = Array.isArray(metricsData?.items) ? metricsData.items : metricsData || [];
        rules.value = Array.isArray(rulesData?.items) ? rulesData.items : rulesData || [];
    } catch (error) {
        toast.error('Не удалось загрузить KPI');
        console.error(error);
    } finally {
        loading.value = false;
    }
}

async function handleSave() {
    const payload = {
        code: metricForm.value.code.trim(),
        name: metricForm.value.name.trim(),
        description: metricForm.value.description?.trim() || null,
        unit: metricForm.value.unit?.trim() || null,
        calculation_base: metricForm.value.calculationBase || 'none',
        is_active: Boolean(metricForm.value.isActive),
    };
    if (!payload.code || !payload.name) {
        toast.error('Заполните код и название метрики');
        return;
    }
    if (!ruleForms.value.length) {
        toast.error('Добавьте хотя бы одно правило');
        return;
    }
    if (!validateRules()) {
        return;
    }

    saving.value = true;
    try {
        let metricId = editingMetricId.value;
        if (metricId) {
            await updateKpiMetric(metricId, payload);
        } else {
            const created = await createKpiMetric(payload);
            metricId = created?.id;
        }

        if (!metricId) {
            throw new Error('Metric id is missing after save');
        }

        const ruleRequests = ruleForms.value.map((rule) => {
            const rulePayload = buildRulePayload(rule, metricId);
            if (rule.id) {
                return updateKpiRule(rule.id, rulePayload);
            }
            return createKpiRule(rulePayload);
        });

        const deleteRequests = removedRuleIds.value.map((id) => deleteKpiRule(id));

        await Promise.all([...ruleRequests, ...deleteRequests]);

        toast.success(isEditing.value ? 'KPI обновлен' : 'KPI создан');
        await loadKpiData();
        closeModal();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить KPI');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function handleDeleteMetric() {
    if (!editingMetricId.value) return;
    if (!window.confirm('Удалить KPI и все связанные правила?')) return;
    saving.value = true;
    try {
        await deleteKpiMetric(editingMetricId.value);
        toast.success('KPI удален');
        await loadKpiData();
        closeModal();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить KPI');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

onMounted(async () => {
    await Promise.all([loadOptions(), loadKpiData()]);
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kpi-settings' as *;
</style>
