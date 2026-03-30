<template>
    <div class="employees-page__modal-section">
        <div class="employees-page__att-toolbar">
            <form class="employees-page__att-filter" @submit.prevent="emit('load-attendances')">
                <div class="employees-page__att-filter-main-row">
                    <DateInput
                        :model-value="attendanceDateFrom"
                        label="C"
                        class="employees-page__att-filter-input"
                        @update:model-value="(value) => emit('update:attendanceDateFrom', value)"
                    />
                    <DateInput
                        :model-value="attendanceDateTo"
                        label="По"
                        class="employees-page__att-filter-input"
                        @update:model-value="(value) => emit('update:attendanceDateTo', value)"
                    />
                    <Button type="submit" color="ghost" size="sm" :loading="attendancesLoading">
                        Показать
                    </Button>
                    <div class="employees-page__att-actions">
                        <Button
                            type="button"
                            color="primary"
                            size="sm"
                            :disabled="attendancesLoading"
                            @click="emit('create-attendance')"
                        >
                            Добавить смену
                        </Button>
                        <Button
                            type="button"
                            color="primary"
                            size="sm"
                            :loading="recalculatingNightMinutes"
                            :disabled="attendancesLoading || recalculatingNightMinutes"
                            @click="emit('recalculate-night-minutes')"
                        >
                            Пересчитать часы
                        </Button>
                    </div>
                </div>
                <div class="employees-page__att-filter-secondary-row">
                    <div class="employees-page__att-view-toggle" role="group" aria-label="Фильтр смен">
                        <button
                            type="button"
                            :class="[
                                'employees-page__att-view-toggle-button',
                                { 'is-active': attendanceViewMode === 'all' }
                            ]"
                            @click="emit('update:attendanceViewMode', 'all')"
                        >
                            Все смены
                        </button>
                        <button
                            type="button"
                            :class="[
                                'employees-page__att-view-toggle-button',
                                { 'is-active': attendanceViewMode === 'by_restaurant' }
                            ]"
                            @click="emit('update:attendanceViewMode', 'by_restaurant')"
                        >
                            По ресторану
                        </button>
                    </div>
                    <Select
                        v-if="attendanceViewMode === 'by_restaurant'"
                        :model-value="attendanceRestaurantFilterValue"
                        :options="attendanceShiftRestaurantOptions"
                        class="employees-page__att-filter-select"
                        @update:model-value="(value) => emit('update:attendanceRestaurantFilterValue', value)"
                    />
                </div>
            </form>
        </div>
        <div v-if="attendancesLoading" class="employees-page__modal-loading">Загрузка смен...</div>
        <div v-else>
            <section v-if="effectiveAttendanceSummary" class="employees-page__attendance-summary">
                <p>
                    Найдено <strong>{{ effectiveAttendanceSummary.shiftCount }}</strong> смен.
                    Суммарное время: <strong>{{ effectiveAttendanceSummary.totalDuration }}</strong>,
                    ночное время:
                    <strong>{{ effectiveAttendanceSummary.nightDuration }}</strong>.
                </p>
            </section>
            <Table v-if="filteredAttendances.length">
                <thead>
                    <tr>
                        <th>Дата открытия</th>
                        <th>Время открытия</th>
                        <th>Ресторан</th>
                        <th>Дата закрытия</th>
                        <th>Время закрытия</th>
                        <th>Должность</th>
                        <th>Ставка</th>
                        <th>Длительность</th>
                        <th>Ночная смена</th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="attendance in filteredAttendances"
                        :key="attendance.id"
                        class="employees-page__attendance-row"
                        @click="emit('open-attendance', attendance)"
                    >
                        <td>{{ formatDate(attendance.open_date) }}</td>
                        <td>{{ attendance.open_time }}</td>
                        <td>{{ formatAttendanceRestaurant(attendance) }}</td>
                        <td>{{ formatDate(attendance.close_date) }}</td>
                        <td>{{ attendance.close_time || '—' }}</td>
                        <td>{{ attendance.position_name || '—' }}</td>
                        <td>
                            <span v-if="rateHidden">$$$</span>
                            <span v-else>{{ attendance.rate != null ? attendance.rate : '—' }}</span>
                        </td>
                        <td>{{ formatDurationMinutes(attendance.duration_minutes) }}</td>
                        <td>{{ formatDurationMinutes(attendance.night_minutes ?? 0) }}</td>
                    </tr>
                </tbody>
            </Table>
            <p v-if="filteredAttendances.length" class="employees-page__attendance-hint">
                Нажмите на строку смены, чтобы отредактировать данные.
            </p>
            <p v-else class="employees-page__empty">Смены не найдены за выбранный период.</p>
        </div>
    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';

defineProps({
    attendanceDateFrom: { type: String, default: '' },
    attendanceDateTo: { type: String, default: '' },
    attendancesLoading: { type: Boolean, default: false },
    recalculatingNightMinutes: { type: Boolean, default: false },
    attendanceViewMode: { type: String, default: 'all' },
    attendanceRestaurantFilterValue: { type: String, default: 'all' },
    attendanceShiftRestaurantOptions: { type: Array, default: () => [] },
    effectiveAttendanceSummary: { type: Object, default: null },
    filteredAttendances: { type: Array, default: () => [] },
    rateHidden: { type: Boolean, default: false },
    formatDate: { type: Function, required: true },
    formatAttendanceRestaurant: { type: Function, required: true },
    formatDurationMinutes: { type: Function, required: true }
});

const emit = defineEmits([
    'load-attendances',
    'update:attendanceDateFrom',
    'update:attendanceDateTo',
    'create-attendance',
    'recalculate-night-minutes',
    'update:attendanceViewMode',
    'update:attendanceRestaurantFilterValue',
    'open-attendance'
]);
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

.employees-page__att-toolbar {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.employees-page__att-filter {
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
}

.employees-page__att-filter-main-row {
    display: flex;
    align-items: flex-end;
    gap: 12px;
    flex-wrap: nowrap;
}

.employees-page__att-filter-secondary-row {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.employees-page__att-actions {
    display: flex;
    gap: 12px;
    flex-wrap: nowrap;
    margin-left: auto;
}

.employees-page__att-view-toggle {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--color-border);
}

.employees-page__att-view-toggle-button {
    border: none;
    border-radius: 999px;
    padding: 8px 16px;
    background: transparent;
    color: var(--color-text-soft);
    font-weight: 600;
    cursor: pointer;
    transition: background-color $duration, color $duration;
}

.employees-page__att-view-toggle-button:hover {
    color: var(--color-text);
}

.employees-page__att-view-toggle-button.is-active {
    background: var(--color-primary);
    color: #000;
}

.employees-page__att-filter-input {
    flex-direction: row;
    align-items: center;
    gap: 6px;
    min-width: 220px;
}

.employees-page__att-filter-select {
    min-width: 240px;
}

.employees-page__attendance-summary {
    padding: 12px 16px;
    color: var(--color-text);
    font-size: 14px;
}

.employees-page__attendance-summary p {
    margin: 0;
}

.employees-page__attendance-row {
    cursor: pointer;
}

.employees-page__attendance-hint {
    margin-top: 8px;
    font-size: 14px;
    color: var(--color-text-soft);
}

@media (max-width: 1024px) {
    .employees-page__att-filter-main-row {
        flex-wrap: wrap;
    }

    .employees-page__att-actions {
        margin-left: 0;
    }
}

@media (max-width: 720px) {
    .employees-page__att-filter-main-row {
        flex-direction: column;
        align-items: stretch;
    }

    .employees-page__att-filter-secondary-row {
        flex-direction: column;
        align-items: stretch;
    }

    .employees-page__att-actions {
        width: 100%;
    }

    .employees-page__att-actions > * {
        flex: 1 1 auto;
    }

    .employees-page__att-filter-input,
    .employees-page__att-filter-select,
    .employees-page__att-view-toggle {
        width: 100%;
        min-width: 0;
    }

    .employees-page__att-view-toggle-button {
        flex: 1 1 50%;
    }
}
</style>
