<template>
    <section class="employees-page__section">
        <Table v-if="employees.length" class="employees-page__section-table">
            <thead>
                <tr>
                    <th
                        v-for="(column, columnIndex) in orderedColumns"
                        :key="column.id"
                        :class="stickyClassForIndex(columnIndex)"
                    >
                        <button
                            class="employees-page__sort-button"
                            type="button"
                            @click="toggleSort(column.id)"
                        >
                            <span>{{ column.label }}</span>
                            <span class="employees-page__sort-icons">
                                <span
                                    class="employees-page__sort-icon"
                                    :class="{ 'employees-page__sort-icon--active': isSortedAsc(column.id) }"
                                >
                                    ▲
                                </span>
                                <span
                                    class="employees-page__sort-icon"
                                    :class="{ 'employees-page__sort-icon--active': isSortedDesc(column.id) }"
                                >
                                    ▼
                                </span>
                            </span>
                        </button>
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="employee in employees" :key="employee.id">
                    <td
                        v-for="(column, columnIndex) in orderedColumns"
                        :key="column.id"
                        :class="stickyClassForIndex(columnIndex)"
                    >
                        <template v-if="column.type === 'fullName'">
                            <button
                                class="employees-page__fio-button"
                                type="button"
                                @click="emit('select', employee)"
                            >
                                {{ formatFullName(employee) }}
                            </button>
                        </template>
                        <template v-else-if="column.type === 'status'">
                            <span
                                :class="[
                                    'employees-page__status',
                                    employee.fired ? 'employees-page__status--fired' : '',
                                ]"
                            >
                                {{ employee.fired ? 'Уволен' : 'Активен' }}
                            </span>
                        </template>
                        <template v-else-if="column.type === 'date'">
                            {{ formatDateValue(employee[column.id]) }}
                        </template>
                        <template v-else-if="column.type === 'gender'">
                            {{ formatGenderValue(employee.gender) }}
                        </template>
                        <template v-else-if="column.type === 'boolean'">
                            {{ formatBooleanValue(employee[column.id]) }}
                        </template>
                        <template v-else-if="column.type === 'phone'">
                            {{ formatPhoneValue(employee[column.id]) }}
                        </template>
                        <template v-else-if="column.type === 'money'">
                            {{ formatMoneyValue(employee[column.id]) }}
                        </template>
                        <template v-else-if="column.type === 'restaurants'">
                            {{ formatRestaurantsValue(employee) }}
                        </template>
                        <template v-else-if="column.type === 'list'">
                            {{ formatListValue(employee[column.id]) }}
                        </template>
                        <template v-else>
                            {{ formatDefaultValue(employee[column.id]) }}
                        </template>
                    </td>
                </tr>
            </tbody>
        </Table>
        <Table
            v-else-if="isLoading"
            class="employees-page__section-table employees-page__section-table--skeleton"
            aria-hidden="true"
        >
            <thead>
                <tr>
                    <th
                        v-for="(column, columnIndex) in orderedColumns"
                        :key="`skeleton-header-${column.id}`"
                        :class="stickyClassForIndex(columnIndex)"
                    >
                        {{ column.label }}
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="row in 8" :key="`skeleton-row-${row}`">
                    <td
                        v-for="(column, columnIndex) in orderedColumns"
                        :key="`skeleton-cell-${row}-${column.id}`"
                        :class="stickyClassForIndex(columnIndex)"
                    >
                        <span class="employees-page__skeleton-line" :class="{ 'is-short': columnIndex > 3 }"></span>
                    </td>
                </tr>
            </tbody>
        </Table>
        <div v-else class="employees-page__empty">
            <p v-if="isLoading">Загружаем список сотрудников...</p>
            <p v-else>Сотрудники не найдены.</p>
        </div>
    </section>
</template>

<script setup>
import { computed, toRefs } from 'vue';
import Table from '@/components/UI-components/Table.vue';
import { formatNumberValue } from '@/utils/format';
import { formatPhoneForDisplay } from '@/utils/phone';
import { EMPLOYEE_COLUMNS } from '../employeeColumns';

const props = defineProps({
    employees: { type: Array, default: () => [] },
    isLoading: { type: Boolean, default: false },
    formatFullName: { type: Function, required: true },
    formatDate: { type: Function, required: true },
    formatGender: { type: Function, required: true },
    sortBy: { type: String, default: '' },
    sortDirection: { type: String, default: 'asc' },
    visibleColumns: { type: Array, default: () => [] },
    columnOptions: { type: Array, default: () => [] },
});

const emit = defineEmits(['select', 'update:sort-by', 'update:sort-direction']);

const { employees, isLoading, formatFullName, formatDate, formatGender, sortBy, sortDirection } =
    toRefs(props);

const columnOptions = computed(() => {
    if (Array.isArray(props.columnOptions) && props.columnOptions.length) {
        return props.columnOptions;
    }
    return EMPLOYEE_COLUMNS;
});

const visibleColumnSet = computed(() => {
    const list =
        Array.isArray(props.visibleColumns) && props.visibleColumns.length
            ? props.visibleColumns
            : columnOptions.value.map((column) => column.id);
    return new Set(list);
});

const orderedColumns = computed(() =>
    columnOptions.value.filter((column) => visibleColumnSet.value.has(column.id)),
);

const isSortedAsc = (columnKey) => sortBy.value === columnKey && sortDirection.value === 'asc';
const isSortedDesc = (columnKey) => sortBy.value === columnKey && sortDirection.value === 'desc';

const toggleSort = (columnKey) => {
    const nextDirection =
        sortBy.value === columnKey && sortDirection.value === 'asc' ? 'desc' : 'asc';
    emit('update:sort-by', columnKey);
    emit('update:sort-direction', nextDirection);
};

const stickyClassForIndex = (index) => {
    if (index === 0) {
        return ['employees-page__cell--sticky', 'employees-page__cell--sticky-first'];
    }
    if (index === 1) {
        return ['employees-page__cell--sticky', 'employees-page__cell--sticky-second'];
    }
    return [];
};

const EMPTY_VALUE = '—';

const formatBooleanValue = (value) => (value ? 'Да' : 'Нет');

const formatPhoneValue = (value) => {
    return formatPhoneForDisplay(value, { emptyValue: EMPTY_VALUE });
};

const formatMoneyValue = (value) => {
    return formatNumberValue(value, {
        emptyValue: EMPTY_VALUE,
        invalidValue: EMPTY_VALUE,
        locale: 'ru-RU',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
};

const formatDateValue = (value) => {
    if (!value) {
        return EMPTY_VALUE;
    }
    const formatted = formatDate.value(value);
    return formatted ?? EMPTY_VALUE;
};

const formatGenderValue = (value) => {
    const formatted = formatGender.value(value);
    return formatted ?? EMPTY_VALUE;
};

const formatListValue = (value) => {
    if (Array.isArray(value) && value.length) {
        return value.filter(Boolean).join(', ');
    }
    if (value === null || value === undefined) {
        return EMPTY_VALUE;
    }
    if (value === '') {
        return EMPTY_VALUE;
    }
    return value;
};

const formatRestaurantsValue = (employee) => {
    if (!employee) {
        return EMPTY_VALUE;
    }
    if (Array.isArray(employee.restaurants) && employee.restaurants.length) {
        const names = employee.restaurants
            .map((restaurant) => {
                if (restaurant?.name) {
                    return restaurant.name;
                }
                if (restaurant?.id !== undefined && restaurant?.id !== null) {
                    return `ID ${restaurant.id}`;
                }
                return '';
            })
            .filter(Boolean);
        if (names.length) {
            return names.join(', ');
        }
    }
    if (Array.isArray(employee.restaurant_ids) && employee.restaurant_ids.length) {
        const ids = employee.restaurant_ids.filter(
            (value) => value !== null && value !== undefined && value !== '',
        );
        if (ids.length) {
            return ids.join(', ');
        }
    }
    return EMPTY_VALUE;
};

const formatDefaultValue = (value) => {
    if (value === null || value === undefined || value === '') {
        return EMPTY_VALUE;
    }
    return value;
};
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-table' as *;
</style>
