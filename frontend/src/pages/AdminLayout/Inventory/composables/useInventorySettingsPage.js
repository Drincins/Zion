import { computed, onMounted, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';

import {
    INVENTORY_NOMENCLATURE_DELETE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS,
} from '@/accessPolicy';
import {
    createInventoryInstanceEventType,
    createInventoryStoragePlace,
    deleteInventoryStoragePlace,
    fetchInventoryInstanceEventTypes,
    fetchInventoryStoragePlaces,
    fetchRestaurants,
    updateInventoryInstanceEventType,
    updateInventoryStoragePlace,
} from '@/api';
import { useUserStore } from '@/stores/user';

export function useInventorySettingsPage() {
    const toast = useToast();
    const userStore = useUserStore();

    const loading = ref(false);
    const instanceEventTypes = ref([]);
    const storagePlaces = ref([]);
    const restaurants = ref([]);

    const savingEventType = ref(false);
    const isEventTypeModalOpen = ref(false);
    const editingEventTypeId = ref(null);

    const savingStoragePlace = ref(false);
    const deletingStoragePlaceId = ref(null);
    const isStoragePlaceModalOpen = ref(false);
    const editingStoragePlaceId = ref(null);

    const eventTypeForm = reactive({
        name: '',
        description: '',
        isManual: true,
        isActive: true,
        statusLabel: '',
    });

    const storagePlaceForm = reactive({
        name: '',
        restaurantId: '',
        description: '',
        isActive: true,
    });

    const restaurantOptions = computed(() =>
        [...restaurants.value]
            .sort((a, b) => String(a?.name || '').localeCompare(String(b?.name || ''), 'ru', { sensitivity: 'base' }))
            .map((restaurant) => ({
                value: String(restaurant.id),
                label: restaurant.name,
            })),
    );

    const canEditNomenclature = computed(() =>
        userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS),
    );
    const canDeleteNomenclature = computed(() =>
        userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_DELETE_PERMISSIONS),
    );

    function sortEventTypes(list) {
        return [...(Array.isArray(list) ? list : [])].sort((left, right) => {
            const sortDelta = Number(left?.sort_order || 100) - Number(right?.sort_order || 100);
            if (sortDelta !== 0) {
                return sortDelta;
            }
            return String(left?.name || '').localeCompare(String(right?.name || ''), 'ru', { sensitivity: 'base' });
        });
    }

    function sortStoragePlaces(list) {
        return [...(Array.isArray(list) ? list : [])].sort((left, right) => {
            const sortDelta = Number(left?.sort_order || 100) - Number(right?.sort_order || 100);
            if (sortDelta !== 0) {
                return sortDelta;
            }
            return String(left?.name || '').localeCompare(String(right?.name || ''), 'ru', { sensitivity: 'base' });
        });
    }

    function getRestaurantName(restaurantId) {
        const id = Number(restaurantId);
        if (!Number.isFinite(id) || id <= 0) {
            return '—';
        }
        return restaurants.value.find((entry) => Number(entry.id) === id)?.name || `Ресторан #${id}`;
    }

    function resetEventTypeForm() {
        eventTypeForm.name = '';
        eventTypeForm.description = '';
        eventTypeForm.isManual = true;
        eventTypeForm.isActive = true;
        eventTypeForm.statusLabel = '';
    }

    function resetStoragePlaceForm() {
        storagePlaceForm.name = '';
        storagePlaceForm.restaurantId = '';
        storagePlaceForm.description = '';
        storagePlaceForm.isActive = true;
    }

    async function loadData() {
        loading.value = true;
        try {
            const [eventTypesData, storagePlacesData, restaurantsData] = await Promise.all([
                fetchInventoryInstanceEventTypes(),
                fetchInventoryStoragePlaces(),
                fetchRestaurants(),
            ]);
            instanceEventTypes.value = sortEventTypes(eventTypesData);
            storagePlaces.value = sortStoragePlaces(storagePlacesData);
            restaurants.value = Array.isArray(restaurantsData) ? restaurantsData : [];
        } catch (error) {
            console.error(error);
            toast.error('Не удалось загрузить настройки склада');
        } finally {
            loading.value = false;
        }
    }

    function openEventTypeCreateModal() {
        editingEventTypeId.value = null;
        resetEventTypeForm();
        isEventTypeModalOpen.value = true;
    }

    function openEventTypeEditModal(eventType) {
        editingEventTypeId.value = Number(eventType.id);
        eventTypeForm.name = eventType.name || '';
        eventTypeForm.description = eventType.description || '';
        eventTypeForm.isManual = Boolean(eventType.is_manual);
        eventTypeForm.isActive = Boolean(eventType.is_active);
        eventTypeForm.statusLabel = eventType.status_label || '';
        isEventTypeModalOpen.value = true;
    }

    function closeEventTypeModal() {
        isEventTypeModalOpen.value = false;
        editingEventTypeId.value = null;
        resetEventTypeForm();
    }

    async function handleSaveEventType() {
        if (!canEditNomenclature.value || savingEventType.value) {
            return;
        }
        const name = String(eventTypeForm.name || '').trim();
        if (!name) {
            toast.warning('Укажи название типа работ');
            return;
        }

        savingEventType.value = true;
        try {
            const payload = {
                name,
                description: String(eventTypeForm.description || '').trim() || undefined,
                is_manual: Boolean(eventTypeForm.isManual),
                is_active: Boolean(eventTypeForm.isActive),
                status_label: String(eventTypeForm.statusLabel || '').trim() || undefined,
                status_key: String(eventTypeForm.statusLabel || '').trim() ? 'repair' : undefined,
            };
            let saved;
            if (editingEventTypeId.value) {
                saved = await updateInventoryInstanceEventType(editingEventTypeId.value, payload);
                toast.success('Тип работ обновлён');
            } else {
                saved = await createInventoryInstanceEventType(payload);
                toast.success('Тип работ создан');
            }
            const next = [...instanceEventTypes.value];
            const existingIndex = next.findIndex((entry) => Number(entry.id) === Number(saved.id));
            if (existingIndex === -1) {
                next.push(saved);
            } else {
                next.splice(existingIndex, 1, saved);
            }
            instanceEventTypes.value = sortEventTypes(next);
            closeEventTypeModal();
        } catch (error) {
            console.error(error);
            toast.error(error?.response?.data?.detail || 'Не удалось сохранить тип работ');
        } finally {
            savingEventType.value = false;
        }
    }

    function openStoragePlaceCreateModal() {
        editingStoragePlaceId.value = null;
        resetStoragePlaceForm();
        isStoragePlaceModalOpen.value = true;
    }

    function openStoragePlaceEditModal(place) {
        editingStoragePlaceId.value = Number(place.id);
        storagePlaceForm.name = place.name || '';
        storagePlaceForm.restaurantId = place.restaurant_id ? String(place.restaurant_id) : '';
        storagePlaceForm.description = place.description || '';
        storagePlaceForm.isActive = Boolean(place.is_active);
        isStoragePlaceModalOpen.value = true;
    }

    function closeStoragePlaceModal() {
        isStoragePlaceModalOpen.value = false;
        editingStoragePlaceId.value = null;
        resetStoragePlaceForm();
    }

    async function handleSaveStoragePlace() {
        if (!canEditNomenclature.value || savingStoragePlace.value) {
            return;
        }
        const name = String(storagePlaceForm.name || '').trim();
        if (!name) {
            toast.warning('Укажи название места хранения');
            return;
        }
        if (!storagePlaceForm.restaurantId) {
            toast.warning('Выбери ресторан для этого места хранения');
            return;
        }

        savingStoragePlace.value = true;
        try {
            const payload = {
                name,
                scope_kind: 'restaurant',
                restaurant_id: Number(storagePlaceForm.restaurantId),
                description: String(storagePlaceForm.description || '').trim() || undefined,
                is_active: Boolean(storagePlaceForm.isActive),
            };
            let saved;
            if (editingStoragePlaceId.value) {
                saved = await updateInventoryStoragePlace(editingStoragePlaceId.value, payload);
                toast.success('Место хранения обновлено');
            } else {
                saved = await createInventoryStoragePlace(payload);
                toast.success('Место хранения создано');
            }
            const next = [...storagePlaces.value];
            const existingIndex = next.findIndex((entry) => Number(entry.id) === Number(saved.id));
            if (existingIndex === -1) {
                next.push(saved);
            } else {
                next.splice(existingIndex, 1, saved);
            }
            storagePlaces.value = sortStoragePlaces(next);
            closeStoragePlaceModal();
        } catch (error) {
            console.error(error);
            toast.error(error?.response?.data?.detail || 'Не удалось сохранить место хранения');
        } finally {
            savingStoragePlace.value = false;
        }
    }

    async function handleDeleteStoragePlace(place) {
        if (!canDeleteNomenclature.value || deletingStoragePlaceId.value) {
            return;
        }
        const confirmed = window.confirm(`Удалить место хранения «${place.name}»?`);
        if (!confirmed) {
            return;
        }
        deletingStoragePlaceId.value = Number(place.id);
        try {
            await deleteInventoryStoragePlace(place.id);
            storagePlaces.value = storagePlaces.value.filter((entry) => Number(entry.id) !== Number(place.id));
            toast.success('Место хранения удалено');
        } catch (error) {
            console.error(error);
            toast.error(error?.response?.data?.detail || 'Не удалось удалить место хранения');
        } finally {
            deletingStoragePlaceId.value = null;
        }
    }

    onMounted(() => {
        loadData();
    });

    return {
        loading,
        instanceEventTypes,
        storagePlaces,
        savingEventType,
        isEventTypeModalOpen,
        editingEventTypeId,
        savingStoragePlace,
        deletingStoragePlaceId,
        isStoragePlaceModalOpen,
        editingStoragePlaceId,
        eventTypeForm,
        storagePlaceForm,
        restaurantOptions,
        canEditNomenclature,
        canDeleteNomenclature,
        getRestaurantName,
        loadData,
        openEventTypeCreateModal,
        openEventTypeEditModal,
        closeEventTypeModal,
        handleSaveEventType,
        openStoragePlaceCreateModal,
        openStoragePlaceEditModal,
        closeStoragePlaceModal,
        handleSaveStoragePlace,
        handleDeleteStoragePlace,
    };
}
