import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';

import {
    INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS,
} from '@/accessPolicy';
import { useUserStore } from '@/stores/user';
import { formatDateTimeValue, formatNumberValue } from '@/utils/format';
import { ITEM_CARD_TABS, useInventoryCatalogItemCard } from './useInventoryCatalogItemCard';
import { useInventoryCatalogItemModal } from './useInventoryCatalogItemModal';
import { useInventoryCatalogTree } from './useInventoryCatalogTree';
import {
    fetchInventoryCategories,
    fetchInventoryGroups,
    fetchInventoryItems,
    fetchRestaurants,
    fetchInventoryTypes,
} from '@/api';

export function useInventoryCatalogPage() {
    const toast = useToast();
    const userStore = useUserStore();

    const groups = ref([]);
    const categories = ref([]);
    const types = ref([]);
    const restaurants = ref([]);
    const items = ref([]);

    const loading = ref(false);
    const saving = ref(false);
    const uploadingPhoto = ref(false);

    const searchQuery = ref('');
    const isFiltersOpen = ref(true);
    const isDetailPaneVisible = ref(true);

    const isItemModalOpen = ref(false);
    const isEditMode = ref(false);
    const isCatalogModalOpen = ref(false);
    const itemForm = reactive({
        id: null,
        name: '',
        note: '',
        manufacturer: '',
        storageConditions: '',
        typeId: '',
        cost: '',
        photoUrl: '',
        useInstanceCodes: true,
        isActive: true,
        createdAt: '',
    });

    const selectedItemId = ref(null);
    const photoInputRef = ref(null);
    const catalogModalRef = ref(null);

    const {
        categoriesByGroup,
        categoryMap,
        collapseAll,
        detailItem,
        ensureSelectedItem,
        expandAllVisible,
        expandedCategoryIds,
        expandedGroupIds,
        expandedKindIds,
        expandPathForItem,
        filteredItems,
        getCatalogCategoryName,
        getCatalogGroupName,
        getCatalogPath,
        getCatalogPathByType,
        getCatalogTypeName,
        getHighlightedParts,
        groupedCatalog,
        groupMap,
        isCategoryExpanded,
        isGroupExpanded,
        isKindExpanded,
        isModalCategoryExpanded,
        isModalGroupExpanded,
        modalExpandedCategoryIds,
        modalExpandedGroupIds,
        persistExpandedTree,
        restoreDetailPanePreference,
        restoreExpandedTree,
        seedExpandedTree,
        seedModalPickerTree,
        selectModalType,
        selectedTypeLabel,
        sortedCategories,
        sortedGroups,
        sortedTypes,
        toIdSet,
        toggleCategory,
        toggleGroup,
        toggleKind,
        toggleModalCategory,
        toggleModalGroup,
        toggleSet,
        typeMap,
        typesByCategory,
    } = useInventoryCatalogTree({
        categories,
        groups,
        isCatalogModalOpen,
        isDetailPaneVisible,
        itemForm,
        items,
        searchQuery,
        selectedItemId,
        types,
    });

    const canCreateNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS));
    const canEditNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS));
    const canSubmitItemModal = computed(() => (isEditMode.value ? canEditNomenclature.value : canCreateNomenclature.value));

    const {
        closeItemModal,
        handleUploadItemPhoto,
        openCreateModal,
        openPhotoPicker,
        resetItemForm,
        setItemFormFromItem,
        submitItem,
    } = useInventoryCatalogItemModal({
        canCreateNomenclature,
        canEditNomenclature,
        canSubmitItemModal,
        isCatalogModalOpen,
        isEditMode,
        isItemModalOpen,
        itemForm,
        loadItems,
        parseNumber,
        photoInputRef,
        saving,
        seedModalPickerTree,
        typeMap,
        uploadingPhoto,
    });

    function formatItemCreatedAt(value) {
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

    function toggleFilters() {
        isFiltersOpen.value = !isFiltersOpen.value;
    }

    function toggleDetailPane() {
        isDetailPaneVisible.value = !isDetailPaneVisible.value;
    }

    function clearSearch() {
        searchQuery.value = '';
    }

    function onDocumentClick(event) {
        if (catalogModalRef.value && !catalogModalRef.value.contains(event.target)) {
            isCatalogModalOpen.value = false;
        }
    }

    async function loadLookupData() {
        const [groupData, categoryData, typeData, restaurantData] = await Promise.all([
            fetchInventoryGroups(),
            fetchInventoryCategories(),
            fetchInventoryTypes(),
            fetchRestaurants(),
        ]);
        groups.value = Array.isArray(groupData) ? groupData : [];
        categories.value = Array.isArray(categoryData) ? categoryData : [];
        types.value = Array.isArray(typeData) ? typeData : [];
        restaurants.value = Array.isArray(restaurantData) ? restaurantData : [];
        seedExpandedTree();
        restoreExpandedTree();
    }

    async function loadItems() {
        loading.value = true;
        try {
            const data = await fetchInventoryItems();
            items.value = Array.isArray(data) ? data : [];
            ensureSelectedItem();
        } catch (error) {
            toast.error('Не удалось загрузить каталог товаров');
            console.error(error);
        } finally {
            loading.value = false;
        }
    }

    function openItemDetail(item) {
        selectedItemId.value = Number(item.id);
        expandPathForItem(item);
    }

    function parseNumber(value) {
        const number = Number.parseFloat(String(value).replace(',', '.'));
        return Number.isFinite(number) ? number : NaN;
    }

    function formatMoney(value) {
        const amount = Number(value || 0);
        return formatNumberValue(amount, {
            emptyValue: '0.00',
            invalidValue: 'NaN',
            locale: 'ru-RU',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    const {
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
        reloadItemCardChanges,
        removePreviewPhoto,
        submitItemCardInfo,
    } = useInventoryCatalogItemCard({
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
        saving,
        seedModalPickerTree,
        setItemFormFromItem,
        typeMap,
        uploadingPhoto,
    });

    watch(filteredItems, () => {
        ensureSelectedItem();
    });

    watch(isDetailPaneVisible, (value) => {
        if (typeof window === 'undefined') {
            return;
        }
        window.localStorage.setItem(DETAIL_PANE_STORAGE_KEY, value ? '1' : '0');
    });

    onMounted(async () => {
        document.addEventListener('click', onDocumentClick);
        try {
            restoreDetailPanePreference();
            await loadLookupData();
            await loadItems();
        } catch (error) {
            toast.error('Не удалось загрузить каталог');
            console.error(error);
        }
    });

    onBeforeUnmount(() => {
        document.removeEventListener('click', onDocumentClick);
    });

    return {
        ITEM_CARD_TABS,
        groups,
        categories,
        types,
        restaurants,
        items,
        loading,
        saving,
        uploadingPhoto,
        searchQuery,
        isFiltersOpen,
        isDetailPaneVisible,
        expandedGroupIds,
        expandedCategoryIds,
        expandedKindIds,
        modalExpandedGroupIds,
        modalExpandedCategoryIds,
        isItemModalOpen,
        isEditMode,
        isCatalogModalOpen,
        isItemCardOpen,
        itemCardActiveTab,
        itemCardChangesLoading,
        itemCardChangesError,
        itemCardChanges,
        itemForm,
        previewPhotoItem,
        selectedItemId,
        photoInputRef,
        previewPhotoInputRef,
        catalogModalRef,
        isPreviewPhotoEditable,
        groupMap,
        categoryMap,
        typeMap,
        sortedGroups,
        sortedCategories,
        sortedTypes,
        categoriesByGroup,
        typesByCategory,
        selectedTypeLabel,
        itemCardItem,
        itemCardPhotoUrl,
        previewPhotoUrl,
        canDeletePreviewPhoto,
        canCreateNomenclature,
        canEditNomenclature,
        canSubmitItemModal,
        itemCardRestaurantRows,
        itemCardTotalQuantity,
        itemCardWarehouseQuantity,
        itemCardRestaurantsQuantity,
        filteredItems,
        detailItem,
        groupedCatalog,
        getCatalogGroupName,
        getCatalogCategoryName,
        getCatalogTypeName,
        getCatalogPathByType,
        getCatalogPath,
        formatItemCardChangeDate,
        formatItemCreatedAt,
        formatItemCardChangeField,
        formatItemCardChangeValue,
        getHighlightedParts,
        isGroupExpanded,
        isCategoryExpanded,
        isKindExpanded,
        toggleFilters,
        toggleDetailPane,
        clearSearch,
        toIdSet,
        persistExpandedTree,
        restoreExpandedTree,
        restoreDetailPanePreference,
        toggleSet,
        toggleGroup,
        toggleCategory,
        toggleKind,
        seedExpandedTree,
        expandAllVisible,
        collapseAll,
        expandPathForItem,
        ensureSelectedItem,
        isModalGroupExpanded,
        isModalCategoryExpanded,
        toggleModalGroup,
        toggleModalCategory,
        seedModalPickerTree,
        onDocumentClick,
        loadLookupData,
        loadItems,
        resetItemForm,
        openCreateModal,
        setItemFormFromItem,
        openItemCard,
        closeItemCard,
        reloadItemCardChanges,
        closeItemModal,
        openItemDetail,
        openItemCardPhoto,
        openItemPhoto,
        closeItemPhoto,
        openPreviewPhotoPicker,
        removePreviewPhoto,
        handleReplacePreviewPhoto,
        openPhotoPicker,
        handleUploadItemPhoto,
        parseNumber,
        submitItem,
        submitItemCardInfo,
        formatMoney,
    };
}
