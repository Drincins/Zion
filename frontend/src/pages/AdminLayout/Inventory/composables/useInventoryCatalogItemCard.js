import { computed, ref } from 'vue';
import { useToast } from 'vue-toastification';

import { fetchInventoryMovements, updateInventoryItem, uploadInventoryItemPhoto } from '@/api';
import { formatDateTimeValue } from '@/utils/format';

const ITEM_CARD_CHANGE_ACTIONS = ['item_created', 'item_updated', 'cost_changed'];
const ITEM_CARD_FIELD_LABELS = Object.freeze({
    code: 'Код',
    name: 'Название',
    group_id: 'Группа',
    category_id: 'Категория',
    kind_id: 'Вид',
    cost: 'Стоимость',
    default_cost: 'Себестоимость',
    photo_url: 'Фото',
    note: 'Описание',
    manufacturer: 'Производитель',
    storage_conditions: 'Условия хранения',
    use_instance_codes: 'Индивидуальные коды единиц',
    is_active: 'Статус карточки',
});

export const ITEM_CARD_TABS = [
    { value: 'info', label: 'Информация' },
    { value: 'changes', label: 'Журнал изменений' },
    { value: 'availability', label: 'Наличие по ресторанам' },
];

export function useInventoryCatalogItemCard({
    canEditNomenclature,
    formatMoney,
    getCatalogCategoryName,
    getCatalogGroupName,
    getCatalogPathByType,
    isCatalogModalOpen,
    isItemModalOpen,
    itemForm,
    items,
    loadItems,
    openItemDetail,
    parseNumber,
    resetItemForm,
    restaurants,
    seedModalPickerTree,
    setItemFormFromItem,
    typeMap,
    uploadingPhoto,
    saving,
}) {
    const toast = useToast();

    const isItemCardOpen = ref(false);
    const itemCardActiveTab = ref('info');
    const itemCardChangesLoading = ref(false);
    const itemCardChangesError = ref('');
    const itemCardChanges = ref([]);
    const previewPhotoItem = ref(null);
    const previewPhotoInputRef = ref(null);
    const isPreviewPhotoEditable = ref(false);
    const itemCardPhotoPreviewOverride = ref(null);

    const itemCardItem = computed(() => {
        const id = Number(itemForm.id);
        if (!Number.isFinite(id) || id <= 0) {
            return null;
        }
        return items.value.find((item) => Number(item.id) === id) || null;
    });

    const itemCardPhotoUrl = computed(() => {
        if (itemCardPhotoPreviewOverride.value !== null) {
            return String(itemCardPhotoPreviewOverride.value || '');
        }
        return String(itemCardItem.value?.photo_url || '');
    });

    const previewPhotoUrl = computed(() => {
        if (!previewPhotoItem.value) {
            return '';
        }
        if (isPreviewPhotoEditable.value) {
            return itemCardPhotoUrl.value;
        }
        return String(previewPhotoItem.value.photo_url || '');
    });

    const canDeletePreviewPhoto = computed(() => Boolean(itemForm.photoUrl || previewPhotoUrl.value));

    const sortedRestaurants = computed(() =>
        [...restaurants.value].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' })),
    );

    const itemCardRestaurantRows = computed(() => {
        const totals = Array.isArray(itemCardItem.value?.location_totals) ? itemCardItem.value.location_totals : [];
        const restaurantTotals = totals.filter((row) => row.location_kind === 'restaurant');
        const totalsByRestaurant = new Map(
            restaurantTotals
                .filter((row) => Number.isFinite(Number(row.restaurant_id)))
                .map((row) => [
                    Number(row.restaurant_id),
                    {
                        quantity: Number(row.quantity || 0),
                        avgCost: row.avg_cost === null || row.avg_cost === undefined ? null : Number(row.avg_cost),
                        locationName: row.location_name,
                        lastArrivalAt: row.last_arrival_at || null,
                    },
                ]),
        );

        if (!sortedRestaurants.value.length) {
            return restaurantTotals
                .map((row) => ({
                    restaurantId: Number(row.restaurant_id || 0),
                    restaurantName: row.location_name || `Ресторан #${row.restaurant_id}`,
                    quantity: Number(row.quantity || 0),
                    avgCost: row.avg_cost === null || row.avg_cost === undefined ? null : Number(row.avg_cost),
                    lastArrivalAt: row.last_arrival_at || null,
                }))
                .sort((a, b) => String(a.restaurantName || '').localeCompare(String(b.restaurantName || ''), 'ru', { sensitivity: 'base' }));
        }

        return sortedRestaurants.value.map((restaurant) => {
            const total = totalsByRestaurant.get(Number(restaurant.id));
            return {
                restaurantId: Number(restaurant.id),
                restaurantName: restaurant.name,
                quantity: Number(total?.quantity || 0),
                avgCost: total?.avgCost ?? null,
                lastArrivalAt: total?.lastArrivalAt ?? null,
            };
        });
    });

    const itemCardTotalQuantity = computed(() => Number(itemCardItem.value?.total_quantity || 0));
    const itemCardWarehouseQuantity = computed(() => Number(itemCardItem.value?.warehouse_quantity || 0));
    const itemCardRestaurantsQuantity = computed(() =>
        itemCardRestaurantRows.value.reduce((sum, row) => sum + Number(row.quantity || 0), 0),
    );

    function formatItemCardChangeDate(value) {
        return formatDateTimeValue(value, {
            emptyValue: '—',
            invalidValue: '—',
            locale: 'ru-RU',
            options: {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            },
        });
    }

    function formatItemCardChangeField(field, actionType) {
        if (actionType === 'item_created') {
            return 'Создание карточки';
        }
        return ITEM_CARD_FIELD_LABELS[field] || field || 'Поле';
    }

    function formatItemCardChangeValue(field, value) {
        if (value === null || value === undefined || value === '') {
            return '—';
        }
        if (field === 'cost' || field === 'default_cost') {
            return formatMoney(value);
        }
        if (field === 'photo_url') {
            return value ? 'Фото загружено' : 'Фото удалено';
        }
        if (field === 'use_instance_codes') {
            return ['true', '1', 'yes'].includes(String(value).toLowerCase()) ? 'Включено' : 'Выключено';
        }
        if (field === 'is_active') {
            return ['true', '1', 'yes'].includes(String(value).toLowerCase()) ? 'Активный' : 'Архив';
        }
        if (field === 'group_id') {
            return getCatalogGroupName(value);
        }
        if (field === 'category_id') {
            return getCatalogCategoryName(value);
        }
        if (field === 'kind_id') {
            return getCatalogPathByType(value);
        }
        return String(value);
    }

    function resolveItemPhotoUpdateValue(itemId) {
        const normalizedItemId = Number(itemId);
        const currentItem = items.value.find((entry) => Number(entry.id) === normalizedItemId) || null;
        const currentPhoto = String(currentItem?.photo_key || currentItem?.photo_url || '').trim();
        const draftPhoto = String(itemForm.photoUrl || '').trim();

        if (!draftPhoto && !currentPhoto) {
            return undefined;
        }
        return draftPhoto || '';
    }

    async function loadItemCardChanges(itemId) {
        const normalizedItemId = Number(itemId);
        if (!Number.isFinite(normalizedItemId) || normalizedItemId <= 0) {
            itemCardChanges.value = [];
            return;
        }
        itemCardChangesLoading.value = true;
        itemCardChangesError.value = '';
        try {
            const data = await fetchInventoryMovements({
                limit: 200,
                item_ids: [normalizedItemId],
                action_types: ITEM_CARD_CHANGE_ACTIONS,
            });
            const rows = Array.isArray(data) ? data : [];
            itemCardChanges.value = rows
                .filter((row) => Number(row.item_id) === normalizedItemId)
                .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
        } catch (error) {
            itemCardChanges.value = [];
            itemCardChangesError.value = 'Не удалось загрузить журнал изменений';
            console.error(error);
        } finally {
            itemCardChangesLoading.value = false;
        }
    }

    async function reloadItemCardChanges() {
        await loadItemCardChanges(itemForm.id);
    }

    function openItemCard(item) {
        if (!item) {
            return;
        }
        openItemDetail(item);
        setItemFormFromItem(item);
        itemCardActiveTab.value = 'info';
        isItemCardOpen.value = true;
        isItemModalOpen.value = false;
        isCatalogModalOpen.value = false;
        itemCardChangesError.value = '';
        itemCardChanges.value = [];
        seedModalPickerTree();
        void loadItemCardChanges(item.id);
    }

    function closeItemCard() {
        isItemCardOpen.value = false;
        itemCardActiveTab.value = 'info';
        itemCardChangesError.value = '';
        itemCardChanges.value = [];
        isCatalogModalOpen.value = false;
        previewPhotoItem.value = null;
        isPreviewPhotoEditable.value = false;
        itemCardPhotoPreviewOverride.value = null;
        resetItemForm();
    }

    async function refreshItemCard(item) {
        if (!item) {
            closeItemCard();
            return;
        }
        openItemDetail(item);
        setItemFormFromItem(item);
        await loadItemCardChanges(item.id);
    }

    async function submitItemCardInfo() {
        if (!canEditNomenclature.value) {
            toast.error('Недостаточно прав для редактирования товара');
            return;
        }
        const itemId = Number(itemForm.id);
        if (!Number.isFinite(itemId) || itemId <= 0) {
            toast.error('Товар не выбран');
            return;
        }

        const name = itemForm.name.trim();
        if (!name) {
            toast.error('Введите название товара');
            return;
        }

        const type = typeMap.value.get(Number(itemForm.typeId));
        if (!type) {
            toast.error('Выберите вид товара');
            return;
        }

        const cost = parseNumber(itemForm.cost);
        if (Number.isNaN(cost)) {
            toast.error('Стоимость должна быть числом');
            return;
        }

        saving.value = true;
        try {
            const updatePhotoValue = resolveItemPhotoUpdateValue(itemId);
            await updateInventoryItem(itemId, {
                name,
                group_id: type.group_id,
                category_id: type.category_id,
                kind_id: type.id,
                cost,
                note: itemForm.note || undefined,
                manufacturer: itemForm.manufacturer || undefined,
                storage_conditions: itemForm.storageConditions || undefined,
                photo_url: updatePhotoValue,
                use_instance_codes: Boolean(itemForm.useInstanceCodes),
                is_active: Boolean(itemForm.isActive),
            });
            toast.success('Карточка товара обновлена');
            await loadItems();
            const refreshed = items.value.find((entry) => Number(entry.id) === itemId) || null;
            await refreshItemCard(refreshed);
        } catch (error) {
            toast.error('Не удалось обновить карточку товара');
            console.error(error);
        } finally {
            saving.value = false;
        }
    }

    function openItemPhoto(item, options = {}) {
        if (!item) {
            return;
        }
        previewPhotoItem.value = item;
        isPreviewPhotoEditable.value = Boolean(options.editable);
    }

    function openItemCardPhoto() {
        if (!isItemCardOpen.value) {
            return;
        }
        const fallbackItem = itemCardItem.value || {
            id: itemForm.id,
            name: itemForm.name,
            photo_url: '',
        };
        openItemPhoto(fallbackItem, { editable: canEditNomenclature.value });
    }

    function closeItemPhoto() {
        previewPhotoItem.value = null;
        isPreviewPhotoEditable.value = false;
    }

    function openPreviewPhotoPicker() {
        if (!isPreviewPhotoEditable.value || uploadingPhoto.value || saving.value || !previewPhotoInputRef.value) {
            return;
        }
        previewPhotoInputRef.value.click();
    }

    function removePreviewPhoto() {
        if (!isPreviewPhotoEditable.value || !canEditNomenclature.value || uploadingPhoto.value || saving.value) {
            return;
        }
        itemForm.photoUrl = '';
        itemForm.photoPreviewUrl = '';
        itemCardPhotoPreviewOverride.value = '';
        toast.success('Фото будет удалено после сохранения карточки');
    }

    async function handleReplacePreviewPhoto(event) {
        const file = event?.target?.files?.[0];
        if (!file || !isPreviewPhotoEditable.value || !canEditNomenclature.value) {
            return;
        }
        uploadingPhoto.value = true;
        try {
            const response = await uploadInventoryItemPhoto(file);
            itemForm.photoUrl = response?.attachment_key || response?.attachment_url || '';
            itemForm.photoPreviewUrl = response?.attachment_url || response?.attachment_key || '';
            if (response?.attachment_url) {
                itemCardPhotoPreviewOverride.value = response.attachment_url;
            }
            toast.success('Фото заменено. Нажмите «Сохранить изменения»');
        } catch (error) {
            toast.error('Не удалось загрузить фото');
            console.error(error);
        } finally {
            uploadingPhoto.value = false;
            if (event?.target) {
                event.target.value = '';
            }
        }
    }

    return {
        ITEM_CARD_TABS,
        canDeletePreviewPhoto,
        closeItemCard,
        closeItemPhoto,
        formatItemCardChangeDate,
        formatItemCardChangeField,
        formatItemCardChangeValue,
        handleReplacePreviewPhoto,
        isItemCardOpen,
        isPreviewPhotoEditable,
        itemCardActiveTab,
        itemCardChanges,
        itemCardChangesError,
        itemCardChangesLoading,
        itemCardItem,
        itemCardPhotoUrl,
        itemCardRestaurantRows,
        itemCardRestaurantsQuantity,
        itemCardTotalQuantity,
        itemCardWarehouseQuantity,
        openItemCard,
        openItemCardPhoto,
        openItemPhoto,
        openPreviewPhotoPicker,
        previewPhotoInputRef,
        previewPhotoItem,
        previewPhotoUrl,
        refreshItemCard,
        reloadItemCardChanges,
        removePreviewPhoto,
        submitItemCardInfo,
    };
}
