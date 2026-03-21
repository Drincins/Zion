<template>
    <div class="inventory-operations">
        <header class="inventory-operations__header">
            <div class="inventory-operations__header-main">
                <h1 class="inventory-operations__title">Движение товаров</h1>
                <p class="inventory-operations__subtitle">
                    Создавайте приход, перемещения и списания через учетную запись операции.
                </p>
            </div>

            <div class="inventory-operations__header-actions">
                <router-link :to="{ name: 'inventory-journal' }" class="inventory-operations__journal-link">
                    Журнал операций
                </router-link>
                <Button color="secondary" size="sm" :loading="loadingLookups || loadingOperations" @click="loadAllData">
                    Обновить
                </Button>
                <Button
                    v-if="canCreateMovement"
                    color="primary"
                    size="sm"
                    class="inventory-operations__add-button"
                    @click="openCreateModal"
                >
                    <BaseIcon name="Plus" class="inventory-operations__add-icon" />
                    <span>Добавить</span>
                </Button>
            </div>
        </header>

        <section class="inventory-operations__filters-panel">
            <button class="inventory-operations__filters-toggle" type="button" @click="toggleFilters">
                Фильтры
                <span :class="['inventory-operations__filters-icon', { 'is-open': isFiltersOpen }]">▼</span>
            </button>

            <div v-if="isFiltersOpen" class="inventory-operations__filters-content">
                <div class="inventory-operations__filters-controls">
                    <Input
                        v-model="tableSearchQuery"
                        class="inventory-operations__search"
                        placeholder="Поиск по товару, основанию или сотруднику"
                    />
                    <div class="inventory-operations__filter-types">
                        <button
                            v-for="option in operationTableFilterOptions"
                            :key="option.value"
                            type="button"
                            :class="[
                                'inventory-operations__filter-type-btn',
                                { 'is-active': tableTypeFilter === option.value }
                            ]"
                            @click="tableTypeFilter = option.value"
                        >
                            {{ option.label }}
                        </button>
                    </div>
                </div>

                <div class="inventory-operations__filters-meta">
                    <p class="inventory-operations__filters-summary">
                        Показано: <strong>{{ filteredOperations.length }}</strong> из {{ operations.length }}
                    </p>
                    <Button
                        v-if="tableSearchQuery || tableTypeFilter !== 'all'"
                        color="ghost"
                        size="sm"
                        @click="resetTableFilters"
                    >
                        Сбросить
                    </Button>
                </div>
            </div>
        </section>

        <section class="inventory-operations__table-card">
            <div class="inventory-operations__table-head">
                <h2 class="inventory-operations__table-title">Созданные операции</h2>
                <p class="inventory-operations__table-subtitle">
                    Записей: <strong>{{ filteredOperations.length }}</strong>
                </p>
            </div>

            <div v-if="loadingOperations" class="inventory-page__loading">Загрузка операций...</div>

            <div v-else-if="filteredOperations.length" class="inventory-operations__table-wrap">
                <Table>
                    <thead>
                        <tr>
                            <th>Дата (МСК)</th>
                            <th>Тип операции</th>
                            <th>Товар</th>
                            <th>Откуда</th>
                            <th>Куда</th>
                            <th>Кол-во</th>
                            <th>Основание</th>
                            <th>Кто создал</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="event in filteredOperations" :key="event.id">
                            <td>{{ formatDateTime(event.created_at) }}</td>
                            <td>
                                <span class="inventory-operations__badge" :class="actionClass(event.action_type)">
                                    {{ event.action_label }}
                                </span>
                            </td>
                            <td>
                                <div class="inventory-operations__item">
                                    <strong>{{ event.item_name || '—' }}</strong>
                                    <span>{{ event.item_code || '—' }}</span>
                                </div>
                            </td>
                            <td>{{ formatFrom(event) }}</td>
                            <td>{{ formatTo(event) }}</td>
                            <td>{{ formatQuantity(event) }}</td>
                            <td>{{ formatReason(event) }}</td>
                            <td>{{ event.actor_name || 'Система' }}</td>
                        </tr>
                    </tbody>
                </Table>
            </div>

            <p v-else class="inventory-page__empty">
                {{ operations.length ? 'По выбранным фильтрам операций не найдено.' : 'Операций пока нет.' }}
            </p>
        </section>

        <Modal v-if="isCreateModalOpen" @close="closeCreateModal">
            <template #header>
                <div class="inventory-operations__modal-header">
                    <h3 class="inventory-operations__modal-title">Новая операция</h3>
                    <p class="inventory-operations__modal-subtitle">
                        Запись фиксирует: что, сколько и откуда куда перемещается.
                    </p>
                </div>
            </template>

            <template #default>
                <div class="inventory-operations__modal-body">
                    <div class="inventory-operations__type-row">
                        <label class="inventory-operations__label">Тип операции</label>
                        <div class="inventory-operations__type-list">
                            <button
                                v-for="option in operationTypeOptions"
                                :key="option.value"
                                type="button"
                                :class="[
                                    'inventory-operations__type-btn',
                                    { 'is-active': operationType === option.value }
                                ]"
                                @click="operationType = option.value"
                            >
                                {{ option.label }}
                            </button>
                        </div>
                    </div>

                    <div class="inventory-operations__form-grid">
                        <Select
                            v-model="form.itemId"
                            label="Что перемещаем"
                            :options="itemOptions"
                            placeholder="Выберите товар"
                            searchable
                        />

                        <Input
                            v-model="form.quantity"
                            label="Сколько"
                            type="number"
                            min="1"
                            step="1"
                            placeholder="Например, 5"
                        />

                        <Select
                            v-if="isIncomeOperation"
                            v-model="form.toLocationId"
                            label="Куда зачислить"
                            :options="locationOptions"
                            placeholder="Выберите объект"
                            searchable
                        />

                        <Input
                            v-if="isIncomeOperation"
                            v-model="form.unitCost"
                            label="Цена за единицу (опционально)"
                            type="number"
                            min="0"
                            step="0.01"
                            placeholder="По умолчанию из карточки"
                        />

                        <Select
                            v-if="isTransferOperation || isWriteoffOperation"
                            v-model="form.fromLocationId"
                            label="Откуда"
                            :options="locationOptions"
                            placeholder="Выберите источник"
                            searchable
                        />

                        <Select
                            v-if="isTransferOperation"
                            v-model="form.toLocationId"
                            label="Куда"
                            :options="targetLocationOptions"
                            placeholder="Выберите получателя"
                            searchable
                        />

                        <Input
                            v-model="form.reason"
                            label="Почему / основание"
                            placeholder="Например: поставка, инвентаризация, внутренний перевод"
                        />
                    </div>

                    <p v-if="isTransferOperation || isWriteoffOperation" class="inventory-operations__stock-hint">
                        Доступно в источнике: <strong>{{ sourceLocationQuantity }}</strong> шт.
                    </p>
                    <p
                        v-else-if="isIncomeOperation && selectedToLocation && selectedItem"
                        class="inventory-operations__stock-hint"
                    >
                        Текущий остаток в точке зачисления: <strong>{{ targetLocationQuantity }}</strong> шт.
                    </p>

                    <section class="inventory-operations__record-card">
                        <h4 class="inventory-operations__record-title">Запись операции</h4>
                        <dl class="inventory-operations__record-grid">
                            <dt>Что</dt>
                            <dd>{{ draftRecord.what }}</dd>
                            <dt>Сколько</dt>
                            <dd>{{ draftRecord.quantity }}</dd>
                            <dt>Откуда</dt>
                            <dd>{{ draftRecord.from }}</dd>
                            <dt>Куда</dt>
                            <dd>{{ draftRecord.to }}</dd>
                            <dt>Как</dt>
                            <dd>{{ draftRecord.method }}</dd>
                            <dt>Почему</dt>
                            <dd>{{ draftRecord.reason }}</dd>
                        </dl>
                    </section>
                </div>
            </template>

            <template #footer>
                <div class="inventory-operations__modal-actions">
                    <Button color="ghost" size="sm" :disabled="submitting" @click="closeCreateModal">Отмена</Button>
                    <Button v-if="canCreateMovement" color="primary" size="sm" :loading="submitting" @click="submitOperation">
                        Сохранить операцию
                    </Button>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import { INVENTORY_MOVEMENTS_CREATE_PERMISSIONS } from '@/accessPolicy';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import { useUserStore } from '@/stores/user';
import { formatDateTimeValue } from '@/utils/format';
import {
    allocateInventoryItem,
    fetchInventoryDepartments,
    fetchInventoryItems,
    fetchInventoryMovements,
    transferInventoryItem,
    updateInventoryItemQuantity,
} from '@/api';

const OPERATION_TYPE_OPTIONS = [
    { value: 'income', label: 'Приход товаров' },
    { value: 'transfer', label: 'Перемещение между ресторанами' },
    { value: 'writeoff', label: 'Списание товаров' },
];

const OPERATION_ACTION_TYPES = ['quantity_increase', 'transfer', 'writeoff', 'quantity_adjusted'];
const OPERATION_TABLE_FILTER_OPTIONS = [
    { value: 'all', label: 'Все типы' },
    { value: 'quantity_increase', label: 'Приход' },
    { value: 'transfer', label: 'Перемещение' },
    { value: 'writeoff', label: 'Списание' },
    { value: 'quantity_adjusted', label: 'Корректировка' },
];

const toast = useToast();
const userStore = useUserStore();

const operationType = ref('income');
const operationTypeOptions = OPERATION_TYPE_OPTIONS;
const operationTableFilterOptions = OPERATION_TABLE_FILTER_OPTIONS;

const loadingLookups = ref(false);
const loadingOperations = ref(false);
const loadingSelectedItem = ref(false);
const submitting = ref(false);
const isCreateModalOpen = ref(false);
const isFiltersOpen = ref(true);
const tableSearchQuery = ref('');
const tableTypeFilter = ref('all');

const items = ref([]);
const departments = ref([]);
const operations = ref([]);
const selectedItemDetails = ref(null);

const form = reactive({
    itemId: '',
    quantity: '1',
    unitCost: '',
    fromLocationId: 'warehouse',
    toLocationId: '',
    reason: '',
});

const isIncomeOperation = computed(() => operationType.value === 'income');
const isTransferOperation = computed(() => operationType.value === 'transfer');
const isWriteoffOperation = computed(() => operationType.value === 'writeoff');

const itemOptions = computed(() =>
    [...items.value]
        .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }))
        .map((item) => ({
            value: String(item.id),
            label: `${item.code || `ITEM-${item.id}`} · ${item.name}`,
        })),
);

const selectedItemBase = computed(() => {
    const id = Number(form.itemId);
    if (!Number.isFinite(id)) {
        return null;
    }
    return items.value.find((item) => Number(item.id) === id) || null;
});

const selectedItem = computed(() => {
    const id = Number(form.itemId);
    if (!Number.isFinite(id)) {
        return null;
    }
    const details = selectedItemDetails.value;
    if (details && Number(details.id) === id) {
        return details;
    }
    return selectedItemBase.value;
});

const locationOptions = computed(() => {
    const available = departments.value
        .filter((option) => ['warehouse', 'restaurant'].includes(option.type))
        .map((option) => ({
            value: option.id,
            label: option.type === 'warehouse' ? 'Виртуальный склад' : option.label,
            kind: option.type,
            restaurantId: option.type === 'restaurant' ? Number(option.restaurant_id) : null,
        }));

    const warehouse = available.filter((option) => option.kind === 'warehouse');
    const restaurants = available
        .filter((option) => option.kind === 'restaurant')
        .sort((a, b) => String(a.label || '').localeCompare(String(b.label || ''), 'ru', { sensitivity: 'base' }));

    return [...warehouse, ...restaurants];
});

const locationMap = computed(() => {
    const map = new Map();
    for (const option of locationOptions.value) {
        map.set(option.value, option);
    }
    return map;
});

const targetLocationOptions = computed(() =>
    locationOptions.value.filter((option) => option.value !== form.fromLocationId),
);

const selectedFromLocation = computed(() => locationMap.value.get(form.fromLocationId) || null);
const selectedToLocation = computed(() => locationMap.value.get(form.toLocationId) || null);
const canCreateMovement = computed(() => userStore.hasAnyPermission(...INVENTORY_MOVEMENTS_CREATE_PERMISSIONS));

const sourceLocationQuantity = computed(() => getLocationQuantity(selectedItem.value, selectedFromLocation.value));
const targetLocationQuantity = computed(() => getLocationQuantity(selectedItem.value, selectedToLocation.value));
const filteredOperations = computed(() => {
    const needle = tableSearchQuery.value.trim().toLowerCase();
    return operations.value.filter((event) => {
        if (tableTypeFilter.value !== 'all' && event.action_type !== tableTypeFilter.value) {
            return false;
        }
        if (!needle) {
            return true;
        }

        const searchable = [
            event.item_name,
            event.item_code,
            event.from_location_name,
            event.to_location_name,
            event.comment,
            event.actor_name,
            event.action_label,
            event.action_type,
        ]
            .filter(Boolean)
            .join(' ')
            .toLowerCase();

        return searchable.includes(needle);
    });
});

const draftRecord = computed(() => {
    const quantity = parseQuantity(form.quantity);
    const selectedType = operationTypeOptions.find((option) => option.value === operationType.value);
    const defaultWhat = selectedItem.value
        ? `${selectedItem.value.code || `ITEM-${selectedItem.value.id}`} · ${selectedItem.value.name}`
        : '—';

    let fromValue = '—';
    let toValue = '—';

    if (isIncomeOperation.value) {
        fromValue = 'Поставка';
        toValue = selectedToLocation.value?.label || '—';
    }
    if (isTransferOperation.value) {
        fromValue = selectedFromLocation.value?.label || '—';
        toValue = selectedToLocation.value?.label || '—';
    }
    if (isWriteoffOperation.value) {
        fromValue = selectedFromLocation.value?.label || '—';
        toValue = 'Списание';
    }

    return {
        what: defaultWhat,
        quantity: Number.isFinite(quantity) ? `${quantity} шт.` : '—',
        from: fromValue,
        to: toValue,
        method: selectedType?.label || '—',
        reason: form.reason.trim() || '—',
    };
});

function toggleFilters() {
    isFiltersOpen.value = !isFiltersOpen.value;
}

function resetTableFilters() {
    tableSearchQuery.value = '';
    tableTypeFilter.value = 'all';
}

function parseQuantity(value) {
    const quantity = Number.parseInt(String(value || '0'), 10);
    if (!Number.isFinite(quantity) || quantity <= 0) {
        return null;
    }
    return quantity;
}

function parseUnitCost(value) {
    const normalized = String(value || '').replace(',', '.').trim();
    if (!normalized) {
        return null;
    }
    const amount = Number.parseFloat(normalized);
    if (!Number.isFinite(amount) || amount < 0) {
        return NaN;
    }
    return amount;
}

function getLocationQuantity(item, location) {
    if (!item || !location) {
        return 0;
    }
    const totals = Array.isArray(item.location_totals) ? item.location_totals : [];
    const matched = totals.find((row) => {
        if (row.location_kind !== location.kind) {
            return false;
        }
        if (location.kind === 'restaurant') {
            return Number(row.restaurant_id) === Number(location.restaurantId);
        }
        return true;
    });
    const quantity = Number(matched?.quantity || 0);
    return Number.isFinite(quantity) ? quantity : 0;
}

function getErrorMessage(error, fallback) {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
        return detail;
    }
    return fallback;
}

function ensureLocationDefaults() {
    if (!locationOptions.value.length) {
        form.fromLocationId = '';
        form.toLocationId = '';
        return;
    }

    if (!locationMap.value.has(form.fromLocationId)) {
        form.fromLocationId = locationOptions.value[0].value;
    }

    if (!locationMap.value.has(form.toLocationId)) {
        form.toLocationId = locationOptions.value[0].value;
    }

    if (form.toLocationId === form.fromLocationId) {
        const fallbackTarget = locationOptions.value.find((option) => option.value !== form.fromLocationId);
        if (fallbackTarget) {
            form.toLocationId = fallbackTarget.value;
        }
    }
}

function resetForm() {
    form.itemId = '';
    form.quantity = '1';
    form.unitCost = '';
    form.reason = '';
    ensureLocationDefaults();
}

function openCreateModal() {
    if (!canCreateMovement.value) {
        toast.error('Недостаточно прав для создания складских операций');
        return;
    }
    isCreateModalOpen.value = true;
    ensureLocationDefaults();
}

function closeCreateModal(force = false) {
    if (submitting.value && !force) {
        return;
    }
    isCreateModalOpen.value = false;
    operationType.value = 'income';
    resetForm();
}

function actionClass(actionType) {
    if (actionType === 'transfer') return 'is-transfer';
    if (actionType === 'writeoff') return 'is-writeoff';
    if (actionType === 'quantity_adjusted') return 'is-adjusted';
    return 'is-income';
}

function formatDateTime(value) {
    return formatDateTimeValue(value, {
        emptyValue: '—',
        invalidValue: '—',
        locale: 'ru-RU',
        timeZone: 'Europe/Moscow',
        options: {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        },
    });
}

function formatLocationName(locationKind, locationName, emptyValue = '—') {
    if (locationName) {
        return locationName;
    }
    if (locationKind === 'warehouse') {
        return 'Виртуальный склад';
    }
    if (locationKind === 'restaurant') {
        return 'Ресторан';
    }
    if (locationKind === 'subdivision') {
        return 'Подразделение';
    }
    return emptyValue;
}

function formatFrom(event) {
    if (event.action_type === 'quantity_increase') {
        return 'Поставка';
    }
    return formatLocationName(event.from_location_kind, event.from_location_name);
}

function formatTo(event) {
    if (event.action_type === 'writeoff') {
        return 'Списание';
    }
    return formatLocationName(event.to_location_kind, event.to_location_name);
}

function formatQuantity(event) {
    const raw = Number(event.quantity);
    if (!Number.isFinite(raw)) {
        return '—';
    }
    if (event.action_type === 'writeoff') {
        return raw > 0 ? `-${raw}` : `${raw}`;
    }
    if (raw > 0) {
        return `+${raw}`;
    }
    return `${raw}`;
}

function formatReason(event) {
    if (event.comment && String(event.comment).trim()) {
        return event.comment;
    }
    return '—';
}

async function loadLookups() {
    loadingLookups.value = true;
    try {
        const [itemData, departmentData] = await Promise.all([
            fetchInventoryItems({ include_locations: false }),
            fetchInventoryDepartments(),
        ]);
        items.value = Array.isArray(itemData) ? itemData : [];
        departments.value = Array.isArray(departmentData) ? departmentData : [];
        ensureLocationDefaults();
    } catch (error) {
        toast.error(getErrorMessage(error, 'Не удалось загрузить данные склада'));
        console.error(error);
    } finally {
        loadingLookups.value = false;
    }
}

let selectedItemRequestId = 0;

async function loadSelectedItemDetails(itemId) {
    const normalizedItemId = Number.parseInt(String(itemId || '0'), 10);
    selectedItemRequestId += 1;
    const requestId = selectedItemRequestId;

    if (!Number.isFinite(normalizedItemId) || normalizedItemId <= 0) {
        selectedItemDetails.value = null;
        loadingSelectedItem.value = false;
        return;
    }

    loadingSelectedItem.value = true;
    try {
        const data = await fetchInventoryItems({ item_ids: [normalizedItemId] });
        if (requestId !== selectedItemRequestId) {
            return;
        }
        const rows = Array.isArray(data) ? data : [];
        selectedItemDetails.value = rows.find((item) => Number(item.id) === normalizedItemId) || null;
    } catch (error) {
        if (requestId !== selectedItemRequestId) {
            return;
        }
        selectedItemDetails.value = selectedItemBase.value;
        console.error(error);
    } finally {
        if (requestId === selectedItemRequestId) {
            loadingSelectedItem.value = false;
        }
    }
}

async function loadOperations() {
    loadingOperations.value = true;
    try {
        const data = await fetchInventoryMovements({
            limit: 300,
            action_types: OPERATION_ACTION_TYPES,
        });
        const rows = Array.isArray(data) ? data : [];
        operations.value = [...rows].sort((a, b) => {
            const left = new Date(a.created_at || 0).getTime();
            const right = new Date(b.created_at || 0).getTime();
            return right - left;
        });
    } catch (error) {
        toast.error(getErrorMessage(error, 'Не удалось загрузить операции'));
        console.error(error);
    } finally {
        loadingOperations.value = false;
    }
}

async function loadAllData() {
    await Promise.all([loadLookups(), loadOperations()]);
}

async function submitIncome(itemId, quantity, reason) {
    const targetLocation = selectedToLocation.value;
    if (!targetLocation) {
        toast.error('Выберите куда зачислить товар');
        return false;
    }

    const payload = {
        location_kind: targetLocation.kind,
        quantity,
        comment: reason,
    };
    if (targetLocation.kind === 'restaurant') {
        payload.restaurant_id = targetLocation.restaurantId;
    }

    const unitCost = parseUnitCost(form.unitCost);
    if (Number.isNaN(unitCost)) {
        toast.error('Цена за единицу должна быть числом не меньше 0');
        return false;
    }
    if (unitCost !== null) {
        payload.unit_cost = unitCost;
    }

    await allocateInventoryItem(itemId, payload);
    return true;
}

async function submitTransfer(itemId, quantity, reason) {
    const sourceLocation = selectedFromLocation.value;
    const targetLocation = selectedToLocation.value;
    if (!sourceLocation) {
        toast.error('Выберите откуда перемещать товар');
        return false;
    }
    if (!targetLocation) {
        toast.error('Выберите куда перемещать товар');
        return false;
    }
    if (sourceLocation.value === targetLocation.value) {
        toast.error('Источник и получатель совпадают');
        return false;
    }

    if (quantity > sourceLocationQuantity.value) {
        toast.error('Недостаточно остатка в источнике');
        return false;
    }

    const payload = {
        source_kind: sourceLocation.kind,
        target_kind: targetLocation.kind,
        quantity,
        comment: reason,
    };
    if (sourceLocation.kind === 'restaurant') {
        payload.source_restaurant_id = sourceLocation.restaurantId;
    }
    if (targetLocation.kind === 'restaurant') {
        payload.restaurant_id = targetLocation.restaurantId;
    }

    await transferInventoryItem(itemId, payload);
    return true;
}

async function submitWriteoff(itemId, quantity, reason) {
    const sourceLocation = selectedFromLocation.value;
    if (!sourceLocation) {
        toast.error('Выберите откуда списать товар');
        return false;
    }

    if (quantity > sourceLocationQuantity.value) {
        toast.error('Недостаточно остатка для списания');
        return false;
    }

    const payload = {
        location_kind: sourceLocation.kind,
        quantity: sourceLocationQuantity.value - quantity,
        comment: reason,
    };
    if (sourceLocation.kind === 'restaurant') {
        payload.restaurant_id = sourceLocation.restaurantId;
    }

    await updateInventoryItemQuantity(itemId, payload);
    return true;
}

async function submitOperation() {
    if (!canCreateMovement.value) {
        toast.error('Недостаточно прав для создания складских операций');
        return;
    }
    if (submitting.value) {
        return;
    }

    const itemId = Number.parseInt(String(form.itemId || '0'), 10);
    if (!Number.isFinite(itemId) || itemId <= 0) {
        toast.error('Выберите товар');
        return;
    }

    await loadSelectedItemDetails(itemId);

    const quantity = parseQuantity(form.quantity);
    if (!quantity) {
        toast.error('Введите корректное количество');
        return;
    }

    const reason = form.reason.trim();
    if (!reason) {
        toast.error('Укажите причину операции');
        return;
    }

    submitting.value = true;
    try {
        let operationSaved = false;
        if (isIncomeOperation.value) {
            operationSaved = await submitIncome(itemId, quantity, reason);
        } else if (isTransferOperation.value) {
            operationSaved = await submitTransfer(itemId, quantity, reason);
        } else {
            operationSaved = await submitWriteoff(itemId, quantity, reason);
        }

        if (!operationSaved) {
            return;
        }

        toast.success('Операция сохранена');
        closeCreateModal(true);
        await Promise.all([loadLookups(), loadOperations()]);
    } catch (error) {
        toast.error(getErrorMessage(error, 'Не удалось создать операцию'));
        console.error(error);
    } finally {
        submitting.value = false;
    }
}

watch(locationOptions, ensureLocationDefaults, { immediate: true });

watch(
    () => form.itemId,
    async (value) => {
        await loadSelectedItemDetails(value);
    },
);

watch(operationType, () => {
    if (isTransferOperation.value && form.toLocationId === form.fromLocationId) {
        const fallbackTarget = targetLocationOptions.value[0];
        if (fallbackTarget) {
            form.toLocationId = fallbackTarget.value;
        }
    }
});

watch(
    () => form.fromLocationId,
    () => {
        if (isTransferOperation.value && form.toLocationId === form.fromLocationId) {
            const fallbackTarget = targetLocationOptions.value[0];
            if (fallbackTarget) {
                form.toLocationId = fallbackTarget.value;
            }
        }
    },
);

onMounted(async () => {
    await loadAllData();
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-operations' as *;
</style>
