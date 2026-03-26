import { reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';

import { transferInventoryItem, updateInventoryItemQuantity } from '@/api';

export function useInventoryItemsMovements({
    canCreateMovement,
    departmentOptions,
    hasLoadedByFilters,
    loadItemsByFilters,
    parseNumber,
    saving,
}) {
    const toast = useToast();

    const isTransferModalOpen = ref(false);
    const transferForm = reactive({
        itemId: null,
        itemCode: '',
        sourceOptionId: '',
        targetOptionId: '',
        quantity: '1',
    });
    const quantityForm = reactive({
        value: '',
    });
    const previewPhotoItem = ref(null);
    const detailItemEntry = ref(null);

    function openItemPhoto(item) {
        previewPhotoItem.value = item;
    }

    function closeItemPhoto() {
        previewPhotoItem.value = null;
    }

    function openItemDetail(entry) {
        detailItemEntry.value = entry;
        quantityForm.value = String(entry?.quantity ?? 0);
    }

    function closeItemDetail() {
        detailItemEntry.value = null;
        quantityForm.value = '';
    }

    function buildQuantityPayload(entry, nextQuantity, comment) {
        const payload = {
            location_kind: entry.locationKind,
            quantity: nextQuantity,
            comment,
        };
        const locationUnitCost = parseNumber(entry?.locationAvgCost ?? entry?.item?.cost);
        if (!Number.isNaN(locationUnitCost)) {
            payload.unit_cost = locationUnitCost;
        }
        if (entry.locationKind === 'restaurant') {
            payload.restaurant_id = Number(entry.locationRestaurantId);
        }
        if (entry.locationKind === 'subdivision') {
            payload.subdivision_id = Number(entry.locationSubdivisionId);
        }
        return payload;
    }

    async function handleUpdateQuantityFromDetail() {
        if (!canCreateMovement.value) {
            toast.error('Недостаточно прав для изменения количества');
            return;
        }
        if (!detailItemEntry.value?.item?.id) {
            return;
        }
        const nextQuantity = Number.parseInt(String(quantityForm.value || '0'), 10);
        if (!Number.isFinite(nextQuantity) || nextQuantity < 0) {
            toast.error('Введите корректное количество (0 или больше)');
            return;
        }
        const currentQuantity = Number(detailItemEntry.value.quantity || 0);
        if (nextQuantity === currentQuantity) {
            toast.info('Количество не изменилось');
            return;
        }
        if (nextQuantity === 0) {
            const confirmed = window.confirm('Вы действительно хотите списать товар?');
            if (!confirmed) {
                return;
            }
        }

        saving.value = true;
        try {
            await updateInventoryItemQuantity(
                detailItemEntry.value.item.id,
                buildQuantityPayload(
                    detailItemEntry.value,
                    nextQuantity,
                    'Изменение количества через карточку товара',
                ),
            );
            toast.success(nextQuantity === 0 ? 'Товар списан из подразделения' : 'Количество обновлено');
            if (hasLoadedByFilters.value) {
                await loadItemsByFilters();
            }
            closeItemDetail();
        } catch (error) {
            toast.error(error?.response?.data?.detail || 'Не удалось изменить количество');
            console.error(error);
        } finally {
            saving.value = false;
        }
    }

    function buildLocationOptionId(locationKind, restaurantId, subdivisionId) {
        if (locationKind === 'warehouse') {
            return 'warehouse';
        }
        if (locationKind === 'restaurant' && restaurantId) {
            return `restaurant:${restaurantId}`;
        }
        if (locationKind === 'subdivision' && subdivisionId) {
            return `subdivision:${subdivisionId}`;
        }
        return '';
    }

    function openTransferModal(entry) {
        if (!canCreateMovement.value) {
            toast.error('Недостаточно прав для перевода товара');
            return;
        }
        const item = entry?.item || null;
        if (!item?.id) {
            return;
        }
        transferForm.itemId = item.id;
        transferForm.itemCode = `${item.code} · ${item.name}`;
        transferForm.sourceOptionId = buildLocationOptionId(
            entry.locationKind,
            entry.locationRestaurantId,
            entry.locationSubdivisionId,
        );
        transferForm.targetOptionId = '';
        transferForm.quantity = '1';
        isTransferModalOpen.value = true;
    }

    function closeTransferModal() {
        isTransferModalOpen.value = false;
        transferForm.itemId = null;
        transferForm.itemCode = '';
        transferForm.sourceOptionId = '';
        transferForm.targetOptionId = '';
        transferForm.quantity = '1';
    }

    async function submitTransfer() {
        if (!canCreateMovement.value) {
            toast.error('Недостаточно прав для перевода товара');
            return;
        }
        if (!transferForm.itemId) {
            return;
        }
        const sourceOption = departmentOptions.value.find((option) => option.id === transferForm.sourceOptionId);
        if (!sourceOption || !['warehouse', 'restaurant', 'subdivision'].includes(sourceOption.type)) {
            toast.error('Выберите откуда переводим товар');
            return;
        }
        const targetOption = departmentOptions.value.find((option) => option.id === transferForm.targetOptionId);
        if (!targetOption || !['warehouse', 'restaurant'].includes(targetOption.type)) {
            toast.error('Выберите ресторан или виртуальный склад');
            return;
        }
        if (sourceOption.id === targetOption.id) {
            toast.error('Источник и получатель совпадают');
            return;
        }
        const quantity = Number.parseInt(String(transferForm.quantity || '0'), 10);
        if (!Number.isFinite(quantity) || quantity <= 0) {
            toast.error('Введите корректное количество');
            return;
        }

        const payload = {
            source_kind: sourceOption.type,
            target_kind: targetOption.type,
            quantity,
        };
        if (sourceOption.type === 'restaurant') {
            payload.source_restaurant_id = Number(sourceOption.restaurant_id);
        }
        if (sourceOption.type === 'subdivision') {
            payload.source_subdivision_id = Number(sourceOption.subdivision_id);
        }
        if (targetOption.type === 'restaurant') {
            payload.restaurant_id = Number(targetOption.restaurant_id);
        }

        saving.value = true;
        try {
            await transferInventoryItem(transferForm.itemId, payload);
            toast.success('Товар переведен');
            closeTransferModal();
            if (hasLoadedByFilters.value) {
                await loadItemsByFilters();
            }
        } catch (error) {
            toast.error(error?.response?.data?.detail || 'Не удалось перевести товар');
            console.error(error);
        } finally {
            saving.value = false;
        }
    }

    return {
        buildLocationOptionId,
        buildQuantityPayload,
        closeItemDetail,
        closeItemPhoto,
        closeTransferModal,
        detailItemEntry,
        handleUpdateQuantityFromDetail,
        isTransferModalOpen,
        openItemDetail,
        openItemPhoto,
        openTransferModal,
        previewPhotoItem,
        quantityForm,
        submitTransfer,
        transferForm,
    };
}
