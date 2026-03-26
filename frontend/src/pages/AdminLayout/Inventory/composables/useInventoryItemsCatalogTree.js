import { computed, ref } from 'vue';

export function useInventoryItemsCatalogTree({ categories, groups, isCatalogModalOpen, itemForm, items, types }) {
    const filterExpandedGroupIds = ref(new Set());
    const filterExpandedCategoryIds = ref(new Set());
    const modalExpandedGroupIds = ref(new Set());
    const modalExpandedCategoryIds = ref(new Set());
    const selectedCatalogNodeIds = ref([]);

    const groupMap = computed(() => {
        const map = new Map();
        groups.value.forEach((group) => map.set(group.id, group));
        return map;
    });

    const categoryMap = computed(() => {
        const map = new Map();
        categories.value.forEach((category) => map.set(category.id, category));
        return map;
    });

    const typeMap = computed(() => {
        const map = new Map();
        types.value.forEach((type) => map.set(type.id, type));
        return map;
    });

    const sortedGroups = computed(() =>
        [...groups.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })),
    );
    const sortedCategories = computed(() =>
        [...categories.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })),
    );
    const sortedTypes = computed(() =>
        [...types.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })),
    );

    const categoriesByGroup = computed(() => {
        const map = new Map();
        for (const category of sortedCategories.value) {
            const bucket = map.get(category.group_id) || [];
            bucket.push(category);
            map.set(category.group_id, bucket);
        }
        return map;
    });

    const typesByCategory = computed(() => {
        const map = new Map();
        for (const type of sortedTypes.value) {
            const bucket = map.get(type.category_id) || [];
            bucket.push(type);
            map.set(type.category_id, bucket);
        }
        return map;
    });

    function parseCatalogNodeValue(value) {
        if (!value || !String(value).includes(':')) {
            return null;
        }
        const [level, idRaw] = String(value).split(':');
        const id = Number(idRaw);
        if (!Number.isFinite(id)) {
            return null;
        }
        return { level, id };
    }

    function getCatalogPathByType(typeId) {
        const type = typeMap.value.get(Number(typeId));
        if (!type) {
            return '—';
        }
        const category = categoryMap.value.get(type.category_id);
        const group = groupMap.value.get(type.group_id);
        return [group?.name, category?.name, type.name].filter(Boolean).join(' > ');
    }

    function getCatalogPath(item) {
        if (item?.kind_id) {
            return getCatalogPathByType(item.kind_id);
        }
        const groupName = groupMap.value.get(item?.group_id)?.name || `ID ${item?.group_id || '—'}`;
        const categoryName = categoryMap.value.get(item?.category_id)?.name || `ID ${item?.category_id || '—'}`;
        return [groupName, categoryName].join(' > ');
    }

    function getCatalogGroupName(groupId) {
        return groupMap.value.get(Number(groupId))?.name || `Группа #${groupId}`;
    }

    function getCatalogCategoryName(categoryId) {
        return categoryMap.value.get(Number(categoryId))?.name || `Категория #${categoryId}`;
    }

    function getCatalogTypeName(kindId, fallback = '') {
        return typeMap.value.get(Number(kindId))?.name || fallback || `Вид #${kindId}`;
    }

    function getCatalogNodeLabel(nodeValue) {
        if (!nodeValue) {
            return '';
        }
        const parsed = parseCatalogNodeValue(nodeValue);
        if (!parsed) {
            return '';
        }
        if (parsed.level === 'g') {
            return groupMap.value.get(parsed.id)?.name || `Раздел #${parsed.id}`;
        }
        if (parsed.level === 'c') {
            const category = categoryMap.value.get(parsed.id);
            if (!category) {
                return `Раздел #${parsed.id}`;
            }
            const groupName = groupMap.value.get(category.group_id)?.name || '';
            return [groupName, category.name].filter(Boolean).join(' > ');
        }
        if (parsed.level === 't') {
            return getCatalogPathByType(parsed.id);
        }
        return '';
    }

    const catalogFilterLabel = computed(() => {
        if (!selectedCatalogNodeIds.value.length) {
            return 'Все разделы';
        }
        const labels = selectedCatalogNodeIds.value
            .map((value) => getCatalogNodeLabel(value))
            .filter(Boolean);
        if (!labels.length) {
            return 'Все разделы';
        }
        if (labels.length <= 2) {
            return labels.join(', ');
        }
        return `${labels.slice(0, 2).join(', ')} +${labels.length - 2}`;
    });

    const catalogModalLabel = computed(() => getCatalogNodeLabel(itemForm.catalogNodeId) || 'Выберите раздел');

    function seedCatalogExpandedTrees() {
        filterExpandedGroupIds.value = new Set();
        filterExpandedCategoryIds.value = new Set();
        modalExpandedGroupIds.value = new Set();
        modalExpandedCategoryIds.value = new Set();
    }

    function toggleSet(setRef, id) {
        const next = new Set(setRef.value);
        if (next.has(id)) {
            next.delete(id);
        } else {
            next.add(id);
        }
        setRef.value = next;
    }

    function isFilterGroupExpanded(groupId) {
        return filterExpandedGroupIds.value.has(groupId);
    }

    function isFilterCategoryExpanded(categoryId) {
        return filterExpandedCategoryIds.value.has(categoryId);
    }

    function isModalGroupExpanded(groupId) {
        return modalExpandedGroupIds.value.has(groupId);
    }

    function isModalCategoryExpanded(categoryId) {
        return modalExpandedCategoryIds.value.has(categoryId);
    }

    function toggleFilterGroup(groupId) {
        toggleSet(filterExpandedGroupIds, groupId);
    }

    function toggleFilterCategory(categoryId) {
        toggleSet(filterExpandedCategoryIds, categoryId);
    }

    function toggleModalGroup(groupId) {
        toggleSet(modalExpandedGroupIds, groupId);
    }

    function toggleModalCategory(categoryId) {
        toggleSet(modalExpandedCategoryIds, categoryId);
    }

    function isCatalogNodeSelected(value) {
        return selectedCatalogNodeIds.value.includes(value);
    }

    function toggleFilterCatalogNode(value) {
        const next = new Set(selectedCatalogNodeIds.value);
        if (next.has(value)) {
            next.delete(value);
        } else {
            next.add(value);
        }
        selectedCatalogNodeIds.value = Array.from(next);
    }

    function clearFilterCatalogNodes() {
        selectedCatalogNodeIds.value = [];
    }

    function selectModalType(typeId) {
        itemForm.catalogNodeId = `t:${typeId}`;
        isCatalogModalOpen.value = false;
    }

    function matchCatalogNode(item, nodeValue) {
        const parsed = parseCatalogNodeValue(nodeValue);
        if (!parsed) {
            return false;
        }
        if (parsed.level === 'g') {
            return Number(item.group_id) === parsed.id;
        }
        if (parsed.level === 'c') {
            return Number(item.category_id) === parsed.id;
        }
        if (parsed.level === 't') {
            return Number(item.kind_id) === parsed.id;
        }
        return false;
    }

    const filteredItems = computed(() => {
        if (!selectedCatalogNodeIds.value.length) {
            return items.value;
        }
        return items.value.filter((item) =>
            selectedCatalogNodeIds.value.some((nodeValue) => matchCatalogNode(item, nodeValue)),
        );
    });

    const groupedInventory = computed(() => {
        const locationMap = new Map();

        for (const item of filteredItems.value) {
            const locations = Array.isArray(item.location_totals) ? item.location_totals : [];
            for (const location of locations) {
                const quantity = Number(location.quantity || 0);
                if (quantity <= 0) {
                    continue;
                }

                const locationKey = `${location.location_kind}:${location.restaurant_id || ''}:${location.subdivision_id || ''}`;
                let locationNode = locationMap.get(locationKey);
                if (!locationNode) {
                    locationNode = {
                        key: locationKey,
                        name: location.location_name || 'Подразделение',
                        groupsMap: new Map(),
                    };
                    locationMap.set(locationKey, locationNode);
                }

                const groupId = Number(item.group_id || 0);
                let groupNode = locationNode.groupsMap.get(groupId);
                if (!groupNode) {
                    groupNode = {
                        id: groupId,
                        name: getCatalogGroupName(groupId),
                        categoriesMap: new Map(),
                    };
                    locationNode.groupsMap.set(groupId, groupNode);
                }

                const categoryId = Number(item.category_id || 0);
                let categoryNode = groupNode.categoriesMap.get(categoryId);
                if (!categoryNode) {
                    categoryNode = {
                        id: categoryId,
                        name: getCatalogCategoryName(categoryId),
                        kindsMap: new Map(),
                    };
                    groupNode.categoriesMap.set(categoryId, categoryNode);
                }

                const kindId = Number(item.kind_id || 0);
                let kindNode = categoryNode.kindsMap.get(kindId);
                if (!kindNode) {
                    kindNode = {
                        id: kindId,
                        name: getCatalogTypeName(kindId, item.kind_name),
                        items: [],
                    };
                    categoryNode.kindsMap.set(kindId, kindNode);
                }

                kindNode.items.push({
                    key: `${locationKey}:${item.id}`,
                    quantity,
                    locationAvgCost: location.avg_cost ?? null,
                    locationName: location.location_name || 'Подразделение',
                    locationKind: location.location_kind,
                    locationRestaurantId: location.restaurant_id || null,
                    locationSubdivisionId: location.subdivision_id || null,
                    item,
                });
            }
        }

        return Array.from(locationMap.values())
            .map((locationNode) => ({
                key: locationNode.key,
                name: locationNode.name,
                groups: Array.from(locationNode.groupsMap.values())
                    .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
                    .map((groupNode) => ({
                        id: groupNode.id,
                        name: groupNode.name,
                        categories: Array.from(groupNode.categoriesMap.values())
                            .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
                            .map((categoryNode) => ({
                                id: categoryNode.id,
                                name: categoryNode.name,
                                kinds: Array.from(categoryNode.kindsMap.values())
                                    .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
                                    .map((kindNode) => ({
                                        id: kindNode.id,
                                        name: kindNode.name,
                                        items: [...kindNode.items].sort((a, b) =>
                                            (a.item.name || '').localeCompare(b.item.name || '', 'ru', { sensitivity: 'base' }),
                                        ),
                                    })),
                            })),
                    })),
            }))
            .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }));
    });

    return {
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
    };
}
