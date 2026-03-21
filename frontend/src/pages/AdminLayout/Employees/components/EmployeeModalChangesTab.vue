<template>
    <div class="employees-page__modal-section">
        <section
            v-if="canViewEmployeeChanges"
            class="employees-page__info-card employees-page__info-card--full"
        >
            <div class="employees-page__info-card-header">
                <h4 class="employees-page__info-card-title">Журнал изменений</h4>
                <span class="employees-page__info-card-meta">
                    {{ employeeChangeEvents.length }} записей
                </span>
            </div>
            <div v-if="employeeChangeEventsLoading" class="employees-page__modal-loading">
                Загрузка истории...
            </div>
            <div
                v-else-if="employeeChangeEventsError"
                class="employees-page__state employees-page__state--error"
            >
                {{ employeeChangeEventsError }}
            </div>
            <Table v-else-if="employeeChangeEvents.length" class="employees-page__changes-table">
                <thead>
                    <tr>
                        <th>Дата</th>
                        <th>Поле</th>
                        <th>Было</th>
                        <th>Стало</th>
                        <th>Автор</th>
                        <th>Комментарий</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="event in employeeChangeEvents" :key="event.id">
                        <td>{{ formatChangeDate(event.created_at) }}</td>
                        <td>{{ formatChangeField(event.field) }}</td>
                        <td class="employees-page__changes-value">
                            {{ formatChangeValue(event.old_value) }}
                        </td>
                        <td class="employees-page__changes-value">
                            {{ formatChangeValue(event.new_value) }}
                        </td>
                        <td>{{ formatChangeAuthor(event) }}</td>
                        <td class="employees-page__changes-value">
                            {{ formatChangeComment(event.comment) }}
                        </td>
                    </tr>
                </tbody>
            </Table>
            <p v-else class="employees-page__empty">Записей пока нет.</p>
        </section>
    </div>
</template>

<script setup>
import Table from '@/components/UI-components/Table.vue';

defineProps({
    canViewEmployeeChanges: { type: Boolean, default: false },
    employeeChangeEvents: { type: Array, default: () => [] },
    employeeChangeEventsLoading: { type: Boolean, default: false },
    employeeChangeEventsError: { type: String, default: '' },
    formatChangeDate: { type: Function, required: true },
    formatChangeField: { type: Function, required: true },
    formatChangeValue: { type: Function, required: true },
    formatChangeAuthor: { type: Function, required: true },
    formatChangeComment: { type: Function, required: true }
});
</script>

<style scoped lang="scss">
.employees-page__modal-loading {
    text-align: center;
    padding: 24px 0;
    color: var(--color-text-soft);
}

.employees-page__empty {
    text-align: center;
    color: var(--color-text-soft);
    padding: 24px 0;
}

.employees-page__info-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
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
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.employees-page__info-card-meta {
    font-size: 12px;
    color: var(--color-text-soft);
}

.employees-page__info-card-title {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: var(--color-primary);
}

.employees-page__changes-table {
    width: 100%;
}

.employees-page__changes-value {
    max-width: 240px;
    word-break: break-word;
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
</style>
