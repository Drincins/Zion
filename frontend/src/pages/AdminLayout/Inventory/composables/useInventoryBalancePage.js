import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';

import { INVENTORY_MOVEMENTS_CREATE_PERMISSIONS } from '@/accessPolicy';
import {
    allocateInventoryItem,
    fetchInventoryStoragePlaces,
    createInventoryItemInstanceEvent,
    fetchInventoryCategories,
    fetchInventoryBalanceItemCard,
    fetchInventoryGroups,
    fetchInventoryInstanceEventTypes,
    fetchInventoryItems,
    fetchInventoryItemInstanceEvents,
    fetchInventoryTypes,
    fetchRestaurants,
    transferInventoryItem,
    updateInventoryItemQuantity,
} from '@/api';
import { useUserStore } from '@/stores/user';
import { formatDateTimeValue, formatNumberValue } from '@/utils/format';

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

    const expandedGroupIds = ref(new Set());
    const expandedCategoryIds = ref(new Set());
    const expandedKindIds = ref(new Set());
    const selectedItemId = ref(null);
    const isDetailPaneVisible = ref(true);
    const detailCard = ref(null);
    const detailCardLoading = ref(false);
    const detailTab = ref('arrivals');
    const selectedInstanceCode = ref('');
    const instanceEvents = ref([]);
    const instanceEventTypes = ref([]);
    const instanceEventsLoading = ref(false);
    const isItemCardModalOpen = ref(false);
    const isInstanceEventModalOpen = ref(false);
    const instanceEventSubmitting = ref(false);
    const isOperationModalOpen = ref(false);
    const operationSubmitting = ref(false);
    const operationType = ref('income');
    const instanceEventForm = reactive({
        instanceId: null,
        eventTypeId: '',
        comment: '',
    });
    const operationForm = reactive({
        itemId: '',
        quantity: '1',
        unitCost: '',
        sourceStoragePlaceId: 'none',
        targetRestaurantId: '',
        targetStoragePlaceId: 'none',
        reason: '',
    });
    const selectedOperationItemDetails = ref(null);
    const operationItemLoading = ref(false);
    let detailCardRequestId = 0;
    let instanceEventsRequestId = 0;
    let operationItemRequestId = 0;

    const instanceEventTypeOptions = computed(() =>
        [...instanceEventTypes.value]
            .filter((entry) => Boolean(entry?.is_manual) && Boolean(entry?.is_active))
            .sort((left, right) => {
                const sortDelta = Number(left?.sort_order || 100) - Number(right?.sort_order || 100);
                if (sortDelta !== 0) {
                    return sortDelta;
                }
                return String(left?.name || '').localeCompare(String(right?.name || ''), 'ru', { sensitivity: 'base' });
            })
            .map((entry) => ({
                value: String(entry.id),
                label: entry.name,
            })),
    );

    const OPERATION_TYPE_OPTIONS = [
        { value: 'income', label: 'Приход' },
        { value: 'transfer', label: 'Перемещение' },
        { value: 'writeoff', label: 'Списание' },
    ];

    const operationTypeOptions = OPERATION_TYPE_OPTIONS;
    const canCreateMovement = computed(() => userStore.hasAnyPermission(...INVENTORY_MOVEMENTS_CREATE_PERMISSIONS));
    const isIncomeOperation = computed(() => operationType.value === 'income');
    const isTransferOperation = computed(() => operationType.value === 'transfer');
    const isWriteoffOperation = computed(() => operationType.value === 'writeoff');

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

    const operationItemOptions = computed(() =>
        [...catalogItems.value]
            .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }))
            .map((item) => ({
                value: String(item.id),
                label: `${item.code || `ITEM-${item.id}`} · ${item.name}`,
            })),
    );

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

    const detailArrivals = computed(() => (Array.isArray(detailCard.value?.arrivals) ? detailCard.value.arrivals : []));
    const instanceSummaries = computed(() => {
        const source = Array.isArray(detailCard.value?.instances) ? detailCard.value.instances : [];
        return [...source].sort((left, right) => compareInstanceSummaries(left, right));
    });
    const instanceTrackingEnabled = computed(() => Boolean(detailCard.value?.instance_tracking_enabled));
    const selectedInstanceSummary = computed(() =>
        instanceSummaries.value.find((entry) => entry.instance_code === selectedInstanceCode.value) || null,
    );
    const currentInstanceCount = computed(() => instanceSummaries.value.filter((entry) => entry.is_current).length);
    const historicalInstanceCount = computed(() => instanceSummaries.value.filter((entry) => !entry.is_current).length);

    function getInstanceCodeSortParts(code) {
        const value = String(code || '').trim();
        const match = value.match(/^(.*?)(\d+)$/);
        if (!match) {
            return { prefix: value.toLowerCase(), sequence: null };
        }
        return {
            prefix: String(match[1] || '').toLowerCase(),
            sequence: Number(match[2]),
        };
    }

    function compareInstanceSummaries(left, right) {
        if (Boolean(left?.is_current) !== Boolean(right?.is_current)) {
            return left?.is_current ? -1 : 1;
        }

        const leftParts = getInstanceCodeSortParts(left?.instance_code);
        const rightParts = getInstanceCodeSortParts(right?.instance_code);

        const prefixCompare = leftParts.prefix.localeCompare(rightParts.prefix, 'ru', { sensitivity: 'base' });
        if (prefixCompare !== 0) {
            return prefixCompare;
        }

        if (leftParts.sequence !== null && rightParts.sequence !== null && leftParts.sequence !== rightParts.sequence) {
            return leftParts.sequence - rightParts.sequence;
        }

        if (leftParts.sequence !== null && rightParts.sequence === null) {
            return -1;
        }
        if (leftParts.sequence === null && rightParts.sequence !== null) {
            return 1;
        }

        return String(left?.instance_code || '').localeCompare(String(right?.instance_code || ''), 'ru', { sensitivity: 'base' });
    }

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

    function resetInstanceState() {
        detailCard.value = null;
        detailTab.value = 'arrivals';
        selectedInstanceCode.value = '';
        instanceEvents.value = [];
        isItemCardModalOpen.value = false;
    }

    function ensureSelectedInstance() {
        if (!instanceTrackingEnabled.value || !instanceSummaries.value.length) {
            selectedInstanceCode.value = '';
            instanceEvents.value = [];
            return;
        }
        const exists = instanceSummaries.value.some((entry) => entry.instance_code === selectedInstanceCode.value);
        if (exists) {
            return;
        }
        const fallback = instanceSummaries.value.find((entry) => entry.is_current) || instanceSummaries.value[0];
        selectedInstanceCode.value = fallback?.instance_code || '';
    }

    async function loadDetailCard() {
        const restaurantId = selectedRestaurantIdNum.value;
        const itemId = Number(selectedItemId.value);
        const storagePlaceId = selectedStoragePlaceIdNum.value;
        if (!restaurantId || !Number.isFinite(itemId) || itemId <= 0 || !isItemCardModalOpen.value) {
            resetInstanceState();
            return;
        }

        const requestId = ++detailCardRequestId;
        detailCardLoading.value = true;
        try {
            const data = await fetchInventoryBalanceItemCard(restaurantId, itemId, {
                storage_place_id: storagePlaceId ?? undefined,
            });
            if (requestId !== detailCardRequestId) {
                return;
            }
            detailCard.value = data || null;
            ensureSelectedInstance();
        } catch (error) {
            if (requestId !== detailCardRequestId) {
                return;
            }
            resetInstanceState();
            toast.error('Не удалось загрузить карточку товара по ресторану');
            console.error(error);
        } finally {
            if (requestId === detailCardRequestId) {
                detailCardLoading.value = false;
            }
        }
    }

    async function loadInstanceEvents() {
        const restaurantId = selectedRestaurantIdNum.value;
        const itemId = Number(selectedItemId.value);
        const storagePlaceId = selectedStoragePlaceIdNum.value;
        const instanceCode = String(selectedInstanceCode.value || '').trim();
        if (!restaurantId || !Number.isFinite(itemId) || itemId <= 0 || !instanceCode || !instanceTrackingEnabled.value || !isItemCardModalOpen.value) {
            instanceEvents.value = [];
            return;
        }

        const requestId = ++instanceEventsRequestId;
        instanceEventsLoading.value = true;
        try {
            const data = await fetchInventoryItemInstanceEvents(restaurantId, itemId, instanceCode, {
                storage_place_id: storagePlaceId ?? undefined,
            });
            if (requestId !== instanceEventsRequestId) {
                return;
            }
            instanceEvents.value = Array.isArray(data) ? data : [];
        } catch (error) {
            if (requestId !== instanceEventsRequestId) {
                return;
            }
            instanceEvents.value = [];
            toast.error('Не удалось загрузить историю по выбранному коду');
            console.error(error);
        } finally {
            if (requestId === instanceEventsRequestId) {
                instanceEventsLoading.value = false;
            }
        }
    }

    function selectInstance(instanceCode) {
        selectedInstanceCode.value = String(instanceCode || '');
    }

    function openInstanceEventModal() {
        if (!selectedInstanceSummary.value?.instance_id) {
            return;
        }
        if (!instanceEventTypeOptions.value.length) {
            toast.warning('Сначала добавь хотя бы один активный тип работ в настройках склада');
            return;
        }
        instanceEventForm.instanceId = Number(selectedInstanceSummary.value.instance_id);
        instanceEventForm.eventTypeId = String(instanceEventTypeOptions.value[0]?.value || '');
        instanceEventForm.comment = '';
        isInstanceEventModalOpen.value = true;
    }

    function closeInstanceEventModal() {
        isInstanceEventModalOpen.value = false;
        instanceEventForm.instanceId = null;
        instanceEventForm.eventTypeId = String(instanceEventTypeOptions.value[0]?.value || '');
        instanceEventForm.comment = '';
    }

    function openItemCard(item) {
        if (item) {
            openItemDetail(item);
        }
        detailTab.value = 'arrivals';
        isItemCardModalOpen.value = true;
        void loadDetailCard();
    }

    function closeItemCard() {
        isItemCardModalOpen.value = false;
        detailTab.value = 'arrivals';
        selectedInstanceCode.value = '';
        instanceEvents.value = [];
        detailCard.value = null;
    }

    function parseQuantity(value) {
        const quantity = Number.parseInt(String(value || '0'), 10);
        if (!Number.isFinite(quantity) || quantity <= 0) {
            return null;
        }
        return quantity;
    }

    function parseUnitCost(value) {
        const normalized = String(value || '').replace(',', '.').trim();
        if (!normalized) {
            return null;
        }
        const amount = Number.parseFloat(normalized);
        if (!Number.isFinite(amount) || amount < 0) {
            return NaN;
        }
        return amount;
    }

    function parseStoragePlaceValue(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    }

    function buildStoragePlaceOptionsForRestaurant(restaurantId, { includeAll = false } = {}) {
        const options = [];
        if (includeAll) {
            options.push({ value: 'all', label: 'Все места хранения' });
        }
        options.push({ value: 'none', label: 'Без места хранения' });
        storagePlaces.value
            .filter((place) => Boolean(place?.is_active) && Number(place?.restaurant_id) === Number(restaurantId))
            .sort((a, b) => String(a?.name || '').localeCompare(String(b?.name || ''), 'ru', { sensitivity: 'base' }))
            .forEach((place) => {
                options.push({ value: String(place.id), label: place.name });
            });
        return options;
    }

    const selectedOperationItem = computed(() => {
        const itemId = Number(operationForm.itemId);
        if (!Number.isFinite(itemId) || itemId <= 0) {
            return null;
        }
        if (selectedOperationItemDetails.value && Number(selectedOperationItemDetails.value.id) === itemId) {
            return selectedOperationItemDetails.value;
        }
        return catalogItems.value.find((item) => Number(item.id) === itemId) || null;
    });

    const sourceStoragePlaceOptions = computed(() =>
        buildStoragePlaceOptionsForRestaurant(selectedRestaurantIdNum.value),
    );

    const targetStoragePlaceOptions = computed(() => {
        const targetRestaurantId = isTransferOperation.value
            ? Number(operationForm.targetRestaurantId || 0)
            : Number(selectedRestaurantIdNum.value || 0);
        return buildStoragePlaceOptionsForRestaurant(targetRestaurantId || null);
    });

    const sourceLocationQuantity = computed(() => {
        const storagePlaceId = parseStoragePlaceValue(operationForm.sourceStoragePlaceId);
        return Number(getRestaurantLocation(selectedOperationItem.value, selectedRestaurantIdNum.value, storagePlaceId)?.quantity || 0);
    });

    const operationTargetStoragePlaceLabel = computed(() => {
        const restaurantId = isTransferOperation.value
            ? Number(operationForm.targetRestaurantId || 0)
            : Number(selectedRestaurantIdNum.value || 0);
        const option = buildStoragePlaceOptionsForRestaurant(restaurantId).find(
            (entry) => String(entry.value) === String(operationForm.targetStoragePlaceId),
        );
        return option?.label || 'Без места хранения';
    });

    const operationDraftRecord = computed(() => {
        const quantity = parseQuantity(operationForm.quantity);
        const selectedType = operationTypeOptions.find((option) => option.value === operationType.value);
        const defaultWhat = selectedOperationItem.value
            ? `${selectedOperationItem.value.code || `ITEM-${selectedOperationItem.value.id}`} · ${selectedOperationItem.value.name}`
            : '—';
        const sourceLabel =
            sourceStoragePlaceOptions.value.find((entry) => String(entry.value) === String(operationForm.sourceStoragePlaceId))?.label || '—';
        const targetRestaurantLabel =
            restaurants.value.find((entry) => Number(entry.id) === Number(operationForm.targetRestaurantId || 0))?.name || selectedRestaurantName.value;

        let fromValue = '—';
        let toValue = '—';

        if (isIncomeOperation.value) {
            fromValue = 'Поставка';
            toValue = `${selectedRestaurantName.value} · ${operationTargetStoragePlaceLabel.value}`;
        } else if (isTransferOperation.value) {
            fromValue = `${selectedRestaurantName.value} · ${sourceLabel}`;
            toValue = `${targetRestaurantLabel} · ${operationTargetStoragePlaceLabel.value}`;
        } else if (isWriteoffOperation.value) {
            fromValue = `${selectedRestaurantName.value} · ${sourceLabel}`;
            toValue = 'Списание';
        }

        return {
            what: defaultWhat,
            quantity: Number.isFinite(quantity) ? `${quantity} шт.` : '—',
            from: fromValue,
            to: toValue,
            method: selectedType?.label || '—',
            reason: String(operationForm.reason || '').trim() || '—',
        };
    });

    function resetOperationForm() {
        const defaultStoragePlace = selectedStoragePlaceIdNum.value ? String(selectedStoragePlaceIdNum.value) : 'none';
        operationForm.itemId = '';
        operationForm.quantity = '1';
        operationForm.unitCost = '';
        operationForm.sourceStoragePlaceId = defaultStoragePlace;
        operationForm.targetRestaurantId = selectedRestaurantId.value || '';
        operationForm.targetStoragePlaceId = defaultStoragePlace;
        operationForm.reason = '';
        selectedOperationItemDetails.value = null;
    }

    function openOperationModal() {
        if (!selectedRestaurantIdNum.value) {
            toast.warning('Сначала выбери ресторан');
            return;
        }
        resetOperationForm();
        isOperationModalOpen.value = true;
    }

    function closeOperationModal() {
        if (operationSubmitting.value) {
            return;
        }
        isOperationModalOpen.value = false;
        operationType.value = 'income';
        resetOperationForm();
    }

    async function loadSelectedOperationItemDetails(itemId) {
        const normalizedItemId = Number.parseInt(String(itemId || '0'), 10);
        const restaurantId = selectedRestaurantIdNum.value;
        operationItemRequestId += 1;
        const requestId = operationItemRequestId;

        if (!Number.isFinite(normalizedItemId) || normalizedItemId <= 0 || !restaurantId) {
            selectedOperationItemDetails.value = null;
            operationItemLoading.value = false;
            return;
        }

        operationItemLoading.value = true;
        try {
            const restaurantIds = [restaurantId];
            const targetRestaurantId = Number(operationForm.targetRestaurantId || 0);
            if (isTransferOperation.value && Number.isFinite(targetRestaurantId) && targetRestaurantId > 0 && !restaurantIds.includes(targetRestaurantId)) {
                restaurantIds.push(targetRestaurantId);
            }
            const data = await fetchInventoryItems({
                item_ids: [normalizedItemId],
                restaurant_ids: restaurantIds,
            });
            if (requestId !== operationItemRequestId) {
                return;
            }
            const rows = Array.isArray(data) ? data : [];
            selectedOperationItemDetails.value = rows.find((item) => Number(item.id) === normalizedItemId) || null;
        } catch (error) {
            if (requestId !== operationItemRequestId) {
                return;
            }
            selectedOperationItemDetails.value = catalogItems.value.find((item) => Number(item.id) === normalizedItemId) || null;
            console.error(error);
        } finally {
            if (requestId === operationItemRequestId) {
                operationItemLoading.value = false;
            }
        }
    }

    async function submitOperation() {
        if (operationSubmitting.value) {
            return;
        }
        const restaurantId = selectedRestaurantIdNum.value;
        const itemId = Number.parseInt(String(operationForm.itemId || '0'), 10);
        const quantity = parseQuantity(operationForm.quantity);
        const reason = String(operationForm.reason || '').trim();

        if (!restaurantId) {
            toast.warning('Сначала выбери ресторан');
            return;
        }
        if (!Number.isFinite(itemId) || itemId <= 0) {
            toast.warning('Выбери товар');
            return;
        }
        if (!quantity) {
            toast.warning('Укажи корректное количество');
            return;
        }
        if (!reason) {
            toast.warning('Добавь комментарий или основание');
            return;
        }

        operationSubmitting.value = true;
        try {
            if (isIncomeOperation.value) {
                const unitCost = parseUnitCost(operationForm.unitCost);
                if (Number.isNaN(unitCost)) {
                    toast.warning('Цена за единицу должна быть числом не меньше 0');
                    return;
                }
                await allocateInventoryItem(itemId, {
                    location_kind: 'restaurant',
                    restaurant_id: restaurantId,
                    storage_place_id: parseStoragePlaceValue(operationForm.targetStoragePlaceId) ?? undefined,
                    quantity,
                    unit_cost: unitCost ?? undefined,
                    comment: reason,
                });
            } else if (isTransferOperation.value) {
                const targetRestaurantId = Number(operationForm.targetRestaurantId || 0);
                if (!Number.isFinite(targetRestaurantId) || targetRestaurantId <= 0) {
                    toast.warning('Выбери ресторан получателя');
                    return;
                }
                if (quantity > sourceLocationQuantity.value) {
                    toast.warning('Недостаточно остатка в источнике');
                    return;
                }
                await transferInventoryItem(itemId, {
                    source_kind: 'restaurant',
                    source_restaurant_id: restaurantId,
                    source_storage_place_id: parseStoragePlaceValue(operationForm.sourceStoragePlaceId) ?? undefined,
                    target_kind: 'restaurant',
                    restaurant_id: targetRestaurantId,
                    storage_place_id: parseStoragePlaceValue(operationForm.targetStoragePlaceId) ?? undefined,
                    quantity,
                    comment: reason,
                });
            } else {
                if (quantity > sourceLocationQuantity.value) {
                    toast.warning('Недостаточно остатка для списания');
                    return;
                }
                await updateInventoryItemQuantity(itemId, {
                    location_kind: 'restaurant',
                    restaurant_id: restaurantId,
                    storage_place_id: parseStoragePlaceValue(operationForm.sourceStoragePlaceId) ?? undefined,
                    quantity: Math.max(sourceLocationQuantity.value - quantity, 0),
                    comment: reason,
                });
            }

            toast.success('Операция сохранена');
            closeOperationModal();
            await loadRestaurantItems();
            if (isItemCardModalOpen.value) {
                await loadDetailCard();
            }
        } catch (error) {
            toast.error(error?.response?.data?.detail || 'Не удалось сохранить операцию');
            console.error(error);
        } finally {
            operationSubmitting.value = false;
        }
    }

    async function submitInstanceEvent() {
        const restaurantId = selectedRestaurantIdNum.value;
        const itemId = Number(selectedItemId.value);
        const instanceId = Number(instanceEventForm.instanceId);
        const eventTypeId = Number(instanceEventForm.eventTypeId);
        if (!restaurantId || !Number.isFinite(itemId) || itemId <= 0 || !Number.isFinite(instanceId) || instanceId <= 0) {
            return;
        }
        if (!Number.isFinite(eventTypeId) || eventTypeId <= 0) {
            toast.warning('Выбери тип события');
            return;
        }

        instanceEventSubmitting.value = true;
        try {
            await createInventoryItemInstanceEvent(restaurantId, itemId, instanceId, {
                event_type_id: eventTypeId,
                comment: instanceEventForm.comment?.trim() || null,
            });
            toast.success('Событие по коду сохранено');
            closeInstanceEventModal();
            await loadDetailCard();
            await loadInstanceEvents();
        } catch (error) {
            toast.error('Не удалось сохранить событие по коду');
            console.error(error);
        } finally {
            instanceEventSubmitting.value = false;
        }
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
            resetInstanceState();
            return;
        }

        loading.value = true;
        resetInstanceState();
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

    watch(instanceSummaries, () => {
        ensureSelectedInstance();
    });

    watch(selectedInstanceCode, () => {
        if (isItemCardModalOpen.value) {
            void loadInstanceEvents();
        }
    });

    watch(
        () => operationForm.itemId,
        async (value) => {
            await loadSelectedOperationItemDetails(value);
        },
    );

    watch(
        [() => operationType.value, () => operationForm.targetRestaurantId],
        async () => {
            if (isOperationModalOpen.value && operationForm.itemId) {
                await loadSelectedOperationItemDetails(operationForm.itemId);
            }
        },
    );

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
