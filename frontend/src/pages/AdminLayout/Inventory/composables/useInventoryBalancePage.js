import { computed, onMounted, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';

import { INVENTORY_MOVEMENTS_CREATE_PERMISSIONS } from '@/accessPolicy';
import {
    fetchInventoryStoragePlaces,
    fetchInventoryCategories,
    fetchInventoryGroups,
    fetchInventoryInstanceEventTypes,
    fetchInventoryItems,
    fetchInventoryTypes,
    fetchRestaurants,
} from '@/api';
import { useUserStore } from '@/stores/user';
import { formatDateTimeValue, formatNumberValue } from '@/utils/format';
import { useInventoryBalanceCatalogTree } from './useInventoryBalanceCatalogTree';
import { useInventoryBalanceItemCard } from './useInventoryBalanceItemCard';
import { useInventoryBalanceOperations } from './useInventoryBalanceOperations';

export function useInventoryBalancePage() {
    const toast = useToast();
    const userStore = useUserStore();

    const restaurants = ref([]);
    const storagePlaces = ref([]);
    const groups = ref([]);
    const categories = ref([]);
    const types = ref([]);
    const items = ref([]);
    const catalogItems = ref([]);

    const loading = ref(false);
    const searchQuery = ref('');
    const selectedRestaurantId = ref('');
    const selectedStoragePlaceId = ref('all');
    const selectedItemId = ref(null);
    const isDetailPaneVisible = ref(true);

    const canCreateMovement = computed(() => userStore.hasAnyPermission(...INVENTORY_MOVEMENTS_CREATE_PERMISSIONS));

    const selectedRestaurantIdNum = computed(() => {
        const parsed = Number(selectedRestaurantId.value);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    });

    const selectedRestaurantName = computed(() => {
        const id = selectedRestaurantIdNum.value;
        if (!id) {
            return '—';
        }
        const restaurant = restaurants.value.find((entry) => Number(entry.id) === id);
        return restaurant?.name || `Ресторан #${id}`;
    });

    const selectedStoragePlaceIdNum = computed(() => {
        const parsed = Number(selectedStoragePlaceId.value);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    });

    const restaurantOptions = computed(() =>
        [...restaurants.value]
            .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }))
            .map((restaurant) => ({ value: String(restaurant.id), label: restaurant.name })),
    );

    const currentRestaurantStoragePlaces = computed(() => {
        const restaurantId = selectedRestaurantIdNum.value;
        if (!restaurantId) {
            return [];
        }
        return [...storagePlaces.value]
            .filter((place) => Boolean(place?.is_active) && Number(place?.restaurant_id) === restaurantId)
            .sort((a, b) => String(a?.name || '').localeCompare(String(b?.name || ''), 'ru', { sensitivity: 'base' }));
    });

    const storagePlaceFilterOptions = computed(() => [
        { value: 'all', label: 'Все места хранения' },
        ...currentRestaurantStoragePlaces.value.map((place) => ({
            value: String(place.id),
            label: place.name,
        })),
    ]);

    const selectedStoragePlaceLabel = computed(() => {
        if (!selectedRestaurantIdNum.value) {
            return 'Все места хранения';
        }
        const option = storagePlaceFilterOptions.value.find((entry) => String(entry.value) === String(selectedStoragePlaceId.value));
        return option?.label || 'Все места хранения';
    });

    const {
        collapseAll,
        detailEntry,
        ensureSelectedItem,
        expandAllVisible,
        filteredItems,
        getCatalogCategoryName,
        getCatalogGroupName,
        getCatalogPath,
        getCatalogPathByType,
        getCatalogTypeName,
        getHighlightedParts,
        getRestaurantLocation,
        groupedCatalog,
        groupedItemsCount,
        isCategoryExpanded,
        isGroupExpanded,
        isKindExpanded,
        openItemDetail,
        toggleCategory,
        toggleDetailPane,
        toggleGroup,
        toggleKind,
    } = useInventoryBalanceCatalogTree({
        categories,
        groups,
        isDetailPaneVisible,
        items,
        searchQuery,
        selectedItemId,
        selectedRestaurantIdNum,
        selectedStoragePlaceIdNum,
        types,
    });

    const {
        closeInstanceEventModal,
        closeItemCard,
        currentInstanceCount,
        detailArrivals,
        detailCard,
        detailCardLoading,
        detailTab,
        historicalInstanceCount,
        instanceEventForm,
        instanceEventSubmitting,
        instanceEventTypeOptions,
        instanceEventTypes,
        instanceEvents,
        instanceEventsLoading,
        instanceSummaries,
        instanceTrackingEnabled,
        isInstanceEventModalOpen,
        isItemCardModalOpen,
        loadDetailCard,
        openInstanceEventModal,
        openItemCard,
        resetItemCardState,
        selectInstance,
        selectedInstanceCode,
        selectedInstanceSummary,
        submitInstanceEvent,
    } = useInventoryBalanceItemCard({
        openItemDetail,
        selectedItemId,
        selectedRestaurantIdNum,
        selectedStoragePlaceIdNum,
    });

    const {
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
        selectedOperationItem,
        sourceLocationQuantity,
        sourceStoragePlaceOptions,
        submitOperation,
        targetStoragePlaceOptions,
    } = useInventoryBalanceOperations({
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
    });

    function formatMoney(value) {
        return formatNumberValue(value, {
            emptyValue: '—',
            invalidValue: '—',
            locale: 'ru-RU',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function formatDateTime(value) {
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

    async function loadLookupData() {
        const [restaurantData, storagePlaceData, groupData, categoryData, typeData, eventTypeData, catalogData] = await Promise.all([
            fetchRestaurants(),
            fetchInventoryStoragePlaces({ active_only: true }),
            fetchInventoryGroups(),
            fetchInventoryCategories(),
            fetchInventoryTypes(),
            fetchInventoryInstanceEventTypes({ manual_only: true, active_only: true }),
            fetchInventoryItems({ include_locations: false }),
        ]);
        restaurants.value = Array.isArray(restaurantData) ? restaurantData : [];
        storagePlaces.value = Array.isArray(storagePlaceData) ? storagePlaceData : [];
        groups.value = Array.isArray(groupData) ? groupData : [];
        categories.value = Array.isArray(categoryData) ? categoryData : [];
        types.value = Array.isArray(typeData) ? typeData : [];
        instanceEventTypes.value = Array.isArray(eventTypeData) ? eventTypeData : [];
        catalogItems.value = Array.isArray(catalogData) ? catalogData : [];

        if (!selectedRestaurantId.value && restaurants.value.length) {
            selectedRestaurantId.value = String(restaurants.value[0].id);
        }
        if (!selectedStoragePlaceId.value) {
            selectedStoragePlaceId.value = 'all';
        }
        if (!instanceEventForm.eventTypeId && instanceEventTypeOptions.value.length) {
            instanceEventForm.eventTypeId = String(instanceEventTypeOptions.value[0].value);
        }
    }

    async function loadRestaurantItems() {
        const restaurantId = selectedRestaurantIdNum.value;
        const storagePlaceId = selectedStoragePlaceIdNum.value;
        if (!restaurantId) {
            items.value = [];
            selectedItemId.value = null;
            resetItemCardState();
            return;
        }

        loading.value = true;
        resetItemCardState();
        try {
            const data = await fetchInventoryItems({
                restaurant_ids: [restaurantId],
                storage_place_ids: storagePlaceId ? [storagePlaceId] : undefined,
                only_in_locations: true,
            });
            items.value = Array.isArray(data) ? data : [];
            ensureSelectedItem();
        } catch (error) {
            toast.error('Не удалось загрузить баланс ресторана');
            console.error(error);
        } finally {
            loading.value = false;
        }
    }

    watch(filteredItems, () => {
        ensureSelectedItem();
    });

    watch(selectedRestaurantId, async () => {
        selectedStoragePlaceId.value = 'all';
        operationForm.targetRestaurantId = selectedRestaurantId.value || '';
        await loadRestaurantItems();
    });

    watch(selectedStoragePlaceId, async () => {
        await loadRestaurantItems();
    });

    onMounted(async () => {
        try {
            await loadLookupData();
        } catch (error) {
            toast.error('Не удалось загрузить данные страницы баланса');
            console.error(error);
        }
    });

    return {
        canCreateMovement,
        closeInstanceEventModal,
        closeItemCard,
        closeOperationModal,
        collapseAll,
        currentInstanceCount,
        currentRestaurantStoragePlaces,
        detailArrivals,
        detailCard,
        detailCardLoading,
        detailEntry,
        detailTab,
        expandAllVisible,
        filteredItems,
        formatDateTime,
        formatMoney,
        getCatalogCategoryName,
        getCatalogGroupName,
        getCatalogPath,
        getCatalogPathByType,
        getCatalogTypeName,
        getHighlightedParts,
        groupedCatalog,
        groupedItemsCount,
        historicalInstanceCount,
        instanceEventForm,
        instanceEventSubmitting,
        instanceEventTypeOptions,
        instanceEvents,
        instanceEventsLoading,
        instanceSummaries,
        instanceTrackingEnabled,
        isCategoryExpanded,
        isDetailPaneVisible,
        isGroupExpanded,
        isIncomeOperation,
        isInstanceEventModalOpen,
        isItemCardModalOpen,
        isKindExpanded,
        isOperationModalOpen,
        isTransferOperation,
        isWriteoffOperation,
        loadRestaurantItems,
        loading,
        openInstanceEventModal,
        openItemCard,
        openItemDetail,
        openOperationModal,
        operationDraftRecord,
        operationForm,
        operationItemLoading,
        operationItemOptions,
        operationSubmitting,
        operationTargetStoragePlaceLabel,
        operationType,
        operationTypeOptions,
        restaurantOptions,
        restaurants,
        searchQuery,
        selectInstance,
        selectedInstanceCode,
        selectedInstanceSummary,
        selectedItemId,
        selectedOperationItem,
        selectedRestaurantId,
        selectedRestaurantIdNum,
        selectedRestaurantName,
        selectedStoragePlaceId,
        selectedStoragePlaceIdNum,
        selectedStoragePlaceLabel,
        sourceLocationQuantity,
        sourceStoragePlaceOptions,
        storagePlaceFilterOptions,
        submitInstanceEvent,
        submitOperation,
        targetStoragePlaceOptions,
        toggleCategory,
        toggleDetailPane,
        toggleGroup,
        toggleKind,
    };
}
