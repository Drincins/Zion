<template>
    <div class="employees-page__finance employees-page__change-orders">
        <div class="employees-page__change-orders-bar">
            <div class="employees-page__change-orders-bar-text">
                <h4 class="employees-page__change-orders-bar-title">Кадровые изменения</h4>
                <p class="employees-page__finance-hint">
                    Здесь хранятся кадровые изменения сотрудника с датой вступления в силу.
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
        <Table v-else-if="employeeChangeOrders.length">
            <thead>
                <tr>
                    <th>Дата</th>
                    <th>Изменения</th>
                    <th>Статус</th>
                    <th>Создано</th>
                    <th>Комментарий</th>
                    <th class="employees-page__trainings-actions">Действия</th>
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="order in employeeChangeOrders"
                    :key="order.id"
                    class="employees-page__change-orders-row"
                >
                    <td>
                        <div class="employees-page__change-orders-date">
                            С {{ formatDate(order.effective_date) }}
                        </div>
                    </td>
                    <td>
                        <div class="employees-page__change-orders-summary employees-page__change-orders-summary--table">
                            <div v-if="order.change_position" class="employees-page__change-orders-summary-item">
                                <span class="employees-page__change-orders-summary-label">Должность</span>
                                <span>{{ order.position_name_new || formatIdFallback(order.position_id_new) }}</span>
                            </div>
                            <div
                                v-if="order.change_workplace_restaurant"
                                class="employees-page__change-orders-summary-item"
                            >
                                <span class="employees-page__change-orders-summary-label">Место работы</span>
                                <span>{{ order.workplace_restaurant_name_new || 'Не выбрано' }}</span>
                            </div>
                            <div v-if="order.change_individual_rate" class="employees-page__change-orders-summary-item">
                                <span class="employees-page__change-orders-summary-label">Индивидуальная ставка</span>
                                <span>
                                    {{ order.individual_rate_new === null || order.individual_rate_new === undefined
                                        ? 'Снять'
                                        : formatAmount(order.individual_rate_new) }}
                                </span>
                            </div>
                            <div v-if="order.change_rate" class="employees-page__change-orders-summary-item">
                                <span class="employees-page__change-orders-summary-label">Ставка</span>
                                <span>{{ formatAmount(order.rate_new) }}</span>
                            </div>
                        </div>
                    </td>
                    <td>
                        <span
                            class="employees-page__status-pill"
                            :class="statusClass(order.status)"
                        >
                            {{ formatStatus(order.status) }}
                        </span>
                    </td>
                    <td>
                        <div class="employees-page__change-orders-meta">
                            {{ formatDateTime(order.created_at) }}
                            <template v-if="order.created_by_name">
                                <br>
                                {{ order.created_by_name }}
                            </template>
                        </div>
                    </td>
                    <td class="employees-page__trainings-comment">
                        <div v-if="order.comment" class="employees-page__change-orders-comment">
                            {{ order.comment }}
                        </div>
                        <div v-else class="employees-page__change-orders-meta">—</div>
                        <div v-if="order.error_message" class="employees-page__change-orders-error">
                            {{ order.error_message }}
                        </div>
                    </td>
                    <td class="employees-page__trainings-actions">
                        <div class="employees-page__change-orders-actions">
                            <span v-if="order.applied_at" class="employees-page__change-orders-meta">
                                Применён {{ formatDateTime(order.applied_at) }}
                            </span>
                            <span v-else-if="order.cancelled_at" class="employees-page__change-orders-meta">
                                Отменён {{ formatDateTime(order.cancelled_at) }}
                            </span>
                            <span v-else class="employees-page__change-orders-meta">Ожидает применения</span>
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
                    </td>
                </tr>
            </tbody>
        </Table>
        <p v-else class="employees-page__empty">Кадровых изменений пока нет.</p>
    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Table from '@/components/UI-components/Table.vue';

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
@use '@/assets/styles/pages/employees-documents-tab' as *;
@use '@/assets/styles/pages/employees-change-orders' as *;
</style>
