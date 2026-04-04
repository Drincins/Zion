<template>
    <Modal
        v-if="isOpen"
        class="employees-page__change-order-modal-window"
        :z-index="zIndex"
        @close="emit('close')"
    >
        <template #header>
            <div class="employees-page__modal-header">
                <h3 class="employees-page__modal-title">Создать кадровое изменение</h3>
                <p class="employees-page__modal-subtitle">
                    Выбери дату вступления в силу и параметры, которые должны измениться.
                </p>
            </div>
        </template>

        <template #default>
            <div class="employees-page__change-order-modal">
                <div class="employees-page__change-order-form">
                    <div class="employees-page__change-order-form-grid">
                        <DateInput
                            :model-value="employeeChangeOrderForm.effectiveDate"
                            label="Дата вступления в силу"
                            @update:model-value="updateField('effectiveDate', $event)"
                        />
                        <Input
                            :model-value="employeeChangeOrderForm.comment"
                            label="Комментарий"
                            placeholder="Необязательно"
                            @update:model-value="updateField('comment', $event)"
                        />
                    </div>

                    <section
                        v-if="isBackdatedEffectiveDate"
                        class="employees-page__change-order-option employees-page__change-order-option--full"
                    >
                        <div class="employees-page__change-order-option-head">
                            <div>
                                <h4 class="employees-page__change-order-option-title">Смены за прошедший период</h4>
                                <p class="employees-page__change-order-option-hint">
                                    Если включить этот пункт, новые данные применятся к уже существующим сменам начиная с выбранной даты.
                                </p>
                            </div>
                            <label class="employees-page__change-order-toggle">
                                <input
                                    :checked="employeeChangeOrderForm.applyToAttendances"
                                    type="checkbox"
                                    @change="updateField('applyToAttendances', $event.target.checked)"
                                >
                                <span class="employees-page__change-order-toggle-slider"></span>
                                <span class="employees-page__change-order-toggle-label">Вкл</span>
                            </label>
                        </div>
                    </section>

                    <div class="employees-page__change-order-options">
                        <section class="employees-page__change-order-option">
                            <div class="employees-page__change-order-option-head">
                                <div>
                                    <h4 class="employees-page__change-order-option-title">Должность</h4>
                                    <p class="employees-page__change-order-option-hint">
                                        Если сотрудник без индивидуальной ставки, новая ставка подтянется от должности.
                                    </p>
                                </div>
                                <label class="employees-page__change-order-toggle">
                                    <input
                                        :checked="employeeChangeOrderForm.changePosition"
                                        type="checkbox"
                                        @change="updateField('changePosition', $event.target.checked)"
                                    >
                                    <span class="employees-page__change-order-toggle-slider"></span>
                                    <span class="employees-page__change-order-toggle-label">Вкл</span>
                                </label>
                            </div>
                            <div
                                v-if="employeeChangeOrderForm.changePosition"
                                class="employees-page__change-order-option-body"
                            >
                                <Select
                                    :model-value="employeeChangeOrderForm.positionIdNew"
                                    :options="positionOptions"
                                    placeholder="Выберите должность"
                                    @update:model-value="updateField('positionIdNew', $event)"
                                />
                            </div>
                        </section>

                        <section class="employees-page__change-order-option">
                            <div class="employees-page__change-order-option-head">
                                <div>
                                    <h4 class="employees-page__change-order-option-title">Место работы</h4>
                                    <p class="employees-page__change-order-option-hint">
                                        Можно заранее перевести сотрудника в другой ресторан.
                                    </p>
                                </div>
                                <label class="employees-page__change-order-toggle">
                                    <input
                                        :checked="employeeChangeOrderForm.changeWorkplaceRestaurant"
                                        type="checkbox"
                                        @change="updateField('changeWorkplaceRestaurant', $event.target.checked)"
                                    >
                                    <span class="employees-page__change-order-toggle-slider"></span>
                                    <span class="employees-page__change-order-toggle-label">Вкл</span>
                                </label>
                            </div>
                            <div
                                v-if="employeeChangeOrderForm.changeWorkplaceRestaurant"
                                class="employees-page__change-order-option-body"
                            >
                                <Select
                                    :model-value="employeeChangeOrderForm.workplaceRestaurantIdNew"
                                    :options="workplaceRestaurantOptions"
                                    placeholder="Выберите ресторан"
                                    @update:model-value="updateField('workplaceRestaurantIdNew', $event)"
                                />
                            </div>
                        </section>

                        <section class="employees-page__change-order-option">
                            <div class="employees-page__change-order-option-head">
                                <div>
                                    <h4 class="employees-page__change-order-option-title">Индивидуальная ставка</h4>
                                    <p class="employees-page__change-order-option-hint">
                                        Через приказ сотрудника меняем только индивидуальную ставку.
                                    </p>
                                </div>
                                <label class="employees-page__change-order-toggle">
                                    <input
                                        :checked="employeeChangeOrderForm.changeIndividualRate"
                                        :disabled="!canManageRateChanges"
                                        type="checkbox"
                                        @change="updateField('changeIndividualRate', $event.target.checked)"
                                    >
                                    <span class="employees-page__change-order-toggle-slider"></span>
                                    <span class="employees-page__change-order-toggle-label">Вкл</span>
                                </label>
                            </div>

                            <div
                                v-if="!canManageRateChanges || employeeChangeOrderForm.changeIndividualRate"
                                class="employees-page__change-order-option-body"
                            >
                                <div v-if="!canManageRateChanges" class="employees-page__change-order-note">
                                    Для этого сотрудника недоступно изменение ставки.
                                </div>

                                <div v-else class="employees-page__change-order-rate-block">
                                    <Input
                                        :model-value="employeeChangeOrderForm.individualRateNew"
                                        label="Новая индивидуальная ставка"
                                        type="number"
                                        step="0.01"
                                        placeholder="Например, 3500"
                                        :disabled="employeeChangeOrderForm.clearIndividualRate"
                                        @update:model-value="updateField('individualRateNew', $event)"
                                    />
                                    <label class="employees-page__change-order-toggle employees-page__change-order-toggle--inline">
                                        <input
                                            :checked="employeeChangeOrderForm.clearIndividualRate"
                                            type="checkbox"
                                            @change="updateField('clearIndividualRate', $event.target.checked)"
                                        >
                                        <span class="employees-page__change-order-toggle-slider"></span>
                                        <span class="employees-page__change-order-toggle-label">Снять индивидуальную ставку</span>
                                    </label>
                                </div>
                            </div>
                        </section>

                    </div>
                </div>
            </div>
        </template>

        <template #footer>
            <Button
                color="ghost"
                :disabled="savingEmployeeChangeOrder"
                @click="emit('close')"
            >
                Отмена
            </Button>
            <Button
                color="primary"
                :loading="savingEmployeeChangeOrder"
                @click="emit('submit')"
            >
                Сохранить
            </Button>
        </template>
    </Modal>
</template>

<script setup>
import { computed } from 'vue';
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';

const props = defineProps({
    isOpen: { type: Boolean, default: false },
    zIndex: { type: [Number, String], default: 1001 },
    employeeChangeOrderForm: { type: Object, default: () => ({}) },
    savingEmployeeChangeOrder: { type: Boolean, default: false },
    canManageRateChanges: { type: Boolean, default: false },
    positionOptions: { type: Array, default: () => [] },
    workplaceRestaurantOptions: { type: Array, default: () => [] },
});

const emit = defineEmits(['close', 'submit', 'update-field']);

function updateField(field, value) {
    emit('update-field', { field, value });
}

const isBackdatedEffectiveDate = computed(() => {
    const effectiveDate = String(props.employeeChangeOrderForm?.effectiveDate || '').trim();
    if (!effectiveDate) {
        return false;
    }
    const today = new Date();
    const todayValue = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, '0'),
        String(today.getDate()).padStart(2, '0'),
    ].join('-');
    return effectiveDate < todayValue;
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-attendance-edit-modal' as *;
@use '@/assets/styles/pages/employees-documents-tab' as *;
@use '@/assets/styles/pages/employees-change-orders' as *;
</style>
