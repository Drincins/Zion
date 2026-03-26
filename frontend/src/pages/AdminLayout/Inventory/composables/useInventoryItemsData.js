import { ref } from 'vue';
import { useToast } from 'vue-toastification';

import { formatNumberValue } from '@/utils/format';
import {
    fetchInventoryCategories,
    fetchInventoryDepartments,
    fetchInventoryGroups,
    fetchInventoryItems,
    fetchInventoryTypes,
} from '@/api';

export function useInventoryItemsData({
    catalogItems,
    categories,
    departmentOptions,
    groups,
    items,
    parseDepartmentFilters,
    seedCatalogExpandedTrees,
    selectedDepartmentIds,
    types,
}) {
    const toast = useToast();

    const loadingItems = ref(false);
    const loadingCatalogItems = ref(false);
    const hasLoadedByFilters = ref(false);

    async function loadLookupData() {
        const [groupsData, categoriesData, typesData, departmentsData] = await Promise.all([
            fetchInventoryGroups(),
            fetchInventoryCategories(),
            fetchInventoryTypes(),
            fetchInventoryDepartments(),
        ]);
        groups.value = Array.isArray(groupsData) ? groupsData : [];
        categories.value = Array.isArray(categoriesData) ? categoriesData : [];
        types.value = Array.isArray(typesData) ? typesData : [];
        departmentOptions.value = Array.isArray(departmentsData) ? departmentsData : [];
        seedCatalogExpandedTrees();
    }

    async function loadCatalogItemsForModal(force = false) {
        if (loadingCatalogItems.value) {
            return;
        }
        if (!force && catalogItems.value.length) {
            return;
        }
        loadingCatalogItems.value = true;
        try {
            const data = await fetchInventoryItems({ include_locations: false });
            catalogItems.value = Array.isArray(data) ? data : [];
        } catch (error) {
            toast.error('Не удалось загрузить товары каталога');
            console.error(error);
        } finally {
            loadingCatalogItems.value = false;
        }
    }

    async function loadItemsByFilters() {
        if (!selectedDepartmentIds.value.length) {
            toast.error('Выберите хотя бы одно подразделение');
            return;
        }
        loadingItems.value = true;
        try {
            const departmentParams = parseDepartmentFilters();
            const params = {
                ...departmentParams,
                only_in_locations: true,
            };

            const data = await fetchInventoryItems(params);
            items.value = Array.isArray(data) ? data : [];
            hasLoadedByFilters.value = true;
        } catch (error) {
            toast.error('Не удалось загрузить товары');
            console.error(error);
        } finally {
            loadingItems.value = false;
        }
    }

    function parseNumber(value) {
        const number = Number.parseFloat(String(value).replace(',', '.'));
        return Number.isFinite(number) ? number : NaN;
    }

    function formatMoney(value) {
        const numeric = parseNumber(value);
        const formatted = formatNumberValue(numeric, {
            emptyValue: '0.00',
            invalidValue: '0.00',
            locale: 'ru-RU',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return `${formatted} ₽`;
    }

    function getEntryUnitCost(entry) {
        const numeric = parseNumber(entry?.locationAvgCost ?? entry?.item?.cost);
        return Number.isNaN(numeric) ? 0 : numeric;
    }

    function getEntryTotalCost(entry) {
        const quantity = Number(entry?.quantity || 0);
        if (!Number.isFinite(quantity) || quantity <= 0) {
            return 0;
        }
        return getEntryUnitCost(entry) * quantity;
    }

    return {
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
    };
}
