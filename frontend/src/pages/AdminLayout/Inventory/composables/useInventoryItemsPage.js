import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';

import {
    INVENTORY_MOVEMENTS_CREATE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS,
} from '@/accessPolicy';
import { useClickOutside } from '@/composables/useClickOutside';
import { useUserStore } from '@/stores/user';
import { useInventoryItemsCatalogTree } from './useInventoryItemsCatalogTree';
import { useInventoryItemsData } from './useInventoryItemsData';
import { useInventoryItemsDepartments } from './useInventoryItemsDepartments';
import { useInventoryItemsItemModal } from './useInventoryItemsItemModal';
import { useInventoryItemsMovements } from './useInventoryItemsMovements';

export function useInventoryItemsPage() {
    const toast = useToast();
    const userStore = useUserStore();
    const groups = ref([]);
    const categories = ref([]);
    const types = ref([]);
    const departmentOptions = ref([]);
    const items = ref([]);
    const catalogItems = ref([]);
    const saving = ref(false);
    const uploadingPhoto = ref(false);

    const isCatalogFilterOpen = ref(false);
    const isCatalogModalOpen = ref(false);

    const departmentSelectRef = ref(null);
    const catalogFilterRef = ref(null);
    const catalogModalRef = ref(null);
    const photoInputRef = ref(null);

    const isItemModalOpen = ref(false);
    const isEditMode = ref(false);
    const itemForm = reactive({
        id: null,
        code: '',
        name: '',
        catalogNodeId: '',
        cost: '',
        note: '',
        manufacturer: '',
        storageConditions: '',
        photoUrl: '',
        photoPreviewUrl: '',
        useInstanceCodes: true,
        useCatalogItem: false,
        selectedCatalogItemId: null,
        catalogSearch: '',
        targetOptionId: '',
        targetQuantity: '1',
    });

    const {
        departmentSearch,
        departmentsLabel,
        filteredDepartmentOptions,
        isDepartmentsOpen,
        parseDepartmentFilters,
        selectedDepartmentIds,
        selectedDepartmentLabels,
        toggleDepartment,
    } = useInventoryItemsDepartments({ departmentOptions });

    const {
        categoriesByGroup,
        catalogFilterLabel,
        catalogModalLabel,
        categoryMap,
        clearFilterCatalogNodes,
        filterExpandedCategoryIds,
        filterExpandedGroupIds,
        filteredItems,
        getCatalogCategoryName,
        getCatalogGroupName,
        getCatalogNodeLabel,
        getCatalogPath,
        getCatalogPathByType,
        getCatalogTypeName,
        groupMap,
        groupedInventory,
        isCatalogNodeSelected,
        isFilterCategoryExpanded,
        isFilterGroupExpanded,
        isModalCategoryExpanded,
        isModalGroupExpanded,
        matchCatalogNode,
        modalExpandedCategoryIds,
        modalExpandedGroupIds,
        parseCatalogNodeValue,
        seedCatalogExpandedTrees,
        selectModalType,
        selectedCatalogNodeIds,
        sortedCategories,
        sortedGroups,
        sortedTypes,
        toggleFilterCatalogNode,
        toggleFilterCategory,
        toggleFilterGroup,
        toggleModalCategory,
        toggleModalGroup,
        toggleSet,
        typeMap,
        typesByCategory,
    } = useInventoryItemsCatalogTree({
        categories,
        groups,
        isCatalogModalOpen,
        itemForm,
        items,
        types,
    });

    const sourceTransferLocationOptions = computed(() =>
        departmentOptions.value
            .filter((option) => option.type === 'warehouse' || option.type === 'restaurant' || option.type === 'subdivision')
            .map((option) => ({
                value: option.id,
                label: option.type === 'warehouse' ? 'Виртуальный склад' : option.label,
            })),
    );

    const targetTransferLocationOptions = computed(() =>
        departmentOptions.value
            .filter((option) => option.type === 'warehouse' || option.type === 'restaurant')
            .map((option) => ({
                value: option.id,
                label: option.type === 'warehouse' ? 'Виртуальный склад' : option.label,
            })),
    );

    const createDepartmentOptions = computed(() =>
        departmentOptions.value
            .filter((option) => option.type === 'warehouse' || option.type === 'restaurant' || option.type === 'subdivision')
            .map((option) => ({ value: option.id, label: option.label })),
    );

    const {
        formatMoney,
        getEntryTotalCost,
        getEntryUnitCost,
        hasLoadedByFilters,
        loadCatalogItemsForModal,
        loadItemsByFilters,
        loadLookupData,
        loadingCatalogItems,
        loadingItems,
        parseNumber,
    } = useInventoryItemsData({
        catalogItems,
        categories,
        departmentOptions,
        groups,
        items,
        parseDepartmentFilters,
        seedCatalogExpandedTrees,
        selectedDepartmentIds,
        types,
    });

    const canCreateNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS));
    const canEditNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS));
    const canCreateMovement = computed(() => userStore.hasAnyPermission(...INVENTORY_MOVEMENTS_CREATE_PERMISSIONS));

    const {
        canEditModalPhoto,
        canOpenCreateModal,
        canSubmitItemModal,
        canToggleCreateSourceMode,
        catalogBaseCost,
        catalogItemsForPicker,
        closeItemModal,
        getDefaultCreateDepartmentOptionId,
        handleUploadItemPhoto,
        isCatalogCostOverride,
        isCatalogSourceMode,
        openCreateModal,
        openEditModal,
        openPhotoPicker,
        selectedCatalogItem,
        selectCatalogItem,
        submitItem,
        toggleCatalogSourceMode,
        resetItemForm,
    } = useInventoryItemsItemModal({
        canCreateMovement,
        canCreateNomenclature,
        canEditNomenclature,
        catalogItems,
        departmentOptions,
        hasLoadedByFilters,
        isCatalogModalOpen,
        isEditMode,
        isItemModalOpen,
        itemForm,
        loadCatalogItemsForModal,
        loadItemsByFilters,
        parseCatalogNodeValue,
        parseNumber,
        photoInputRef,
        saving,
        seedCatalogExpandedTrees,
        typeMap,
        uploadingPhoto,
        userStore,
    });

    const {
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
    } = useInventoryItemsMovements({
        canCreateMovement,
        departmentOptions,
        hasLoadedByFilters,
        loadItemsByFilters,
        parseNumber,
        saving,
    });

    function resetFilters() {
        selectedDepartmentIds.value = [];
        clearFilterCatalogNodes();
        items.value = [];
        hasLoadedByFilters.value = false;
    }

    useClickOutside([
        {
            element: departmentSelectRef,
            when: () => isDepartmentsOpen.value,
            onOutside: () => {
                isDepartmentsOpen.value = false;
            },
        },
        {
            element: catalogFilterRef,
            when: () => isCatalogFilterOpen.value,
            onOutside: () => {
                isCatalogFilterOpen.value = false;
            },
        },
        {
            element: catalogModalRef,
            when: () => isCatalogModalOpen.value,
            onOutside: () => {
                isCatalogModalOpen.value = false;
            },
        },
    ]);

    watch(
        () => createDepartmentOptions.value.length,
        () => {
            if (!isItemModalOpen.value || isEditMode.value || !isCatalogSourceMode.value) {
                return;
            }
            if (!itemForm.targetOptionId) {
                itemForm.targetOptionId = getDefaultCreateDepartmentOptionId();
            }
        },
    );

    onMounted(async () => {
        try {
            await loadLookupData();
        } catch (error) {
            toast.error('Не удалось загрузить справочники склада');
            console.error(error);
        }
    });

    return {
        groups,
        categories,
        types,
        departmentOptions,
        items,
        catalogItems,
        loadingItems,
        loadingCatalogItems,
        saving,
        uploadingPhoto,
        hasLoadedByFilters,
        isDepartmentsOpen,
        isCatalogFilterOpen,
        isCatalogModalOpen,
        departmentSearch,
        selectedDepartmentIds,
        departmentSelectRef,
        catalogFilterRef,
        catalogModalRef,
        photoInputRef,
        filterExpandedGroupIds,
        filterExpandedCategoryIds,
        modalExpandedGroupIds,
        modalExpandedCategoryIds,
        selectedCatalogNodeIds,
        isItemModalOpen,
        isEditMode,
        itemForm,
        isTransferModalOpen,
        transferForm,
        quantityForm,
        previewPhotoItem,
        detailItemEntry,
        groupMap,
        categoryMap,
        typeMap,
        sortedGroups,
        sortedCategories,
        sortedTypes,
        categoriesByGroup,
        typesByCategory,
        sourceTransferLocationOptions,
        targetTransferLocationOptions,
        createDepartmentOptions,
        filteredDepartmentOptions,
        selectedDepartmentLabels,
        departmentsLabel,
        catalogFilterLabel,
        catalogModalLabel,
        selectedCatalogItem,
        isCatalogSourceMode,
        canCreateNomenclature,
        canEditNomenclature,
        canCreateMovement,
        canOpenCreateModal,
        canToggleCreateSourceMode,
        canSubmitItemModal,
        canEditModalPhoto,
        catalogItemsForPicker,
        catalogBaseCost,
        isCatalogCostOverride,
        parseCatalogNodeValue,
        getCatalogPathByType,
        getCatalogPath,
        getCatalogGroupName,
        getCatalogCategoryName,
        getCatalogTypeName,
        getCatalogNodeLabel,
        seedCatalogExpandedTrees,
        toggleSet,
        isFilterGroupExpanded,
        isFilterCategoryExpanded,
        isModalGroupExpanded,
        isModalCategoryExpanded,
        toggleFilterGroup,
        toggleFilterCategory,
        toggleModalGroup,
        toggleModalCategory,
        isCatalogNodeSelected,
        toggleFilterCatalogNode,
        clearFilterCatalogNodes,
        selectModalType,
        toggleDepartment,
        parseDepartmentFilters,
        resetFilters,
        matchCatalogNode,
        filteredItems,
        groupedInventory,
        loadLookupData,
        loadCatalogItemsForModal,
        loadItemsByFilters,
        resetItemForm,
        getDefaultCreateDepartmentOptionId,
        selectCatalogItem,
        toggleCatalogSourceMode,
        openPhotoPicker,
        openCreateModal,
        openEditModal,
        closeItemModal,
        parseNumber,
        formatMoney,
        getEntryUnitCost,
        getEntryTotalCost,
        submitItem,
        openItemPhoto,
        closeItemPhoto,
        openItemDetail,
        closeItemDetail,
        buildQuantityPayload,
        handleUpdateQuantityFromDetail,
        handleUploadItemPhoto,
        buildLocationOptionId,
        openTransferModal,
        closeTransferModal,
        submitTransfer,
    };
}
