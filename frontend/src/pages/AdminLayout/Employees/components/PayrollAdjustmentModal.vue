<template>
    <Modal v-if="isOpen" @close="emit('close')">
        <template #header>
            <div class="payroll-adjustment-modal__header">
                <h3 class="payroll-adjustment-modal__title">Добавить начисление/удержание</h3>
            </div>
        </template>
        <template #default>
            <div v-if="payrollAdjustmentTypesLoading" class="payroll-adjustment-modal__loading">
                Загрузка доступных типов...
            </div>
            <form
                v-else
                class="payroll-adjustment-modal__form"
                @submit.prevent="handleValidatedSubmit"
            >
                <div class="payroll-adjustment-modal__type-toggle" role="group" aria-label="Тип операции">
                    <button
                        v-for="option in payrollTypeFilterOptions"
                        :key="option.value"
                        type="button"
                        class="payroll-adjustment-modal__type-toggle-button"
                        :class="{ 'is-active': payrollTypeFilter === option.value }"
                        :aria-pressed="payrollTypeFilter === option.value"
                        @click="payrollTypeFilter = option.value"
                    >
                        {{ option.label }}
                    </button>
                </div>
                <div class="payroll-adjustment-modal__field">
                    <Select
                        v-model="adjustmentTypeIdModel"
                        :label="payrollTypeLabel"
                        :options="filteredPayrollAdjustmentTypeOptions"
                        placeholder="Выберите тип"
                    />
                    <p v-if="getFieldError('adjustmentTypeId')" class="payroll-adjustment-modal__error">
                        {{ getFieldError('adjustmentTypeId') }}
                    </p>
                </div>
                <div class="payroll-adjustment-modal__field">
                    <Select
                        v-model="restaurantIdModel"
                        label="Ресторан"
                        :options="payrollRestaurantOptions"
                        placeholder="Выберите ресторан"
                    />
                    <p v-if="getFieldError('restaurantId')" class="payroll-adjustment-modal__error">
                        {{ getFieldError('restaurantId') }}
                    </p>
                </div>
                <div class="payroll-adjustment-modal__field">
                    <Input
                        v-model="amountModel"
                        label="Сумма"
                        type="number"
                        step="0.01"
                    />
                    <p v-if="getFieldError('amount')" class="payroll-adjustment-modal__error">
                        {{ getFieldError('amount') }}
                    </p>
                </div>
                <div class="payroll-adjustment-modal__field">
                    <DateInput v-model="dateModel" label="Дата" />
                    <p v-if="getFieldError('date')" class="payroll-adjustment-modal__error">
                        {{ getFieldError('date') }}
                    </p>
                </div>
                <div class="payroll-adjustment-modal__field">
                    <Select
                        v-model="responsibleIdModel"
                        label="Ответственный"
                        :options="responsibleOptions"
                        placeholder="Выберите ответственного"
                    />
                </div>
                <div class="payroll-adjustment-modal__field">
                    <Input v-model="commentModel" label="Комментарий" />
                    <p v-if="getFieldError('comment')" class="payroll-adjustment-modal__error">
                        {{ getFieldError('comment') }}
                    </p>
                </div>
                <p
                    v-if="payrollAdjustmentTypes.length && !filteredPayrollAdjustmentTypeOptions.length"
                    class="payroll-adjustment-modal__hint"
                >
                    Нет доступных типов для выбранного фильтра.
                </p>
                <p
                    v-if="!payrollAdjustmentTypes.length && !payrollAdjustmentTypesLoading"
                    class="payroll-adjustment-modal__hint"
                >
                    Нет доступных типов начислений/удержаний. Добавьте типы, чтобы создать запись.
                </p>
            </form>
        </template>
        <template #footer>
            <Button color="ghost" :disabled="creatingPayrollAdjustment" @click="emit('close')">
                Отмена
            </Button>
            <Button
                color="primary"
                :loading="creatingPayrollAdjustment"
                :disabled="!filteredPayrollAdjustmentTypeOptions.length"
                @click="handleValidatedSubmit"
            >
                Сохранить
            </Button>
        </template>
    </Modal>
</template>

<script setup>
import { computed, ref, toRefs, watch } from 'vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import { useEmployeeModalValidation } from './useEmployeeModalValidation';

const props = defineProps({
    isOpen: { type: Boolean, default: false },
    newPayrollAdjustment: { type: Object, required: true },
    payrollAdjustmentTypeOptions: { type: Array, default: () => [] },
    payrollRestaurantOptions: { type: Array, default: () => [] },
    payrollAdjustmentTypes: { type: Array, default: () => [] },
    payrollAdjustmentTypesLoading: { type: Boolean, default: false },
    creatingPayrollAdjustment: { type: Boolean, default: false },
    responsibleOptions: { type: Array, default: () => [] },
});

const emit = defineEmits(['close', 'create-payroll-adjustment']);

const {
    isOpen,
    newPayrollAdjustment,
    payrollRestaurantOptions,
    payrollAdjustmentTypes,
    payrollAdjustmentTypesLoading,
    creatingPayrollAdjustment,
    responsibleOptions,
} = toRefs(props);

const payrollValidationSchema = {
    adjustmentTypeId: 'required',
    restaurantId: 'required',
    amount: 'required|min_value:0.01',
    date: 'required',
    comment: 'max:500',
};

const { bindField, getFieldError, handleValidatedSubmit } = useEmployeeModalValidation({
    isOpen,
    sourceModel: newPayrollAdjustment,
    validationSchema: payrollValidationSchema,
    onSubmit: (values) => emit('create-payroll-adjustment', values),
});

const adjustmentTypeIdModel = bindField('adjustmentTypeId');
const restaurantIdModel = bindField('restaurantId');
const amountModel = bindField('amount');
const dateModel = bindField('date');
const responsibleIdModel = bindField('responsibleId');
const commentModel = bindField('comment');

const payrollTypeFilterOptions = [
    { value: 'accrual', label: 'Начисления' },
    { value: 'deduction', label: 'Удержания' },
];

const payrollTypeFilter = ref(payrollTypeFilterOptions[0].value);

const payrollTypeLabel = computed(() =>
    payrollTypeFilter.value === 'deduction' ? 'Тип удержания' : 'Тип начисления',
);

const availablePayrollKinds = computed(() => {
    const kinds = new Set();
    const list = Array.isArray(payrollAdjustmentTypes.value) ? payrollAdjustmentTypes.value : [];
    list.forEach((type) => {
        const kind = String(type?.kind || '').toLowerCase();
        if (kind === 'accrual' || kind === 'deduction') {
            kinds.add(kind);
        }
    });
    return kinds;
});

const filteredPayrollAdjustmentTypeOptions = computed(() => {
    const list = Array.isArray(payrollAdjustmentTypes.value) ? payrollAdjustmentTypes.value : [];
    return list
        .filter((type) => String(type?.kind || '').toLowerCase() === payrollTypeFilter.value)
        .map((type) => ({
            value: String(type.id),
            label: type.name,
        }));
});

function syncPayrollAdjustmentTypeSelection() {
    const options = filteredPayrollAdjustmentTypeOptions.value;
    if (!options.length) {
        newPayrollAdjustment.value.adjustmentTypeId = null;
        return;
    }
    const current = String(newPayrollAdjustment.value.adjustmentTypeId || '');
    if (!options.some((option) => option.value === current)) {
        newPayrollAdjustment.value.adjustmentTypeId = options[0].value;
    }
}

watch(
    () => availablePayrollKinds.value,
    (kinds) => {
        if (!kinds.size) {
            return;
        }
        if (!kinds.has(payrollTypeFilter.value)) {
            payrollTypeFilter.value = kinds.has('accrual') ? 'accrual' : 'deduction';
        }
    },
    { immediate: true },
);

watch(
    () => filteredPayrollAdjustmentTypeOptions.value,
    () => {
        syncPayrollAdjustmentTypeSelection();
    },
    { immediate: true },
);
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-payroll-adjustment-modal' as *;
</style>
