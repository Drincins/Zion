<template>
    <Modal
        v-if="isOpen"
        :z-index="zIndex"
        @close="emit('close')"
    >
        <template #header>
            <div class="employee-change-order-modal__header">
                <h3 class="employee-change-order-modal__title">Создать кадровое изменение</h3>
                <p class="employee-change-order-modal__subtitle">
                    Выбери дату вступления в силу и параметры, которые должны измениться.
                </p>
            </div>
        </template>

        <template #default>
            <div class="employee-change-order-modal__form">
                <div class="employee-change-order-modal__grid">
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

                <section class="employee-change-order-modal__section">
                    <div class="employee-change-order-modal__section-head">
                        <div>
                            <h4 class="employee-change-order-modal__section-title">Должность</h4>
                            <p class="employee-change-order-modal__section-hint">
                                Если сотрудник без индивидуальной ставки, новая ставка подтянется от должности.
                            </p>
                        </div>
                        <label class="employee-change-order-modal__toggle">
                            <input
                                :checked="employeeChangeOrderForm.changePosition"
                                type="checkbox"
                                @change="updateField('changePosition', $event.target.checked)"
                            >
                            <span class="employee-change-order-modal__toggle-slider"></span>
                            <span class="employee-change-order-modal__toggle-label">Изменить</span>
                        </label>
                    </div>
                    <Select
                        :model-value="employeeChangeOrderForm.positionIdNew"
                        :options="positionOptions"
                        placeholder="Выберите должность"
                        :disabled="!employeeChangeOrderForm.changePosition"
                        @update:model-value="updateField('positionIdNew', $event)"
                    />
                </section>

                <section class="employee-change-order-modal__section">
                    <div class="employee-change-order-modal__section-head">
                        <div>
                            <h4 class="employee-change-order-modal__section-title">Место работы</h4>
                            <p class="employee-change-order-modal__section-hint">
                                Можно заранее перевести сотрудника в другой ресторан.
                            </p>
                        </div>
                        <label class="employee-change-order-modal__toggle">
                            <input
                                :checked="employeeChangeOrderForm.changeWorkplaceRestaurant"
                                type="checkbox"
                                @change="updateField('changeWorkplaceRestaurant', $event.target.checked)"
                            >
                            <span class="employee-change-order-modal__toggle-slider"></span>
                            <span class="employee-change-order-modal__toggle-label">Изменить</span>
                        </label>
                    </div>
                    <Select
                        :model-value="employeeChangeOrderForm.workplaceRestaurantIdNew"
                        :options="workplaceRestaurantOptions"
                        placeholder="Выберите ресторан"
                        :disabled="!employeeChangeOrderForm.changeWorkplaceRestaurant"
                        @update:model-value="updateField('workplaceRestaurantIdNew', $event)"
                    />
                </section>

                <section class="employee-change-order-modal__section">
                    <div class="employee-change-order-modal__section-head">
                        <div>
                            <h4 class="employee-change-order-modal__section-title">Индивидуальная ставка</h4>
                            <p class="employee-change-order-modal__section-hint">
                                Через приказ сотрудника меняем только индивидуальную ставку.
                            </p>
                        </div>
                        <label class="employee-change-order-modal__toggle">
                            <input
                                :checked="employeeChangeOrderForm.changeIndividualRate"
                                :disabled="!canManageRateChanges"
                                type="checkbox"
                                @change="updateField('changeIndividualRate', $event.target.checked)"
                            >
                            <span class="employee-change-order-modal__toggle-slider"></span>
                            <span class="employee-change-order-modal__toggle-label">Изменить</span>
                        </label>
                    </div>

                    <div v-if="!canManageRateChanges" class="employee-change-order-modal__note">
                        Для этого сотрудника недоступно изменение ставки.
                    </div>

                    <div v-else class="employee-change-order-modal__rate-block">
                        <Input
                            :model-value="employeeChangeOrderForm.individualRateNew"
                            label="Новая индивидуальная ставка"
                            type="number"
                            step="0.01"
                            placeholder="Например, 3500"
                            :disabled="!employeeChangeOrderForm.changeIndividualRate || employeeChangeOrderForm.clearIndividualRate"
                            @update:model-value="updateField('individualRateNew', $event)"
                        />
                        <label class="employee-change-order-modal__toggle">
                            <input
                                :checked="employeeChangeOrderForm.clearIndividualRate"
                                :disabled="!employeeChangeOrderForm.changeIndividualRate"
                                type="checkbox"
                                @change="updateField('clearIndividualRate', $event.target.checked)"
                            >
                            <span class="employee-change-order-modal__toggle-slider"></span>
                            <span class="employee-change-order-modal__toggle-label">Снять индивидуальную ставку</span>
                        </label>
                    </div>
                </section>

                <section class="employee-change-order-modal__section employee-change-order-modal__section--compact">
                    <div class="employee-change-order-modal__section-head">
                        <div>
                            <h4 class="employee-change-order-modal__section-title">Смены</h4>
                            <p class="employee-change-order-modal__section-hint">
                                Применить новые данные к будущим сменам сотрудника.
                            </p>
                        </div>
                        <label class="employee-change-order-modal__toggle">
                            <input
                                :checked="employeeChangeOrderForm.applyToAttendances"
                                type="checkbox"
                                @change="updateField('applyToAttendances', $event.target.checked)"
                            >
                            <span class="employee-change-order-modal__toggle-slider"></span>
                            <span class="employee-change-order-modal__toggle-label">Обновлять</span>
                        </label>
                    </div>
                </section>
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
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';

defineProps({
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
</script>

<style scoped lang="scss">
.employee-change-order-modal__header {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.employee-change-order-modal__title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: var(--color-primary);
}

.employee-change-order-modal__subtitle {
    margin: 0;
    color: var(--color-text-soft);
    font-size: 13px;
    line-height: 1.45;
}

.employee-change-order-modal__form {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.employee-change-order-modal__grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
}

.employee-change-order-modal__section {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid var(--color-border);
    background: var(--color-surface-200);
}

.employee-change-order-modal__section--compact {
    padding-bottom: 12px;
}

.employee-change-order-modal__section-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}

.employee-change-order-modal__section-title {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--color-text);
}

.employee-change-order-modal__section-hint {
    margin: 4px 0 0;
    font-size: 12px;
    line-height: 1.45;
    color: var(--color-text-soft);
}

.employee-change-order-modal__toggle {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--color-text-soft);
    width: fit-content;
    user-select: none;
}

.employee-change-order-modal__toggle input {
    opacity: 0;
    width: 0;
    height: 0;
}

.employee-change-order-modal__toggle-slider {
    position: relative;
    width: 38px;
    height: 22px;
    border-radius: 999px;
    background: var(--color-border);
    transition: background-color 0.2s ease;
    cursor: pointer;
}

.employee-change-order-modal__toggle-slider::before {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--color-primary);
    transition: transform 0.25s ease;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
}

.employee-change-order-modal__toggle input:checked + .employee-change-order-modal__toggle-slider {
    background: color-mix(in srgb, var(--color-primary) 26%, var(--color-surface) 74%);
}

.employee-change-order-modal__toggle input:checked + .employee-change-order-modal__toggle-slider::before {
    transform: translateX(16px);
}

.employee-change-order-modal__toggle input:disabled + .employee-change-order-modal__toggle-slider {
    cursor: not-allowed;
    opacity: 0.6;
}

.employee-change-order-modal__toggle-label {
    font-weight: 600;
    line-height: 1.1;
}

.employee-change-order-modal__rate-block {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.employee-change-order-modal__note {
    margin: 0;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    color: var(--color-text-soft);
    font-size: 13px;
}

@media (max-width: 720px) {
    .employee-change-order-modal__section-head {
        display: grid;
        grid-template-columns: 1fr;
    }
}
</style>
