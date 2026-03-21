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
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import {
    INVENTORY_MOVEMENTS_CREATE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS,
} from '@/accessPolicy';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import { useUserStore } from '@/stores/user';
import { useClickOutside } from '@/composables/useClickOutside';
import { formatNumberValue } from '@/utils/format';
import {
    allocateInventoryItem,
    createInventoryItem,
    fetchInventoryCategories,
    fetchInventoryDepartments,
    fetchInventoryGroups,
    fetchInventoryItems,
    fetchInventoryTypes,
    transferInventoryItem,
    updateInventoryItemQuantity,
    updateInventoryItem,
    uploadInventoryItemPhoto,
} from '@/api';

const toast = useToast();
const userStore = useUserStore();

const groups = ref([]);
const categories = ref([]);
const types = ref([]);
const departmentOptions = ref([]);
const items = ref([]);
const catalogItems = ref([]);

const loadingItems = ref(false);
const loadingCatalogItems = ref(false);
const saving = ref(false);
const uploadingPhoto = ref(false);
const hasLoadedByFilters = ref(false);

const isDepartmentsOpen = ref(false);
const isCatalogFilterOpen = ref(false);
const isCatalogModalOpen = ref(false);

const departmentSearch = ref('');
const selectedDepartmentIds = ref([]);

const departmentSelectRef = ref(null);
const catalogFilterRef = ref(null);
const catalogModalRef = ref(null);
const photoInputRef = ref(null);

const filterExpandedGroupIds = ref(new Set());
const filterExpandedCategoryIds = ref(new Set());
const modalExpandedGroupIds = ref(new Set());
const modalExpandedCategoryIds = ref(new Set());

const selectedCatalogNodeIds = ref([]);

const isItemModalOpen = ref(false);
const isEditMode = ref(false);
const itemForm = reactive({
    id: null,
    code: '',
    name: '',
    catalogNodeId: '',
    cost: '',
    note: '',
    manufacturer: '',
    storageConditions: '',
    photoUrl: '',
    useInstanceCodes: true,
    useCatalogItem: false,
    selectedCatalogItemId: null,
    catalogSearch: '',
    targetOptionId: '',
    targetQuantity: '1',
});

const isTransferModalOpen = ref(false);
const transferForm = reactive({
    itemId: null,
    itemCode: '',
    sourceOptionId: '',
    targetOptionId: '',
    quantity: '1',
});
const quantityForm = reactive({
    value: '',
});

const previewPhotoItem = ref(null);
const detailItemEntry = ref(null);

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

const sourceTransferLocationOptions = computed(() =>
    departmentOptions.value
        .filter((option) => option.type === 'warehouse' || option.type === 'restaurant' || option.type === 'subdivision')
        .map((option) => ({
            value: option.id,
            label: option.type === 'warehouse' ? 'Виртуальный склад' : option.label,
        })),
);

const targetTransferLocationOptions = computed(() =>
    departmentOptions.value
        .filter((option) => option.type === 'warehouse' || option.type === 'restaurant')
        .map((option) => ({
            value: option.id,
            label: option.type === 'warehouse' ? 'Виртуальный склад' : option.label,
        })),
);

const createDepartmentOptions = computed(() =>
    departmentOptions.value
        .filter((option) => option.type === 'warehouse' || option.type === 'restaurant' || option.type === 'subdivision')
        .map((option) => ({ value: option.id, label: option.label })),
);

const filteredDepartmentOptions = computed(() => {
    const search = departmentSearch.value.trim().toLowerCase();
    const sorted = [...departmentOptions.value].sort((a, b) => {
        const priority = (option) => {
            if (option.id === 'all_departments') return 0;
            if (option.id === 'all_restaurants') return 1;
            if (option.id === 'warehouse') return 2;
            if (option.type === 'restaurant') return 3;
            return 4;
        };
        const pa = priority(a);
        const pb = priority(b);
        if (pa !== pb) {
            return pa - pb;
        }
        return a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' });
    });
    if (!search) {
        return sorted;
    }
    return sorted.filter((option) => option.label.toLowerCase().includes(search));
});

const selectedDepartmentLabels = computed(() =>
    departmentOptions.value
        .filter((option) => selectedDepartmentIds.value.includes(option.id))
        .map((option) => option.label),
);

const departmentsLabel = computed(() => {
    if (!selectedDepartmentLabels.value.length) {
        return 'Выберите подразделения';
    }
    if (selectedDepartmentLabels.value.length <= 2) {
        return selectedDepartmentLabels.value.join(', ');
    }
    return `${selectedDepartmentLabels.value.slice(0, 2).join(', ')} +${selectedDepartmentLabels.value.length - 2}`;
});

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
const selectedCatalogItem = computed(() =>
    catalogItems.value.find((entry) => Number(entry.id) === Number(itemForm.selectedCatalogItemId)) || null,
);
const isCatalogSourceMode = computed(() => !isEditMode.value && itemForm.useCatalogItem);
const canCreateNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS));
const canEditNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS));
const canCreateMovement = computed(() => userStore.hasAnyPermission(...INVENTORY_MOVEMENTS_CREATE_PERMISSIONS));
const canOpenCreateModal = computed(() => canCreateNomenclature.value || canCreateMovement.value);
const canToggleCreateSourceMode = computed(() =>
    !isEditMode.value && canCreateNomenclature.value && canCreateMovement.value,
);
const canSubmitItemModal = computed(() => {
    if (isEditMode.value) {
        return canEditNomenclature.value;
    }
    return isCatalogSourceMode.value ? canCreateMovement.value : canCreateNomenclature.value;
});
const canEditModalPhoto = computed(() => {
    if (isEditMode.value) {
        return canEditNomenclature.value;
    }
    return !isCatalogSourceMode.value && canCreateNomenclature.value;
});
const catalogItemsForPicker = computed(() => {
    const search = itemForm.catalogSearch.trim().toLowerCase();
    const source = [...catalogItems.value].sort((a, b) =>
        String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }),
    );
    if (!search) {
        return source.slice(0, 200);
    }
    return source
        .filter((item) => {
            const stack = [item.code, item.name, item.note]
                .filter(Boolean)
                .join(' ')
                .toLowerCase();
            return stack.includes(search);
        })
        .slice(0, 200);
});
const catalogBaseCost = computed(() => {
    if (!selectedCatalogItem.value) {
        return NaN;
    }
    return parseNumber(
        selectedCatalogItem.value.default_cost ?? selectedCatalogItem.value.cost,
    );
});
const isCatalogCostOverride = computed(() => {
    if (!isCatalogSourceMode.value || !selectedCatalogItem.value) {
        return false;
    }
    const currentCost = parseNumber(itemForm.cost);
    const baseCost = catalogBaseCost.value;
    if (Number.isNaN(currentCost) || Number.isNaN(baseCost)) {
        return false;
    }
    return Math.abs(currentCost - baseCost) > 0.0001;
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

function toggleDepartment(option) {
    const selected = new Set(selectedDepartmentIds.value);
    const isSelected = selected.has(option.id);
    if (option.id === 'all_departments') {
        selectedDepartmentIds.value = isSelected ? [] : ['all_departments'];
        return;
    }
    if (isSelected) {
        selected.delete(option.id);
    } else {
        selected.add(option.id);
        selected.delete('all_departments');
    }
    selectedDepartmentIds.value = Array.from(selected);
}

function parseDepartmentFilters() {
    const selected = new Set(selectedDepartmentIds.value);
    const allRestaurantIds = departmentOptions.value
        .filter((option) => option.type === 'restaurant' && option.restaurant_id)
        .map((option) => Number(option.restaurant_id));
    const allSubdivisionIds = departmentOptions.value
        .filter((option) => option.type === 'subdivision' && option.subdivision_id)
        .map((option) => Number(option.subdivision_id));

    if (selected.has('all_departments')) {
        return {
            restaurant_ids: allRestaurantIds,
            subdivision_ids: allSubdivisionIds,
            include_warehouse: true,
        };
    }

    const restaurantIds = new Set();
    const subdivisionIds = new Set();
    let includeWarehouse = false;

    if (selected.has('all_restaurants')) {
        allRestaurantIds.forEach((id) => restaurantIds.add(id));
    }
    if (selected.has('warehouse')) {
        includeWarehouse = true;
    }

    for (const option of departmentOptions.value) {
        if (!selected.has(option.id)) {
            continue;
        }
        if (option.type === 'restaurant' && option.restaurant_id) {
            restaurantIds.add(Number(option.restaurant_id));
        }
        if (option.type === 'subdivision' && option.subdivision_id) {
            subdivisionIds.add(Number(option.subdivision_id));
        }
    }

    return {
        restaurant_ids: Array.from(restaurantIds),
        subdivision_ids: Array.from(subdivisionIds),
        include_warehouse: includeWarehouse,
    };
}

function resetFilters() {
    selectedDepartmentIds.value = [];
    selectedCatalogNodeIds.value = [];
    items.value = [];
    hasLoadedByFilters.value = false;
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

async function loadLookupData() {
    const [groupsData, categoriesData, typesData, departmentsData] = await Promise.all([
        fetchInventoryGroups(),
        fetchInventoryCategories(),
        fetchInventoryTypes(),
        fetchInventoryDepartments(),
    ]);
    groups.value = Array.isArray(groupsData) ? groupsData : [];
    categories.value = Array.isArray(categoriesData) ? categoriesData : [];
    types.value = Array.isArray(typesData) ? typesData : [];
    departmentOptions.value = Array.isArray(departmentsData) ? departmentsData : [];
    seedCatalogExpandedTrees();
}

async function loadCatalogItemsForModal(force = false) {
    if (loadingCatalogItems.value) {
        return;
    }
    if (!force && catalogItems.value.length) {
        return;
    }
    loadingCatalogItems.value = true;
    try {
        const data = await fetchInventoryItems({ include_locations: false });
        catalogItems.value = Array.isArray(data) ? data : [];
    } catch (error) {
        toast.error('Не удалось загрузить товары каталога');
        console.error(error);
    } finally {
        loadingCatalogItems.value = false;
    }
}

async function loadItemsByFilters() {
    if (!selectedDepartmentIds.value.length) {
        toast.error('Выберите хотя бы одно подразделение');
        return;
    }
    loadingItems.value = true;
    try {
        const departmentParams = parseDepartmentFilters();
        const params = {
            ...departmentParams,
            only_in_locations: true,
        };

        const data = await fetchInventoryItems(params);
        items.value = Array.isArray(data) ? data : [];
        hasLoadedByFilters.value = true;
    } catch (error) {
        toast.error('Не удалось загрузить товары');
        console.error(error);
    } finally {
        loadingItems.value = false;
    }
}

function resetItemForm() {
    itemForm.id = null;
    itemForm.code = '';
    itemForm.name = '';
    itemForm.catalogNodeId = '';
    itemForm.cost = '';
    itemForm.note = '';
    itemForm.manufacturer = '';
    itemForm.storageConditions = '';
    itemForm.photoUrl = '';
    itemForm.useInstanceCodes = true;
    itemForm.useCatalogItem = false;
    itemForm.selectedCatalogItemId = null;
    itemForm.catalogSearch = '';
    itemForm.targetOptionId = '';
    itemForm.targetQuantity = '1';
}

function getDefaultCreateDepartmentOptionId() {
    const options = departmentOptions.value.filter(
        (option) => option.type === 'warehouse' || option.type === 'restaurant' || option.type === 'subdivision',
    );
    if (!options.length) {
        return '';
    }

    const preferredSubdivisionId = Number(userStore.restaurantSubdivisionId);
    if (Number.isFinite(preferredSubdivisionId) && preferredSubdivisionId > 0) {
        const subdivisionOption = options.find(
            (option) => option.type === 'subdivision' && Number(option.subdivision_id) === preferredSubdivisionId,
        );
        if (subdivisionOption) {
            return subdivisionOption.id;
        }
    }

    const preferredRestaurantId = Number(userStore.workplaceRestaurantId);
    if (Number.isFinite(preferredRestaurantId) && preferredRestaurantId > 0) {
        const restaurantOption = options.find(
            (option) => option.type === 'restaurant' && Number(option.restaurant_id) === preferredRestaurantId,
        );
        if (restaurantOption) {
            return restaurantOption.id;
        }
    }

    if (options.length === 1) {
        return options[0].id;
    }
    return '';
}

function selectCatalogItem(item) {
    if (!item || !item.id) {
        return;
    }
    itemForm.useCatalogItem = true;
    itemForm.selectedCatalogItemId = Number(item.id);
    itemForm.name = item.name || '';
    itemForm.note = item.note || '';
    itemForm.manufacturer = item.manufacturer || '';
    itemForm.storageConditions = item.storage_conditions || '';
    itemForm.catalogNodeId = item.kind_id ? `t:${item.kind_id}` : '';
    itemForm.photoUrl = item.photo_key || item.photo_url || '';
    itemForm.cost = String(item.default_cost ?? item.cost ?? '');
    itemForm.useInstanceCodes = item.use_instance_codes !== false;
    if (!itemForm.targetOptionId) {
        itemForm.targetOptionId = getDefaultCreateDepartmentOptionId();
    }
}

function toggleCatalogSourceMode() {
    if (isEditMode.value || !canToggleCreateSourceMode.value) {
        return;
    }
    itemForm.useCatalogItem = !itemForm.useCatalogItem;
    itemForm.selectedCatalogItemId = null;
    itemForm.catalogSearch = '';
    if (itemForm.useCatalogItem) {
        itemForm.name = '';
        itemForm.note = '';
        itemForm.manufacturer = '';
        itemForm.storageConditions = '';
        itemForm.catalogNodeId = '';
        itemForm.cost = '';
        itemForm.photoUrl = '';
        itemForm.useInstanceCodes = true;
        itemForm.targetQuantity = '1';
        if (!itemForm.targetOptionId) {
            itemForm.targetOptionId = getDefaultCreateDepartmentOptionId();
        }
        void loadCatalogItemsForModal();
    } else {
        itemForm.name = '';
        itemForm.note = '';
        itemForm.manufacturer = '';
        itemForm.storageConditions = '';
        itemForm.catalogNodeId = '';
        itemForm.cost = '';
        itemForm.photoUrl = '';
        itemForm.useInstanceCodes = true;
        itemForm.targetOptionId = '';
        itemForm.targetQuantity = '1';
    }
}

function openPhotoPicker() {
    if (!photoInputRef.value || uploadingPhoto.value || !canEditModalPhoto.value) {
        return;
    }
    photoInputRef.value.click();
}

function openCreateModal() {
    if (!canOpenCreateModal.value) {
        toast.error('Недостаточно прав для работы с номенклатурой склада');
        return;
    }
    resetItemForm();
    itemForm.useCatalogItem = canCreateMovement.value;
    itemForm.targetOptionId = getDefaultCreateDepartmentOptionId();
    isEditMode.value = false;
    isItemModalOpen.value = true;
    seedCatalogExpandedTrees();
    if (itemForm.useCatalogItem) {
        void loadCatalogItemsForModal();
    }
}

function openEditModal(item) {
    if (!canEditNomenclature.value) {
        toast.error('Недостаточно прав для редактирования товара');
        return;
    }
    itemForm.id = item.id;
    itemForm.code = item.code || '';
    itemForm.name = item.name || '';
    itemForm.catalogNodeId = item.kind_id ? `t:${item.kind_id}` : '';
    itemForm.cost = item.cost !== null && item.cost !== undefined ? String(item.cost) : '';
    itemForm.note = item.note || '';
    itemForm.manufacturer = item.manufacturer || '';
    itemForm.storageConditions = item.storage_conditions || '';
    itemForm.photoUrl = item.photo_key || item.photo_url || '';
    itemForm.useInstanceCodes = item.use_instance_codes !== false;
    itemForm.useCatalogItem = false;
    itemForm.selectedCatalogItemId = null;
    itemForm.catalogSearch = '';
    itemForm.targetOptionId = '';
    itemForm.targetQuantity = '1';
    isEditMode.value = true;
    isItemModalOpen.value = true;
    seedCatalogExpandedTrees();
}

function closeItemModal() {
    isItemModalOpen.value = false;
    isCatalogModalOpen.value = false;
    isEditMode.value = false;
    resetItemForm();
}

function parseNumber(value) {
    const number = Number.parseFloat(String(value).replace(',', '.'));
    return Number.isFinite(number) ? number : NaN;
}

function formatMoney(value) {
    const numeric = parseNumber(value);
    const formatted = formatNumberValue(numeric, {
        emptyValue: '0.00',
        invalidValue: '0.00',
        locale: 'ru-RU',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    return `${formatted} ₽`;
}

function getEntryUnitCost(entry) {
    const numeric = parseNumber(entry?.locationAvgCost ?? entry?.item?.cost);
    return Number.isNaN(numeric) ? 0 : numeric;
}

function getEntryTotalCost(entry) {
    const quantity = Number(entry?.quantity || 0);
    if (!Number.isFinite(quantity) || quantity <= 0) {
        return 0;
    }
    return getEntryUnitCost(entry) * quantity;
}

async function submitItem() {
    if (!canSubmitItemModal.value) {
        toast.error('Недостаточно прав для сохранения изменений');
        return;
    }
    const cost = parseNumber(itemForm.cost);
    if (Number.isNaN(cost)) {
        toast.error('Стоимость должна быть числом');
        return;
    }

    const targetOption = departmentOptions.value.find((option) => option.id === itemForm.targetOptionId);
    const quantity = Number.parseInt(String(itemForm.targetQuantity || '0'), 10);

    saving.value = true;
    try {
        if (isCatalogSourceMode.value) {
            if (!selectedCatalogItem.value?.id) {
                toast.error('Выберите товар из каталога');
                return;
            }
            if (!targetOption || !['warehouse', 'restaurant', 'subdivision'].includes(targetOption.type)) {
                toast.error('Выберите подразделение');
                return;
            }
            if (!Number.isFinite(quantity) || quantity <= 0) {
                toast.error('Введите корректное количество');
                return;
            }

            if (isCatalogCostOverride.value) {
                const confirmed = window.confirm(
                    'Стоимость отличается от каталога. Изменение применится только к этой партии товара. Продолжить?',
                );
                if (!confirmed) {
                    return;
                }
            }

            const allocatePayload = {
                location_kind: targetOption.type,
                quantity,
                unit_cost: cost,
                comment: isCatalogCostOverride.value
                    ? 'Добавление партии из каталога с изменением стоимости'
                    : 'Добавление партии из каталога',
            };
            if (targetOption.type === 'restaurant') {
                allocatePayload.restaurant_id = Number(targetOption.restaurant_id);
            }
            if (targetOption.type === 'subdivision') {
                allocatePayload.subdivision_id = Number(targetOption.subdivision_id);
            }

            await allocateInventoryItem(selectedCatalogItem.value.id, allocatePayload);
            toast.success('Партия добавлена в подразделение');
        } else if (isEditMode.value && itemForm.id) {
            const parsedNode = parseCatalogNodeValue(itemForm.catalogNodeId);
            if (!parsedNode || parsedNode.level !== 't') {
                toast.error('Выберите раздел 3-го этажа');
                return;
            }

            const type = typeMap.value.get(parsedNode.id);
            if (!type) {
                toast.error('Раздел каталога не найден');
                return;
            }

            const name = itemForm.name.trim();
            if (!name) {
                toast.error('Введите название товара');
                return;
            }

            await updateInventoryItem(itemForm.id, {
                name,
                group_id: type.group_id,
                category_id: type.category_id,
                kind_id: type.id,
                cost,
                note: itemForm.note || undefined,
                manufacturer: itemForm.manufacturer || undefined,
                storage_conditions: itemForm.storageConditions || undefined,
                photo_url: itemForm.photoUrl || null,
                use_instance_codes: Boolean(itemForm.useInstanceCodes),
            });
            toast.success('Товар обновлен');
        } else {
            const parsedNode = parseCatalogNodeValue(itemForm.catalogNodeId);
            if (!parsedNode || parsedNode.level !== 't') {
                toast.error('Выберите раздел 3-го этажа');
                return;
            }

            const type = typeMap.value.get(parsedNode.id);
            if (!type) {
                toast.error('Раздел каталога не найден');
                return;
            }

            const name = itemForm.name.trim();
            if (!name) {
                toast.error('Введите название товара');
                return;
            }

            const createPayload = {
                name,
                group_id: type.group_id,
                category_id: type.category_id,
                kind_id: type.id,
                cost,
                note: itemForm.note || undefined,
                manufacturer: itemForm.manufacturer || undefined,
                storage_conditions: itemForm.storageConditions || undefined,
                photo_url: itemForm.photoUrl || null,
                use_instance_codes: Boolean(itemForm.useInstanceCodes),
                initial_quantity: 0,
            };

            await createInventoryItem({
                ...createPayload,
            });
            toast.success('Товар создан');
        }
        closeItemModal();
        if (hasLoadedByFilters.value) {
            await loadItemsByFilters();
        }
        await loadCatalogItemsForModal(true);
    } catch (error) {
        toast.error('Не удалось сохранить товар');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

function openItemPhoto(item) {
    previewPhotoItem.value = item;
}

function closeItemPhoto() {
    previewPhotoItem.value = null;
}

function openItemDetail(entry) {
    detailItemEntry.value = entry;
    quantityForm.value = String(entry?.quantity ?? 0);
}

function closeItemDetail() {
    detailItemEntry.value = null;
    quantityForm.value = '';
}

function buildQuantityPayload(entry, nextQuantity, comment) {
    const payload = {
        location_kind: entry.locationKind,
        quantity: nextQuantity,
        comment,
    };
    const locationUnitCost = parseNumber(entry.locationAvgCost ?? entry.item?.cost);
    if (!Number.isNaN(locationUnitCost)) {
        payload.unit_cost = locationUnitCost;
    }
    if (entry.locationKind === 'restaurant') {
        payload.restaurant_id = Number(entry.locationRestaurantId);
    }
    if (entry.locationKind === 'subdivision') {
        payload.subdivision_id = Number(entry.locationSubdivisionId);
    }
    return payload;
}

async function handleUpdateQuantityFromDetail() {
    if (!canCreateMovement.value) {
        toast.error('Недостаточно прав для изменения количества');
        return;
    }
    if (!detailItemEntry.value?.item?.id) {
        return;
    }
    const nextQuantity = Number.parseInt(String(quantityForm.value || '0'), 10);
    if (!Number.isFinite(nextQuantity) || nextQuantity < 0) {
        toast.error('Введите корректное количество (0 или больше)');
        return;
    }
    const currentQuantity = Number(detailItemEntry.value.quantity || 0);
    if (nextQuantity === currentQuantity) {
        toast.info('Количество не изменилось');
        return;
    }
    if (nextQuantity === 0) {
        const confirmed = window.confirm('Вы действительно хотите списать товар?');
        if (!confirmed) {
            return;
        }
    }

    saving.value = true;
    try {
        await updateInventoryItemQuantity(
            detailItemEntry.value.item.id,
            buildQuantityPayload(
                detailItemEntry.value,
                nextQuantity,
                'Изменение количества через карточку товара',
            ),
        );
        toast.success(nextQuantity === 0 ? 'Товар списан из подразделения' : 'Количество обновлено');
        if (hasLoadedByFilters.value) {
            await loadItemsByFilters();
        }
        closeItemDetail();
    } catch (error) {
        toast.error(error?.response?.data?.detail || 'Не удалось изменить количество');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function handleUploadItemPhoto(event) {
    const file = event?.target?.files?.[0];
    if (!file || !canEditModalPhoto.value) {
        return;
    }
    uploadingPhoto.value = true;
    try {
        const response = await uploadInventoryItemPhoto(file);
        itemForm.photoUrl = response?.attachment_key || response?.attachment_url || '';
        toast.success('Фото загружено');
    } catch (error) {
        toast.error('Не удалось загрузить фото');
        console.error(error);
    } finally {
        uploadingPhoto.value = false;
        if (event?.target) {
            event.target.value = '';
        }
    }
}

function buildLocationOptionId(locationKind, restaurantId, subdivisionId) {
    if (locationKind === 'warehouse') {
        return 'warehouse';
    }
    if (locationKind === 'restaurant' && restaurantId) {
        return `restaurant:${restaurantId}`;
    }
    if (locationKind === 'subdivision' && subdivisionId) {
        return `subdivision:${subdivisionId}`;
    }
    return '';
}

function openTransferModal(entry) {
    if (!canCreateMovement.value) {
        toast.error('Недостаточно прав для перевода товара');
        return;
    }
    const item = entry?.item || null;
    if (!item?.id) {
        return;
    }
    transferForm.itemId = item.id;
    transferForm.itemCode = `${item.code} · ${item.name}`;
    transferForm.sourceOptionId = buildLocationOptionId(
        entry.locationKind,
        entry.locationRestaurantId,
        entry.locationSubdivisionId,
    );
    transferForm.targetOptionId = '';
    transferForm.quantity = '1';
    isTransferModalOpen.value = true;
}

function closeTransferModal() {
    isTransferModalOpen.value = false;
    transferForm.itemId = null;
    transferForm.itemCode = '';
    transferForm.sourceOptionId = '';
    transferForm.targetOptionId = '';
    transferForm.quantity = '1';
}

async function submitTransfer() {
    if (!canCreateMovement.value) {
        toast.error('Недостаточно прав для перевода товара');
        return;
    }
    if (!transferForm.itemId) {
        return;
    }
    const sourceOption = departmentOptions.value.find((option) => option.id === transferForm.sourceOptionId);
    if (!sourceOption || !['warehouse', 'restaurant', 'subdivision'].includes(sourceOption.type)) {
        toast.error('Выберите откуда переводим товар');
        return;
    }
    const targetOption = departmentOptions.value.find((option) => option.id === transferForm.targetOptionId);
    if (!targetOption || !['warehouse', 'restaurant'].includes(targetOption.type)) {
        toast.error('Выберите ресторан или виртуальный склад');
        return;
    }
    if (sourceOption.id === targetOption.id) {
        toast.error('Источник и получатель совпадают');
        return;
    }
    const quantity = Number.parseInt(String(transferForm.quantity || '0'), 10);
    if (!Number.isFinite(quantity) || quantity <= 0) {
        toast.error('Введите корректное количество');
        return;
    }

    const payload = {
        source_kind: sourceOption.type,
        target_kind: targetOption.type,
        quantity,
    };
    if (sourceOption.type === 'restaurant') {
        payload.source_restaurant_id = Number(sourceOption.restaurant_id);
    }
    if (sourceOption.type === 'subdivision') {
        payload.source_subdivision_id = Number(sourceOption.subdivision_id);
    }
    if (targetOption.type === 'restaurant') {
        payload.restaurant_id = Number(targetOption.restaurant_id);
    }

    saving.value = true;
    try {
        await transferInventoryItem(transferForm.itemId, payload);
        toast.success('Товар переведен');
        closeTransferModal();
        if (hasLoadedByFilters.value) {
            await loadItemsByFilters();
        }
    } catch (error) {
        toast.error(error?.response?.data?.detail || 'Не удалось перевести товар');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

useClickOutside([
    {
        element: departmentSelectRef,
        when: () => isDepartmentsOpen.value,
        onOutside: () => {
            isDepartmentsOpen.value = false;
        },
    },
    {
        element: catalogFilterRef,
        when: () => isCatalogFilterOpen.value,
        onOutside: () => {
            isCatalogFilterOpen.value = false;
        },
    },
    {
        element: catalogModalRef,
        when: () => isCatalogModalOpen.value,
        onOutside: () => {
            isCatalogModalOpen.value = false;
        },
    },
]);

watch(
    () => createDepartmentOptions.value.length,
    () => {
        if (!isItemModalOpen.value || isEditMode.value || !isCatalogSourceMode.value) {
            return;
        }
        if (!itemForm.targetOptionId) {
            itemForm.targetOptionId = getDefaultCreateDepartmentOptionId();
        }
    },
);

onMounted(async () => {
    try {
        await loadLookupData();
    } catch (error) {
        toast.error('Не удалось загрузить справочники склада');
        console.error(error);
    }
});

</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-items' as *;
</style>
