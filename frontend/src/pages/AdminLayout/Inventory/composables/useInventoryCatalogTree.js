import { computed, ref } from 'vue';

const TREE_STATE_STORAGE_KEY = 'zion.inventory.catalog.tree.v1';
export const DETAIL_PANE_STORAGE_KEY = 'zion.inventory.catalog.detail-pane.v1';

export function useInventoryCatalogTree({
    categories,
    groups,
    isCatalogModalOpen,
    isDetailPaneVisible,
    itemForm,
    items,
    searchQuery,
    selectedItemId,
    types,
}) {
    const expandedGroupIds = ref(new Set());
    const expandedCategoryIds = ref(new Set());
    const expandedKindIds = ref(new Set());
    const modalExpandedGroupIds = ref(new Set());
    const modalExpandedCategoryIds = ref(new Set());

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

    const sortedGroups = computed(() =>
        [...groups.value].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' })),
    );

    const sortedCategories = computed(() =>
        [...categories.value].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' })),
    );

    const sortedTypes = computed(() =>
        [...types.value].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' })),
    );

    const categoriesByGroup = computed(() => {
        const map = new Map();
        for (const category of sortedCategories.value) {
            const bucket = map.get(Number(category.group_id)) || [];
            bucket.push(category);
            map.set(Number(category.group_id), bucket);
        }
        return map;
    });

    const typesByCategory = computed(() => {
        const map = new Map();
        for (const type of sortedTypes.value) {
            const bucket = map.get(Number(type.category_id)) || [];
            bucket.push(type);
            map.set(Number(type.category_id), bucket);
        }
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
        const groupName = getCatalogGroupName(item?.group_id || 0);
        const categoryName = getCatalogCategoryName(item?.category_id || 0);
        return `${groupName} > ${categoryName}`;
    }

    const selectedTypeLabel = computed(() => {
        if (!itemForm.typeId) {
            return 'Выберите раздел';
        }
        return getCatalogPathByType(itemForm.typeId);
    });

    const filteredItems = computed(() => {
        const needle = searchQuery.value.trim().toLowerCase();
        if (!needle) {
            return items.value;
        }
        return items.value.filter((item) => {
            const stack = [item.name, item.note, item.code, String(item.id)]
                .filter(Boolean)
                .join(' ')
                .toLowerCase();
            return stack.includes(needle);
        });
    });

    const detailItem = computed(() => {
        const id = Number(selectedItemId.value);
        if (!Number.isFinite(id)) {
            return null;
        }
        return items.value.find((item) => Number(item.id) === id) || null;
    });

    const groupedCatalog = computed(() => {
        const groupsMap = new Map();

        for (const item of filteredItems.value) {
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
            kindNode.items.push(item);
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
                                    String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }),
                                ),
                            })),
                    })),
            }));
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

    function toIdSet(values) {
        if (!Array.isArray(values)) {
            return new Set();
        }
        return new Set(
            values
                .map((value) => Number(value))
                .filter((value) => Number.isFinite(value)),
        );
    }

    function persistExpandedTree() {
        if (typeof window === 'undefined') {
            return;
        }
        const payload = {
            groups: Array.from(expandedGroupIds.value),
            categories: Array.from(expandedCategoryIds.value),
            kinds: Array.from(expandedKindIds.value),
        };
        window.localStorage.setItem(TREE_STATE_STORAGE_KEY, JSON.stringify(payload));
    }

    function restoreExpandedTree() {
        if (typeof window === 'undefined') {
            return;
        }
        const rawState = window.localStorage.getItem(TREE_STATE_STORAGE_KEY);
        if (!rawState) {
            return;
        }

        try {
            const parsed = JSON.parse(rawState);
            const knownGroups = new Set(groups.value.map((entry) => Number(entry.id)));
            const knownCategories = new Set(categories.value.map((entry) => Number(entry.id)));
            const knownKinds = new Set(types.value.map((entry) => Number(entry.id)));

            expandedGroupIds.value = new Set([...toIdSet(parsed?.groups)].filter((id) => knownGroups.has(id)));
            expandedCategoryIds.value = new Set([...toIdSet(parsed?.categories)].filter((id) => knownCategories.has(id)));
            expandedKindIds.value = new Set([...toIdSet(parsed?.kinds)].filter((id) => knownKinds.has(id)));
        } catch (error) {
            console.warn('Не удалось восстановить состояние дерева каталога', error);
        }
    }

    function restoreDetailPanePreference() {
        if (typeof window === 'undefined') {
            return;
        }
        const value = window.localStorage.getItem(DETAIL_PANE_STORAGE_KEY);
        if (value === null) {
            return;
        }
        isDetailPaneVisible.value = value !== '0';
    }

    function toggleSet(setRef, id, options = {}) {
        const { persist = false } = options;
        const next = new Set(setRef.value);
        if (next.has(Number(id))) {
            next.delete(Number(id));
        } else {
            next.add(Number(id));
        }
        setRef.value = next;
        if (persist) {
            persistExpandedTree();
        }
    }

    function toggleGroup(groupId) {
        toggleSet(expandedGroupIds, groupId, { persist: true });
    }

    function toggleCategory(categoryId) {
        toggleSet(expandedCategoryIds, categoryId, { persist: true });
    }

    function toggleKind(kindId) {
        toggleSet(expandedKindIds, kindId, { persist: true });
    }

    function seedExpandedTree(options = {}) {
        const { persist = false } = options;
        expandedGroupIds.value = new Set();
        expandedCategoryIds.value = new Set();
        expandedKindIds.value = new Set();
        if (persist) {
            persistExpandedTree();
        }
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
        persistExpandedTree();
    }

    function collapseAll() {
        seedExpandedTree({ persist: true });
    }

    function expandPathForItem(item) {
        if (!item) {
            return;
        }
        const groupId = Number(item.group_id);
        const categoryId = Number(item.category_id);
        const kindId = Number(item.kind_id);

        if (Number.isFinite(groupId)) {
            expandedGroupIds.value = new Set([...expandedGroupIds.value, groupId]);
        }
        if (Number.isFinite(categoryId)) {
            expandedCategoryIds.value = new Set([...expandedCategoryIds.value, categoryId]);
        }
        if (Number.isFinite(kindId)) {
            expandedKindIds.value = new Set([...expandedKindIds.value, kindId]);
        }
        persistExpandedTree();
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

    function isModalGroupExpanded(groupId) {
        return modalExpandedGroupIds.value.has(Number(groupId));
    }

    function isModalCategoryExpanded(categoryId) {
        return modalExpandedCategoryIds.value.has(Number(categoryId));
    }

    function toggleModalGroup(groupId) {
        toggleSet(modalExpandedGroupIds, groupId);
    }

    function toggleModalCategory(categoryId) {
        toggleSet(modalExpandedCategoryIds, categoryId);
    }

    function selectModalType(typeId) {
        itemForm.typeId = String(typeId);
        isCatalogModalOpen.value = false;
    }

    function seedModalPickerTree() {
        modalExpandedGroupIds.value = new Set();
        modalExpandedCategoryIds.value = new Set();
    }

    return {
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
    };
}
