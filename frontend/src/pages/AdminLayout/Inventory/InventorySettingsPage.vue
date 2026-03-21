<template>
    <div class="admin-page inventory-settings">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Настройки склада</h1>
                <p class="admin-page__subtitle">
                    Справочники, которые управляют логикой и будущими настройками складского модуля.
                </p>
            </div>
            <div class="admin-page__header-actions">
                <div class="admin-page__toolbar">
                    <Button type="button" color="secondary" size="sm" :loading="loading" @click="loadData">
                        Обновить
                    </Button>
                </div>
            </div>
        </header>

        <section class="admin-page__section inventory-settings__section">
            <div class="inventory-settings__section-head">
                <div>
                    <h2>Типы работ по единицам</h2>
                    <p>Эти значения используются в карточке товара во вкладке «Единицы и коды».</p>
                </div>
                <Button
                    v-if="canEditNomenclature"
                    type="button"
                    color="primary"
                    size="sm"
                    @click="openEventTypeCreateModal"
                >
                    Добавить тип работ
                </Button>
            </div>

            <Table v-if="instanceEventTypes.length">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>Описание</th>
                        <th>Вручную</th>
                        <th>Статус единицы</th>
                        <th>Активен</th>
                        <th class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="eventType in instanceEventTypes" :key="eventType.id">
                        <td>
                            <button
                                type="button"
                                class="admin-page__row-link"
                                @click="openEventTypeEditModal(eventType)"
                            >
                                {{ eventType.name }}
                            </button>
                        </td>
                        <td>{{ eventType.description || '—' }}</td>
                        <td>
                            <span class="inventory-settings__flag" :class="{ 'inventory-settings__flag--on': eventType.is_manual }">
                                {{ eventType.is_manual ? 'Да' : 'Нет' }}
                            </span>
                        </td>
                        <td>{{ eventType.status_label || '—' }}</td>
                        <td>
                            <span class="inventory-settings__flag" :class="{ 'inventory-settings__flag--on': eventType.is_active }">
                                {{ eventType.is_active ? 'Да' : 'Нет' }}
                            </span>
                        </td>
                        <td class="admin-page__actions">
                            <button
                                v-if="canEditNomenclature"
                                type="button"
                                class="admin-page__icon-button"
                                title="Редактировать"
                                @click="openEventTypeEditModal(eventType)"
                            >
                                <BaseIcon name="Edit" />
                            </button>
                        </td>
                    </tr>
                </tbody>
            </Table>
            <div v-else class="admin-page__empty">
                <p v-if="loading">Загрузка типов работ...</p>
                <p v-else>Типы работ пока не созданы.</p>
            </div>
        </section>

        <section class="admin-page__section inventory-settings__section">
            <div class="inventory-settings__section-head">
                <div>
                    <h2>Места хранения</h2>
                    <p>Места хранения внутри ресторанов. Они используются для остатков, перемещений и истории товара.</p>
                </div>
                <Button
                    v-if="canEditNomenclature"
                    type="button"
                    color="primary"
                    size="sm"
                    @click="openStoragePlaceCreateModal"
                >
                    Добавить место хранения
                </Button>
            </div>

            <Table v-if="storagePlaces.length">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>Ресторан</th>
                        <th>Описание</th>
                        <th>Активно</th>
                        <th class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="place in storagePlaces" :key="place.id">
                        <td>
                            <button
                                type="button"
                                class="admin-page__row-link"
                                @click="openStoragePlaceEditModal(place)"
                            >
                                {{ place.name }}
                            </button>
                        </td>
                        <td>{{ getRestaurantName(place.restaurant_id) }}</td>
                        <td>{{ place.description || '—' }}</td>
                        <td>
                            <span class="inventory-settings__flag" :class="{ 'inventory-settings__flag--on': place.is_active }">
                                {{ place.is_active ? 'Да' : 'Нет' }}
                            </span>
                        </td>
                        <td class="admin-page__actions">
                            <button
                                v-if="canEditNomenclature"
                                type="button"
                                class="admin-page__icon-button"
                                title="Редактировать"
                                @click="openStoragePlaceEditModal(place)"
                            >
                                <BaseIcon name="Edit" />
                            </button>
                            <button
                                v-if="canDeleteNomenclature"
                                type="button"
                                class="admin-page__icon-button admin-page__icon-button--danger"
                                :disabled="deletingStoragePlaceId === place.id"
                                title="Удалить"
                                @click="handleDeleteStoragePlace(place)"
                            >
                                <BaseIcon name="Trash" />
                            </button>
                        </td>
                    </tr>
                </tbody>
            </Table>
            <div v-else class="admin-page__empty">
                <p v-if="loading">Загрузка мест хранения...</p>
                <p v-else>Места хранения пока не добавлены.</p>
            </div>
        </section>

        <Modal v-if="isEventTypeModalOpen" @close="closeEventTypeModal">
            <template #header>
                <div>
                    <h3 class="inventory-settings__modal-title">
                        {{ editingEventTypeId ? 'Редактировать тип работ' : 'Новый тип работ' }}
                    </h3>
                    <p class="inventory-settings__modal-subtitle">
                        Эти типы доступны для истории по коду и ручных сервисных действий.
                    </p>
                </div>
            </template>

            <form class="inventory-settings__form" @submit.prevent="handleSaveEventType">
                <Input v-model="eventTypeForm.name" label="Название" placeholder="Например, Клининг" required />
                <Input
                    v-model="eventTypeForm.description"
                    label="Короткое описание"
                    placeholder="Когда и для чего используется этот тип работ"
                />
                <div class="inventory-settings__form-grid">
                    <label class="inventory-settings__checkbox">
                        <input v-model="eventTypeForm.isManual" type="checkbox">
                        <span>Доступен для ручного добавления</span>
                    </label>
                    <label class="inventory-settings__checkbox">
                        <input v-model="eventTypeForm.isActive" type="checkbox">
                        <span>Активен</span>
                    </label>
                </div>
                <Input
                    v-model="eventTypeForm.statusLabel"
                    label="Статус единицы после события"
                    placeholder="Например, На диагностике"
                />
            </form>

            <template #footer>
                <Button type="button" color="ghost" :disabled="savingEventType" @click="closeEventTypeModal">
                    Отмена
                </Button>
                <Button
                    v-if="canEditNomenclature"
                    type="button"
                    color="primary"
                    :loading="savingEventType"
                    @click="handleSaveEventType"
                >
                    Сохранить
                </Button>
            </template>
        </Modal>

        <Modal v-if="isStoragePlaceModalOpen" @close="closeStoragePlaceModal">
            <template #header>
                <div>
                    <h3 class="inventory-settings__modal-title">
                        {{ editingStoragePlaceId ? 'Редактировать место хранения' : 'Новое место хранения' }}
                    </h3>
                    <p class="inventory-settings__modal-subtitle">
                        Это место хранения уже используется в остатках, операциях и истории товара внутри ресторана.
                    </p>
                </div>
            </template>

            <form class="inventory-settings__form" @submit.prevent="handleSaveStoragePlace">
                <Input v-model="storagePlaceForm.name" label="Название" placeholder="Например, Моечная" required />
                <Select
                    v-model="storagePlaceForm.restaurantId"
                    label="Ресторан"
                    :options="restaurantOptions"
                    placeholder="Выберите ресторан"
                    searchable
                />
                <Input
                    v-model="storagePlaceForm.description"
                    label="Описание"
                    placeholder="Короткое описание места хранения"
                />
                <div class="inventory-settings__form-grid">
                    <label class="inventory-settings__checkbox">
                        <input v-model="storagePlaceForm.isActive" type="checkbox">
                        <span>Активно</span>
                    </label>
                </div>
            </form>

            <template #footer>
                <Button type="button" color="ghost" :disabled="savingStoragePlace" @click="closeStoragePlaceModal">
                    Отмена
                </Button>
                <Button
                    v-if="canEditNomenclature"
                    type="button"
                    color="primary"
                    :loading="savingStoragePlace"
                    @click="handleSaveStoragePlace"
                >
                    Сохранить
                </Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
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
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';

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

const canEditNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS));
const canDeleteNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_DELETE_PERMISSIONS));

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
</script>

<style lang="scss">
@use '@/assets/styles/pages/inventory-settings' as *;
</style>
