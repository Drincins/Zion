<template>
    <div class="employees-page__modal-section">
        <section class="employees-page__info-card employees-page__info-card--full">
            <div class="employees-page__info-card-header employees-page__orders-header">
                <div>
                    <h4 class="employees-page__info-card-title">Кадровые изменения</h4>
                    <p class="employees-page__orders-hint">
                        Здесь хранятся отложенные изменения сотрудника с датой вступления в силу.
                    </p>
                </div>
                <Button
                    v-if="canManageEmployeeChangeOrders"
                    color="primary"
                    size="sm"
                    @click="emit('open-form')"
                >
                    Создать изменение
                </Button>
            </div>

            <div v-if="employeeChangeOrdersLoading" class="employees-page__modal-loading">
                Загрузка кадровых изменений...
            </div>
            <div
                v-else-if="employeeChangeOrdersError"
                class="employees-page__state employees-page__state--error"
            >
                {{ employeeChangeOrdersError }}
            </div>
            <div v-else-if="employeeChangeOrders.length" class="employees-page__orders-list">
                <article
                    v-for="order in employeeChangeOrders"
                    :key="order.id"
                    class="employees-page__orders-item"
                >
                    <div class="employees-page__orders-item-head">
                        <div>
                            <div class="employees-page__orders-item-date">
                                С {{ formatDate(order.effective_date) }}
                            </div>
                            <div class="employees-page__orders-item-meta">
                                Создано {{ formatDateTime(order.created_at) }}
                                <template v-if="order.created_by_name">
                                    · {{ order.created_by_name }}
                                </template>
                            </div>
                        </div>
                        <span
                            class="employees-page__orders-status"
                            :class="`is-${order.status}`"
                        >
                            {{ formatStatus(order.status) }}
                        </span>
                    </div>

                    <ul class="employees-page__orders-summary">
                        <li v-if="order.change_position">
                            Должность: {{ order.position_name_new || formatIdFallback(order.position_id_new) }}
                        </li>
                        <li v-if="order.change_workplace_restaurant">
                            Место работы: {{ order.workplace_restaurant_name_new || 'Не выбрано' }}
                        </li>
                        <li v-if="order.change_individual_rate">
                            Индивидуальная ставка:
                            {{ order.individual_rate_new === null || order.individual_rate_new === undefined
                                ? 'снять'
                                : formatAmount(order.individual_rate_new) }}
                        </li>
                        <li v-if="order.change_rate">
                            Ставка: {{ formatAmount(order.rate_new) }}
                        </li>
                        <li v-if="order.apply_to_attendances">
                            Обновлять будущие смены с даты вступления
                        </li>
                    </ul>

                    <p v-if="order.comment" class="employees-page__orders-comment">
                        {{ order.comment }}
                    </p>
                    <p v-if="order.error_message" class="employees-page__orders-error">
                        {{ order.error_message }}
                    </p>

                    <div class="employees-page__orders-item-foot">
                        <span v-if="order.applied_at" class="employees-page__orders-item-meta">
                            Применён {{ formatDateTime(order.applied_at) }}
                        </span>
                        <span v-else-if="order.cancelled_at" class="employees-page__orders-item-meta">
                            Отменён {{ formatDateTime(order.cancelled_at) }}
                        </span>
                        <span v-else class="employees-page__orders-item-meta">Ожидает применения</span>
                        <Button
                            v-if="order.status === 'pending'"
                            color="secondary"
                            size="sm"
                            :loading="cancellingEmployeeChangeOrderId === order.id"
                            :disabled="cancellingEmployeeChangeOrderId === order.id"
                            @click="emit('cancel-order', order.id)"
                        >
                            Отменить
                        </Button>
                    </div>
                </article>
            </div>
            <p v-else class="employees-page__empty">Кадровых изменений пока нет.</p>
        </section>
    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';

defineProps({
    canManageEmployeeChangeOrders: { type: Boolean, default: false },
    employeeChangeOrders: { type: Array, default: () => [] },
    employeeChangeOrdersLoading: { type: Boolean, default: false },
    employeeChangeOrdersError: { type: String, default: '' },
    cancellingEmployeeChangeOrderId: { type: [Number, String], default: null },
    formatDate: { type: Function, required: true },
    formatAmount: { type: Function, required: true },
});

const emit = defineEmits([
    'open-form',
    'cancel-order',
]);

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

function formatIdFallback(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? `ID ${parsed}` : 'Не выбрано';
}
</script>

<style scoped lang="scss">
.employees-page__modal-loading,
.employees-page__empty {
    text-align: center;
    padding: 24px 0;
    color: var(--color-text-soft);
}

.employees-page__info-card {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 20px;
    background: var(--color-surface);
    border-radius: 16px;
    border: 1px solid var(--color-border);
    color: var(--color-text);
}

.employees-page__info-card--full {
    grid-column: 1 / -1;
}

.employees-page__info-card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}

.employees-page__info-card-title {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: var(--color-primary);
}

.employees-page__orders-hint {
    margin: 6px 0 0;
    color: var(--color-text-soft);
    font-size: 13px;
    line-height: 1.45;
}

.employees-page__orders-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.employees-page__orders-item {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid var(--color-border);
    background: var(--color-surface-100);
}

.employees-page__orders-item-head,
.employees-page__orders-item-foot {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}

.employees-page__orders-item-date {
    font-weight: 700;
    color: var(--color-text);
}

.employees-page__orders-item-meta {
    color: var(--color-text-soft);
    font-size: 12px;
}

.employees-page__orders-status {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text-soft);
}

.employees-page__orders-status.is-applied {
    color: var(--color-green-text);
    background: var(--color-green-background);
    border-color: color-mix(in srgb, var(--color-green-text) 30%, transparent);
}

.employees-page__orders-status.is-failed {
    color: var(--color-red-text);
    background: var(--color-red-background);
    border-color: color-mix(in srgb, var(--color-red-text) 30%, transparent);
}

.employees-page__orders-status.is-cancelled {
    background: var(--color-surface-200);
}

.employees-page__orders-summary {
    margin: 0;
    padding-left: 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.employees-page__orders-comment,
.employees-page__orders-error {
    margin: 0;
    font-size: 13px;
    line-height: 1.45;
}

.employees-page__orders-comment {
    color: var(--color-text-soft);
}

.employees-page__orders-error {
    color: var(--color-red-text);
}

.employees-page__state {
    margin: 0;
    padding: 12px 14px;
    border-radius: 8px;
    background: var(--color-surface-200);
    border: 1px solid var(--color-border);
    color: var(--color-text-soft);
}

.employees-page__state--error {
    background: var(--color-red-background);
    border: 1px solid var(--color-red-text);
    color: var(--color-red-text);
}

@media (max-width: 720px) {
    .employees-page__info-card-header,
    .employees-page__orders-item-head,
    .employees-page__orders-item-foot {
        display: grid;
        grid-template-columns: 1fr;
    }
}
</style>
