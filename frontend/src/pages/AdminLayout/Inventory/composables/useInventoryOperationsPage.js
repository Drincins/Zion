import { computed, onMounted, ref } from 'vue';
import { useToast } from 'vue-toastification';

import { INVENTORY_MOVEMENTS_CREATE_PERMISSIONS } from '@/accessPolicy';
import { useUserStore } from '@/stores/user';
import { formatDateTimeValue } from '@/utils/format';
import { useInventoryOperationsRuntime } from './useInventoryOperationsRuntime';
import {
    fetchInventoryDepartments,
    fetchInventoryItems,
    fetchInventoryMovements,
} from '@/api';

const OPERATION_ACTION_TYPES = ['quantity_increase', 'transfer', 'writeoff', 'quantity_adjusted'];
const OPERATION_TABLE_FILTER_OPTIONS = [
    { value: 'all', label: 'Все типы' },
    { value: 'quantity_increase', label: 'Приход' },
    { value: 'transfer', label: 'Перемещение' },
    { value: 'writeoff', label: 'Списание' },
    { value: 'quantity_adjusted', label: 'Корректировка' },
];

export function useInventoryOperationsPage() {
    const toast = useToast();
    const userStore = useUserStore();

    const operationTableFilterOptions = OPERATION_TABLE_FILTER_OPTIONS;

    const loadingLookups = ref(false);
    const loadingOperations = ref(false);
    const isFiltersOpen = ref(true);
    const tableSearchQuery = ref('');
    const tableTypeFilter = ref('all');

    const items = ref([]);
    const departments = ref([]);
    const operations = ref([]);
    const canCreateMovement = computed(() => userStore.hasAnyPermission(...INVENTORY_MOVEMENTS_CREATE_PERMISSIONS));
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

    function toggleFilters() {
        isFiltersOpen.value = !isFiltersOpen.value;
    }

    function resetTableFilters() {
        tableSearchQuery.value = '';
        tableTypeFilter.value = 'all';
    }

    function getErrorMessage(error, fallback) {
        const detail = error?.response?.data?.detail;
        if (typeof detail === 'string' && detail.trim()) {
            return detail;
        }
        return fallback;
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
        } catch (error) {
            toast.error(getErrorMessage(error, 'Не удалось загрузить данные склада'));
            console.error(error);
        } finally {
            loadingLookups.value = false;
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

    const {
        closeCreateModal,
        draftRecord,
        form,
        isCreateModalOpen,
        isIncomeOperation,
        isTransferOperation,
        isWriteoffOperation,
        itemOptions,
        locationOptions,
        openCreateModal,
        operationType,
        operationTypeOptions,
        selectedItem,
        selectedToLocation,
        sourceLocationQuantity,
        submitOperation,
        submitting,
        targetLocationOptions,
        targetLocationQuantity,
    } = useInventoryOperationsRuntime({
        canCreateMovement,
        departments,
        getErrorMessage,
        items,
        loadLookups,
        loadOperations,
    });

    onMounted(async () => {
        await loadAllData();
    });

    return {
        operationType,
        operationTypeOptions,
        operationTableFilterOptions,
        loadingLookups,
        loadingOperations,
        submitting,
        isCreateModalOpen,
        isFiltersOpen,
        tableSearchQuery,
        tableTypeFilter,
        operations,
        form,
        isIncomeOperation,
        isTransferOperation,
        isWriteoffOperation,
        itemOptions,
        selectedItem,
        locationOptions,
        targetLocationOptions,
        selectedToLocation,
        canCreateMovement,
        sourceLocationQuantity,
        targetLocationQuantity,
        filteredOperations,
        draftRecord,
        toggleFilters,
        resetTableFilters,
        openCreateModal,
        closeCreateModal,
        actionClass,
        formatDateTime,
        formatLocationName,
        formatFrom,
        formatTo,
        formatQuantity,
        formatReason,
        loadLookups,
        loadOperations,
        loadAllData,
        submitOperation,
    };
}
