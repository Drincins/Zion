<template>
    <div class="inventory-items">
        <header class="inventory-items__header">
            <div>
                <h1 class="inventory-items__title">Склад · Номенклатура</h1>
                <p class="inventory-items__subtitle">
                    Выберите подразделения и раздел каталога, затем нажмите «Показать».
                </p>
            </div>
            <Button v-if="canOpenCreateModal" color="primary" size="sm" @click="openCreateModal">Новый товар</Button>
        </header>

        <section class="inventory-items__filters">
            <div ref="departmentSelectRef" class="inventory-items__department-select">
                <label class="inventory-items__label">Подразделения</label>
                <button
                    type="button"
                    class="inventory-items__department-trigger"
                    @click="isDepartmentsOpen = !isDepartmentsOpen"
                >
                    <span :class="{ 'is-placeholder': !selectedDepartmentLabels.length }">{{ departmentsLabel }}</span>
                    <span class="inventory-items__caret">{{ isDepartmentsOpen ? '▲' : '▼' }}</span>
                </button>
                <div v-if="isDepartmentsOpen" class="inventory-items__department-menu">
                    <Input
                        v-model="departmentSearch"
                        label=""
                        placeholder="Поиск подразделения"
                        class="inventory-items__department-search"
                    />
                    <div class="inventory-items__department-list">
                        <label
                            v-for="option in filteredDepartmentOptions"
                            :key="option.id"
                            class="inventory-items__department-option"
                        >
                            <input
                                type="checkbox"
                                :checked="selectedDepartmentIds.includes(option.id)"
                                @change="toggleDepartment(option)"
                            />
                            <span>{{ option.label }}</span>
                        </label>
                        <p v-if="!filteredDepartmentOptions.length" class="inventory-items__department-empty">Ничего не найдено</p>
                    </div>
                </div>
            </div>

            <div ref="catalogFilterRef" class="catalog-picker">
                <label class="inventory-items__label">Раздел каталога</label>
                <button
                    type="button"
                    class="catalog-picker__trigger"
                    @click="isCatalogFilterOpen = !isCatalogFilterOpen"
                >
                    <span :class="{ 'is-placeholder': !selectedCatalogNodeIds.length }">{{ catalogFilterLabel }}</span>
                    <span class="inventory-items__caret">{{ isCatalogFilterOpen ? '▲' : '▼' }}</span>
                </button>
                <div v-if="isCatalogFilterOpen" class="catalog-picker__menu">
                    <label class="catalog-picker__item catalog-picker__item--root catalog-picker__item--check">
                        <input
                            type="checkbox"
                            :checked="!selectedCatalogNodeIds.length"
                            @change="clearFilterCatalogNodes"
                        />
                        <span>Все разделы</span>
                    </label>
                    <template v-for="group in sortedGroups" :key="group.id">
                        <div class="catalog-picker__row catalog-picker__row--l1">
                            <button
                                v-if="(categoriesByGroup.get(group.id) || []).length"
                                type="button"
                                class="catalog-picker__toggle"
                                @click="toggleFilterGroup(group.id)"
                            >
                                {{ isFilterGroupExpanded(group.id) ? '⌄' : '›' }}
                            </button>
                            <span v-else class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                            <label class="catalog-picker__item catalog-picker__item--check" :class="{ 'is-selected': isCatalogNodeSelected(`g:${group.id}`) }">
                                <input
                                    type="checkbox"
                                    :checked="isCatalogNodeSelected(`g:${group.id}`)"
                                    @change="toggleFilterCatalogNode(`g:${group.id}`)"
                                />
                                <span>{{ group.name }}</span>
                            </label>
                        </div>

                        <template v-if="isFilterGroupExpanded(group.id)">
                            <template v-for="category in categoriesByGroup.get(group.id) || []" :key="category.id">
                                <div class="catalog-picker__row catalog-picker__row--l2">
                                    <button
                                        v-if="(typesByCategory.get(category.id) || []).length"
                                        type="button"
                                        class="catalog-picker__toggle"
                                        @click="toggleFilterCategory(category.id)"
                                    >
                                        {{ isFilterCategoryExpanded(category.id) ? '⌄' : '›' }}
                                    </button>
                                    <span v-else class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                    <label class="catalog-picker__item catalog-picker__item--check" :class="{ 'is-selected': isCatalogNodeSelected(`c:${category.id}`) }">
                                        <input
                                            type="checkbox"
                                            :checked="isCatalogNodeSelected(`c:${category.id}`)"
                                            @change="toggleFilterCatalogNode(`c:${category.id}`)"
                                        />
                                        <span>{{ category.name }}</span>
                                    </label>
                                </div>

                                <template v-if="isFilterCategoryExpanded(category.id)">
                                    <div
                                        v-for="type in typesByCategory.get(category.id) || []"
                                        :key="type.id"
                                        class="catalog-picker__row catalog-picker__row--l3"
                                    >
                                        <span class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                        <label class="catalog-picker__item catalog-picker__item--check" :class="{ 'is-selected': isCatalogNodeSelected(`t:${type.id}`) }">
                                            <input
                                                type="checkbox"
                                                :checked="isCatalogNodeSelected(`t:${type.id}`)"
                                                @change="toggleFilterCatalogNode(`t:${type.id}`)"
                                            />
                                            <span>{{ type.name }}</span>
                                        </label>
                                    </div>
                                </template>
                            </template>
                        </template>
                    </template>
                </div>
            </div>

            <div class="inventory-page__form-actions">
                <Button color="primary" size="sm" :loading="loadingItems" @click="loadItemsByFilters">Показать</Button>
                <Button color="ghost" size="sm" :disabled="loadingItems" @click="resetFilters">Сбросить</Button>
            </div>
        </section>

        <section class="inventory-items__table-card">
            <div v-if="!hasLoadedByFilters" class="inventory-items__empty-state">
                Выберите подразделения и нажмите «Показать».
            </div>

            <div v-else-if="loadingItems" class="inventory-page__loading">Загрузка товаров...</div>

            <div v-else-if="groupedInventory.length" class="inventory-items__hierarchy">
                <div
                    v-for="locationNode in groupedInventory"
                    :key="locationNode.key"
                    class="inventory-items__department-block"
                >
                    <div class="inventory-items__department-title">
                        {{ locationNode.name }}
                    </div>

                    <div v-for="groupNode in locationNode.groups" :key="`${locationNode.key}:g:${groupNode.id}`">
                        <div class="inventory-items__group-line">{{ groupNode.name }}</div>
                        <div
                            v-for="categoryNode in groupNode.categories"
                            :key="`${locationNode.key}:c:${categoryNode.id}`"
                        >
                            <div class="inventory-items__category-line">{{ categoryNode.name }}</div>
                            <div
                                v-for="kindNode in categoryNode.kinds"
                                :key="`${locationNode.key}:t:${kindNode.id}`"
                                class="inventory-items__kind-block"
                            >
                                <div class="inventory-items__kind-line">{{ kindNode.name }}</div>
                                <div
                                    v-for="entry in kindNode.items"
                                    :key="entry.key"
                                    class="inventory-items__item-row"
                                    role="button"
                                    tabindex="0"
                                    @click="openItemDetail(entry)"
                                    @keydown.enter.prevent="openItemDetail(entry)"
                                    @keydown.space.prevent="openItemDetail(entry)"
                                >
                                    <div class="inventory-items__item-main">
                                        <div class="inventory-items__item-text">
                                            <span class="inventory-items__item-name">{{ entry.item.name }}</span>
                                            <span class="inventory-items__item-costs">
                                                Кол-во: {{ entry.quantity }} шт. · Цена: {{ formatMoney(getEntryUnitCost(entry)) }} ·
                                                Сумма: {{ formatMoney(getEntryTotalCost(entry)) }}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="inventory-items__item-actions">
                                        <button
                                            type="button"
                                            class="inventory-items__icon-btn"
                                            title="Фото"
                                            @click.stop="openItemPhoto(entry.item)"
                                        >
                                            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                                <path
                                                    d="M4 8h3l1.2-2h7.6L17 8h3a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a1 1 0 0 1 1-1Z"
                                                    stroke="currentColor"
                                                    stroke-width="1.8"
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                />
                                                <circle cx="12" cy="13.5" r="3.2" stroke="currentColor" stroke-width="1.8" />
                                            </svg>
                                        </button>
                                        <button
                                            v-if="canCreateMovement"
                                            type="button"
                                            class="inventory-items__icon-btn"
                                            title="Перевести"
                                            @click.stop="openTransferModal(entry)"
                                        >
                                            <BaseIcon name="Arrow" />
                                        </button>
                                        <button
                                            v-if="canEditNomenclature"
                                            type="button"
                                            class="inventory-items__icon-btn"
                                            title="Изменить"
                                            @click.stop="openEditModal(entry.item)"
                                        >
                                            <BaseIcon name="Edit" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div v-else class="inventory-page__empty">По выбранным фильтрам товаров не найдено.</div>
        </section>

        <Modal v-if="isItemModalOpen" @close="closeItemModal">
            <template #header>{{ isEditMode ? 'Изменить товар' : 'Новый товар' }}</template>
            <template #default>
                <div class="inventory-items__modal-form">
                    <div v-if="!isEditMode" class="inventory-items__catalog-source">
                        <Button
                            v-if="canToggleCreateSourceMode"
                            type="button"
                            color="ghost"
                            size="sm"
                            class="inventory-items__catalog-source-btn"
                            :disabled="loadingCatalogItems"
                            @click="toggleCatalogSourceMode"
                        >
                            {{ isCatalogSourceMode ? 'Добавить новый товар' : 'Выбрать из каталога' }}
                        </Button>
                        <p class="inventory-items__catalog-source-help">
                            {{ isCatalogSourceMode
                                ? 'Выберите товар из каталога, затем укажите объект, количество и цену партии.'
                                : 'Если в каталоге нет нужного товара, создайте новую карточку вручную.' }}
                        </p>
                    </div>

                    <div v-if="isCatalogSourceMode" class="inventory-items__catalog-search-block">
                        <Input
                            v-model="itemForm.catalogSearch"
                            label="Поиск в каталоге"
                            placeholder="Введите название, описание или код"
                        />
                        <div class="inventory-items__catalog-search-results">
                            <div v-if="loadingCatalogItems" class="inventory-items__catalog-empty">
                                Загружаем каталог...
                            </div>
                            <template v-else-if="catalogItemsForPicker.length">
                                <button
                                    v-for="catalogItem in catalogItemsForPicker"
                                    :key="catalogItem.id"
                                    type="button"
                                    class="inventory-items__catalog-search-item"
                                    :class="{ 'is-selected': Number(itemForm.selectedCatalogItemId) === Number(catalogItem.id) }"
                                    @click="selectCatalogItem(catalogItem)"
                                >
                                    <span class="inventory-items__catalog-search-title">{{ catalogItem.name }}</span>
                                    <span class="inventory-items__catalog-search-meta">
                                        {{ catalogItem.code || `ITEM-${catalogItem.id}` }} · {{ getCatalogPath(catalogItem) }}
                                    </span>
                                </button>
                            </template>
                            <div v-else class="inventory-items__catalog-empty">Ничего не найдено.</div>
                        </div>
                    </div>

                    <Input v-model="itemForm.name" label="Название" :readonly="isCatalogSourceMode" />
                    <Input
                        v-model="itemForm.note"
                        label="Описание"
                        placeholder="Описание товара"
                        :readonly="isCatalogSourceMode"
                    />
                    <Input
                        v-model="itemForm.manufacturer"
                        label="Производитель"
                        placeholder="Например: Valio"
                        :readonly="isCatalogSourceMode"
                    />
                    <Input
                        v-model="itemForm.storageConditions"
                        label="Условия хранения"
                        placeholder="Температура, сроки, требования к хранению"
                        :readonly="isCatalogSourceMode"
                    />
                    <label v-if="!isCatalogSourceMode" class="inventory-items__instance-toggle">
                        <input v-model="itemForm.useInstanceCodes" type="checkbox">
                        <span>Индивидуальные коды единиц (1, 2, 3...)</span>
                    </label>
                    <p v-if="!isCatalogSourceMode" class="inventory-items__instance-toggle-hint">
                        Для массовых товаров можно выключить: учет будет только по общему коду.
                    </p>

                    <div ref="catalogModalRef" class="catalog-picker catalog-picker--modal">
                        <label class="inventory-items__label">Группа / категория / вид</label>
                        <button
                            type="button"
                            class="catalog-picker__trigger"
                            :disabled="isCatalogSourceMode"
                            @click="!isCatalogSourceMode && (isCatalogModalOpen = !isCatalogModalOpen)"
                        >
                            <span :class="{ 'is-placeholder': !itemForm.catalogNodeId }">{{ catalogModalLabel }}</span>
                            <span class="inventory-items__caret">{{ isCatalogModalOpen ? '▲' : '▼' }}</span>
                        </button>
                        <div v-if="isCatalogModalOpen" class="catalog-picker__menu">
                            <template v-for="group in sortedGroups" :key="group.id">
                                <div class="catalog-picker__row catalog-picker__row--l1">
                                    <button
                                        v-if="(categoriesByGroup.get(group.id) || []).length"
                                        type="button"
                                        class="catalog-picker__toggle"
                                        @click="toggleModalGroup(group.id)"
                                    >
                                        {{ isModalGroupExpanded(group.id) ? '⌄' : '›' }}
                                    </button>
                                    <span v-else class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                    <span class="catalog-picker__item catalog-picker__item--static">{{ group.name }}</span>
                                </div>

                                <template v-if="isModalGroupExpanded(group.id)">
                                    <template v-for="category in categoriesByGroup.get(group.id) || []" :key="category.id">
                                        <div class="catalog-picker__row catalog-picker__row--l2">
                                            <button
                                                v-if="(typesByCategory.get(category.id) || []).length"
                                                type="button"
                                                class="catalog-picker__toggle"
                                                @click="toggleModalCategory(category.id)"
                                            >
                                                {{ isModalCategoryExpanded(category.id) ? '⌄' : '›' }}
                                            </button>
                                            <span v-else class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                            <span class="catalog-picker__item catalog-picker__item--static">{{ category.name }}</span>
                                        </div>

                                        <template v-if="isModalCategoryExpanded(category.id)">
                                            <div
                                                v-for="type in typesByCategory.get(category.id) || []"
                                                :key="type.id"
                                                class="catalog-picker__row catalog-picker__row--l3"
                                            >
                                                <span class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                                <button
                                                    type="button"
                                                    class="catalog-picker__item"
                                                    :class="{ 'is-selected': itemForm.catalogNodeId === `t:${type.id}` }"
                                                    @click="selectModalType(type.id)"
                                                >
                                                    {{ type.name }}
                                                </button>
                                            </div>
                                        </template>
                                    </template>
                                </template>
                            </template>
                        </div>
                    </div>

                    <Input
                        v-model="itemForm.cost"
                        label="Стоимость"
                        type="number"
                        step="0.01"
                        :disabled="isCatalogSourceMode && !selectedCatalogItem"
                    />
                    <p v-if="isCatalogSourceMode" class="inventory-items__catalog-cost-hint" :class="{ 'is-warning': isCatalogCostOverride }">
                        <template v-if="isCatalogCostOverride">
                            Стоимость партии отличается от каталожной. Изменение запишется в «Журнал операций».
                        </template>
                        <template v-else>
                            Стоимость в каталоге не изменится. Можно задать цену только для добавляемой партии.
                        </template>
                    </p>

                    <div v-if="!isCatalogSourceMode" class="inventory-items__photo-block">
                        <label class="inventory-items__label">Фото</label>
                        <button
                            type="button"
                            class="inventory-items__photo-trigger"
                            :disabled="uploadingPhoto || !canEditModalPhoto"
                            @click="openPhotoPicker"
                        >
                            <span class="inventory-items__photo-icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none">
                                    <path
                                        d="M4 8h3l1.2-2h7.6L17 8h3a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a1 1 0 0 1 1-1Z"
                                        stroke="currentColor"
                                        stroke-width="1.8"
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                    />
                                    <circle cx="12" cy="13.5" r="3.2" stroke="currentColor" stroke-width="1.8" />
                                </svg>
                            </span>
                            <span>{{ uploadingPhoto ? 'Загрузка...' : 'Загрузить фото' }}</span>
                        </button>
                        <input
                            ref="photoInputRef"
                            class="inventory-items__photo-input"
                            type="file"
                            accept="image/*"
                            :disabled="uploadingPhoto || !canEditModalPhoto"
                            @change="handleUploadItemPhoto"
                        />
                        <div class="inventory-items__photo-meta">
                            <span v-if="itemForm.photoUrl" class="inventory-items__photo-state">
                                Фото добавлено
                            </span>
                            <span v-else class="inventory-items__photo-state inventory-items__photo-state--muted">
                                Фото пока не выбрано
                            </span>
                            <Button
                                v-if="itemForm.photoUrl"
                                type="button"
                                color="ghost"
                                size="sm"
                                :disabled="uploadingPhoto || saving || !canEditModalPhoto"
                                @click="itemForm.photoUrl = ''"
                            >
                                Удалить фото
                            </Button>
                        </div>
                    </div>
                    <div v-else class="inventory-items__catalog-photo-readonly">
                        <label class="inventory-items__label">Фото</label>
                        <div v-if="itemForm.photoUrl" class="inventory-items__catalog-photo-preview">
                            <img :src="itemForm.photoUrl" alt="Фото из каталога" />
                        </div>
                        <p class="inventory-items__catalog-source-help">
                            Фото и описание подтягиваются из карточки каталога и в этом окне не редактируются.
                        </p>
                    </div>

                    <div v-if="!isEditMode && isCatalogSourceMode" class="inventory-items__assign-block">
                        <p class="inventory-items__catalog-source-help">
                            Укажите объект и количество для выбранного товара из каталога.
                        </p>

                        <div class="inventory-items__assign-fields">
                            <Select
                                v-model="itemForm.targetOptionId"
                                label="Подразделение"
                                :options="createDepartmentOptions"
                                placeholder="Выберите подразделение"
                                searchable
                            />
                            <Input
                                v-model="itemForm.targetQuantity"
                                label="Количество наименований"
                                type="number"
                                min="1"
                            />
                        </div>
                    </div>
                </div>
            </template>
            <template #footer>
                <Button color="ghost" :disabled="saving || uploadingPhoto" @click="closeItemModal">Отмена</Button>
                <Button v-if="canSubmitItemModal" color="primary" :loading="saving" @click="submitItem">Сохранить</Button>
            </template>
        </Modal>

        <Modal v-if="isTransferModalOpen" @close="closeTransferModal">
            <template #header>Перевести товар</template>
            <template #default>
                <div class="inventory-items__modal-form">
                    <Input :model-value="transferForm.itemCode" label="Товар" disabled />
                    <Select
                        v-model="transferForm.sourceOptionId"
                        label="Откуда перевести"
                        :options="sourceTransferLocationOptions"
                        placeholder="Выберите источник"
                        searchable
                    />
                    <Select
                        v-model="transferForm.targetOptionId"
                        label="Куда перевести"
                        :options="targetTransferLocationOptions"
                        placeholder="Выберите ресторан или виртуальный склад"
                        searchable
                    />
                    <Input v-model="transferForm.quantity" label="Количество" type="number" min="1" />
                </div>
            </template>
            <template #footer>
                <Button color="ghost" :disabled="saving" @click="closeTransferModal">Отмена</Button>
                <Button v-if="canCreateMovement" color="primary" :loading="saving" @click="submitTransfer">Перевести</Button>
            </template>
        </Modal>

        <Modal v-if="previewPhotoItem" @close="closeItemPhoto">
            <template #header>Фото товара</template>
            <template #default>
                <div class="inventory-items__preview-modal">
                    <img
                        v-if="previewPhotoItem.photo_url"
                        :src="previewPhotoItem.photo_url"
                        :alt="previewPhotoItem.name || 'Фото товара'"
                        class="inventory-items__preview-image"
                    />
                    <p v-else class="inventory-items__preview-empty">Для этого товара фото не загружено.</p>
                </div>
            </template>
        </Modal>

        <Modal v-if="detailItemEntry" @close="closeItemDetail">
            <template #header>Карточка товара</template>
            <template #default>
                <div class="inventory-items__detail-card">
                    <div class="inventory-items__detail-info">
                        <h3 class="inventory-items__detail-title">{{ detailItemEntry.item.name }}</h3>
                        <p class="inventory-items__detail-note">
                            {{ detailItemEntry.item.note || 'Описание не заполнено' }}
                        </p>
                        <div class="inventory-items__detail-grid">
                            <div>
                                <span class="inventory-items__detail-label">Код</span>
                                <span class="inventory-items__detail-value">{{ detailItemEntry.item.code }}</span>
                            </div>
                            <div>
                                <span class="inventory-items__detail-label">Стоимость в подразделении</span>
                                <span class="inventory-items__detail-value">
                                    {{ formatMoney(detailItemEntry.locationAvgCost ?? detailItemEntry.item.cost) }}
                                </span>
                            </div>
                            <div>
                                <span class="inventory-items__detail-label">Раздел каталога</span>
                                <span class="inventory-items__detail-value">{{ getCatalogPath(detailItemEntry.item) }}</span>
                            </div>
                            <div>
                                <span class="inventory-items__detail-label">Количество в подразделении</span>
                                <span class="inventory-items__detail-value">{{ detailItemEntry.quantity }} шт.</span>
                            </div>
                            <div>
                                <span class="inventory-items__detail-label">Производитель</span>
                                <span class="inventory-items__detail-value">
                                    {{ detailItemEntry.item.manufacturer || '—' }}
                                </span>
                            </div>
                            <div>
                                <span class="inventory-items__detail-label">Условия хранения</span>
                                <span class="inventory-items__detail-value">
                                    {{ detailItemEntry.item.storage_conditions || '—' }}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="inventory-items__detail-photo">
                        <img
                            v-if="detailItemEntry.item.photo_url"
                            :src="detailItemEntry.item.photo_url"
                            :alt="detailItemEntry.item.name || 'Фото товара'"
                        />
                        <div v-else class="inventory-items__detail-photo-empty">Нет фото</div>
                    </div>
                </div>
                <div class="inventory-items__detail-actions">
                    <Input
                        v-model="quantityForm.value"
                        label="Изменить количество в подразделении"
                        type="number"
                        min="0"
                        :readonly="!canCreateMovement"
                    />
                    <Button
                        v-if="canCreateMovement"
                        color="primary"
                        size="sm"
                        :loading="saving"
                        @click="handleUpdateQuantityFromDetail"
                    >
                        Сохранить количество
                    </Button>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import { useInventoryItemsPage } from './composables/useInventoryItemsPage';

const {
    loadingItems,
    loadingCatalogItems,
    saving,
    uploadingPhoto,
    hasLoadedByFilters,
    isDepartmentsOpen,
    isCatalogFilterOpen,
    isCatalogModalOpen,
    departmentSearch,
    selectedDepartmentIds,
    departmentSelectRef,
    catalogFilterRef,
    catalogModalRef,
    photoInputRef,
    isItemModalOpen,
    isEditMode,
    itemForm,
    isTransferModalOpen,
    transferForm,
    quantityForm,
    previewPhotoItem,
    detailItemEntry,
    sortedGroups,
    categoriesByGroup,
    typesByCategory,
    sourceTransferLocationOptions,
    targetTransferLocationOptions,
    createDepartmentOptions,
    filteredDepartmentOptions,
    selectedDepartmentLabels,
    departmentsLabel,
    catalogFilterLabel,
    catalogModalLabel,
    isCatalogSourceMode,
    canEditNomenclature,
    canCreateMovement,
    canOpenCreateModal,
    canToggleCreateSourceMode,
    canSubmitItemModal,
    canEditModalPhoto,
    catalogItemsForPicker,
    isCatalogCostOverride,
    isFilterGroupExpanded,
    isFilterCategoryExpanded,
    isModalGroupExpanded,
    isModalCategoryExpanded,
    toggleFilterGroup,
    toggleFilterCategory,
    toggleModalGroup,
    toggleModalCategory,
    isCatalogNodeSelected,
    toggleFilterCatalogNode,
    clearFilterCatalogNodes,
    selectModalType,
    toggleDepartment,
    resetFilters,
    groupedInventory,
    loadItemsByFilters,
    selectCatalogItem,
    toggleCatalogSourceMode,
    openPhotoPicker,
    openCreateModal,
    openEditModal,
    closeItemModal,
    formatMoney,
    getEntryUnitCost,
    getEntryTotalCost,
    submitItem,
    openItemPhoto,
    closeItemPhoto,
    openItemDetail,
    closeItemDetail,
    handleUpdateQuantityFromDetail,
    handleUploadItemPhoto,
    openTransferModal,
    closeTransferModal,
    submitTransfer,
    getCatalogPath,
} = useInventoryItemsPage();

</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-items' as *;
</style>
