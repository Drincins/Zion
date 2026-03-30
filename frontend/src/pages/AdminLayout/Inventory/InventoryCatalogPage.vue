<template>
    <div class="inventory-catalog">
        <header class="inventory-catalog__header">
            <div class="inventory-catalog__header-main">
                <h1 class="inventory-catalog__title">Каталог товаров</h1>
                <p class="inventory-catalog__subtitle">
                    Полный каталог товаров компании с иерархией групп, категорий и видов.
                </p>
            </div>
            <div class="inventory-catalog__header-actions">
                <Button color="secondary" size="sm" :loading="loading" @click="loadItems">Обновить</Button>
                <Button v-if="canCreateNomenclature" color="primary" size="sm" @click="openCreateModal">Новый товар</Button>
            </div>
        </header>

        <section class="inventory-catalog__filters-panel">
            <button class="inventory-catalog__filters-toggle" type="button" @click="toggleFilters">
                Фильтры
                <span :class="['inventory-catalog__filters-icon', { 'is-open': isFiltersOpen }]">▼</span>
            </button>
            <div v-if="isFiltersOpen" class="inventory-catalog__filters-content">
                <div class="inventory-catalog__filters-row">
                    <Input
                        v-model="searchQuery"
                        label=""
                        class="inventory-catalog__search-control"
                        placeholder="Поиск по названию, описанию или коду товара"
                    />
                    <p class="inventory-catalog__summary">
                        Найдено: <strong>{{ filteredItems.length }}</strong>
                    </p>
                    <Button v-if="searchQuery" color="ghost" size="sm" @click="clearSearch">Сбросить</Button>
                </div>
            </div>
        </section>

        <section class="inventory-catalog__tree-card">
            <div v-if="loading" class="inventory-page__loading">Загрузка каталога...</div>

            <InventoryCatalogWorkspace
                v-else-if="groupedCatalog.length"
                :collapse-all="collapseAll"
                :detail-item="detailItem"
                :expand-all-visible="expandAllVisible"
                :format-item-created-at="formatItemCreatedAt"
                :format-money="formatMoney"
                :get-catalog-path="getCatalogPath"
                :get-highlighted-parts="getHighlightedParts"
                :grouped-catalog="groupedCatalog"
                :is-category-expanded="isCategoryExpanded"
                :is-detail-pane-visible="isDetailPaneVisible"
                :is-group-expanded="isGroupExpanded"
                :is-kind-expanded="isKindExpanded"
                :open-item-card="openItemCard"
                :open-item-detail="openItemDetail"
                :selected-item-id="selectedItemId"
                :toggle-category="toggleCategory"
                :toggle-detail-pane="toggleDetailPane"
                :toggle-group="toggleGroup"
                :toggle-kind="toggleKind"
            />

            <div v-else class="inventory-page__empty">По текущему поиску товары не найдены.</div>
        </section>

        <InventoryCatalogItemModal
            v-if="isItemModalOpen"
            :can-submit-item-modal="canSubmitItemModal"
            :categories-by-group="categoriesByGroup"
            :catalog-modal-ref="catalogModalRef"
            :close-item-modal="closeItemModal"
            :handle-upload-item-photo="handleUploadItemPhoto"
            :is-catalog-modal-open="isCatalogModalOpen"
            :is-edit-mode="isEditMode"
            :is-modal-category-expanded="isModalCategoryExpanded"
            :is-modal-group-expanded="isModalGroupExpanded"
            :item-form="itemForm"
            :open-photo-picker="openPhotoPicker"
            :photo-input-ref="setPhotoInputRef"
            :saving="saving"
            :select-modal-type="selectModalType"
            :selected-type-label="selectedTypeLabel"
            :sorted-groups="sortedGroups"
            :submit-item="submitItem"
            :toggle-modal-category="toggleModalCategory"
            :toggle-modal-group="toggleModalGroup"
            :types-by-category="typesByCategory"
            :uploading-photo="uploadingPhoto"
            @update:is-catalog-modal-open="isCatalogModalOpen = $event"
            @update:item-form="Object.assign(itemForm, $event)"
        />

        <InventoryCatalogItemCardModal
            v-if="isItemCardOpen"
            :can-edit-nomenclature="canEditNomenclature"
            :categories-by-group="categoriesByGroup"
            :catalog-modal-ref="catalogModalRef"
            :close-item-card="closeItemCard"
            :format-item-card-change-date="formatItemCardChangeDate"
            :format-item-card-change-field="formatItemCardChangeField"
            :format-item-card-change-value="formatItemCardChangeValue"
            :format-item-created-at="formatItemCreatedAt"
            :format-money="formatMoney"
            :get-catalog-path="getCatalogPath"
            :is-catalog-modal-open="isCatalogModalOpen"
            :is-modal-category-expanded="isModalCategoryExpanded"
            :is-modal-group-expanded="isModalGroupExpanded"
            :item-card-active-tab="itemCardActiveTab"
            :item-card-changes="itemCardChanges"
            :item-card-changes-error="itemCardChangesError"
            :item-card-changes-loading="itemCardChangesLoading"
            :item-card-item="itemCardItem"
            :item-card-photo-url="itemCardPhotoUrl"
            :item-card-restaurant-rows="itemCardRestaurantRows"
            :item-card-restaurants-quantity="itemCardRestaurantsQuantity"
            :item-card-tabs="ITEM_CARD_TABS"
            :item-card-total-quantity="itemCardTotalQuantity"
            :item-card-warehouse-quantity="itemCardWarehouseQuantity"
            :item-form="itemForm"
            :open-item-card-photo="openItemCardPhoto"
            :reload-item-card-changes="reloadItemCardChanges"
            :saving="saving"
            :select-modal-type="selectModalType"
            :selected-type-label="selectedTypeLabel"
            :sorted-groups="sortedGroups"
            :submit-item-card-info="submitItemCardInfo"
            :toggle-modal-category="toggleModalCategory"
            :toggle-modal-group="toggleModalGroup"
            :types-by-category="typesByCategory"
            :uploading-photo="uploadingPhoto"
            @update:is-catalog-modal-open="isCatalogModalOpen = $event"
            @update:item-card-active-tab="itemCardActiveTab = $event"
            @update:item-form="Object.assign(itemForm, $event)"
        />

        <InventoryCatalogPhotoModal
            v-if="previewPhotoItem"
            :can-delete-preview-photo="canDeletePreviewPhoto"
            :close-item-photo="closeItemPhoto"
            :handle-replace-preview-photo="handleReplacePreviewPhoto"
            :is-preview-photo-editable="isPreviewPhotoEditable"
            :open-preview-photo-picker="openPreviewPhotoPicker"
            :preview-photo-input-ref="setPreviewPhotoInputRef"
            :preview-photo-item="previewPhotoItem"
            :preview-photo-url="previewPhotoUrl"
            :remove-preview-photo="removePreviewPhoto"
            :saving="saving"
            :uploading-photo="uploadingPhoto"
        />

    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import InventoryCatalogItemCardModal from './components/InventoryCatalogItemCardModal.vue';
import InventoryCatalogItemModal from './components/InventoryCatalogItemModal.vue';
import InventoryCatalogPhotoModal from './components/InventoryCatalogPhotoModal.vue';
import InventoryCatalogWorkspace from './components/InventoryCatalogWorkspace.vue';
import { useInventoryCatalogPage } from './composables/useInventoryCatalogPage';

const {
    ITEM_CARD_TABS,
    loading,
    saving,
    uploadingPhoto,
    searchQuery,
    isFiltersOpen,
    isDetailPaneVisible,
    isItemModalOpen,
    isEditMode,
    isCatalogModalOpen,
    isItemCardOpen,
    itemCardActiveTab,
    itemCardChangesLoading,
    itemCardChangesError,
    itemCardChanges,
    itemForm,
    previewPhotoItem,
    selectedItemId,
    photoInputRef,
    previewPhotoInputRef,
    catalogModalRef,
    isPreviewPhotoEditable,
    selectedTypeLabel,
    itemCardItem,
    itemCardPhotoUrl,
    previewPhotoUrl,
    canDeletePreviewPhoto,
    canCreateNomenclature,
    canEditNomenclature,
    canSubmitItemModal,
    itemCardRestaurantRows,
    itemCardTotalQuantity,
    itemCardWarehouseQuantity,
    itemCardRestaurantsQuantity,
    filteredItems,
    detailItem,
    groupedCatalog,
    getCatalogPath,
    formatItemCardChangeDate,
    formatItemCreatedAt,
    formatItemCardChangeField,
    formatItemCardChangeValue,
    getHighlightedParts,
    isGroupExpanded,
    isCategoryExpanded,
    isKindExpanded,
    toggleFilters,
    toggleDetailPane,
    clearSearch,
    toggleGroup,
    toggleCategory,
    toggleKind,
    expandAllVisible,
    collapseAll,
    isModalGroupExpanded,
    isModalCategoryExpanded,
    toggleModalGroup,
    toggleModalCategory,
    selectModalType,
    loadItems,
    openCreateModal,
    openItemCard,
    closeItemCard,
    reloadItemCardChanges,
    closeItemModal,
    openItemDetail,
    openItemCardPhoto,
    closeItemPhoto,
    openPreviewPhotoPicker,
    removePreviewPhoto,
    handleReplacePreviewPhoto,
    openPhotoPicker,
    handleUploadItemPhoto,
    submitItem,
    submitItemCardInfo,
    formatMoney,
    sortedGroups,
    categoriesByGroup,
    typesByCategory,
} = useInventoryCatalogPage();

function setPhotoInputRef(el) {
    photoInputRef.value = el;
}

function setPreviewPhotoInputRef(el) {
    previewPhotoInputRef.value = el;
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-catalog' as *;
</style>
