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

        <InventoryTechnicalTabs />

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
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import InventoryTechnicalTabs from '@/pages/AdminLayout/Inventory/components/InventoryTechnicalTabs.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import { useInventorySettingsPage } from '@/pages/AdminLayout/Inventory/composables/useInventorySettingsPage';

const {
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
} = useInventorySettingsPage();
</script>

<style lang="scss">
@use '@/assets/styles/pages/inventory-settings' as *;
</style>
