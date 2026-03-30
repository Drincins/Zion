import { computed, onMounted, ref } from 'vue';
import { useToast } from 'vue-toastification';

import { useClickOutside } from '@/composables/useClickOutside';
import { formatNumberValue } from '@/utils/format';
import {
    fetchInventoryCategories,
    fetchInventoryDepartments,
    fetchInventoryGroups,
    fetchInventoryItems,
    fetchInventoryTypes,
} from '@/api';

const TAGS = [
    { value: 'fixed_assets', label: 'Основные средства' },
    { value: 'high_value_property', label: 'Имущество высокой стоимости' },
    { value: 'object_property', label: 'Имущество объекта' },
];

export function useInventoryTaggedItemsPage() {
    const toast = useToast();

    const groups = ref([]);
    const categories = ref([]);
    const types = ref([]);
    const departmentOptions = ref([]);
    const items = ref([]);

    const loadingItems = ref(false);
    const hasLoadedByFilters = ref(false);

    const isDepartmentsOpen = ref(false);
    const isTagsOpen = ref(false);

    const departmentSearch = ref('');
    const selectedDepartmentIds = ref([]);
    const selectedTagIds = ref([]);

    const departmentSelectRef = ref(null);
    const tagFilterRef = ref(null);
    const detailEntry = ref(null);

    const groupMap = computed(() => {
        const map = new Map();
        groups.value.forEach((group) => map.set(Number(group.id), group));
        return map;
    });

    const categoryMap = computed(() => {
        const map = new Map();
        categories.value.forEach((category) => map.set(Number(category.id), category));
        return map;
    });

    const typeMap = computed(() => {
        const map = new Map();
        types.value.forEach((type) => map.set(Number(type.id), type));
        return map;
    });

    const tagOptions = computed(() => TAGS);

    const filteredDepartmentOptions = computed(() => {
        const search = departmentSearch.value.trim().toLowerCase();
        const sorted = [...departmentOptions.value].sort((a, b) => {
            const priority = (option) => {
                if (option.id === 'all_departments') return 0;
                if (option.id === 'all_restaurants') return 1;
                if (option.id === 'warehouse') return 2;
                if (option.type === 'restaurant') return 3;
                return 4;
            };
            const pa = priority(a);
            const pb = priority(b);
            if (pa !== pb) {
                return pa - pb;
            }
            return String(a.label || '').localeCompare(String(b.label || ''), 'ru', { sensitivity: 'base' });
        });
        if (!search) {
            return sorted;
        }
        return sorted.filter((option) => String(option.label || '').toLowerCase().includes(search));
    });

    const selectedDepartmentLabels = computed(() =>
        departmentOptions.value
            .filter((option) => selectedDepartmentIds.value.includes(option.id))
            .map((option) => option.label),
    );

    const departmentsLabel = computed(() => {
        if (!selectedDepartmentLabels.value.length) {
            return 'Выберите объекты';
        }
        if (selectedDepartmentLabels.value.length <= 2) {
            return selectedDepartmentLabels.value.join(', ');
        }
        return `${selectedDepartmentLabels.value.slice(0, 2).join(', ')} +${selectedDepartmentLabels.value.length - 2}`;
    });

    const tagFilterLabel = computed(() => {
        if (!selectedTagIds.value.length) {
            return 'Все теги';
        }
        if (selectedTagIds.value.length === 1) {
            return TAGS.find((tag) => tag.value === selectedTagIds.value[0])?.label || 'Все теги';
        }
        return `Выбрано: ${selectedTagIds.value.length}`;
    });

    const flatEntries = computed(() => {
        const entries = [];
        for (const item of items.value) {
            const locations = Array.isArray(item.location_totals) ? item.location_totals : [];
            for (const location of locations) {
                const quantity = Number(location.quantity || 0);
                if (quantity <= 0) {
                    continue;
                }
                const unitCost = resolveCost(location.avg_cost, item.cost);
                const tagId = resolveTagByCost(unitCost);
                entries.push({
                    key: `${item.id}:${location.location_kind}:${location.restaurant_id || ''}:${location.subdivision_id || ''}`,
                    item,
                    quantity,
                    unitCost,
                    totalCost: quantity * unitCost,
                    tagId,
                    tagLabel: TAGS.find((tag) => tag.value === tagId)?.label || '',
                    locationName: location.location_name || 'Подразделение',
                    locationKind: location.location_kind,
                    locationRestaurantId: location.restaurant_id || null,
                    locationSubdivisionId: location.subdivision_id || null,
                    catalogPath: getCatalogPath(item),
                });
            }
        }
        return entries;
    });

    const tagGroups = computed(() => {
        const activeTags = selectedTagIds.value.length
            ? TAGS.filter((tag) => selectedTagIds.value.includes(tag.value))
            : TAGS;

        const grouped = [];
        for (const tag of activeTags) {
            const tagEntries = flatEntries.value.filter((entry) => entry.tagId === tag.value);
            const objectMap = new Map();
            let totalCost = 0;
            let totalQuantity = 0;

            for (const entry of tagEntries) {
                totalCost += entry.totalCost;
                totalQuantity += entry.quantity;
                const objectKey = `${entry.locationKind}:${entry.locationRestaurantId || ''}:${entry.locationSubdivisionId || ''}`;
                let objectNode = objectMap.get(objectKey);
                if (!objectNode) {
                    objectNode = {
                        key: objectKey,
                        name: entry.locationName,
                        items: [],
                    };
                    objectMap.set(objectKey, objectNode);
                }
                objectNode.items.push(entry);
            }

            grouped.push({
                id: tag.value,
                label: tag.label,
                totalCost,
                totalQuantity,
                objects: Array.from(objectMap.values())
                    .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }))
                    .map((objectNode) => ({
                        ...objectNode,
                        items: [...objectNode.items].sort((a, b) =>
                            String(a.item?.name || '').localeCompare(String(b.item?.name || ''), 'ru', { sensitivity: 'base' }),
                        ),
                    })),
            });
        }
        return grouped;
    });

    function resolveCost(locationCost, itemCost) {
        const source = locationCost ?? itemCost;
        const parsed = Number.parseFloat(String(source ?? 0).replace(',', '.'));
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function resolveTagByCost(cost) {
        if (cost > 100000) {
            return 'fixed_assets';
        }
        if (cost >= 10000) {
            return 'high_value_property';
        }
        return 'object_property';
    }

    function getCatalogPath(item) {
        const type = typeMap.value.get(Number(item?.kind_id));
        const category = categoryMap.value.get(Number(item?.category_id));
        const group = groupMap.value.get(Number(item?.group_id));
        return [group?.name, category?.name, type?.name].filter(Boolean).join(' > ') || '—';
    }

    function formatMoney(value) {
        const numeric = Number(value || 0);
        const formatted = formatNumberValue(numeric, {
            emptyValue: '0.00',
            invalidValue: 'NaN',
            locale: 'ru-RU',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return `${formatted} \u20BD`;
    }

    function toggleDepartment(option) {
        const selected = new Set(selectedDepartmentIds.value);
        const isSelected = selected.has(option.id);
        if (option.id === 'all_departments') {
            selectedDepartmentIds.value = isSelected ? [] : ['all_departments'];
            return;
        }
        if (isSelected) {
            selected.delete(option.id);
        } else {
            selected.add(option.id);
            selected.delete('all_departments');
        }
        selectedDepartmentIds.value = Array.from(selected);
    }

    function parseDepartmentFilters() {
        const selected = new Set(selectedDepartmentIds.value);
        const allRestaurantIds = departmentOptions.value
            .filter((option) => option.type === 'restaurant' && option.restaurant_id)
            .map((option) => Number(option.restaurant_id));
        const allSubdivisionIds = departmentOptions.value
            .filter((option) => option.type === 'subdivision' && option.subdivision_id)
            .map((option) => Number(option.subdivision_id));

        if (selected.has('all_departments')) {
            return {
                restaurant_ids: allRestaurantIds,
                subdivision_ids: allSubdivisionIds,
                include_warehouse: true,
            };
        }

        const restaurantIds = new Set();
        const subdivisionIds = new Set();
        let includeWarehouse = false;

        if (selected.has('all_restaurants')) {
            allRestaurantIds.forEach((id) => restaurantIds.add(id));
        }
        if (selected.has('warehouse')) {
            includeWarehouse = true;
        }

        for (const option of departmentOptions.value) {
            if (!selected.has(option.id)) {
                continue;
            }
            if (option.type === 'restaurant' && option.restaurant_id) {
                restaurantIds.add(Number(option.restaurant_id));
            }
            if (option.type === 'subdivision' && option.subdivision_id) {
                subdivisionIds.add(Number(option.subdivision_id));
            }
        }

        return {
            restaurant_ids: Array.from(restaurantIds),
            subdivision_ids: Array.from(subdivisionIds),
            include_warehouse: includeWarehouse,
        };
    }

    function toggleTag(tagValue) {
        const selected = new Set(selectedTagIds.value);
        if (selected.has(tagValue)) {
            selected.delete(tagValue);
        } else {
            selected.add(tagValue);
        }
        selectedTagIds.value = Array.from(selected);
    }

    function clearTags() {
        selectedTagIds.value = [];
    }

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
    }

    async function loadItemsByFilters() {
        if (!selectedDepartmentIds.value.length) {
            toast.error('Выберите хотя бы один объект');
            return;
        }
        loadingItems.value = true;
        try {
            const params = {
                ...parseDepartmentFilters(),
                only_in_locations: true,
            };
            const data = await fetchInventoryItems(params);
            items.value = Array.isArray(data) ? data : [];
            hasLoadedByFilters.value = true;
        } catch (error) {
            toast.error('Не удалось загрузить товары по тегам');
            console.error(error);
        } finally {
            loadingItems.value = false;
        }
    }

    function resetFilters() {
        selectedDepartmentIds.value = [];
        selectedTagIds.value = [];
        items.value = [];
        hasLoadedByFilters.value = false;
    }

    function openDetail(entry) {
        detailEntry.value = entry;
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
            element: tagFilterRef,
            when: () => isTagsOpen.value,
            onOutside: () => {
                isTagsOpen.value = false;
            },
        },
    ]);

    onMounted(async () => {
        try {
            await loadLookupData();
        } catch (error) {
            toast.error('Не удалось загрузить справочники');
            console.error(error);
        }
    });

    return {
        loadingItems,
        hasLoadedByFilters,
        isDepartmentsOpen,
        isTagsOpen,
        departmentSearch,
        selectedDepartmentIds,
        selectedTagIds,
        departmentSelectRef,
        tagFilterRef,
        detailEntry,
        tagOptions,
        filteredDepartmentOptions,
        selectedDepartmentLabels,
        departmentsLabel,
        tagFilterLabel,
        tagGroups,
        formatMoney,
        toggleDepartment,
        toggleTag,
        clearTags,
        loadItemsByFilters,
        resetFilters,
        openDetail,
    };
}
