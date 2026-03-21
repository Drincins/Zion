<template>
    <div class="admin-page kitchen-non-cash-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Лимиты безнала</h1>
                <p class="admin-page__subtitle">
                    Связка типов безнала с сотрудниками и контроль потребления за выбранный период.
                </p>
            </div>
            <div class="admin-page__header-actions">
                <Button
                    v-if="canManage"
                    color="secondary"
                    :disabled="loading"
                    @click="openCreateTypeModal()"
                >
                    Добавить тип
                </Button>
                <Button :loading="loading" :disabled="loading" @click="reloadAll">Обновить</Button>
            </div>
        </header>

        <section class="kitchen-non-cash-page__filters-panel">
            <button
                type="button"
                class="kitchen-non-cash-page__filters-toggle"
                @click="isFiltersOpen = !isFiltersOpen"
            >
                Фильтры
                <span :class="['kitchen-non-cash-page__filters-icon', { 'is-open': isFiltersOpen }]">
                    ▼
                </span>
            </button>
            <div v-if="isFiltersOpen" class="kitchen-non-cash-page__filters-content">
                <div class="kitchen-non-cash-page__filters">
                    <div class="kitchen-non-cash-page__filter-control">
                        <Select
                            v-model="restaurantId"
                            label="Ресторан"
                            :options="restaurantOptions"
                            placeholder="Все рестораны"
                        />
                    </div>
                    <div class="kitchen-non-cash-page__filter-control">
                        <DateInput v-model="fromDate" label="С даты" />
                    </div>
                    <div class="kitchen-non-cash-page__filter-control">
                        <DateInput v-model="toDate" label="По дату" />
                    </div>
                    <div class="kitchen-non-cash-page__filter-control kitchen-non-cash-page__filter-control--action">
                        <Button
                            :loading="loadingConsumption"
                            :disabled="loadingConsumption"
                            @click="loadConsumption"
                        >
                            Пересчитать
                        </Button>
                    </div>
                </div>
            </div>
            <p class="kitchen-non-cash-page__totals">
                Период: {{ fromDate }} - {{ toDate }} |
                Итого затрат: {{ formatMoney(totalConsumed) }}
            </p>
        </section>

        <section class="admin-page__section">
            <Table v-if="displayNonCashTypes.length">
                <thead>
                    <tr>
                        <th>Тип безнала</th>
                        <th>Код</th>
                        <th>Категория</th>
                        <th>Активен</th>
                        <th>Лимитов</th>
                        <th>Потреблено</th>
                        <th>Заказов</th>
                        <th class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in displayNonCashTypes" :key="row.id">
                        <td>{{ row.name || '-' }}</td>
                        <td class="kitchen-non-cash-page__mono">{{ row.id }}</td>
                        <td>{{ formatCategory(row.category) }}</td>
                        <td>{{ row.is_active ? 'Да' : 'Нет' }}</td>
                        <td>{{ limitsCountByType[row.id] || 0 }}</td>
                        <td>{{ formatMoney(getTypeStat(row.id, 'consumed_amount')) }}</td>
                        <td>{{ formatNumber(getTypeStat(row.id, 'orders_count')) }}</td>
                        <td class="admin-page__actions">
                            <button
                                type="button"
                                class="admin-page__icon-button"
                                title="Открыть карточку"
                                @click="openTypeCard(row)"
                            >
                                <BaseIcon name="Edit" />
                            </button>
                        </td>
                    </tr>
                </tbody>
            </Table>
            <div v-else-if="loading" class="admin-page__empty">Загрузка справочника безнала...</div>
            <div v-else class="admin-page__empty">Типы безнала еще не загружены.</div>
        </section>

        <Modal v-if="selectedType" class="kitchen-non-cash-page__type-modal" @close="closeTypeCard">
            <template #header>
                <div class="kitchen-non-cash-page__modal-header">
                    <h3 class="kitchen-non-cash-page__modal-title">{{ selectedType.name || 'Карточка безнала' }}</h3>
                    <p class="kitchen-non-cash-page__modal-subtitle">Код: {{ selectedType.id }}</p>
                </div>
            </template>

            <div class="kitchen-non-cash-page__modal-layout">
                <div class="kitchen-non-cash-page__card kitchen-non-cash-page__card--settings">
                    <h4 class="kitchen-non-cash-page__card-title">Настройка типа</h4>
                    <div class="kitchen-non-cash-page__settings-grid">
                        <Select
                            v-model="selectedTypeDraft.category"
                            label="Категория"
                            :options="categoryEditOptions"
                            :disabled="!canManage"
                            placeholder="Не задано"
                        />
                        <Input
                            v-model="selectedTypeDraft.comment"
                            label="Комментарий"
                            placeholder="Опционально"
                            :readonly="!canManage"
                        />
                        <div class="kitchen-non-cash-page__settings-checkbox">
                            <Checkbox
                                v-model="selectedTypeDraft.is_active"
                                :disabled="!canManage"
                                label="Активный тип безнала"
                            />
                        </div>
                    </div>
                </div>

                <div class="kitchen-non-cash-page__card">
                    <h4 class="kitchen-non-cash-page__card-title">Лимиты сотрудников</h4>
                    <div v-if="selectedTypeLimits.length" class="kitchen-non-cash-page__table-wrap">
                        <Table class="kitchen-non-cash-page__limits-table">
                            <thead>
                                <tr>
                                    <th>Сотрудник</th>
                                    <th>Период</th>
                                    <th>Лимит</th>
                                    <th>Потреблено</th>
                                    <th>Остаток</th>
                                    <th>Активен</th>
                                    <th>Комментарий</th>
                                    <th>Категории</th>
                                    <th class="admin-page__actions">Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                <template v-for="row in selectedTypeLimits" :key="row.id">
                                    <tr>
                                        <td>{{ row.user_name || `#${row.user_id}` }}</td>
                                        <td>
                                            <Select
                                                v-model="limitDrafts[row.id].period_type"
                                                :options="periodOptions"
                                                :disabled="!canManage"
                                            />
                                        </td>
                                        <td>
                                            <Input
                                                v-model="limitDrafts[row.id].limit_amount"
                                                type="number"
                                                step="0.01"
                                                :readonly="!canManage"
                                            />
                                        </td>
                                        <td>{{ formatMoney(row.consumed_amount) }}</td>
                                        <td>{{ formatMoney(row.balance_amount) }}</td>
                                        <td class="kitchen-non-cash-page__status">
                                            <Checkbox v-model="limitDrafts[row.id].is_active" :disabled="!canManage" label="" />
                                        </td>
                                        <td>
                                            <Input
                                                v-model="limitDrafts[row.id].comment"
                                                type="text"
                                                :readonly="!canManage"
                                            />
                                        </td>
                                        <td class="kitchen-non-cash-page__limit-details-cell">
                                            <button
                                                type="button"
                                                class="kitchen-non-cash-page__limit-details-toggle"
                                                @click="toggleLimitDetails(row)"
                                            >
                                                {{ isLimitDetailsOpen(row) ? 'Скрыть' : 'Показать' }}
                                            </button>
                                        </td>
                                        <td class="admin-page__actions">
                                            <button
                                                type="button"
                                                class="admin-page__icon-button"
                                                :disabled="!canManage || savingLimitId === row.id"
                                                title="Сохранить лимит"
                                                @click="saveLimit(row)"
                                            >
                                                <BaseIcon name="Edit" />
                                            </button>
                                            <button
                                                type="button"
                                                class="admin-page__icon-button admin-page__icon-button--danger"
                                                :disabled="!canManage || deletingLimitId === row.id"
                                                title="Удалить лимит"
                                                @click="deleteLimit(row)"
                                            >
                                                <BaseIcon name="Trash" />
                                            </button>
                                        </td>
                                    </tr>
                                    <tr v-if="isLimitDetailsOpen(row)">
                                        <td colspan="9" class="kitchen-non-cash-page__limit-details-expanded">
                                            <div class="kitchen-non-cash-page__table-wrap">
                                                <Table v-if="row.by_category?.length" class="kitchen-non-cash-page__limits-table">
                                                    <thead>
                                                        <tr>
                                                            <th>Категория</th>
                                                            <th>Потреблено</th>
                                                            <th>Количество</th>
                                                            <th>Заказов</th>
                                                            <th>Позиции</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        <tr v-for="category in row.by_category" :key="`${row.id}:${category.category_name}`">
                                                            <td>{{ category.category_name || 'Без категории' }}</td>
                                                            <td>{{ formatMoney(category.consumed_amount) }}</td>
                                                            <td>{{ formatNumber(category.consumed_qty) }}</td>
                                                            <td>{{ formatNumber(category.orders_count) }}</td>
                                                            <td>{{ formatNumber(category.items_count) }}</td>
                                                        </tr>
                                                    </tbody>
                                                </Table>
                                            </div>
                                            <div v-if="!row.by_category?.length" class="admin-page__empty">
                                                Нет данных по категориям за период.
                                            </div>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </Table>
                    </div>
                    <div v-else class="admin-page__empty">Лимиты для этого типа еще не добавлены.</div>

                    <h5 class="kitchen-non-cash-page__add-title">Затраты по ресторанам (этот тип)</h5>
                    <div v-if="selectedTypeRestaurantRows.length" class="kitchen-non-cash-page__table-wrap">
                        <Table class="kitchen-non-cash-page__limits-table">
                            <thead>
                                <tr>
                                    <th>Ресторан</th>
                                    <th>Потреблено</th>
                                    <th>Количество</th>
                                    <th>Заказов</th>
                                    <th>Позиции</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="rest in selectedTypeRestaurantRows" :key="rest.restaurant_id">
                                    <td>{{ rest.restaurant_name || `#${rest.restaurant_id}` }}</td>
                                    <td>{{ formatMoney(rest.consumed_amount) }}</td>
                                    <td>{{ formatNumber(rest.consumed_qty) }}</td>
                                    <td>{{ formatNumber(rest.orders_count) }}</td>
                                    <td>{{ formatNumber(rest.items_count) }}</td>
                                </tr>
                            </tbody>
                        </Table>
                    </div>
                    <div v-else class="admin-page__empty">По выбранному типу нет затрат по ресторанам за период.</div>

                    <div class="kitchen-non-cash-page__add-limit">
                        <h5 class="kitchen-non-cash-page__add-title">Привязать сотрудника (опционально)</h5>
                        <div class="kitchen-non-cash-page__add-grid">
                            <Select
                                v-model="newLimit.user_id"
                                label="Сотрудник"
                                :options="userOptions"
                                searchable
                                search-placeholder="Начни вводить фамилию"
                                placeholder="Выберите сотрудника"
                            />
                            <Select
                                v-model="newLimit.period_type"
                                label="Период"
                                :options="periodOptions"
                                placeholder="Выберите период"
                            />
                            <Input
                                v-model="newLimit.limit_amount"
                                type="number"
                                label="Сумма лимита"
                                step="0.01"
                                placeholder="0.00"
                            />
                            <Input
                                v-model="newLimit.comment"
                                type="text"
                                label="Комментарий"
                                placeholder="Опционально"
                            />
                            <div class="kitchen-non-cash-page__add-actions">
                                <Checkbox v-model="newLimit.is_active" label="Активен" />
                                <Button
                                    :loading="creatingLimit"
                                    :disabled="creatingLimit || !canManage"
                                    @click="createLimitForSelectedType"
                                >
                                    Добавить
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <template #footer>
                <Button
                    :loading="selectedType ? savingNonCashId === selectedType.id : false"
                    :disabled="!canManage || !selectedType || savingNonCashId === selectedType.id"
                    @click="saveSelectedType"
                >
                    Сохранить карточку
                </Button>
                <Button color="ghost" @click="closeTypeCard">
                    Закрыть
                </Button>
            </template>
        </Modal>

        <Modal v-if="isCreateTypeOpen" @close="closeCreateTypeModal">
            <template #header>
                <div class="kitchen-non-cash-page__modal-header">
                    <h3 class="kitchen-non-cash-page__modal-title">Новый тип безнала</h3>
                    <p class="kitchen-non-cash-page__modal-subtitle">
                        Создание записи в справочнике для ручной настройки.
                    </p>
                </div>
            </template>

            <div class="kitchen-non-cash-page__create-grid">
                <Input
                    v-model="newType.id"
                    label="Код"
                    placeholder="Например: manual::no-payment"
                />
                <Input
                    v-model="newType.name"
                    label="Название"
                    placeholder="Например: Без оплаты"
                />
                <Select
                    v-model="newType.category"
                    label="Категория"
                    :options="categoryEditOptions"
                    placeholder="Не задано"
                />
                <Input
                    v-model="newType.comment"
                    label="Комментарий"
                    placeholder="Опционально"
                />
                <Checkbox
                    v-model="newType.is_active"
                    label="Активный тип"
                />
            </div>

            <template #footer>
                <Button color="ghost" :disabled="creatingType" @click="applyNoPaymentPreset">
                    Шаблон: Без оплаты
                </Button>
                <Button
                    :loading="creatingType"
                    :disabled="creatingType || !canManage"
                    @click="createNonCashType"
                >
                    Создать
                </Button>
                <Button color="ghost" :disabled="creatingType" @click="closeCreateTypeModal">
                    Закрыть
                </Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import {
    createKitchenNonCashType,
    deleteKitchenNonCashEmployeeLimit,
    fetchKitchenNonCashConsumption,
    fetchKitchenNonCashTypes,
    fetchKitchenRestaurants,
    fetchKitchenUsers,
    patchKitchenNonCashEmployeeLimit,
    patchKitchenNonCashType,
    putKitchenNonCashEmployeeLimits,
} from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Button from '@/components/UI-components/Button.vue';
import Table from '@/components/UI-components/Table.vue';
import Select from '@/components/UI-components/Select.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Modal from '@/components/UI-components/Modal.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import { formatNumberValue } from '@/utils/format';

const CATEGORY_OPTIONS = [
    { value: 'real_money', label: 'Реальные деньги' },
    { value: 'non_money', label: 'Неденежный' },
    { value: 'staff', label: 'Персонал' },
    { value: 'certificate', label: 'Сертификат' },
    { value: 'bonus', label: 'Бонус' },
    { value: 'other', label: 'Другое' },
];

const EMPTY_CATEGORY = '__empty__';

const PERIOD_OPTIONS = [
    { value: 'day', label: 'День' },
    { value: 'week', label: 'Неделя' },
    { value: 'month', label: 'Месяц' },
    { value: 'custom', label: 'Произвольный' },
];

const toast = useToast();
const userStore = useUserStore();

const loading = ref(false);
const loadingConsumption = ref(false);
const creatingLimit = ref(false);
const creatingType = ref(false);
const savingLimitId = ref('');
const deletingLimitId = ref('');
const savingNonCashId = ref('');
const isFiltersOpen = ref(true);
const isCreateTypeOpen = ref(false);

const restaurants = ref([]);
const users = ref([]);
const nonCashTypes = ref([]);
const limitRows = ref([]);
const unmappedRows = ref([]);
const typeRows = ref([]);
const openedLimitDetailsIds = ref([]);

const restaurantId = ref('');
const fromDate = ref(defaultMonthStart());
const toDate = ref(defaultToday());

const selectedTypeId = ref('');
const nonCashDrafts = reactive({});
const limitDrafts = reactive({});

const newLimit = reactive({
    user_id: '',
    period_type: 'month',
    limit_amount: '',
    comment: '',
    is_active: true,
});

const newType = reactive({
    id: '',
    name: '',
    category: EMPTY_CATEGORY,
    comment: '',
    is_active: true,
});

const canManage = computed(() => userStore.hasAnyPermission('iiko.manage'));
const restaurantOptions = computed(() => [
    { value: '', label: 'Все рестораны' },
    ...(restaurants.value || []).map((item) => ({ value: String(item.id), label: item.name })),
]);
const userOptions = computed(() =>
    (users.value || []).map((item) => ({ value: String(item.id), label: userDisplayName(item) })),
);
const periodOptions = computed(() => PERIOD_OPTIONS);
const categoryEditOptions = computed(() => [
    { value: EMPTY_CATEGORY, label: 'Не задано' },
    ...CATEGORY_OPTIONS,
]);
const categoryMap = computed(() => {
    const map = {};
    for (const option of CATEGORY_OPTIONS) {
        map[option.value] = option.label;
    }
    return map;
});

const selectedType = computed(() =>
    displayNonCashTypes.value.find((row) => row.id === selectedTypeId.value) || null,
);
const selectedTypeDraft = computed(() =>
    selectedType.value ? nonCashDrafts[selectedType.value.id] || {} : {},
);
const selectedTypeLimits = computed(() =>
    (limitRows.value || []).filter((row) => row.non_cash_type_id === selectedTypeId.value),
);
const limitsCountByType = computed(() => {
    const mapping = {};
    for (const row of limitRows.value || []) {
        const key = row?.non_cash_type_id;
        if (!key) {
            continue;
        }
        mapping[key] = (mapping[key] || 0) + 1;
    }
    return mapping;
});
const displayNonCashTypes = computed(() => {
    const map = new Map();
    for (const row of nonCashTypes.value || []) {
        if (!row?.id) {
            continue;
        }
        map.set(String(row.id), row);
    }
    for (const row of typeRows.value || []) {
        const key = String(row?.non_cash_type_id || '').trim();
        if (!key || map.has(key)) {
            continue;
        }
        map.set(key, {
            id: key,
            name: row?.non_cash_type_name || key,
            category: row?.category || null,
            is_active: row?.is_active !== false,
            comment: null,
        });
    }
    return Array.from(map.values()).sort((a, b) => {
        const left = String(a?.name || a?.id || '').toLowerCase();
        const right = String(b?.name || b?.id || '').toLowerCase();
        return left.localeCompare(right, 'ru');
    });
});
const typeStatsById = computed(() => {
    const mapping = {};
    for (const row of typeRows.value || []) {
        const key = row?.non_cash_type_id;
        if (!key || mapping[key]) {
            continue;
        }
        mapping[key] = {
            consumed_amount: Number(row?.consumed_amount || 0),
            orders_count: Number(row?.orders_count || 0),
            items_count: Number(row?.items_count || 0),
            by_restaurant: Array.isArray(row?.by_restaurant) ? row.by_restaurant : [],
        };
    }
    return mapping;
});
const totalConsumed = computed(() =>
    (typeRows.value || []).reduce((sum, row) => sum + Number(row?.consumed_amount || 0), 0),
);
const selectedTypeStats = computed(() => typeStatsById.value[selectedTypeId.value] || null);
const selectedTypeRestaurantRows = computed(() => selectedTypeStats.value?.by_restaurant || []);

function defaultToday() {
    return new Date().toISOString().slice(0, 10);
}

function defaultMonthStart() {
    const dt = new Date();
    dt.setDate(1);
    return dt.toISOString().slice(0, 10);
}

function normalizeNumeric(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

function formatMoney(value) {
    return formatNumberValue(value, {
        emptyValue: '-',
        invalidValue: '-',
        locale: 'ru-RU',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function formatNumber(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) {
        return '0';
    }
    return num.toLocaleString('ru-RU');
}

function formatCategory(value) {
    if (!value) {
        return '-';
    }
    return categoryMap.value[value] || value;
}

function userDisplayName(user) {
    const parts = [user?.last_name, user?.first_name, user?.middle_name]
        .map((part) => (part || '').trim())
        .filter(Boolean);
    if (parts.length) {
        return parts.join(' ');
    }
    return user?.username || `#${user?.id}`;
}

function getTypeStat(typeId, fieldName) {
    return Number(typeStatsById.value[typeId]?.[fieldName] || 0);
}

function getLimitDetailsId(row) {
    const value = String(row?.id || '').trim();
    return value || null;
}

function isLimitDetailsOpen(row) {
    const id = getLimitDetailsId(row);
    return Boolean(id && openedLimitDetailsIds.value.includes(id));
}

function toggleLimitDetails(row) {
    const id = getLimitDetailsId(row);
    if (!id) {
        return;
    }
    if (openedLimitDetailsIds.value.includes(id)) {
        openedLimitDetailsIds.value = openedLimitDetailsIds.value.filter((item) => item !== id);
        return;
    }
    openedLimitDetailsIds.value = [...openedLimitDetailsIds.value, id];
}

function syncOpenedLimitDetails() {
    const available = new Set(
        (limitRows.value || [])
            .map((row) => String(row?.id || '').trim())
            .filter(Boolean),
    );
    openedLimitDetailsIds.value = openedLimitDetailsIds.value.filter((value) => available.has(value));
}

function ensureNonCashDraft(row) {
    if (!row?.id) {
        return;
    }
    if (!nonCashDrafts[row.id]) {
        nonCashDrafts[row.id] = {
            category: EMPTY_CATEGORY,
            comment: '',
            is_active: true,
        };
    }
    nonCashDrafts[row.id].category = row.category || EMPTY_CATEGORY;
    nonCashDrafts[row.id].comment = row.comment || '';
    nonCashDrafts[row.id].is_active = Boolean(row.is_active);
}

function syncNonCashDrafts() {
    const activeIds = new Set((nonCashTypes.value || []).map((row) => row.id));
    for (const key of Object.keys(nonCashDrafts)) {
        if (!activeIds.has(key)) {
            delete nonCashDrafts[key];
        }
    }
    for (const row of nonCashTypes.value || []) {
        ensureNonCashDraft(row);
    }
}

function ensureLimitDraft(row) {
    if (!row?.id) {
        return;
    }
    if (!limitDrafts[row.id]) {
        limitDrafts[row.id] = {
            period_type: 'month',
            limit_amount: '',
            comment: '',
            is_active: true,
        };
    }
    limitDrafts[row.id].period_type = row.period_type || 'month';
    limitDrafts[row.id].limit_amount = row.limit_amount ?? '';
    limitDrafts[row.id].comment = row.comment || '';
    limitDrafts[row.id].is_active = Boolean(row.is_active);
}

function syncLimitDrafts() {
    const activeIds = new Set((limitRows.value || []).map((row) => row.id));
    for (const key of Object.keys(limitDrafts)) {
        if (!activeIds.has(key)) {
            delete limitDrafts[key];
        }
    }
    for (const row of limitRows.value || []) {
        ensureLimitDraft(row);
    }
}

function ensureValidDateRange() {
    if (!fromDate.value || !toDate.value) {
        toast.error('Выбери обе даты');
        return false;
    }
    if (fromDate.value > toDate.value) {
        toast.error('Дата "С" не может быть позже даты "По"');
        return false;
    }
    return true;
}

function resetNewLimitDraft() {
    newLimit.user_id = '';
    newLimit.period_type = 'month';
    newLimit.limit_amount = '';
    newLimit.comment = '';
    newLimit.is_active = true;
}

function resetNewTypeDraft() {
    newType.id = '';
    newType.name = '';
    newType.category = EMPTY_CATEGORY;
    newType.comment = '';
    newType.is_active = true;
}

function applyNoPaymentPreset() {
    newType.id = 'manual::no-payment';
    newType.name = 'Без оплаты';
    newType.category = 'non_money';
    if (!newType.comment) {
        newType.comment = 'Списание без фактической оплаты';
    }
    newType.is_active = true;
}

function openCreateTypeModal() {
    resetNewTypeDraft();
    isCreateTypeOpen.value = true;
}

function closeCreateTypeModal() {
    isCreateTypeOpen.value = false;
    creatingType.value = false;
    resetNewTypeDraft();
}

function openTypeCard(row) {
    if (!row?.id) {
        return;
    }
    selectedTypeId.value = row.id;
    openedLimitDetailsIds.value = [];
    ensureNonCashDraft(row);
    resetNewLimitDraft();
}

function closeTypeCard() {
    selectedTypeId.value = '';
    openedLimitDetailsIds.value = [];
    resetNewLimitDraft();
}

async function loadRestaurants() {
    const data = await fetchKitchenRestaurants();
    restaurants.value = Array.isArray(data) ? data : [];
}

async function loadUsers() {
    const data = await fetchKitchenUsers();
    users.value = Array.isArray(data) ? data : [];
}

async function loadNonCashTypes() {
    const data = await fetchKitchenNonCashTypes({ include_inactive: true });
    nonCashTypes.value = Array.isArray(data) ? data : [];
    syncNonCashDrafts();
}

async function loadConsumption() {
    if (!ensureValidDateRange()) {
        return;
    }
    loadingConsumption.value = true;
    try {
        const payload = await fetchKitchenNonCashConsumption({
            from_date: fromDate.value,
            to_date: toDate.value,
            restaurant_id: restaurantId.value || undefined,
            include_inactive_limits: true,
        });
        limitRows.value = Array.isArray(payload.items) ? payload.items : [];
        unmappedRows.value = Array.isArray(payload.unmapped) ? payload.unmapped : [];
        typeRows.value = Array.isArray(payload.types) ? payload.types : [];
        syncOpenedLimitDetails();
        syncLimitDrafts();
    } catch (error) {
        toast.error(`Ошибка загрузки потребления безнала: ${error.response?.data?.detail || error.message}`);
    } finally {
        loadingConsumption.value = false;
    }
}

async function reloadAll() {
    loading.value = true;
    try {
        await Promise.all([loadRestaurants(), loadUsers(), loadNonCashTypes()]);
        await loadConsumption();
    } catch (error) {
        toast.error(`Ошибка загрузки данных: ${error.response?.data?.detail || error.message}`);
    } finally {
        loading.value = false;
    }
}

async function createNonCashType() {
    if (!canManage.value) {
        return;
    }
    const id = String(newType.id || '').trim();
    const name = String(newType.name || '').trim();
    if (!id) {
        toast.error('Укажи код типа безнала');
        return;
    }
    if (!name) {
        toast.error('Укажи название типа безнала');
        return;
    }

    creatingType.value = true;
    try {
        await createKitchenNonCashType({
            id,
            name,
            category: newType.category === EMPTY_CATEGORY ? null : newType.category,
            comment: (newType.comment || '').trim() || null,
            is_active: Boolean(newType.is_active),
        });
        await loadNonCashTypes();
        await loadConsumption();
        const created = (nonCashTypes.value || []).find((item) => item.id === id);
        closeCreateTypeModal();
        if (created) {
            openTypeCard(created);
        }
        toast.success('Тип безнала создан');
    } catch (error) {
        toast.error(`Ошибка создания типа безнала: ${error.response?.data?.detail || error.message}`);
    } finally {
        creatingType.value = false;
    }
}

async function saveNonCashType(row) {
    if (!canManage.value || !row?.id) {
        return;
    }
    savingNonCashId.value = row.id;
    try {
        const draft = nonCashDrafts[row.id] || {};
        await patchKitchenNonCashType(row.id, {
            category: draft.category === EMPTY_CATEGORY ? null : draft.category,
            comment: draft.comment || null,
            is_active: Boolean(draft.is_active),
        });
        await loadNonCashTypes();
        toast.success('Карточка безнала сохранена');
    } catch (error) {
        toast.error(`Ошибка сохранения карточки: ${error.response?.data?.detail || error.message}`);
    } finally {
        savingNonCashId.value = '';
    }
}

async function saveSelectedType() {
    if (!selectedType.value) {
        return;
    }
    await saveNonCashType(selectedType.value);
}

async function createLimitForSelectedType() {
    if (!canManage.value) {
        return;
    }
    if (!selectedType.value?.id) {
        toast.error('Сначала открой карточку типа безнала');
        return;
    }
    if (!newLimit.user_id) {
        toast.error('Выбери сотрудника');
        return;
    }
    creatingLimit.value = true;
    try {
        await putKitchenNonCashEmployeeLimits({
            non_cash_type_id: String(selectedType.value.id),
            user_id: Number(newLimit.user_id),
            period_type: String(newLimit.period_type || 'month'),
            limit_amount: normalizeNumeric(newLimit.limit_amount),
            comment: newLimit.comment || null,
            is_active: Boolean(newLimit.is_active),
        });
        resetNewLimitDraft();
        await loadConsumption();
        toast.success('Лимит добавлен');
    } catch (error) {
        toast.error(`Ошибка сохранения лимита: ${error.response?.data?.detail || error.message}`);
    } finally {
        creatingLimit.value = false;
    }
}

async function saveLimit(row) {
    if (!canManage.value || !row?.id) {
        return;
    }
    savingLimitId.value = row.id;
    try {
        const draft = limitDrafts[row.id] || {};
        await patchKitchenNonCashEmployeeLimit(row.id, {
            period_type: draft.period_type || 'month',
            limit_amount: normalizeNumeric(draft.limit_amount),
            comment: draft.comment || null,
            is_active: Boolean(draft.is_active),
        });
        await loadConsumption();
        toast.success('Лимит обновлен');
    } catch (error) {
        toast.error(`Ошибка обновления лимита: ${error.response?.data?.detail || error.message}`);
    } finally {
        savingLimitId.value = '';
    }
}

async function deleteLimit(row) {
    if (!canManage.value || !row?.id) {
        return;
    }
    const confirmed = window.confirm('Удалить привязку лимита?');
    if (!confirmed) {
        return;
    }
    deletingLimitId.value = row.id;
    try {
        await deleteKitchenNonCashEmployeeLimit(row.id);
        await loadConsumption();
        toast.success('Лимит удален');
    } catch (error) {
        toast.error(`Ошибка удаления лимита: ${error.response?.data?.detail || error.message}`);
    } finally {
        deletingLimitId.value = '';
    }
}

reloadAll();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-non-cash-limits' as *;
</style>
