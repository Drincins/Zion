import { computed, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';

import {
    allocateInventoryItem,
    fetchInventoryItems,
    transferInventoryItem,
    updateInventoryItemQuantity,
} from '@/api';

const OPERATION_TYPE_OPTIONS = [
    { value: 'income', label: 'Приход товаров' },
    { value: 'transfer', label: 'Перемещение между ресторанами' },
    { value: 'writeoff', label: 'Списание товаров' },
];

export function useInventoryOperationsRuntime({
    canCreateMovement,
    departments,
    getErrorMessage,
    items,
    loadLookups,
    loadOperations,
}) {
    const toast = useToast();

    const operationType = ref('income');
    const loadingSelectedItem = ref(false);
    const submitting = ref(false);
    const isCreateModalOpen = ref(false);
    const selectedItemDetails = ref(null);

    const form = reactive({
        itemId: '',
        quantity: '1',
        unitCost: '',
        fromLocationId: 'warehouse',
        toLocationId: '',
        reason: '',
    });

    const operationTypeOptions = OPERATION_TYPE_OPTIONS;
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
    const sourceLocationQuantity = computed(() => getLocationQuantity(selectedItem.value, selectedFromLocation.value));
    const targetLocationQuantity = computed(() => getLocationQuantity(selectedItem.value, selectedToLocation.value));

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

    return {
        closeCreateModal,
        draftRecord,
        form,
        isCreateModalOpen,
        isIncomeOperation,
        isTransferOperation,
        isWriteoffOperation,
        itemOptions,
        loadingSelectedItem,
        locationMap,
        locationOptions,
        openCreateModal,
        operationType,
        operationTypeOptions,
        parseQuantity,
        selectedFromLocation,
        selectedItem,
        selectedItemBase,
        selectedItemDetails,
        selectedToLocation,
        sourceLocationQuantity,
        submitOperation,
        targetLocationOptions,
        targetLocationQuantity,
        submitting,
    };
}
