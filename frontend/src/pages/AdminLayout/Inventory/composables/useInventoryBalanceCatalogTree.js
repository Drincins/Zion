import { computed, ref } from 'vue';

export function useInventoryBalanceCatalogTree({
    categories,
    groups,
    isDetailPaneVisible,
    items,
    searchQuery,
    selectedItemId,
    selectedRestaurantIdNum,
    selectedStoragePlaceIdNum,
    types,
}) {
    const expandedGroupIds = ref(new Set());
    const expandedCategoryIds = ref(new Set());
    const expandedKindIds = ref(new Set());

    const groupMap = computed(() => {
        const map = new Map();
        groups.value.forEach((entry) => map.set(Number(entry.id), entry));
        return map;
    });

    const categoryMap = computed(() => {
        const map = new Map();
        categories.value.forEach((entry) => map.set(Number(entry.id), entry));
        return map;
    });

    const typeMap = computed(() => {
        const map = new Map();
        types.value.forEach((entry) => map.set(Number(entry.id), entry));
        return map;
    });

    function getCatalogGroupName(groupId) {
        return groupMap.value.get(Number(groupId))?.name || `Группа #${groupId}`;
    }

    function getCatalogCategoryName(categoryId) {
        return categoryMap.value.get(Number(categoryId))?.name || `Категория #${categoryId}`;
    }

    function getCatalogTypeName(typeId, fallback = '') {
        return typeMap.value.get(Number(typeId))?.name || fallback || `Вид #${typeId}`;
    }

    function getCatalogPathByType(typeId) {
        const type = typeMap.value.get(Number(typeId));
        if (!type) {
            return '—';
        }
        const category = categoryMap.value.get(Number(type.category_id));
        const group = groupMap.value.get(Number(type.group_id));
        return [group?.name, category?.name, type.name].filter(Boolean).join(' > ');
    }

    function getCatalogPath(item) {
        if (item?.kind_id) {
            return getCatalogPathByType(item.kind_id);
        }
        return [getCatalogGroupName(item?.group_id || 0), getCatalogCategoryName(item?.category_id || 0)].join(' > ');
    }

    function getRestaurantLocationRows(item, restaurantId = selectedRestaurantIdNum.value, storagePlaceId = selectedStoragePlaceIdNum.value) {
        if (!restaurantId || !item) {
            return [];
        }
        const totals = Array.isArray(item.location_totals) ? item.location_totals : [];
        return totals.filter((row) => {
            if (row.location_kind !== 'restaurant' || Number(row.restaurant_id) !== Number(restaurantId)) {
                return false;
            }
            if (storagePlaceId === null) {
                return true;
            }
            return Number(row.storage_place_id || 0) === Number(storagePlaceId);
        });
    }

    function getRestaurantLocation(item, restaurantId = selectedRestaurantIdNum.value, storagePlaceId = selectedStoragePlaceIdNum.value) {
        const rows = getRestaurantLocationRows(item, restaurantId, storagePlaceId);
        if (!rows.length) {
            return null;
        }

        let quantity = 0;
        let weightedCost = 0;
        let hasAvgCost = false;
        let lastArrivalAt = null;

        rows.forEach((row) => {
            const rowQty = Number(row.quantity || 0);
            quantity += rowQty;
            const rowAvg = Number(row.avg_cost);
            if (Number.isFinite(rowAvg)) {
                weightedCost += rowAvg * rowQty;
                hasAvgCost = true;
            }
            if (row.last_arrival_at && (!lastArrivalAt || new Date(row.last_arrival_at).getTime() > new Date(lastArrivalAt).getTime())) {
                lastArrivalAt = row.last_arrival_at;
            }
        });

        return {
            quantity,
            avg_cost: hasAvgCost && quantity > 0 ? weightedCost / quantity : null,
            last_arrival_at: lastArrivalAt,
        };
    }

    const filteredItems = computed(() => {
        const needle = searchQuery.value.trim().toLowerCase();
        const source = items.value.filter((item) => {
            const row = getRestaurantLocation(item);
            return Number(row?.quantity || 0) > 0;
        });
        if (!needle) {
            return source;
        }
        return source.filter((item) => {
            const stack = [item.name, item.note, item.code, item.manufacturer, String(item.id)]
                .filter(Boolean)
                .join(' ')
                .toLowerCase();
            return stack.includes(needle);
        });
    });

    const groupedCatalog = computed(() => {
        const groupsMap = new Map();

        for (const item of filteredItems.value) {
            const location = getRestaurantLocation(item);
            if (!location || Number(location.quantity || 0) <= 0) {
                continue;
            }

            const groupId = Number(item.group_id || 0);
            const categoryId = Number(item.category_id || 0);
            const kindId = Number(item.kind_id || 0);

            let groupNode = groupsMap.get(groupId);
            if (!groupNode) {
                groupNode = {
                    id: groupId,
                    name: getCatalogGroupName(groupId),
                    categoriesMap: new Map(),
                    itemsCount: 0,
                };
                groupsMap.set(groupId, groupNode);
            }
            groupNode.itemsCount += 1;

            let categoryNode = groupNode.categoriesMap.get(categoryId);
            if (!categoryNode) {
                categoryNode = {
                    id: categoryId,
                    name: getCatalogCategoryName(categoryId),
                    kindsMap: new Map(),
                    itemsCount: 0,
                };
                groupNode.categoriesMap.set(categoryId, categoryNode);
            }
            categoryNode.itemsCount += 1;

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
                item,
                quantity: Number(location.quantity || 0),
                avgCost: location.avg_cost === null || location.avg_cost === undefined ? null : Number(location.avg_cost),
                lastArrivalAt: location.last_arrival_at || null,
            });
        }

        return Array.from(groupsMap.values())
            .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
            .map((groupNode) => ({
                id: groupNode.id,
                name: groupNode.name,
                itemsCount: groupNode.itemsCount,
                categories: Array.from(groupNode.categoriesMap.values())
                    .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
                    .map((categoryNode) => ({
                        id: categoryNode.id,
                        name: categoryNode.name,
                        itemsCount: categoryNode.itemsCount,
                        kinds: Array.from(categoryNode.kindsMap.values())
                            .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
                            .map((kindNode) => ({
                                id: kindNode.id,
                                name: kindNode.name,
                                items: [...kindNode.items].sort((a, b) =>
                                    String(a.item.name || '').localeCompare(String(b.item.name || ''), 'ru', { sensitivity: 'base' }),
                                ),
                            })),
                    })),
            }));
    });

    const groupedItemsCount = computed(() =>
        groupedCatalog.value.reduce((sum, groupNode) => sum + Number(groupNode.itemsCount || 0), 0),
    );

    const detailEntry = computed(() => {
        const itemId = Number(selectedItemId.value);
        if (!Number.isFinite(itemId) || itemId <= 0) {
            return null;
        }
        const item = filteredItems.value.find((entry) => Number(entry.id) === itemId);
        if (!item) {
            return null;
        }
        const location = getRestaurantLocation(item);
        if (!location) {
            return null;
        }
        return {
            item,
            quantity: Number(location.quantity || 0),
            avgCost: location.avg_cost === null || location.avg_cost === undefined ? null : Number(location.avg_cost),
            lastArrivalAt: location.last_arrival_at || null,
        };
    });

    function getHighlightedParts(value) {
        const source = String(value || '');
        const needle = searchQuery.value.trim();
        if (!needle || !source) {
            return [{ text: source, match: false }];
        }

        const sourceLower = source.toLowerCase();
        const needleLower = needle.toLowerCase();
        const parts = [];
        let cursor = 0;

        while (cursor < source.length) {
            const matchIndex = sourceLower.indexOf(needleLower, cursor);
            if (matchIndex === -1) {
                parts.push({ text: source.slice(cursor), match: false });
                break;
            }
            if (matchIndex > cursor) {
                parts.push({ text: source.slice(cursor, matchIndex), match: false });
            }
            parts.push({ text: source.slice(matchIndex, matchIndex + needle.length), match: true });
            cursor = matchIndex + needle.length;
        }

        return parts.length ? parts : [{ text: source, match: false }];
    }

    function isGroupExpanded(groupId) {
        return expandedGroupIds.value.has(Number(groupId));
    }

    function isCategoryExpanded(categoryId) {
        return expandedCategoryIds.value.has(Number(categoryId));
    }

    function isKindExpanded(kindId) {
        return expandedKindIds.value.has(Number(kindId));
    }

    function toggleSet(setRef, id) {
        const next = new Set(setRef.value);
        if (next.has(Number(id))) {
            next.delete(Number(id));
        } else {
            next.add(Number(id));
        }
        setRef.value = next;
    }

    function toggleGroup(groupId) {
        toggleSet(expandedGroupIds, groupId);
    }

    function toggleCategory(categoryId) {
        toggleSet(expandedCategoryIds, categoryId);
    }

    function toggleKind(kindId) {
        toggleSet(expandedKindIds, kindId);
    }

    function expandAllVisible() {
        const groupIds = new Set();
        const categoryIds = new Set();
        const kindIds = new Set();

        groupedCatalog.value.forEach((groupNode) => {
            groupIds.add(Number(groupNode.id));
            groupNode.categories.forEach((categoryNode) => {
                categoryIds.add(Number(categoryNode.id));
                categoryNode.kinds.forEach((kindNode) => {
                    kindIds.add(Number(kindNode.id));
                });
            });
        });

        expandedGroupIds.value = groupIds;
        expandedCategoryIds.value = categoryIds;
        expandedKindIds.value = kindIds;
    }

    function collapseAll() {
        expandedGroupIds.value = new Set();
        expandedCategoryIds.value = new Set();
        expandedKindIds.value = new Set();
    }

    function expandPathForItem(item) {
        if (!item) {
            return;
        }
        expandedGroupIds.value = new Set([...expandedGroupIds.value, Number(item.group_id)]);
        expandedCategoryIds.value = new Set([...expandedCategoryIds.value, Number(item.category_id)]);
        expandedKindIds.value = new Set([...expandedKindIds.value, Number(item.kind_id)]);
    }

    function ensureSelectedItem() {
        if (!filteredItems.value.length) {
            selectedItemId.value = null;
            return;
        }

        const exists = filteredItems.value.some((item) => Number(item.id) === Number(selectedItemId.value));
        if (exists) {
            return;
        }

        const fallback = filteredItems.value[0];
        selectedItemId.value = Number(fallback.id);
        expandPathForItem(fallback);
    }

    function openItemDetail(item) {
        selectedItemId.value = Number(item.id);
        expandPathForItem(item);
    }

    function toggleDetailPane() {
        isDetailPaneVisible.value = !isDetailPaneVisible.value;
    }

    return {
        categoryMap,
        collapseAll,
        detailEntry,
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
        getRestaurantLocation,
        getRestaurantLocationRows,
        groupedCatalog,
        groupedItemsCount,
        groupMap,
        isCategoryExpanded,
        isGroupExpanded,
        isKindExpanded,
        openItemDetail,
        toggleCategory,
        toggleDetailPane,
        toggleGroup,
        toggleKind,
        toggleSet,
        typeMap,
    };
}
