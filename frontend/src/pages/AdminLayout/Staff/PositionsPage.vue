<template>
    <div class="user-info">
        <section id="positions" class="user-info__positions-card">
            <div class="user-info__positions-header">
                <h3 class="h3 user-info__card-title">Должности</h3>
                <Button
                    v-if="canManagePositions"
                    type="button"
                    size="sm"
                    :disabled="positionsLoading || rolesLoading || !roles.length"
                    @click="openCreatePositionModal"
                >
                    Создать должность
                </Button>
            </div>
            <div class="user-info__positions-toolbar">
                <Input
                    v-model="positionSearch"
                    class="user-info__positions-search"
                    placeholder="Поиск по должности"
                />
            </div>
            <div class="user-info__positions-list">
                <p v-if="positionsLoading" class="user-info__empty">Загрузка должностей...</p>
                <p v-else-if="!positions.length" class="user-info__empty">Должности не найдены.</p>
                <p v-else-if="!filteredPositions.length" class="user-info__empty">
                    {{ positionSearch ? 'Ничего не найдено.' : 'Должности не найдены.' }}
                </p>
                <div v-else class="user-info__table-wrapper">
                    <Table class="user-info__positions-table">
                        <thead>
                            <tr>
                                <th>
                                    <button
                                        class="user-info__sort-button"
                                        type="button"
                                        @click="toggleSort('name')"
                                    >
                                        <span>Должность</span>
                                        <span class="user-info__sort-icons">
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active': isSortedAsc('name'),
                                                }"
                                            >
                                                ▲
                                            </span>
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active': isSortedDesc('name'),
                                                }"
                                            >
                                                ▼
                                            </span>
                                        </span>
                                    </button>
                                </th>
                                <th>
                                    <button
                                        class="user-info__sort-button"
                                        type="button"
                                        @click="toggleSort('code')"
                                    >
                                        <span>Код</span>
                                        <span class="user-info__sort-icons">
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active': isSortedAsc('code'),
                                                }"
                                            >
                                                ▲
                                            </span>
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active': isSortedDesc('code'),
                                                }"
                                            >
                                                ▼
                                            </span>
                                        </span>
                                    </button>
                                </th>
                                <th>
                                    <button
                                        class="user-info__sort-button"
                                        type="button"
                                        @click="toggleSort('role')"
                                    >
                                        <span>Роль</span>
                                        <span class="user-info__sort-icons">
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active': isSortedAsc('role'),
                                                }"
                                            >
                                                ▲
                                            </span>
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active': isSortedDesc('role'),
                                                }"
                                            >
                                                ▼
                                            </span>
                                        </span>
                                    </button>
                                </th>
                                <th>
                                    <button
                                        class="user-info__sort-button"
                                        type="button"
                                        @click="toggleSort('subdivision')"
                                    >
                                        <span>Подразделение</span>
                                        <span class="user-info__sort-icons">
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active':
                                                        isSortedAsc('subdivision'),
                                                }"
                                            >
                                                ▲
                                            </span>
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active':
                                                        isSortedDesc('subdivision'),
                                                }"
                                            >
                                                ▼
                                            </span>
                                        </span>
                                    </button>
                                </th>
                                <th>
                                    <button
                                        class="user-info__sort-button"
                                        type="button"
                                        @click="toggleSort('rate')"
                                    >
                                        <span>Ставка</span>
                                        <span class="user-info__sort-icons">
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active': isSortedAsc('rate'),
                                                }"
                                            >
                                                ▲
                                            </span>
                                            <span
                                                class="user-info__sort-icon"
                                                :class="{
                                                    'user-info__sort-icon--active': isSortedDesc('rate'),
                                                }"
                                            >
                                                ▼
                                            </span>
                                        </span>
                                    </button>
                                </th>
                                <th class="user-info__positions-actions-header">Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr
                                v-for="position in sortedPositions"
                                :key="position.id"
                                class="user-info__positions-row"
                                @click="openEditPositionModal(position)"
                            >
                                <td>{{ position.name }}</td>
                                <td>{{ position.code || '-' }}</td>
                                <td>{{ position.role_name || 'Роль не назначена' }}</td>
                                <td>{{ getSubdivisionLabel(position) }}</td>
                                <td>{{ formatRate(position.rate) }}</td>
                                <td class="user-info__positions-actions">
                                    <button
                                        type="button"
                                        class="user-info__icon-button"
                                        :disabled="deletingPosition"
                                        title="Удалить"
                                        aria-label="Удалить"
                                        @click.stop="handleDeletePosition(position)"
                                    >
                                        <BaseIcon name="Trash" />
                                    </button>
                                </td>
                            </tr>
                        </tbody>
                    </Table>
                </div>
            </div>
        </section>

        <Modal v-if="isPositionModalOpen" @close="closePositionModal">
            <template #header>
                {{ editingPositionId ? 'Редактирование должности' : 'Новая должность' }}
            </template>
            <template #default>
                <form class="user-info__card-form" @submit.prevent="handleSavePosition">
                    <Input v-model="positionForm.name" label="Название должности" required />
                    <Input
                        v-model="positionForm.code"
                        label="Код должности (Айки)"
                        placeholder="Не задан"
                    />
                    <Input
                        v-model="positionForm.rate"
                        label="Ставка по умолчанию"
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="Не задано"
                    />
                    <Input
                        v-model="positionForm.hoursPerShift"
                        label="Часов в смене"
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="Не задано"
                    />
                    <Input
                        v-model="positionForm.monthlyShiftNorm"
                        label="Норма смен в месяц"
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="Не задано"
                    />
                    <Select
                        v-model="positionForm.roleId"
                        label="Роль"
                        :options="roleOptions"
                        :disabled="rolesLoading || !roleOptions.length"
                    />
                    <Select
                        v-model="positionForm.parentId"
                        label="Родительская должность"
                        :options="positionParentOptions"
                    />
                    <Select
                        v-model="positionForm.paymentFormatId"
                        label="Формат оплаты"
                        :options="paymentFormatOptions"
                        :disabled="paymentFormatsLoading"
                    />
                    <Checkbox
                        v-model="positionForm.nightBonusEnabled"
                        label="Учитывать ночные часы"
                    />
                    <Input
                        v-model="positionForm.nightBonusPercent"
                        label="Ночная надбавка, %"
                        type="number"
                        step="0.01"
                        min="0"
                        :disabled="!positionForm.nightBonusEnabled"
                        placeholder="0"
                    />
                    <Select
                        v-model="positionForm.restaurantSubdivisionId"
                        label="Подразделение ресторана"
                        :options="restaurantSubdivisionOptions"
                        :disabled="restaurantSubdivisionsLoading"
                    />
                </form>
            </template>
            <template #footer>
                <Button
                    v-if="editingPositionId && canManagePositionChangeOrders"
                    type="button"
                    color="secondary"
                    @click="openPositionChangeOrderModal"
                >
                    Изменение с даты
                </Button>
                <Button
                    v-if="canManagePositions"
                    type="button"
                    :loading="positionModalSaving"
                    @click="handleSavePosition"
                >
                    Сохранить
                </Button>
                <Button type="button" color="secondary" @click="closePositionModal">
                    Отмена
                </Button>
            </template>
        </Modal>

        <PositionChangeOrderModal
            v-if="isPositionChangeOrderModalOpen"
            :is-open="isPositionChangeOrderModalOpen"
            :position-name="editingPositionName"
            :form="positionChangeOrderForm"
            :orders="positionChangeOrders"
            :loading="positionChangeOrdersLoading"
            :error="positionChangeOrdersError"
            :saving="positionChangeOrderSaving"
            :cancelling-id="cancellingPositionChangeOrderId"
            @close="closePositionChangeOrderModal"
            @submit="handleCreatePositionChangeOrder"
            @cancel-order="handleCancelPositionChangeOrder"
            @update-field="updatePositionChangeOrderField"
        />
    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import {
    createAccessPosition,
    createPositionChangeOrder,
    cancelPositionChangeOrder,
    deleteAccessPosition,
    fetchAccessPositions,
    fetchAccessRoles,
    fetchPositionChangeOrders,
    fetchPaymentFormats,
    fetchRestaurantSubdivisions,
    fetchRoles,
    updateAccessPosition,
} from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Input from '@/components/UI-components/Input.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Button from '@/components/UI-components/Button.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import { extractApiErrorMessage } from '@/utils/apiErrors';
import { POSITIONS_CHANGE_ORDERS_MANAGE_PERMISSIONS } from '@/accessPolicy';
import PositionChangeOrderModal from './components/PositionChangeOrderModal.vue';

const userStore = useUserStore();
const toast = useToast();

const canViewRoles = computed(() => userStore.hasAnyPermission('roles.manage', 'system.admin'));
const canManagePositions = computed(() =>
    userStore.hasAnyPermission('positions.manage', 'system.admin'),
);
const canManagePositionChangeOrders = computed(() =>
    userStore.hasAnyPermission(...POSITIONS_CHANGE_ORDERS_MANAGE_PERMISSIONS),
);

const positions = ref([]);
const positionsLoading = ref(false);
const roles = ref([]);
const rolesLoading = ref(false);
const paymentFormats = ref([]);
const paymentFormatsLoading = ref(false);
const restaurantSubdivisions = ref([]);
const restaurantSubdivisionsLoading = ref(false);
const positionSearch = ref('');

const isPositionModalOpen = ref(false);
const editingPositionId = ref(null);
const positionModalSaving = ref(false);
const deletingPosition = ref(false);
const isPositionChangeOrderModalOpen = ref(false);
const positionChangeOrders = ref([]);
const positionChangeOrdersLoading = ref(false);
const positionChangeOrdersError = ref('');
const positionChangeOrderSaving = ref(false);
const cancellingPositionChangeOrderId = ref(null);
const positionForm = reactive({
    name: '',
    code: '',
    roleId: '',
    parentId: '',
    rate: '',
    hoursPerShift: '',
    monthlyShiftNorm: '',
    paymentFormatId: '',
    restaurantSubdivisionId: '',
    nightBonusEnabled: false,
    nightBonusPercent: '',
});
const positionChangeOrderForm = reactive({
    effectiveDate: formatTodayDate(),
    rateNew: '',
    applyToAttendances: false,
    comment: '',
});

const sortBy = ref('');
const sortDirection = ref('asc');

const filteredPositions = computed(() => {
    const list = Array.isArray(positions.value) ? positions.value : [];
    const query = positionSearch.value.trim().toLocaleLowerCase('ru-RU');
    if (!query) {
        return list;
    }
    return list.filter((position) =>
        String(position?.name ?? '').toLocaleLowerCase('ru-RU').includes(query),
    );
});

const sortedPositions = computed(() => {
    const list = Array.isArray(filteredPositions.value) ? [...filteredPositions.value] : [];
    if (!sortBy.value) {
        return list;
    }
    const direction = sortDirection.value === 'desc' ? -1 : 1;
    return list.sort((a, b) => {
        const comparison = comparePositionValues(a, b, sortBy.value);
        if (comparison !== 0) {
            return comparison * direction;
        }
        const nameComparison = compareNullable(a?.name, b?.name);
        if (nameComparison !== 0) {
            return nameComparison;
        }
        return compareNullable(a?.id, b?.id, { numeric: true });
    });
});

const isSortedAsc = (columnKey) => sortBy.value === columnKey && sortDirection.value === 'asc';
const isSortedDesc = (columnKey) => sortBy.value === columnKey && sortDirection.value === 'desc';

const toggleSort = (columnKey) => {
    if (sortBy.value === columnKey) {
        sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
        return;
    }
    sortBy.value = columnKey;
    sortDirection.value = 'asc';
};

const sortedRoles = computed(() => {
    const list = Array.isArray(roles.value) ? [...roles.value] : [];
    return list.sort((a, b) => {
        const levelA = typeof a.level === 'number' ? a.level : 0;
        const levelB = typeof b.level === 'number' ? b.level : 0;
        if (levelA !== levelB) {
            return levelA - levelB;
        }
        return a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' });
    });
});

const roleOptions = computed(() =>
    sortedRoles.value.map((role) => ({
        value: String(role.id),
        label: role.name,
    })),
);

const paymentFormatOptions = computed(() => {
    const options = paymentFormats.value.map((format) => ({
        value: String(format.id),
        label: format.name,
    }));
    return [{ value: '', label: 'Не выбрано' }, ...options];
});

const restaurantSubdivisionOptions = computed(() => {
    const options = restaurantSubdivisions.value.map((item) => ({
        value: String(item.id),
        label: item.name,
    }));
    return [{ value: '', label: 'Не выбрано' }, ...options];
});

const restaurantSubdivisionMap = computed(() => {
    const map = {};
    for (const item of restaurantSubdivisions.value) {
        const itemId = item?.id;
        if (itemId !== null && itemId !== undefined) {
            map[item.id] = item;
        }
    }
    return map;
});

const editingPositionName = computed(() => {
    const current = positions.value.find((item) => item.id === editingPositionId.value);
    return current?.name || '';
});

const positionParentOptions = computed(() => {
    const base = [
        {
            value: '',
            label: 'Без родителя',
        },
    ];

    if (!positions.value.length) {
        return base;
    }

    return base.concat(
        positions.value
            .filter((position) => position.id !== editingPositionId.value)
            .map((position) => ({
                value: String(position.id),
                label: position.name,
            })),
    );
});

function resetPositionForm() {
    positionForm.name = '';
    positionForm.code = '';
    positionForm.roleId = '';
    positionForm.parentId = '';
    positionForm.rate = '';
    positionForm.hoursPerShift = '';
    positionForm.monthlyShiftNorm = '';
    positionForm.paymentFormatId = '';
    positionForm.restaurantSubdivisionId = '';
    positionForm.nightBonusEnabled = false;
    positionForm.nightBonusPercent = '';
}

function formatTodayDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function resetPositionChangeOrderForm() {
    positionChangeOrderForm.effectiveDate = formatTodayDate();
    positionChangeOrderForm.rateNew = '';
    positionChangeOrderForm.applyToAttendances = false;
    positionChangeOrderForm.comment = '';
}

function openCreatePositionModal() {
    resetPositionForm();
    if (roles.value.length) {
        positionForm.roleId = String(roles.value[0].id);
    }
    editingPositionId.value = null;
    isPositionModalOpen.value = true;
}

function openEditPositionModal(position) {
    if (!position) return;
    editingPositionId.value = position.id;
    positionForm.name = position.name ?? '';
    positionForm.code = position.code ?? '';
    positionForm.roleId =
        position.role_id !== null && position.role_id !== undefined ? String(position.role_id) : '';
    positionForm.parentId =
        position.parent_id !== null && position.parent_id !== undefined
            ? String(position.parent_id)
            : '';
    positionForm.paymentFormatId =
        position.payment_format_id !== null && position.payment_format_id !== undefined
            ? String(position.payment_format_id)
            : '';
    positionForm.restaurantSubdivisionId =
        position.restaurant_subdivision_id !== null && position.restaurant_subdivision_id !== undefined
            ? String(position.restaurant_subdivision_id)
            : '';
    positionForm.rate =
        position.rate !== null && position.rate !== undefined && position.rate !== ''
            ? String(position.rate)
            : '';
    positionForm.hoursPerShift =
        position.hours_per_shift !== null && position.hours_per_shift !== undefined && position.hours_per_shift !== ''
            ? String(position.hours_per_shift)
            : '';
    positionForm.monthlyShiftNorm =
        position.monthly_shift_norm !== null &&
        position.monthly_shift_norm !== undefined &&
        position.monthly_shift_norm !== ''
            ? String(position.monthly_shift_norm)
            : '';
    positionForm.nightBonusEnabled = Boolean(position.night_bonus_enabled);
    positionForm.nightBonusPercent =
        position.night_bonus_percent !== null && position.night_bonus_percent !== undefined
            ? String(position.night_bonus_percent)
            : '';
    isPositionModalOpen.value = true;
}

function closePositionModal() {
    isPositionModalOpen.value = false;
    positionModalSaving.value = false;
    editingPositionId.value = null;
    resetPositionForm();
    closePositionChangeOrderModal();
}

function updatePositionChangeOrderField(payload) {
    const field = payload?.field;
    if (!field || !Object.prototype.hasOwnProperty.call(positionChangeOrderForm, field)) {
        return;
    }
    positionChangeOrderForm[field] = payload.value;
}

async function loadPositionChangeOrders() {
    if (!editingPositionId.value || !canManagePositionChangeOrders.value) {
        positionChangeOrders.value = [];
        positionChangeOrdersError.value = '';
        return;
    }
    positionChangeOrdersLoading.value = true;
    positionChangeOrdersError.value = '';
    try {
        const data = await fetchPositionChangeOrders(editingPositionId.value);
        positionChangeOrders.value = Array.isArray(data?.items) ? data.items : [];
    } catch (error) {
        positionChangeOrders.value = [];
        positionChangeOrdersError.value = extractApiErrorMessage(
            error,
            'Не удалось загрузить кадровые изменения должности',
        );
        console.error(error);
    } finally {
        positionChangeOrdersLoading.value = false;
    }
}

async function openPositionChangeOrderModal() {
    if (!editingPositionId.value || !canManagePositionChangeOrders.value) {
        return;
    }
    resetPositionChangeOrderForm();
    positionChangeOrderForm.rateNew =
        positionForm.rate !== '' && positionForm.rate !== null && positionForm.rate !== undefined
            ? String(positionForm.rate)
            : '';
    isPositionChangeOrderModalOpen.value = true;
    await loadPositionChangeOrders();
}

function closePositionChangeOrderModal() {
    isPositionChangeOrderModalOpen.value = false;
    positionChangeOrderSaving.value = false;
    positionChangeOrdersError.value = '';
    positionChangeOrders.value = [];
    cancellingPositionChangeOrderId.value = null;
    resetPositionChangeOrderForm();
}

async function handleCreatePositionChangeOrder() {
    if (!editingPositionId.value || !canManagePositionChangeOrders.value) {
        return;
    }
    if (!positionChangeOrderForm.effectiveDate) {
        toast.error('Укажите дату вступления в силу');
        return;
    }

    const parsedRate = Number.parseFloat(String(positionChangeOrderForm.rateNew).replace(',', '.'));
    if (!Number.isFinite(parsedRate) || parsedRate < 0) {
        toast.error('Укажите корректную новую ставку');
        return;
    }

    positionChangeOrderSaving.value = true;
    try {
        await createPositionChangeOrder(editingPositionId.value, {
            effective_date: positionChangeOrderForm.effectiveDate,
            rate_new: parsedRate,
            apply_to_attendances: Boolean(positionChangeOrderForm.applyToAttendances),
            comment: positionChangeOrderForm.comment.trim() || null,
        });
        toast.success('Кадровое изменение должности сохранено');
        if (positionChangeOrderForm.effectiveDate === formatTodayDate()) {
            positionForm.rate = String(parsedRate);
        }
        await Promise.all([loadPositionChangeOrders(), loadPositions()]);
        closePositionChangeOrderModal();
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось сохранить кадровое изменение должности'));
        console.error(error);
    } finally {
        positionChangeOrderSaving.value = false;
    }
}

async function handleCancelPositionChangeOrder(orderId) {
    if (!editingPositionId.value || !orderId || !canManagePositionChangeOrders.value) {
        return;
    }
    cancellingPositionChangeOrderId.value = orderId;
    try {
        await cancelPositionChangeOrder(editingPositionId.value, orderId);
        toast.success('Кадровое изменение должности отменено');
        await loadPositionChangeOrders();
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось отменить кадровое изменение должности'));
        console.error(error);
    } finally {
        cancellingPositionChangeOrderId.value = null;
    }
}

function resolveSubdivisionName(subdivisionId) {
    if (!subdivisionId) {
        return '-';
    }
    const subdivision = restaurantSubdivisionMap.value[subdivisionId];
    return subdivision ? subdivision.name : `ID ${subdivisionId}`;
}

function getSubdivisionLabel(position) {
    if (!position) {
        return '-';
    }
    if (position.restaurant_subdivision_name) {
        return position.restaurant_subdivision_name;
    }
    return resolveSubdivisionName(position.restaurant_subdivision_id);
}

function compareNullable(aValue, bValue, { numeric = false } = {}) {
    const aMissing = aValue === null || aValue === undefined || aValue === '';
    const bMissing = bValue === null || bValue === undefined || bValue === '';
    if (aMissing && bMissing) {
        return 0;
    }
    if (aMissing) {
        return 1;
    }
    if (bMissing) {
        return -1;
    }
    if (numeric) {
        const aNumber = Number(aValue);
        const bNumber = Number(bValue);
        const aValid = Number.isFinite(aNumber);
        const bValid = Number.isFinite(bNumber);
        if (!aValid && !bValid) {
            return 0;
        }
        if (!aValid) {
            return 1;
        }
        if (!bValid) {
            return -1;
        }
        if (aNumber === bNumber) {
            return 0;
        }
        return aNumber > bNumber ? 1 : -1;
    }
    return String(aValue).localeCompare(String(bValue), 'ru', { sensitivity: 'base', numeric: true });
}

function getSubdivisionSortValue(position) {
    const label = getSubdivisionLabel(position);
    if (label === '-') {
        return null;
    }
    return label;
}

function comparePositionValues(a, b, sortKey) {
    switch (sortKey) {
        case 'name':
            return compareNullable(a?.name, b?.name);
        case 'code':
            return compareNullable(a?.code, b?.code);
        case 'role':
            return compareNullable(a?.role_name, b?.role_name);
        case 'subdivision':
            return compareNullable(getSubdivisionSortValue(a), getSubdivisionSortValue(b));
        case 'rate':
            return compareNullable(a?.rate, b?.rate, { numeric: true });
        default:
            return 0;
    }
}

function formatRate(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
        return value;
    }
    return numericValue.toLocaleString('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

async function loadPositions() {
    positionsLoading.value = true;
    try {
        const data = await fetchAccessPositions();
        positions.value = Array.isArray(data) ? data : [];
    } catch (error) {
        positions.value = [];
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить должности'));
        console.error(error);
    } finally {
        positionsLoading.value = false;
    }
}

async function loadRoles() {
    if (!canViewRoles.value) {
        roles.value = [];
        return;
    }
    rolesLoading.value = true;
    try {
        const data = await fetchAccessRoles();
        roles.value = Array.isArray(data) ? data : [];
    } catch (error) {
        if (error?.response?.status === 403) {
            try {
                const fallbackData = await fetchRoles();
                roles.value = Array.isArray(fallbackData) ? fallbackData : [];
            } catch (fallbackError) {
                roles.value = [];
                if (fallbackError?.response?.status !== 403) {
                    toast.error('Не удалось загрузить роли');
                    console.error(fallbackError);
                }
            }
        } else {
            roles.value = [];
            toast.error(extractApiErrorMessage(error, 'Не удалось загрузить роли'));
            console.error(error);
        }
    } finally {
        rolesLoading.value = false;
    }
}

async function loadPaymentFormats() {
    paymentFormatsLoading.value = true;
    try {
        const data = await fetchPaymentFormats();
        paymentFormats.value = Array.isArray(data) ? data : [];
    } catch (error) {
        if (error?.response?.status === 403) {
            paymentFormats.value = [];
        } else {
            toast.error('Не удалось загрузить форматы оплаты');
            console.error(error);
        }
    } finally {
        paymentFormatsLoading.value = false;
    }
}

async function loadRestaurantSubdivisions() {
    if (!canManagePositions.value) {
        restaurantSubdivisions.value = [];
        return;
    }
    restaurantSubdivisionsLoading.value = true;
    try {
        const data = await fetchRestaurantSubdivisions();
        restaurantSubdivisions.value = Array.isArray(data) ? data : [];
    } catch (error) {
        if (error?.response?.status === 403) {
            restaurantSubdivisions.value = [];
        } else {
            toast.error('Не удалось загрузить подразделения ресторана');
            console.error(error);
        }
    } finally {
        restaurantSubdivisionsLoading.value = false;
    }
}

async function handleSavePosition() {
    const trimmedName = positionForm.name.trim();
    if (!trimmedName) {
        toast.error('Введите название должности');
        return;
    }
    if (!positionForm.roleId) {
        toast.error('Выберите роль для должности');
        return;
    }

    const roleId = Number(positionForm.roleId);
    if (!Number.isInteger(roleId) || roleId <= 0) {
        toast.error('Некорректная роль для должности');
        return;
    }

    let parentId = null;
    if (positionForm.parentId) {
        const parsedParent = Number(positionForm.parentId);
        if (!Number.isInteger(parsedParent) || parsedParent <= 0) {
            toast.error('Некорректная родительская должность');
            return;
        }
        parentId = parsedParent;
    }

    let rate = null;
    if (positionForm.rate !== '' && positionForm.rate !== null && positionForm.rate !== undefined) {
        const parsedRate = Number.parseFloat(String(positionForm.rate).replace(',', '.'));
        if (!Number.isFinite(parsedRate) || parsedRate < 0) {
            toast.error('Некорректная ставка');
            return;
        }
        rate = parsedRate;
    }

    let hoursPerShift = null;
    if (
        positionForm.hoursPerShift !== '' &&
        positionForm.hoursPerShift !== null &&
        positionForm.hoursPerShift !== undefined
    ) {
        const parsed = Number.parseFloat(String(positionForm.hoursPerShift).replace(',', '.'));
        if (!Number.isFinite(parsed) || parsed <= 0) {
            toast.error('Некорректное значение часов в смене');
            return;
        }
        hoursPerShift = parsed;
    }

    let monthlyShiftNorm = null;
    if (
        positionForm.monthlyShiftNorm !== '' &&
        positionForm.monthlyShiftNorm !== null &&
        positionForm.monthlyShiftNorm !== undefined
    ) {
        const parsed = Number.parseFloat(String(positionForm.monthlyShiftNorm).replace(',', '.'));
        if (!Number.isFinite(parsed) || parsed <= 0) {
            toast.error('Некорректная норма смен в месяц');
            return;
        }
        monthlyShiftNorm = parsed;
    }

    let paymentFormatId = null;
    if (positionForm.paymentFormatId) {
        const parsedFormat = Number(positionForm.paymentFormatId);
        if (!Number.isInteger(parsedFormat) || parsedFormat <= 0) {
            toast.error('Некорректный формат оплаты');
            return;
        }
        paymentFormatId = parsedFormat;
    }

    let restaurantSubdivisionId = null;
    if (positionForm.restaurantSubdivisionId) {
        const parsedSubdivision = Number(positionForm.restaurantSubdivisionId);
        if (!Number.isInteger(parsedSubdivision) || parsedSubdivision <= 0) {
            toast.error('Некорректное подразделение');
            return;
        }
        restaurantSubdivisionId = parsedSubdivision;
    }

    const nightBonusEnabled = Boolean(positionForm.nightBonusEnabled);
    let nightBonusPercent = null;
    if (
        positionForm.nightBonusPercent !== '' &&
        positionForm.nightBonusPercent !== null &&
        positionForm.nightBonusPercent !== undefined
    ) {
        const parsedNightBonus = Number.parseFloat(
            String(positionForm.nightBonusPercent).replace(',', '.'),
        );
        if (!Number.isFinite(parsedNightBonus) || parsedNightBonus < 0) {
            toast.error('Некорректная ночная надбавка');
            return;
        }
        nightBonusPercent = parsedNightBonus;
    }

    const payload = {
        name: trimmedName,
        code: positionForm.code.trim() || null,
        role_id: roleId,
        parent_id: parentId,
        rate,
        hours_per_shift: hoursPerShift,
        monthly_shift_norm: monthlyShiftNorm,
        payment_format_id: paymentFormatId,
        restaurant_subdivision_id: restaurantSubdivisionId,
        night_bonus_enabled: nightBonusEnabled,
        night_bonus_percent: nightBonusEnabled ? nightBonusPercent ?? 0 : 0,
    };

    positionModalSaving.value = true;
    try {
        if (editingPositionId.value) {
            await updateAccessPosition(editingPositionId.value, payload);
            toast.success('Должность обновлена');
        } else {
            await createAccessPosition(payload);
            toast.success('Должность создана');
        }

        await loadPositions();
        closePositionModal();
    } catch (error) {
        toast.error(
            extractApiErrorMessage(
                error,
                editingPositionId.value
                    ? 'Не удалось обновить должность'
                    : 'Не удалось создать должность',
            ),
        );
        console.error(error);
    } finally {
        positionModalSaving.value = false;
    }
}

async function handleDeletePosition(position) {
    if (!position) {
        return;
    }

    if (!confirm(`Удалить должность "${position.name}"?`)) {
        return;
    }

    deletingPosition.value = true;
    try {
        await deleteAccessPosition(position.id);
        toast.success(`Должность "${position.name}" удалена`);
        await loadPositions();
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось удалить должность'));
        console.error(error);
    } finally {
        deletingPosition.value = false;
    }
}

onMounted(() => {
    loadRoles();
    loadPaymentFormats();
    loadPositions();
    loadRestaurantSubdivisions();
});

watch(
    () => canViewRoles.value,
    (canView) => {
        if (!canView) {
            roles.value = [];
            return;
        }
        loadRoles();
    },
);

watch(
    () => canManagePositions.value,
    (canManage) => {
        if (!canManage) {
            restaurantSubdivisions.value = [];
            return;
        }
        loadRestaurantSubdivisions();
    },
);
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/user-info.scss' as *;
</style>
