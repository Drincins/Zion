<template>
    <Modal v-if="isOpen" @close="emit('close')">
        <template #header>
            <div class="position-change-order-modal__header">
                <h3 class="position-change-order-modal__title">Изменение ставки должности</h3>
                <p class="position-change-order-modal__subtitle">
                    {{ positionName || 'Выбранная должность' }}
                </p>
            </div>
        </template>

        <template #default>
            <div class="position-change-order-modal__content">
                <section class="position-change-order-modal__form">
                    <div class="position-change-order-modal__grid">
                        <DateInput
                            :model-value="form.effectiveDate"
                            label="Дата вступления в силу"
                            @update:model-value="updateField('effectiveDate', $event)"
                        />
                        <Input
                            :model-value="form.rateNew"
                            label="Новая ставка"
                            type="number"
                            step="0.01"
                            min="0"
                            placeholder="Например, 3500"
                            @update:model-value="updateField('rateNew', $event)"
                        />
                    </div>

                    <Input
                        :model-value="form.comment"
                        label="Комментарий"
                        placeholder="Необязательно"
                        @update:model-value="updateField('comment', $event)"
                    />

                    <label class="position-change-order-modal__toggle">
                        <input
                            :checked="form.applyToAttendances"
                            type="checkbox"
                            @change="updateField('applyToAttendances', $event.target.checked)"
                        >
                        <span class="position-change-order-modal__toggle-slider"></span>
                        <span class="position-change-order-modal__toggle-label">
                            Обновить будущие смены сотрудников без индивидуальной ставки
                        </span>
                    </label>
                </section>

                <section class="position-change-order-modal__history">
                    <div class="position-change-order-modal__history-head">
                        <h4 class="position-change-order-modal__history-title">Запланированные изменения</h4>
                    </div>

                    <div v-if="loading" class="position-change-order-modal__state">
                        Загрузка изменений...
                    </div>
                    <div
                        v-else-if="error"
                        class="position-change-order-modal__state position-change-order-modal__state--error"
                    >
                        {{ error }}
                    </div>
                    <div v-else-if="orders.length" class="position-change-order-modal__orders">
                        <article
                            v-for="order in orders"
                            :key="order.id"
                            class="position-change-order-modal__order"
                        >
                            <div class="position-change-order-modal__order-head">
                                <div>
                                    <div class="position-change-order-modal__order-date">
                                        С {{ formatDate(order.effective_date) }}
                                    </div>
                                    <div class="position-change-order-modal__order-meta">
                                        Создано {{ formatDateTime(order.created_at) }}
                                        <template v-if="order.created_by_name">
                                            · {{ order.created_by_name }}
                                        </template>
                                    </div>
                                </div>
                                <span
                                    class="position-change-order-modal__status"
                                    :class="`is-${order.status}`"
                                >
                                    {{ formatStatus(order.status) }}
                                </span>
                            </div>
                            <div class="position-change-order-modal__order-rate">
                                Новая ставка: {{ formatRate(order.rate_new) }}
                            </div>
                            <div
                                v-if="order.apply_to_attendances"
                                class="position-change-order-modal__order-note"
                            >
                                Будут обновлены будущие смены сотрудников без индивидуальной ставки
                            </div>
                            <p v-if="order.comment" class="position-change-order-modal__order-comment">
                                {{ order.comment }}
                            </p>
                            <p v-if="order.error_message" class="position-change-order-modal__order-error">
                                {{ order.error_message }}
                            </p>
                            <div class="position-change-order-modal__order-foot">
                                <span v-if="order.applied_at" class="position-change-order-modal__order-meta">
                                    Применён {{ formatDateTime(order.applied_at) }}
                                </span>
                                <span v-else-if="order.cancelled_at" class="position-change-order-modal__order-meta">
                                    Отменён {{ formatDateTime(order.cancelled_at) }}
                                </span>
                                <span v-else class="position-change-order-modal__order-meta">
                                    Ожидает применения
                                </span>
                                <Button
                                    v-if="order.status === 'pending'"
                                    color="secondary"
                                    size="sm"
                                    :loading="cancellingId === order.id"
                                    :disabled="cancellingId === order.id"
                                    @click="emit('cancel-order', order.id)"
                                >
                                    Отменить
                                </Button>
                            </div>
                        </article>
                    </div>
                    <div v-else class="position-change-order-modal__state">
                        Изменений пока нет.
                    </div>
                </section>
            </div>
        </template>

        <template #footer>
            <Button color="ghost" :disabled="saving" @click="emit('close')">Отмена</Button>
            <Button color="primary" :loading="saving" @click="emit('submit')">
                Сохранить изменение
            </Button>
        </template>
    </Modal>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';

defineProps({
    isOpen: { type: Boolean, default: false },
    positionName: { type: String, default: '' },
    form: { type: Object, required: true },
    orders: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    error: { type: String, default: '' },
    saving: { type: Boolean, default: false },
    cancellingId: { type: [Number, String], default: null },
});

const emit = defineEmits(['close', 'submit', 'cancel-order', 'update-field']);

function updateField(field, value) {
    emit('update-field', { field, value });
}

function formatStatus(status) {
    switch (status) {
    case 'applied':
        return 'Применён';
    case 'cancelled':
        return 'Отменён';
    case 'failed':
        return 'Ошибка';
    default:
        return 'Ожидает';
    }
}

function formatDate(value) {
    if (!value) {
        return '—';
    }
    const date = new Date(`${value}T00:00:00`);
    if (Number.isNaN(date.getTime())) {
        return '—';
    }
    return new Intl.DateTimeFormat('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
    }).format(date);
}

function formatDateTime(value) {
    if (!value) {
        return '—';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return '—';
    }
    return new Intl.DateTimeFormat('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    }).format(date);
}

function formatRate(value) {
    if (value === null || value === undefined || value === '') {
        return 'Не задана';
    }
    const number = Number(value);
    if (!Number.isFinite(number)) {
        return String(value);
    }
    return new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(number);
}
</script>

<style scoped lang="scss">
.position-change-order-modal__header {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.position-change-order-modal__title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: var(--color-primary);
}

.position-change-order-modal__subtitle {
    margin: 0;
    color: var(--color-text-soft);
    font-size: 13px;
}

.position-change-order-modal__content {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.position-change-order-modal__form,
.position-change-order-modal__history {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid var(--color-border);
    background: var(--color-surface-200);
}

.position-change-order-modal__grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
}

.position-change-order-modal__toggle {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    width: fit-content;
    user-select: none;
    color: var(--color-text-soft);
    font-size: 13px;
}

.position-change-order-modal__toggle input {
    opacity: 0;
    width: 0;
    height: 0;
}

.position-change-order-modal__toggle-slider {
    position: relative;
    width: 40px;
    height: 22px;
    border-radius: 999px;
    background: var(--color-border);
    transition: background-color 0.2s ease;
}

.position-change-order-modal__toggle-slider::before {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--color-primary);
    transition: transform 0.2s ease;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
}

.position-change-order-modal__toggle input:checked + .position-change-order-modal__toggle-slider {
    background: color-mix(in srgb, var(--color-primary) 26%, var(--color-surface) 74%);
}

.position-change-order-modal__toggle input:checked + .position-change-order-modal__toggle-slider::before {
    transform: translateX(18px);
}

.position-change-order-modal__toggle-label {
    font-weight: 600;
    line-height: 1.35;
}

.position-change-order-modal__history-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.position-change-order-modal__history-title {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
}

.position-change-order-modal__orders {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.position-change-order-modal__order {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px;
    border-radius: 12px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
}

.position-change-order-modal__order-head,
.position-change-order-modal__order-foot {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
}

.position-change-order-modal__order-date,
.position-change-order-modal__order-rate {
    font-weight: 700;
    color: var(--color-text);
}

.position-change-order-modal__order-meta,
.position-change-order-modal__state {
    color: var(--color-text-soft);
    font-size: 12px;
}

.position-change-order-modal__state {
    text-align: center;
    padding: 20px 0;
}

.position-change-order-modal__state--error,
.position-change-order-modal__order-error {
    color: var(--color-danger);
}

.position-change-order-modal__order-note,
.position-change-order-modal__order-comment {
    margin: 0;
    font-size: 13px;
    color: var(--color-text-soft);
}

.position-change-order-modal__status {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid var(--color-border);
    background: var(--color-surface-200);
    color: var(--color-text-soft);
    font-size: 12px;
    font-weight: 700;
}

.position-change-order-modal__status.is-applied {
    color: var(--color-green-text);
    background: var(--color-green-background);
    border-color: color-mix(in srgb, var(--color-green-text) 28%, transparent);
}

.position-change-order-modal__status.is-cancelled {
    color: var(--color-warning-text);
    background: var(--color-warning-background);
    border-color: color-mix(in srgb, var(--color-warning-text) 28%, transparent);
}

.position-change-order-modal__status.is-failed {
    color: var(--color-danger);
    background: color-mix(in srgb, var(--color-danger) 10%, var(--color-surface) 90%);
    border-color: color-mix(in srgb, var(--color-danger) 28%, transparent);
}

@media (max-width: 720px) {
    .position-change-order-modal__order-head,
    .position-change-order-modal__order-foot {
        flex-direction: column;
    }
}
</style>
