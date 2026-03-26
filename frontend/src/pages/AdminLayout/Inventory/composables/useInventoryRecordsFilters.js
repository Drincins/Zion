import { computed, reactive, ref } from 'vue';

import { useClickOutside } from '@/composables/useClickOutside';

export function useInventoryRecordsFilters({
    actions,
    categories,
    departments,
    groups,
    items,
    staff,
}) {
    const isFiltersOpen = ref(true);

    const dateFrom = ref('');
    const dateTo = ref('');
    const searchQuery = ref('');

    const selectedFilters = reactive({
        catalog: [],
        objects: [],
        actions: [],
        actors: [],
    });

    const dropdownState = reactive({
        catalog: false,
        objects: false,
        actions: false,
        actors: false,
    });

    const filterRefs = reactive({
        catalog: null,
        objects: null,
        actions: null,
        actors: null,
    });

    const catalogExpandedGroupIds = ref(new Set());
    const catalogExpandedCategoryIds = ref(new Set());

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

    const itemMap = computed(() => {
        const map = new Map();
        items.value.forEach((item) => map.set(Number(item.id), item));
        return map;
    });

    const groupedCatalogOptions = computed(() => {
        const groupsMap = new Map();
        for (const item of items.value) {
            const groupId = Number(item.group_id || 0);
            const categoryId = Number(item.category_id || 0);
            let groupNode = groupsMap.get(groupId);
            if (!groupNode) {
                groupNode = {
                    id: groupId,
                    name: groupMap.value.get(groupId)?.name || `Группа #${groupId}`,
                    categoriesMap: new Map(),
                };
                groupsMap.set(groupId, groupNode);
            }
            let categoryNode = groupNode.categoriesMap.get(categoryId);
            if (!categoryNode) {
                categoryNode = {
                    id: categoryId,
                    name: categoryMap.value.get(categoryId)?.name || `Категория #${categoryId}`,
                    items: [],
                };
                groupNode.categoriesMap.set(categoryId, categoryNode);
            }
            categoryNode.items.push(item);
        }

        return Array.from(groupsMap.values())
            .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }))
            .map((groupNode) => ({
                id: groupNode.id,
                name: groupNode.name,
                categories: Array.from(groupNode.categoriesMap.values())
                    .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }))
                    .map((categoryNode) => ({
                        id: categoryNode.id,
                        name: categoryNode.name,
                        items: [...categoryNode.items].sort((a, b) =>
                            String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }),
                        ),
                    })),
            }));
    });

    const objectOptions = computed(() => {
        const source = departments.value.filter((option) =>
            ['warehouse', 'restaurant', 'subdivision'].includes(option.type),
        );
        const ordered = [...source].sort((a, b) => {
            const rank = (entry) => {
                if (entry.type === 'warehouse') return 0;
                if (entry.type === 'restaurant') return 1;
                return 2;
            };
            const rankDiff = rank(a) - rank(b);
            if (rankDiff !== 0) return rankDiff;
            return String(a.label || '').localeCompare(String(b.label || ''), 'ru', { sensitivity: 'base' });
        });
        return ordered.map((option) => ({ value: option.id, label: option.label }));
    });

    const actionOptions = computed(() =>
        actions.value
            .map((action) => ({ value: action.value, label: action.label }))
            .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
    );

    const actorOptions = computed(() =>
        staff.value
            .map((user) => ({ value: String(user.id), label: formatUser(user) }))
            .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
    );

    const catalogFilterLabel = computed(() =>
        buildCatalogFilterLabel(selectedFilters.catalog, 'Все товары и категории'),
    );
    const objectFilterLabel = computed(() => buildFilterLabel(selectedFilters.objects, objectOptions.value, 'Все объекты'));
    const actionFilterLabel = computed(() => buildFilterLabel(selectedFilters.actions, actionOptions.value, 'Все действия'));
    const actorFilterLabel = computed(() => buildFilterLabel(selectedFilters.actors, actorOptions.value, 'Все сотрудники'));

    function setFilterRef(key, element) {
        filterRefs[key] = element;
    }

    function closeAllDropdowns(exceptKey = '') {
        Object.keys(dropdownState).forEach((key) => {
            if (key !== exceptKey) {
                dropdownState[key] = false;
            }
        });
    }

    function toggleDropdown(key) {
        const nextState = !dropdownState[key];
        closeAllDropdowns(nextState ? key : '');
        dropdownState[key] = nextState;
    }

    function toggleSelection(key, value) {
        const selected = selectedFilters[key];
        const index = selected.indexOf(value);
        if (index >= 0) {
            selected.splice(index, 1);
            return;
        }
        selected.push(value);
    }

    function clearSelection(key) {
        selectedFilters[key].splice(0, selectedFilters[key].length);
    }

    function clearAllFilters() {
        dateFrom.value = '';
        dateTo.value = '';
        searchQuery.value = '';
        clearSelection('catalog');
        clearSelection('objects');
        clearSelection('actions');
        clearSelection('actors');
        closeAllDropdowns();
    }

    function buildFilterLabel(selectedValues, options, fallback) {
        if (!selectedValues.length) {
            return fallback;
        }
        if (selectedValues.length === 1) {
            const selectedOption = options.find((option) => option.value === selectedValues[0]);
            return selectedOption ? selectedOption.label : fallback;
        }
        return `Выбрано: ${selectedValues.length}`;
    }

    function parseCatalogToken(value) {
        if (!value || !String(value).includes(':')) {
            return null;
        }
        const [kind, idRaw] = String(value).split(':');
        const id = Number(idRaw);
        if (!Number.isFinite(id)) {
            return null;
        }
        return { kind, id };
    }

    function getCatalogNodeLabel(value) {
        const parsed = parseCatalogToken(value);
        if (!parsed) {
            return '';
        }
        if (parsed.kind === 'g') {
            return groupMap.value.get(parsed.id)?.name || `Группа #${parsed.id}`;
        }
        if (parsed.kind === 'c') {
            const category = categoryMap.value.get(parsed.id);
            if (!category) {
                return `Категория #${parsed.id}`;
            }
            const groupName = groupMap.value.get(Number(category.group_id))?.name || '';
            return [groupName, category.name].filter(Boolean).join(' > ');
        }
        if (parsed.kind === 'i') {
            const item = itemMap.value.get(parsed.id);
            return item ? `${item.code || `ITEM-${item.id}`} · ${item.name}` : `Товар #${parsed.id}`;
        }
        return '';
    }

    function buildCatalogFilterLabel(selectedValues, fallback) {
        if (!selectedValues.length) {
            return fallback;
        }
        if (selectedValues.length === 1) {
            return getCatalogNodeLabel(selectedValues[0]) || fallback;
        }
        return `Выбрано: ${selectedValues.length}`;
    }

    function isCatalogGroupExpanded(groupId) {
        return catalogExpandedGroupIds.value.has(Number(groupId));
    }

    function isCatalogCategoryExpanded(categoryId) {
        return catalogExpandedCategoryIds.value.has(Number(categoryId));
    }

    function toggleCatalogGroup(groupId) {
        const next = new Set(catalogExpandedGroupIds.value);
        if (next.has(Number(groupId))) {
            next.delete(Number(groupId));
        } else {
            next.add(Number(groupId));
        }
        catalogExpandedGroupIds.value = next;
    }

    function toggleCatalogCategory(categoryId) {
        const next = new Set(catalogExpandedCategoryIds.value);
        if (next.has(Number(categoryId))) {
            next.delete(Number(categoryId));
        } else {
            next.add(Number(categoryId));
        }
        catalogExpandedCategoryIds.value = next;
    }

    function formatUser(user) {
        if (!user) {
            return '';
        }
        const fullName = [user.last_name, user.first_name, user.patronymic].filter(Boolean).join(' ').trim();
        return fullName || user.username || `ID ${user.id}`;
    }

    function buildMovementParams() {
        const params = { limit: 1000 };
        if (dateFrom.value) {
            params.created_from = `${dateFrom.value}T00:00:00+03:00`;
        }
        if (dateTo.value) {
            params.created_to = `${dateTo.value}T23:59:59+03:00`;
        }
        const query = searchQuery.value.trim();
        if (query) {
            params.q = query;
        }
        if (selectedFilters.catalog.length) {
            const itemIds = new Set();
            for (const token of selectedFilters.catalog) {
                const parsed = parseCatalogToken(token);
                if (!parsed) {
                    continue;
                }
                if (parsed.kind === 'i') {
                    itemIds.add(parsed.id);
                    continue;
                }
                if (parsed.kind === 'c') {
                    items.value
                        .filter((item) => Number(item.category_id) === parsed.id)
                        .forEach((item) => itemIds.add(Number(item.id)));
                    continue;
                }
                if (parsed.kind === 'g') {
                    items.value
                        .filter((item) => Number(item.group_id) === parsed.id)
                        .forEach((item) => itemIds.add(Number(item.id)));
                }
            }
            if (itemIds.size) {
                params.item_ids = Array.from(itemIds);
            }
        }
        if (selectedFilters.objects.length) {
            params.object_ids = [...selectedFilters.objects];
        }
        if (selectedFilters.actions.length) {
            params.action_types = [...selectedFilters.actions];
        }
        if (selectedFilters.actors.length) {
            params.actor_ids = selectedFilters.actors.map((id) => Number(id));
        }
        return params;
    }

    useClickOutside(() =>
        Object.keys(filterRefs).map((key) => ({
            element: () => filterRefs[key],
            when: () => Boolean(dropdownState[key]),
            onOutside: () => {
                dropdownState[key] = false;
            },
        })),
    );

    return {
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
    };
}
