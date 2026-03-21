<template>
    <div class="kpi-page">
        <section class="kpi-panel">
            <div class="kpi-panel__header">
                <div>
                    <h2 class="kpi-panel__title">Правила KPI</h2>
                    <p class="kpi-panel__subtitle">Всего: {{ rules.length }}</p>
                </div>
                <div class="kpi-panel__header-actions">
                    <Button color="outline" size="sm" :loading="rulesLoading" @click="loadRules">
                        Обновить
                    </Button>
                    <Button color="primary" size="sm" @click="openCreateRuleModal">
                        Добавить правило
                    </Button>
                </div>
            </div>
            <div v-if="rules.length" class="kpi-list">
                <div v-for="rule in rules" :key="rule.id" class="kpi-card">
                    <div class="kpi-card__top">
                        <span class="kpi-card__id">№ {{ rule.id }}</span>
                        <span class="kpi-card__status" :class="{ 'is-muted': !rule.is_active }">
                            {{ rule.is_active ? 'Активно' : 'Отключено' }}
                        </span>
                    </div>
                    <div class="kpi-card__title">{{ metricName(rule.metric) }}</div>
                    <div class="kpi-card__meta">
                        <span>Тип условия: {{ comparisonBasisLabel(rule.comparison_basis) }}</span>
                        <span>{{ subdivisionLabel(rule.position_id) }}</span>
                        <span>{{ positionLabel(rule.position_id) }}</span>
                        <span v-if="rule.employee_id">Сотрудник ID: {{ rule.employee_id }}</span>
                        <span>
                            Премия: если факт {{ comparisonLabel(rule.bonus_condition) }}
                            {{ formatNumber(rule.target_value) }},
                            {{ effectLabel(rule.bonus_type, rule.bonus_value) }}
                        </span>
                        <span>
                            Штраф: если факт {{ comparisonLabel(rule.penalty_condition) }}
                            {{ formatNumber(rule.warning_value ?? rule.target_value) }},
                            {{ effectLabel(rule.penalty_type, rule.penalty_value) }}
                        </span>
                    </div>
                    <div class="kpi-card__footer">
                        <Button size="sm" @click="openEditRuleModal(rule)">Изменить</Button>
                        <Button
                            size="sm"
                            color="danger"
                            :loading="ruleDeletingId === rule.id"
                            @click="handleDeleteRule(rule)"
                        >
                            Удалить
                        </Button>
                    </div>
                </div>
            </div>
            <p v-else class="kpi-list__empty">Правила KPI пока не созданы.</p>
        </section>

        <Modal v-if="isRuleModalOpen" class="kpi-rules__modal" @close="closeRuleModal">
            <template #header>
                <div>
                    <h3 class="kpi-rules__modal-title">{{ ruleFormTitle }}</h3>
                    <p class="kpi-rules__modal-subtitle">Настройте условия начисления KPI.</p>
                </div>
            </template>

            <div class="kpi-section">
                <h4 class="kpi-section__title">Область действия</h4>
                <div class="kpi-panel__grid">
                    <Select
                        v-model="ruleForm.metricId"
                        label="Показатель KPI"
                        :options="metricOptions"
                        placeholder="Выберите показатель"
                    />
                    <Select
                        v-model="ruleForm.comparisonBasis"
                        label="Тип условия"
                        :options="comparisonBasisOptions"
                    />
                    <Select
                        v-model="ruleForm.subdivisionId"
                        label="Подразделение"
                        :options="subdivisionOptions"
                        placeholder="Все подразделения"
                    />
                    <Select
                        v-model="ruleForm.positionId"
                        label="Должность"
                        :options="positionOptions"
                        placeholder="Все должности"
                    />
                    <div class="kpi-panel__field">
                        <label class="kpi-panel__label">Индивидуальный KPI</label>
                        <input v-model="ruleForm.isIndividual" type="checkbox" class="kpi-panel__checkbox">
                    </div>
                    <Select
                        v-if="ruleForm.isIndividual"
                        v-model="ruleForm.employeeId"
                        label="Сотрудник"
                        :options="employeeOptions"
                        placeholder="Выберите сотрудника"
                        :disabled="employeeSearchLoading"
                        searchable
                        search-placeholder="Введите ФИО"
                        @search="handleEmployeeSearch"
                    />
                </div>
            </div>

            <div class="kpi-section">
                <h4 class="kpi-section__title">Условия премии</h4>
                <div class="kpi-panel__grid">
                    <Select
                        v-model="ruleForm.bonusCondition"
                        :label="conditionLabel"
                        :options="comparisonOptions"
                    />
                    <Input
                        v-model="ruleForm.targetValue"
                        :label="thresholdLabel"
                        type="number"
                        step="0.01"
                    />
                    <Select
                        v-model="ruleForm.bonusType"
                        label="То (премия)"
                        :options="effectTypeOptions"
                    />
                    <Input
                        v-model="ruleForm.bonusValue"
                        label="Значение"
                        type="number"
                        step="0.01"
                        :disabled="ruleForm.bonusType === 'none'"
                    />
                </div>
            </div>

            <div class="kpi-section">
                <h4 class="kpi-section__title">Условия штрафа</h4>
                <div class="kpi-panel__grid">
                    <Select
                        v-model="ruleForm.penaltyCondition"
                        :label="conditionLabel"
                        :options="comparisonOptions"
                    />
                    <Input
                        v-model="ruleForm.warningValue"
                        :label="thresholdLabel"
                        type="number"
                        step="0.01"
                    />
                    <Select
                        v-model="ruleForm.penaltyType"
                        label="То (штраф)"
                        :options="effectTypeOptions"
                    />
                    <Input
                        v-model="ruleForm.penaltyValue"
                        label="Значение"
                        type="number"
                        step="0.01"
                        :disabled="ruleForm.penaltyType === 'none'"
                    />
                </div>
            </div>

            <div class="kpi-section">
                <h4 class="kpi-section__title">Дополнительно</h4>
                <div class="kpi-panel__grid">
                    <div class="kpi-panel__field">
                        <label class="kpi-panel__label">Активно</label>
                        <input v-model="ruleForm.isActive" type="checkbox" class="kpi-panel__checkbox">
                    </div>
                    <div class="kpi-panel__field kpi-panel__field--full">
                        <label class="kpi-panel__label">Комментарий</label>
                        <textarea v-model="ruleForm.comment" class="kpi-panel__textarea" rows="2" />
                    </div>
                </div>
            </div>

            <template #footer>
                <div class="kpi-panel__actions">
                    <Button color="primary" :loading="ruleSaving" @click="handleSaveRule">
                        {{ ruleFormAction }}
                    </Button>
                    <Button color="ghost" :disabled="ruleSaving" @click="closeRuleModal">
                        Отмена
                    </Button>
                    <Button
                        v-if="ruleEditingId"
                        color="danger"
                        :disabled="ruleSaving"
                        :loading="ruleDeletingId === ruleEditingId"
                        @click="handleDeleteRule({ id: ruleEditingId })"
                    >
                        Удалить
                    </Button>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import {
    createKpiRule,
    deleteKpiRule,
    fetchAccessPositions,
    fetchEmployees,
    fetchKpiRules,
    fetchKpiMetrics,
    fetchRestaurantSubdivisions,
    updateKpiRule,
} from '@/api';
import { useDebounce } from '@/composables/useDebounce';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import Modal from '@/components/UI-components/Modal.vue';

const toast = useToast();

const rules = ref([]);
const rulesLoading = ref(false);
const ruleSaving = ref(false);
const ruleDeletingId = ref(null);
const ruleEditingId = ref(null);
const isRuleModalOpen = ref(false);

const metrics = ref([]);
const positions = ref([]);
const subdivisions = ref([]);

const employeeSearch = ref('');
const employeeSearchResults = ref([]);
const employeeSearchLoading = ref(false);

const comparisonOptions = [
    { value: 'gte', label: 'больше или равно' },
    { value: 'gt', label: 'больше' },
    { value: 'lte', label: 'меньше или равно' },
    { value: 'lt', label: 'меньше' },
    { value: 'eq', label: 'равно' },
];
const comparisonBasisOptions = [
    { value: 'plan_percent', label: 'Выполнение плана, %' },
    { value: 'plan_delta_percent', label: 'Отклонение от плана, %' },
    { value: 'absolute', label: 'Абсолютное значение' },
];
const effectTypeOptions = [
    { value: 'none', label: 'Нет' },
    { value: 'fixed', label: 'Фиксированная сумма' },
    { value: 'percent', label: 'Процент' },
];

const ruleForm = ref(defaultRuleForm());

function defaultRuleForm() {
    return {
        metricId: null,
        comparisonBasis: 'plan_percent',
        subdivisionId: null,
        positionId: null,
        isIndividual: false,
        employeeId: null,
        targetValue: '',
        warningValue: '',
        bonusCondition: 'gte',
        bonusType: 'none',
        bonusValue: '',
        penaltyCondition: 'lte',
        penaltyType: 'none',
        penaltyValue: '',
        isActive: true,
        comment: '',
    };
}

const ruleFormTitle = computed(() =>
    ruleEditingId.value ? 'Редактировать правило' : 'Новое правило',
);
const ruleFormAction = computed(() => (ruleEditingId.value ? 'Сохранить' : 'Создать'));
const thresholdLabel = computed(() =>
    ['plan_percent', 'plan_delta_percent'].includes(ruleForm.value.comparisonBasis)
        ? 'Порог (%)'
        : 'Порог',
);
const conditionLabel = computed(() => {
    if (ruleForm.value.comparisonBasis === 'plan_percent') {
        return 'Если выполнение плана';
    }
    if (ruleForm.value.comparisonBasis === 'plan_delta_percent') {
        return 'Если отклонение от плана';
    }
    return 'Если факт';
});

const metricOptions = computed(() =>
    metrics.value.map((metric) => ({
        value: metric.id,
        label: metric.name,
    })),
);
const subdivisionOptions = computed(() => [
    { value: null, label: 'Все подразделения' },
    ...subdivisions.value.map((sub) => ({ value: sub.id, label: sub.name })),
]);

const positionOptions = computed(() => {
    if (!ruleForm.value.subdivisionId) {
        return [
            { value: null, label: 'Все должности' },
            ...positions.value.map((pos) => ({ value: pos.id, label: pos.name })),
        ];
    }
    const filtered = positions.value.filter(
        (pos) => Number(pos.restaurant_subdivision_id) === Number(ruleForm.value.subdivisionId),
    );
    return [
        { value: null, label: 'Все должности' },
        ...filtered.map((pos) => ({ value: pos.id, label: pos.name })),
    ];
});

const employeeOptions = computed(() => {
    const options = employeeSearchResults.value.map((employee) => ({
        value: employee.id,
        label: formatFullName(employee),
    }));
    if (ruleForm.value.employeeId && !options.find((item) => Number(item.value) === Number(ruleForm.value.employeeId))) {
        options.unshift({ value: ruleForm.value.employeeId, label: `ID ${ruleForm.value.employeeId}` });
    }
    return options;
});

function metricName(metric) {
    return metric?.name || `Показатель ${metric?.id || ''}`.trim();
}

function subdivisionLabel(positionId) {
    if (!positionId) {
        return 'Все подразделения';
    }
    const position = positions.value.find((item) => Number(item.id) === Number(positionId));
    const subdivisionId = position?.restaurant_subdivision_id;
    if (!subdivisionId) {
        return 'Без подразделения';
    }
    const subdivision = subdivisions.value.find((item) => Number(item.id) === Number(subdivisionId));
    return subdivision?.name || `Подразделение ${subdivisionId}`;
}

function positionLabel(id) {
    const pos = positions.value.find((item) => Number(item.id) === Number(id));
    return pos?.name || (id ? `Должность ${id}` : 'Все должности');
}

function comparisonLabel(value) {
    const option = comparisonOptions.find((item) => item.value === value);
    return option ? option.label : value;
}

function comparisonBasisLabel(value) {
    if (!value) {
        return '—';
    }
    const option = comparisonBasisOptions.find((item) => item.value === value);
    return option ? option.label : value;
}

function effectLabel(type, value) {
    const typeLabel = effectTypeOptions.find((item) => item.value === type)?.label || type;
    if (type === 'none') {
        return 'нет';
    }
    if (type === 'fixed') {
        return `${typeLabel}: ${formatNumber(value)}`;
    }
    return `${typeLabel}: ${formatNumber(value)} от итоговых часов`;
}

function formatNumber(value) {
    const num = Number(value || 0);
    return new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(num);
}

function formatFullName(employee) {
    if (!employee) return '—';
    const parts = [employee.last_name, employee.first_name, employee.middle_name].filter(Boolean);
    return parts.length ? parts.join(' ') : employee.username || `ID ${employee.id}`;
}

async function loadOptions() {
    try {
        const [metricsData, positionsData, subdivisionsData] = await Promise.all([
            fetchKpiMetrics(),
            fetchAccessPositions(),
            fetchRestaurantSubdivisions(),
        ]);
        metrics.value = Array.isArray(metricsData?.items) ? metricsData.items : metricsData || [];
        positions.value = Array.isArray(positionsData) ? positionsData : positionsData?.items || [];
        subdivisions.value = Array.isArray(subdivisionsData) ? subdivisionsData : [];
    } catch (error) {
        toast.error('Не удалось загрузить справочники');
        console.error(error);
    }
}

async function loadRules() {
    rulesLoading.value = true;
    try {
        const data = await fetchKpiRules();
        rules.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить правила KPI');
        console.error(error);
    } finally {
        rulesLoading.value = false;
    }
}

function resetRuleForm() {
    ruleEditingId.value = null;
    ruleForm.value = defaultRuleForm();
    employeeSearch.value = '';
    employeeSearchResults.value = [];
}

function openCreateRuleModal() {
    resetRuleForm();
    isRuleModalOpen.value = true;
}

function openEditRuleModal(rule) {
    if (!rule) return;
    startEditRule(rule);
    isRuleModalOpen.value = true;
}

function closeRuleModal() {
    isRuleModalOpen.value = false;
    ruleSaving.value = false;
    resetRuleForm();
}

function startEditRule(rule) {
    ruleEditingId.value = rule.id;
    const position = positions.value.find((item) => Number(item.id) === Number(rule.position_id));
    ruleForm.value = {
        metricId: rule.metric_id || null,
        comparisonBasis: rule.comparison_basis || 'plan_percent',
        subdivisionId: position?.restaurant_subdivision_id ?? null,
        positionId: rule.position_id ?? null,
        isIndividual: Boolean(rule.employee_id),
        employeeId: rule.employee_id ?? null,
        targetValue: rule.target_value ?? '',
        warningValue: rule.warning_value ?? '',
        bonusCondition: rule.bonus_condition || 'gte',
        bonusType: rule.bonus_type || 'none',
        bonusValue: rule.bonus_value ?? '',
        penaltyCondition: rule.penalty_condition || 'lte',
        penaltyType: rule.penalty_type || 'none',
        penaltyValue: rule.penalty_value ?? '',
        isActive: Boolean(rule.is_active),
        comment: rule.comment || '',
    };
    employeeSearch.value = '';
    employeeSearchResults.value = [];
}

function parseNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(String(value).replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
}

async function handleSaveRule() {
    if (!ruleForm.value.metricId) {
        toast.error('Выберите показатель KPI');
        return;
    }
    if (ruleForm.value.isIndividual && !ruleForm.value.employeeId) {
        toast.error('Выберите сотрудника для индивидуального KPI');
        return;
    }

    const targetValue = parseNumber(ruleForm.value.targetValue) ?? 0;
    const warningValue = parseNumber(ruleForm.value.warningValue);
    const normalizedWarning = warningValue === null ? targetValue : warningValue;

    const bonusType = ruleForm.value.bonusType;
    const bonusValue = bonusType === 'none' ? 0 : parseNumber(ruleForm.value.bonusValue) ?? 0;

    const penaltyType = ruleForm.value.penaltyType;
    const penaltyValue = penaltyType === 'none' ? 0 : parseNumber(ruleForm.value.penaltyValue) ?? 0;

    const payload = {
        metric_id: Number(ruleForm.value.metricId),
        restaurant_id: null,
        position_id: ruleForm.value.positionId ? Number(ruleForm.value.positionId) : null,
        department_code: null,
        employee_id: ruleForm.value.isIndividual ? Number(ruleForm.value.employeeId) : null,
        comparison_basis: ruleForm.value.comparisonBasis,
        threshold_type: 'dual',
        target_value: targetValue,
        warning_value: normalizedWarning,
        bonus_condition: ruleForm.value.bonusCondition,
        bonus_type: bonusType,
        bonus_value: bonusValue,
        penalty_condition: ruleForm.value.penaltyCondition,
        penalty_type: penaltyType,
        penalty_value: penaltyValue,
        is_active: Boolean(ruleForm.value.isActive),
        comment: ruleForm.value.comment || null,
    };

    ruleSaving.value = true;
    try {
        if (ruleEditingId.value) {
            await updateKpiRule(ruleEditingId.value, payload);
            toast.success('Правило обновлено');
        } else {
            await createKpiRule(payload);
            toast.success('Правило создано');
        }
        await loadRules();
        closeRuleModal();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить правило');
        console.error(error);
    } finally {
        ruleSaving.value = false;
    }
}

async function handleDeleteRule(rule) {
    const ruleId = rule?.id || null;
    if (!ruleId) return;
    if (!window.confirm('Удалить правило?')) return;
    ruleDeletingId.value = ruleId;
    try {
        await deleteKpiRule(ruleId);
        toast.success('Правило удалено');
        await loadRules();
        if (ruleEditingId.value === ruleId) {
            closeRuleModal();
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить правило');
        console.error(error);
    } finally {
        ruleDeletingId.value = null;
    }
}

const searchEmployees = useDebounce(async (query) => {
    if (!ruleForm.value.isIndividual || !query || query.trim().length < 2) {
        employeeSearchResults.value = [];
        return;
    }
    employeeSearchLoading.value = true;
    try {
        const data = await fetchEmployees({ q: query.trim(), include_fired: true, limit: 50 });
        employeeSearchResults.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        console.error(error);
        employeeSearchResults.value = [];
    } finally {
        employeeSearchLoading.value = false;
    }
}, 350);

function handleEmployeeSearch(query) {
    employeeSearch.value = query;
    searchEmployees(query);
}

watch(
    () => ruleForm.value.subdivisionId,
    () => {
        if (!ruleForm.value.positionId) return;
        const selected = positions.value.find((pos) => Number(pos.id) === Number(ruleForm.value.positionId));
        if (!selected) return;
        if (
            ruleForm.value.subdivisionId &&
            Number(selected.restaurant_subdivision_id) !== Number(ruleForm.value.subdivisionId)
        ) {
            ruleForm.value.positionId = null;
        }
    },
);

watch(
    () => ruleForm.value.isIndividual,
    (value) => {
        if (!value) {
            ruleForm.value.employeeId = null;
            employeeSearch.value = '';
            employeeSearchResults.value = [];
        }
    },
);

onMounted(async () => {
    await loadOptions();
    await loadRules();
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kpi-rules' as *;
</style>
