<template>
    <div class="employees-page__finance">
        <div class="employees-page__finance-actions">
            <div
                ref="payrollFilterTabsRef"
                class="employees-page__finance-filters"
                role="group"
                aria-label="Фильтр начислений"
            >
                <span
                    class="employees-page__finance-filter-indicator"
                    :style="payrollFilterIndicatorStyle"
                    aria-hidden="true"
                ></span>
                <button
                    v-for="option in payrollFilterOptions"
                    :key="option.value"
                    :ref="setPayrollFilterTabRef(option.value)"
                    type="button"
                    class="employees-page__finance-filter"
                    :class="{ 'is-active': selectedPayrollFilter === option.value }"
                    :aria-pressed="selectedPayrollFilter === option.value"
                    @click="selectedPayrollFilter = option.value"
                >
                    {{ option.label }}
                </button>
            </div>
            <Button
                color="primary"
                size="sm"
                :disabled="rateHidden"
                @click="emit('open-payroll-adjustment-form')"
            >
                Добавить начисление
            </Button>
        </div>
        <p
            v-if="!payrollAdjustmentTypes.length && !payrollAdjustmentTypesLoading"
            class="employees-page__finance-hint"
        >
            Нет доступных типов начислений. Создайте тип в разделе «Пользователи».
        </p>
        <div v-if="payrollAdjustmentsLoading" class="employees-page__modal-loading">
            Загрузка начислений...
        </div>
        <div v-else>
            <Table v-if="filteredPayrollAdjustments.length">
                <thead>
                    <tr>
                        <th>Дата</th>
                        <th>Тип</th>
                        <th>Ресторан</th>
                        <th>Сумма</th>
                        <th>Ответственный</th>
                        <th>Комментарий</th>
                        <th class="employees-page__trainings-actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="adjustment in filteredPayrollAdjustments"
                        :key="adjustment.id"
                        :class="[
                            'employees-page__finance-row',
                            {
                                'employees-page__finance-row--editing':
                                    editingPayrollAdjustment.id === adjustment.id,
                            },
                        ]"
                        @click="emit('start-edit-payroll-adjustment', adjustment)"
                    >
                        <td>
                            <template v-if="editingPayrollAdjustment.id === adjustment.id">
                                <div @click.stop>
                                    <DateInput
                                        v-model="editingPayrollAdjustment.date"
                                        label=""
                                    />
                                </div>
                            </template>
                            <template v-else>
                                {{ formatDate(adjustment.date) }}
                            </template>
                        </td>
                        <td>
                            <template v-if="editingPayrollAdjustment.id === adjustment.id">
                                <div @click.stop>
                                    <Select
                                        v-model="editingPayrollAdjustment.adjustmentTypeId"
                                        label=""
                                        :options="payrollAdjustmentTypeOptions"
                                        placeholder="Выберите тип"
                                    />
                                </div>
                            </template>
                            <template v-else>
                                {{ adjustment.adjustment_type?.name || '—' }}
                            </template>
                        </td>
                        <td>
                            <template v-if="editingPayrollAdjustment.id === adjustment.id">
                                <div @click.stop>
                                    <Select
                                        v-model="editingPayrollAdjustment.restaurantId"
                                        label=""
                                        :options="payrollRestaurantOptions"
                                        placeholder="Выберите ресторан"
                                    />
                                </div>
                            </template>
                            <template v-else>
                                {{
                                    adjustment.restaurant_name ||
                                    formatRestaurant(adjustment.restaurant_id ?? adjustment.restaurant?.id)
                                }}
                            </template>
                        </td>
                        <td>
                            <template v-if="editingPayrollAdjustment.id === adjustment.id">
                                <div @click.stop>
                                    <Input
                                        v-model="editingPayrollAdjustment.amount"
                                        label=""
                                        type="number"
                                        step="0.01"
                                    />
                                </div>
                            </template>
                            <template v-else>
                                {{
                                    adjustment.amount === null || adjustment.amount === undefined
                                        ? '$$$'
                                        : formatAmount(adjustment.amount)
                                }}
                            </template>
                        </td>
                        <td>
                            <template v-if="editingPayrollAdjustment.id === adjustment.id">
                                <div @click.stop>
                                    <Select
                                        v-model="editingPayrollAdjustment.responsibleId"
                                        label=""
                                        :options="responsibleOptions"
                                        placeholder="Выберите ответственного"
                                    />
                                </div>
                            </template>
                            <template v-else>
                                {{
                                    formatResponsible(
                                        adjustment.responsible_id,
                                        adjustment.responsible_name,
                                    )
                                }}
                            </template>
                        </td>
                        <td class="employees-page__trainings-comment">
                            <template v-if="editingPayrollAdjustment.id === adjustment.id">
                                <div @click.stop>
                                    <Input
                                        v-model="editingPayrollAdjustment.comment"
                                        label=""
                                    />
                                </div>
                            </template>
                            <template v-else>
                                {{ adjustment.comment || '—' }}
                            </template>
                        </td>
                        <td class="employees-page__trainings-actions">
                            <template v-if="editingPayrollAdjustment.id === adjustment.id">
                                <Button
                                    color="primary"
                                    size="sm"
                                    :loading="updatingPayrollAdjustment"
                                    @click.stop="emit('update-payroll-adjustment')"
                                >
                                    Сохранить
                                </Button>
                                <Button
                                    color="ghost"
                                    size="sm"
                                    :disabled="updatingPayrollAdjustment"
                                    @click.stop="emit('cancel-edit-payroll-adjustment')"
                                >
                                    Отмена
                                </Button>
                            </template>
                            <template v-else>
                                <button
                                    type="button"
                                    class="employees-page__icon-button employees-page__icon-button--edit"
                                    :disabled="adjustment.amount === null || adjustment.amount === undefined"
                                    title="Редактировать"
                                    @click.stop="emit('start-edit-payroll-adjustment', adjustment)"
                                >
                                    <BaseIcon name="Edit" />
                                </button>
                                <button
                                    type="button"
                                    class="employees-page__icon-button"
                                    :disabled="
                                        deletingPayrollAdjustmentId === adjustment.id ||
                                        adjustment.amount === null ||
                                        adjustment.amount === undefined
                                    "
                                    title="Удалить начисление"
                                    @click.stop="emit('delete-payroll-adjustment', adjustment.id)"
                                >
                                    <BaseIcon name="Trash" />
                                </button>
                            </template>
                        </td>
                    </tr>
                </tbody>
            </Table>
            <p v-else class="employees-page__empty">
                {{ payrollEmptyLabel }}
            </p>
        </div>
    </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, toRefs, watch } from 'vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';

const props = defineProps({
    payrollAdjustmentTypeOptions: { type: Array, default: () => [] },
    payrollRestaurantOptions: { type: Array, default: () => [] },
    payrollAdjustments: { type: Array, default: () => [] },
    payrollAdjustmentsLoading: { type: Boolean, default: false },
    editingPayrollAdjustment: { type: Object, default: () => ({}) },
    updatingPayrollAdjustment: { type: Boolean, default: false },
    deletingPayrollAdjustmentId: { type: [Number, String], default: null },
    payrollAdjustmentTypes: { type: Array, default: () => [] },
    payrollAdjustmentTypesLoading: { type: Boolean, default: false },
    responsibleOptions: { type: Array, default: () => [] },
    formatDate: { type: Function, required: true },
    formatAmount: { type: Function, required: true },
    formatResponsible: { type: Function, required: true },
    formatRestaurant: { type: Function, required: true },
    rateHidden: { type: Boolean, default: false },
    payrollFilter: { type: String, default: 'all' },
});

const emit = defineEmits([
    'open-payroll-adjustment-form',
    'start-edit-payroll-adjustment',
    'cancel-edit-payroll-adjustment',
    'update-payroll-adjustment',
    'delete-payroll-adjustment',
    'update:payroll-filter',
]);

const {
    payrollAdjustmentTypeOptions,
    payrollRestaurantOptions,
    payrollAdjustments,
    payrollAdjustmentsLoading,
    editingPayrollAdjustment,
    updatingPayrollAdjustment,
    deletingPayrollAdjustmentId,
    payrollAdjustmentTypes,
    payrollAdjustmentTypesLoading,
    responsibleOptions,
    formatDate,
    formatAmount,
    formatResponsible,
    formatRestaurant,
    rateHidden,
    payrollFilter: payrollFilterProp,
} = toRefs(props);

const payrollFilterTabsRef = ref(null);
const payrollFilterTabRefs = ref({});
const payrollFilterIndicatorState = ref({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
    visible: false,
});
let payrollFilterResizeObserver = null;

const payrollFilterIndicatorStyle = computed(() => ({
    '--finance-indicator-x': `${payrollFilterIndicatorState.value.x}px`,
    '--finance-indicator-y': `${payrollFilterIndicatorState.value.y}px`,
    '--finance-indicator-width': `${payrollFilterIndicatorState.value.width}px`,
    '--finance-indicator-height': `${payrollFilterIndicatorState.value.height}px`,
    opacity: payrollFilterIndicatorState.value.visible ? '1' : '0',
}));

const payrollFilterOptions = [
    { value: 'all', label: 'Все' },
    { value: 'accrual', label: 'Начисления' },
    { value: 'deduction', label: 'Удержания' },
];

const selectedPayrollFilter = computed({
    get() {
        const fallback = payrollFilterOptions[0].value;
        const value = payrollFilterProp.value || fallback;
        return payrollFilterOptions.some((option) => option.value === value) ? value : fallback;
    },
    set(value) {
        emit('update:payroll-filter', value);
    },
});

const payrollAdjustmentKindMap = computed(() => {
    const map = new Map();
    const list = Array.isArray(payrollAdjustmentTypes.value) ? payrollAdjustmentTypes.value : [];
    list.forEach((type) => {
        const id = Number(type?.id);
        if (Number.isFinite(id) && type?.kind) {
            map.set(id, String(type.kind).toLowerCase());
        }
    });
    return map;
});

function resolvePayrollAdjustmentKind(adjustment) {
    if (!adjustment) {
        return null;
    }
    const directKind = adjustment.adjustment_type?.kind;
    if (directKind) {
        return String(directKind).toLowerCase();
    }
    const rawTypeId = adjustment.adjustment_type_id ?? adjustment.adjustment_type?.id;
    const typeId = Number(rawTypeId);
    if (!Number.isFinite(typeId)) {
        return null;
    }
    return payrollAdjustmentKindMap.value.get(typeId) ?? null;
}

const filteredPayrollAdjustments = computed(() => {
    const list = Array.isArray(payrollAdjustments.value) ? payrollAdjustments.value : [];
    if (selectedPayrollFilter.value === 'all') {
        return list;
    }
    return list.filter((item) => resolvePayrollAdjustmentKind(item) === selectedPayrollFilter.value);
});

const payrollEmptyLabel = computed(() => {
    switch (selectedPayrollFilter.value) {
        case 'accrual':
            return 'Начисления ещё не добавлены.';
        case 'deduction':
            return 'Удержания ещё не добавлены.';
        default:
            return 'Начисления и удержания ещё не добавлены.';
    }
});

function setPayrollFilterTabRef(tabKey) {
    return (element) => {
        if (element) {
            payrollFilterTabRefs.value[tabKey] = element;
            return;
        }
        delete payrollFilterTabRefs.value[tabKey];
    };
}

function updatePayrollFilterIndicator() {
    const tabsRoot = payrollFilterTabsRef.value;
    const activeTabButton = payrollFilterTabRefs.value[selectedPayrollFilter.value];
    if (!tabsRoot || !activeTabButton) {
        payrollFilterIndicatorState.value.visible = false;
        return;
    }

    const tabsRect = tabsRoot.getBoundingClientRect();
    const tabRect = activeTabButton.getBoundingClientRect();
    payrollFilterIndicatorState.value = {
        x: tabRect.left - tabsRect.left,
        y: tabRect.top - tabsRect.top,
        width: tabRect.width,
        height: tabRect.height,
        visible: true,
    };
}

function schedulePayrollFilterIndicatorUpdate() {
    nextTick(() => {
        updatePayrollFilterIndicator();
    });
}

watch(
    () => payrollFilterTabsRef.value,
    (node, prevNode) => {
        if (payrollFilterResizeObserver && prevNode) {
            payrollFilterResizeObserver.unobserve(prevNode);
        }
        if (payrollFilterResizeObserver && node) {
            payrollFilterResizeObserver.observe(node);
        }
        schedulePayrollFilterIndicatorUpdate();
    },
);

watch(
    () => selectedPayrollFilter.value,
    () => {
        schedulePayrollFilterIndicatorUpdate();
    },
    { immediate: true },
);

onMounted(() => {
    if (typeof ResizeObserver !== 'undefined') {
        payrollFilterResizeObserver = new ResizeObserver(() => {
            updatePayrollFilterIndicator();
        });
        if (payrollFilterTabsRef.value) {
            payrollFilterResizeObserver.observe(payrollFilterTabsRef.value);
        }
    }
    window.addEventListener('resize', schedulePayrollFilterIndicatorUpdate);
    schedulePayrollFilterIndicatorUpdate();
});

onBeforeUnmount(() => {
    if (payrollFilterResizeObserver) {
        payrollFilterResizeObserver.disconnect();
        payrollFilterResizeObserver = null;
    }
    window.removeEventListener('resize', schedulePayrollFilterIndicatorUpdate);
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-finance-tab' as *;
</style>
