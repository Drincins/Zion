import { computed, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';

import {
    allocateInventoryItem,
    fetchInventoryItems,
    transferInventoryItem,
    updateInventoryItemQuantity,
} from '@/api';

const OPERATION_TYPE_OPTIONS = [
    { value: 'income', label: 'Приход' },
    { value: 'transfer', label: 'Перемещение' },
    { value: 'writeoff', label: 'Списание' },
];

export function useInventoryBalanceOperations({
    catalogItems,
    getRestaurantLocation,
    isItemCardModalOpen,
    loadDetailCard,
    loadRestaurantItems,
    restaurants,
    selectedRestaurantId,
    selectedRestaurantIdNum,
    selectedRestaurantName,
    selectedStoragePlaceIdNum,
    storagePlaces,
}) {
    const toast = useToast();

    const isOperationModalOpen = ref(false);
    const operationSubmitting = ref(false);
    const operationType = ref('income');
    const operationForm = reactive({
        itemId: '',
        quantity: '1',
        unitCost: '',
        sourceStoragePlaceId: 'none',
        targetRestaurantId: '',
        targetStoragePlaceId: 'none',
        reason: '',
    });
    const selectedOperationItemDetails = ref(null);
    const operationItemLoading = ref(false);
    let operationItemRequestId = 0;

    const operationTypeOptions = OPERATION_TYPE_OPTIONS;
    const isIncomeOperation = computed(() => operationType.value === 'income');
    const isTransferOperation = computed(() => operationType.value === 'transfer');
    const isWriteoffOperation = computed(() => operationType.value === 'writeoff');

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

    function parseStoragePlaceValue(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    }

    function buildStoragePlaceOptionsForRestaurant(restaurantId, { includeAll = false } = {}) {
        const options = [];
        if (includeAll) {
            options.push({ value: 'all', label: 'Все места хранения' });
        }
        options.push({ value: 'none', label: 'Без места хранения' });
        storagePlaces.value
            .filter((place) => Boolean(place?.is_active) && Number(place?.restaurant_id) === Number(restaurantId))
            .sort((a, b) => String(a?.name || '').localeCompare(String(b?.name || ''), 'ru', { sensitivity: 'base' }))
            .forEach((place) => {
                options.push({ value: String(place.id), label: place.name });
            });
        return options;
    }

    const selectedOperationItem = computed(() => {
        const itemId = Number(operationForm.itemId);
        if (!Number.isFinite(itemId) || itemId <= 0) {
            return null;
        }
        if (selectedOperationItemDetails.value && Number(selectedOperationItemDetails.value.id) === itemId) {
            return selectedOperationItemDetails.value;
        }
        return catalogItems.value.find((item) => Number(item.id) === itemId) || null;
    });

    const operationItemOptions = computed(() =>
        [...catalogItems.value]
            .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }))
            .map((item) => ({
                value: String(item.id),
                label: `${item.code || `ITEM-${item.id}`} · ${item.name}`,
            })),
    );

    const sourceStoragePlaceOptions = computed(() =>
        buildStoragePlaceOptionsForRestaurant(selectedRestaurantIdNum.value),
    );

    const targetStoragePlaceOptions = computed(() => {
        const targetRestaurantId = isTransferOperation.value
            ? Number(operationForm.targetRestaurantId || 0)
            : Number(selectedRestaurantIdNum.value || 0);
        return buildStoragePlaceOptionsForRestaurant(targetRestaurantId || null);
    });

    const sourceLocationQuantity = computed(() => {
        const storagePlaceId = parseStoragePlaceValue(operationForm.sourceStoragePlaceId);
        return Number(getRestaurantLocation(selectedOperationItem.value, selectedRestaurantIdNum.value, storagePlaceId)?.quantity || 0);
    });

    const operationTargetStoragePlaceLabel = computed(() => {
        const restaurantId = isTransferOperation.value
            ? Number(operationForm.targetRestaurantId || 0)
            : Number(selectedRestaurantIdNum.value || 0);
        const option = buildStoragePlaceOptionsForRestaurant(restaurantId).find(
            (entry) => String(entry.value) === String(operationForm.targetStoragePlaceId),
        );
        return option?.label || 'Без места хранения';
    });

    const operationDraftRecord = computed(() => {
        const quantity = parseQuantity(operationForm.quantity);
        const selectedType = operationTypeOptions.find((option) => option.value === operationType.value);
        const defaultWhat = selectedOperationItem.value
            ? `${selectedOperationItem.value.code || `ITEM-${selectedOperationItem.value.id}`} · ${selectedOperationItem.value.name}`
            : '—';
        const sourceLabel =
            sourceStoragePlaceOptions.value.find((entry) => String(entry.value) === String(operationForm.sourceStoragePlaceId))?.label || '—';
        const targetRestaurantLabel =
            restaurants.value.find((entry) => Number(entry.id) === Number(operationForm.targetRestaurantId || 0))?.name || selectedRestaurantName.value;

        let fromValue = '—';
        let toValue = '—';

        if (isIncomeOperation.value) {
            fromValue = 'Поставка';
            toValue = `${selectedRestaurantName.value} · ${operationTargetStoragePlaceLabel.value}`;
        } else if (isTransferOperation.value) {
            fromValue = `${selectedRestaurantName.value} · ${sourceLabel}`;
            toValue = `${targetRestaurantLabel} · ${operationTargetStoragePlaceLabel.value}`;
        } else if (isWriteoffOperation.value) {
            fromValue = `${selectedRestaurantName.value} · ${sourceLabel}`;
            toValue = 'Списание';
        }

        return {
            what: defaultWhat,
            quantity: Number.isFinite(quantity) ? `${quantity} шт.` : '—',
            from: fromValue,
            to: toValue,
            method: selectedType?.label || '—',
            reason: String(operationForm.reason || '').trim() || '—',
        };
    });

    function resetOperationForm() {
        const defaultStoragePlace = selectedStoragePlaceIdNum.value ? String(selectedStoragePlaceIdNum.value) : 'none';
        operationForm.itemId = '';
        operationForm.quantity = '1';
        operationForm.unitCost = '';
        operationForm.sourceStoragePlaceId = defaultStoragePlace;
        operationForm.targetRestaurantId = selectedRestaurantId.value || '';
        operationForm.targetStoragePlaceId = defaultStoragePlace;
        operationForm.reason = '';
        selectedOperationItemDetails.value = null;
    }

    function openOperationModal() {
        if (!selectedRestaurantIdNum.value) {
            toast.warning('Сначала выбери ресторан');
            return;
        }
        resetOperationForm();
        isOperationModalOpen.value = true;
    }

    function closeOperationModal() {
        if (operationSubmitting.value) {
            return;
        }
        isOperationModalOpen.value = false;
        operationType.value = 'income';
        resetOperationForm();
    }

    async function loadSelectedOperationItemDetails(itemId) {
        const normalizedItemId = Number.parseInt(String(itemId || '0'), 10);
        const restaurantId = selectedRestaurantIdNum.value;
        operationItemRequestId += 1;
        const requestId = operationItemRequestId;

        if (!Number.isFinite(normalizedItemId) || normalizedItemId <= 0 || !restaurantId) {
            selectedOperationItemDetails.value = null;
            operationItemLoading.value = false;
            return;
        }

        operationItemLoading.value = true;
        try {
            const restaurantIds = [restaurantId];
            const targetRestaurantId = Number(operationForm.targetRestaurantId || 0);
            if (isTransferOperation.value && Number.isFinite(targetRestaurantId) && targetRestaurantId > 0 && !restaurantIds.includes(targetRestaurantId)) {
                restaurantIds.push(targetRestaurantId);
            }
            const data = await fetchInventoryItems({
                item_ids: [normalizedItemId],
                restaurant_ids: restaurantIds,
            });
            if (requestId !== operationItemRequestId) {
                return;
            }
            const rows = Array.isArray(data) ? data : [];
            selectedOperationItemDetails.value = rows.find((item) => Number(item.id) === normalizedItemId) || null;
        } catch (error) {
            if (requestId !== operationItemRequestId) {
                return;
            }
            selectedOperationItemDetails.value = catalogItems.value.find((item) => Number(item.id) === normalizedItemId) || null;
            console.error(error);
        } finally {
            if (requestId === operationItemRequestId) {
                operationItemLoading.value = false;
            }
        }
    }

    async function submitOperation() {
        if (operationSubmitting.value) {
            return;
        }
        const restaurantId = selectedRestaurantIdNum.value;
        const itemId = Number.parseInt(String(operationForm.itemId || '0'), 10);
        const quantity = parseQuantity(operationForm.quantity);
        const reason = String(operationForm.reason || '').trim();

        if (!restaurantId) {
            toast.warning('Сначала выбери ресторан');
            return;
        }
        if (!Number.isFinite(itemId) || itemId <= 0) {
            toast.warning('Выбери товар');
            return;
        }
        if (!quantity) {
            toast.warning('Укажи корректное количество');
            return;
        }
        if (!reason) {
            toast.warning('Добавь комментарий или основание');
            return;
        }

        operationSubmitting.value = true;
        try {
            if (isIncomeOperation.value) {
                const unitCost = parseUnitCost(operationForm.unitCost);
                if (Number.isNaN(unitCost)) {
                    toast.warning('Цена за единицу должна быть числом не меньше 0');
                    return;
                }
                await allocateInventoryItem(itemId, {
                    location_kind: 'restaurant',
                    restaurant_id: restaurantId,
                    storage_place_id: parseStoragePlaceValue(operationForm.targetStoragePlaceId) ?? undefined,
                    quantity,
                    unit_cost: unitCost ?? undefined,
                    comment: reason,
                });
            } else if (isTransferOperation.value) {
                const targetRestaurantId = Number(operationForm.targetRestaurantId || 0);
                if (!Number.isFinite(targetRestaurantId) || targetRestaurantId <= 0) {
                    toast.warning('Выбери ресторан получателя');
                    return;
                }
                if (quantity > sourceLocationQuantity.value) {
                    toast.warning('Недостаточно остатка в источнике');
                    return;
                }
                await transferInventoryItem(itemId, {
                    source_kind: 'restaurant',
                    source_restaurant_id: restaurantId,
                    source_storage_place_id: parseStoragePlaceValue(operationForm.sourceStoragePlaceId) ?? undefined,
                    target_kind: 'restaurant',
                    restaurant_id: targetRestaurantId,
                    storage_place_id: parseStoragePlaceValue(operationForm.targetStoragePlaceId) ?? undefined,
                    quantity,
                    comment: reason,
                });
            } else {
                if (quantity > sourceLocationQuantity.value) {
                    toast.warning('Недостаточно остатка для списания');
                    return;
                }
                await updateInventoryItemQuantity(itemId, {
                    location_kind: 'restaurant',
                    restaurant_id: restaurantId,
                    storage_place_id: parseStoragePlaceValue(operationForm.sourceStoragePlaceId) ?? undefined,
                    quantity: Math.max(sourceLocationQuantity.value - quantity, 0),
                    comment: reason,
                });
            }

            toast.success('Операция сохранена');
            closeOperationModal();
            await loadRestaurantItems();
            if (isItemCardModalOpen.value) {
                await loadDetailCard();
            }
        } catch (error) {
            toast.error(error?.response?.data?.detail || 'Не удалось сохранить операцию');
            console.error(error);
        } finally {
            operationSubmitting.value = false;
        }
    }

    watch(
        () => operationForm.itemId,
        async (value) => {
            await loadSelectedOperationItemDetails(value);
        },
    );

    watch(
        [() => operationType.value, () => operationForm.targetRestaurantId],
        async () => {
            if (isOperationModalOpen.value && operationForm.itemId) {
                await loadSelectedOperationItemDetails(operationForm.itemId);
            }
        },
    );

    return {
        closeOperationModal,
        isIncomeOperation,
        isOperationModalOpen,
        isTransferOperation,
        isWriteoffOperation,
        openOperationModal,
        operationDraftRecord,
        operationForm,
        operationItemLoading,
        operationItemOptions,
        operationSubmitting,
        operationTargetStoragePlaceLabel,
        operationType,
        operationTypeOptions,
        resetOperationForm,
        selectedOperationItem,
        sourceLocationQuantity,
        sourceStoragePlaceOptions,
        submitOperation,
        targetStoragePlaceOptions,
    };
}
