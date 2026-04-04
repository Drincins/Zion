<template>
    <Modal
        v-if="isOpen"
        class="employees-page__change-order-modal-window positions-page__change-order-modal-window"
        @close="emit('close')"
    >
        <template #header>
            <div class="employees-page__modal-header">
                <h3 class="employees-page__modal-title">Создать изменение ставки</h3>
                <p class="employees-page__modal-subtitle">
                    {{ positionName || 'Выбранная должность' }}
                </p>
            </div>
        </template>

        <template #default>
            <div class="employees-page__change-order-modal positions-page__change-order-modal">
                <div class="employees-page__change-order-form">
                    <div class="employees-page__change-order-form-grid">
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

                    <section class="employees-page__change-order-option employees-page__change-order-option--full">
                        <div class="employees-page__change-order-option-head">
                            <div>
                                <h4 class="employees-page__change-order-option-title">Запланированные изменения</h4>
                                <p class="employees-page__change-order-option-hint">
                                    Здесь хранятся все будущие изменения ставки для выбранной должности.
                                </p>
                            </div>
                        </div>

                        <div class="employees-page__change-order-option-body">
                            <div v-if="loading" class="employees-page__state">
                                Загрузка изменений...
                            </div>
                            <div
                                v-else-if="error"
                                class="employees-page__state employees-page__state--error"
                            >
                                {{ error }}
                            </div>
                            <div v-else-if="orders.length" class="positions-page__change-order-list">
                                <article
                                    v-for="order in orders"
                                    :key="order.id"
                                    class="positions-page__change-order-card"
                                >
                                    <div class="positions-page__change-order-card-head">
                                        <div>
                                            <div class="employees-page__change-orders-date">
                                                С {{ formatDate(order.effective_date) }}
                                            </div>
                                            <div class="employees-page__change-orders-meta">
                                                Создано {{ formatDateTime(order.created_at) }}
                                                <template v-if="order.created_by_name">
                                                    <br>
                                                    {{ order.created_by_name }}
                                                </template>
                                            </div>
                                        </div>
                                        <span
                                            class="employees-page__status-pill"
                                            :class="statusClass(order.status)"
                                        >
                                            {{ formatStatus(order.status) }}
                                        </span>
                                    </div>

                                    <div class="employees-page__change-orders-summary positions-page__change-order-summary">
                                        <div class="employees-page__change-orders-summary-item">
                                            <span class="employees-page__change-orders-summary-label">Новая ставка</span>
                                            <span>{{ formatRate(order.rate_new) }}</span>
                                        </div>
                                    </div>

                                    <p v-if="order.comment" class="employees-page__change-orders-comment">
                                        {{ order.comment }}
                                    </p>
                                    <p v-if="order.error_message" class="employees-page__change-orders-error">
                                        {{ order.error_message }}
                                    </p>

                                    <div class="positions-page__change-order-card-foot">
                                        <span v-if="order.applied_at" class="employees-page__change-orders-meta">
                                            Применён {{ formatDateTime(order.applied_at) }}
                                        </span>
                                        <span v-else-if="order.cancelled_at" class="employees-page__change-orders-meta">
                                            Отменён {{ formatDateTime(order.cancelled_at) }}
                                        </span>
                                        <span v-else class="employees-page__change-orders-meta">
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
                            <div v-else class="employees-page__state">
                                Изменений пока нет.
                            </div>
                        </div>
                    </section>
                </div>
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

function statusClass(status) {
    switch (status) {
    case 'applied':
        return 'employees-page__status-pill--success';
    case 'failed':
        return 'employees-page__status-pill--danger';
    case 'cancelled':
        return 'employees-page__status-pill--muted';
    default:
        return 'employees-page__status-pill--warning';
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
@use '@/assets/styles/pages/employees-attendance-edit-modal' as *;
@use '@/assets/styles/pages/employees-documents-tab' as *;
@use '@/assets/styles/pages/employees-change-orders' as *;

.positions-page__change-order-modal-window :deep(.modal-window) {
    max-width: 720px;
}

.positions-page__change-order-modal {
    width: min(100%, 620px);
}

.positions-page__change-order-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.positions-page__change-order-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px;
    border-radius: 12px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
}

.positions-page__change-order-card-head,
.positions-page__change-order-card-foot {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}

.positions-page__change-order-summary {
    min-width: min(100%, 240px);
}

@media (max-width: 640px) {
    .positions-page__change-order-card-head,
    .positions-page__change-order-card-foot {
        flex-direction: column;
    }
}
</style>
