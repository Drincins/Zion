import { onMounted, ref } from 'vue';
import { useToast } from 'vue-toastification';

import { useInventoryRecordsFilters } from './useInventoryRecordsFilters';
import { useInventoryRecordsFormatting } from './useInventoryRecordsFormatting';
import {
    fetchEmployees,
    fetchInventoryCategories,
    fetchInventoryDepartments,
    fetchInventoryGroups,
    fetchInventoryItems,
    fetchInventoryMovementActions,
    fetchInventoryMovements,
} from '@/api';

export function useInventoryRecordsPage() {
    const toast = useToast();

    const loading = ref(false);
    const movements = ref([]);

    const groups = ref([]);
    const items = ref([]);
    const categories = ref([]);
    const departments = ref([]);
    const actions = ref([]);
    const staff = ref([]);

    const {
        actionFilterLabel,
        actionOptions,
        actorFilterLabel,
        actorOptions,
        buildMovementParams,
        catalogFilterLabel,
        clearAllFilters,
        clearSelection,
        dateFrom,
        dateTo,
        dropdownState,
        groupedCatalogOptions,
        isCatalogCategoryExpanded,
        isCatalogGroupExpanded,
        isFiltersOpen,
        objectFilterLabel,
        objectOptions,
        searchQuery,
        selectedFilters,
        setFilterRef,
        toggleCatalogCategory,
        toggleCatalogGroup,
        toggleDropdown,
        toggleSelection,
    } = useInventoryRecordsFilters({
        actions,
        categories,
        departments,
        groups,
        items,
        staff,
    });

    const {
        actionClass,
        formatDateTime,
        formatDetails,
        formatObject,
        formatQuantity,
    } = useInventoryRecordsFormatting();

    async function loadLookups() {
        const [groupData, itemsData, categoriesData, departmentData, actionData, staffData] = await Promise.all([
            fetchInventoryGroups(),
            fetchInventoryItems({ include_locations: false }),
            fetchInventoryCategories(),
            fetchInventoryDepartments(),
            fetchInventoryMovementActions(),
            fetchEmployees({ include_fired: true, limit: 1000 }),
        ]);
        groups.value = Array.isArray(groupData) ? groupData : [];
        items.value = Array.isArray(itemsData) ? itemsData : [];
        categories.value = Array.isArray(categoriesData) ? categoriesData : [];
        departments.value = Array.isArray(departmentData) ? departmentData : [];
        actions.value = Array.isArray(actionData) ? actionData : [];
        staff.value = Array.isArray(staffData?.items) ? staffData.items : [];
    }

    async function loadMovements() {
        loading.value = true;
        Object.keys(dropdownState).forEach((key) => {
            dropdownState[key] = false;
        });
        try {
            const data = await fetchInventoryMovements(buildMovementParams());
            movements.value = Array.isArray(data) ? data : [];
        } catch (error) {
            toast.error('Не удалось загрузить журнал операций');
            console.error(error);
        } finally {
            loading.value = false;
        }
    }

    async function resetFilters() {
        clearAllFilters();
        await loadMovements();
    }

    onMounted(async () => {
        try {
            await loadLookups();
            await loadMovements();
        } catch (error) {
            toast.error('Не удалось загрузить справочники движений');
            console.error(error);
        }
    });

    return {
        actionClass,
        actionFilterLabel,
        actionOptions,
        actorFilterLabel,
        actorOptions,
        catalogFilterLabel,
        clearSelection,
        dateFrom,
        dateTo,
        dropdownState,
        formatDateTime,
        formatDetails,
        formatObject,
        formatQuantity,
        groupedCatalogOptions,
        isCatalogCategoryExpanded,
        isCatalogGroupExpanded,
        isFiltersOpen,
        loading,
        loadLookups,
        loadMovements,
        movements,
        objectFilterLabel,
        objectOptions,
        resetFilters,
        searchQuery,
        selectedFilters,
        setFilterRef,
        toggleCatalogCategory,
        toggleCatalogGroup,
        toggleDropdown,
        toggleSelection,
    };
}
