import { computed, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';

import {
    createInventoryItemInstanceEvent,
    fetchInventoryBalanceItemCard,
    fetchInventoryItemInstanceEvents,
} from '@/api';

export function useInventoryBalanceItemCard({
    openItemDetail,
    selectedItemId,
    selectedRestaurantIdNum,
    selectedStoragePlaceIdNum,
}) {
    const toast = useToast();

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
    const instanceEventForm = reactive({
        instanceId: null,
        eventTypeId: '',
        comment: '',
    });
    let detailCardRequestId = 0;
    let instanceEventsRequestId = 0;

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

    function resetItemCardState() {
        detailCardRequestId += 1;
        instanceEventsRequestId += 1;
        detailCard.value = null;
        detailCardLoading.value = false;
        detailTab.value = 'arrivals';
        selectedInstanceCode.value = '';
        instanceEvents.value = [];
        instanceEventsLoading.value = false;
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
            resetItemCardState();
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
            resetItemCardState();
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
        resetItemCardState();
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

    watch(instanceSummaries, () => {
        ensureSelectedInstance();
    });

    watch(selectedInstanceCode, () => {
        if (isItemCardModalOpen.value) {
            void loadInstanceEvents();
        }
    });

    return {
        closeInstanceEventModal,
        closeItemCard,
        currentInstanceCount,
        detailArrivals,
        detailCard,
        detailCardLoading,
        detailTab,
        historicalInstanceCount,
        instanceEventForm,
        instanceEventSubmitting,
        instanceEventTypeOptions,
        instanceEventTypes,
        instanceEvents,
        instanceEventsLoading,
        instanceSummaries,
        instanceTrackingEnabled,
        isInstanceEventModalOpen,
        isItemCardModalOpen,
        loadDetailCard,
        openInstanceEventModal,
        openItemCard,
        resetItemCardState,
        selectInstance,
        selectedInstanceCode,
        selectedInstanceSummary,
        submitInstanceEvent,
    };
}
