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

        <InventoryItemsFilters
            :catalog-filter-label="catalogFilterLabel"
            :catalog-filter-ref="catalogFilterRef"
            :categories-by-group="categoriesByGroup"
            :clear-filter-catalog-nodes="clearFilterCatalogNodes"
            :department-search="departmentSearch"
            :department-select-ref="departmentSelectRef"
            :departments-label="departmentsLabel"
            :filtered-department-options="filteredDepartmentOptions"
            :is-catalog-filter-open="isCatalogFilterOpen"
            :is-catalog-node-selected="isCatalogNodeSelected"
            :is-departments-open="isDepartmentsOpen"
            :is-filter-category-expanded="isFilterCategoryExpanded"
            :is-filter-group-expanded="isFilterGroupExpanded"
            :load-items-by-filters="loadItemsByFilters"
            :loading-items="loadingItems"
            :reset-filters="resetFilters"
            :selected-catalog-node-ids="selectedCatalogNodeIds"
            :selected-department-ids="selectedDepartmentIds"
            :selected-department-labels="selectedDepartmentLabels"
            :sorted-groups="sortedGroups"
            :toggle-department="toggleDepartment"
            :toggle-filter-catalog-node="toggleFilterCatalogNode"
            :toggle-filter-category="toggleFilterCategory"
            :toggle-filter-group="toggleFilterGroup"
            :types-by-category="typesByCategory"
            @update:department-search="departmentSearch = $event"
            @update:is-catalog-filter-open="isCatalogFilterOpen = $event"
            @update:is-departments-open="isDepartmentsOpen = $event"
        />

        <InventoryItemsHierarchy
            :can-create-movement="canCreateMovement"
            :can-edit-nomenclature="canEditNomenclature"
            :format-money="formatMoney"
            :get-entry-total-cost="getEntryTotalCost"
            :get-entry-unit-cost="getEntryUnitCost"
            :grouped-inventory="groupedInventory"
            :has-loaded-by-filters="hasLoadedByFilters"
            :loading-items="loadingItems"
            :open-edit-modal="openEditModal"
            :open-item-detail="openItemDetail"
            :open-item-photo="openItemPhoto"
            :open-transfer-modal="openTransferModal"
        />

        <InventoryItemsItemModal
            v-if="isItemModalOpen"
            :can-edit-modal-photo="canEditModalPhoto"
            :can-submit-item-modal="canSubmitItemModal"
            :can-toggle-create-source-mode="canToggleCreateSourceMode"
            :catalog-items-for-picker="catalogItemsForPicker"
            :catalog-modal-label="catalogModalLabel"
            :catalog-modal-ref="catalogModalRef"
            :categories-by-group="categoriesByGroup"
            :close-item-modal="closeItemModal"
            :create-department-options="createDepartmentOptions"
            :get-catalog-path="getCatalogPath"
            :handle-upload-item-photo="handleUploadItemPhoto"
            :is-catalog-cost-override="isCatalogCostOverride"
            :is-catalog-modal-open="isCatalogModalOpen"
            :is-catalog-source-mode="isCatalogSourceMode"
            :is-edit-mode="isEditMode"
            :is-modal-category-expanded="isModalCategoryExpanded"
            :is-modal-group-expanded="isModalGroupExpanded"
            :item-form="itemForm"
            :loading-catalog-items="loadingCatalogItems"
            :open-photo-picker="openPhotoPicker"
            :photo-input-ref="setPhotoInputRef"
            :saving="saving"
            :select-catalog-item="selectCatalogItem"
            :select-modal-type="selectModalType"
            :selected-catalog-item="selectedCatalogItem"
            :sorted-groups="sortedGroups"
            :submit-item="submitItem"
            :toggle-catalog-source-mode="toggleCatalogSourceMode"
            :toggle-modal-category="toggleModalCategory"
            :toggle-modal-group="toggleModalGroup"
            :types-by-category="typesByCategory"
            :uploading-photo="uploadingPhoto"
            @update:is-catalog-modal-open="isCatalogModalOpen = $event"
            @update:item-form="Object.assign(itemForm, $event)"
        />

        <InventoryItemsTransferModal
            v-if="isTransferModalOpen"
            :can-create-movement="canCreateMovement"
            :close-transfer-modal="closeTransferModal"
            :saving="saving"
            :source-transfer-location-options="sourceTransferLocationOptions"
            :submit-transfer="submitTransfer"
            :target-transfer-location-options="targetTransferLocationOptions"
            :transfer-form="transferForm"
            @update:transfer-form="Object.assign(transferForm, $event)"
        />

        <InventoryItemsPhotoModal
            v-if="previewPhotoItem"
            :close-item-photo="closeItemPhoto"
            :preview-photo-item="previewPhotoItem"
        />

        <InventoryItemsDetailModal
            v-if="detailItemEntry"
            :can-create-movement="canCreateMovement"
            :close-item-detail="closeItemDetail"
            :detail-item-entry="detailItemEntry"
            :format-money="formatMoney"
            :get-catalog-path="getCatalogPath"
            :handle-update-quantity-from-detail="handleUpdateQuantityFromDetail"
            :quantity-form="quantityForm"
            :saving="saving"
            @update:quantity-form="Object.assign(quantityForm, $event)"
        />
    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import InventoryItemsDetailModal from './components/InventoryItemsDetailModal.vue';
import InventoryItemsFilters from './components/InventoryItemsFilters.vue';
import InventoryItemsHierarchy from './components/InventoryItemsHierarchy.vue';
import InventoryItemsItemModal from './components/InventoryItemsItemModal.vue';
import InventoryItemsPhotoModal from './components/InventoryItemsPhotoModal.vue';
import InventoryItemsTransferModal from './components/InventoryItemsTransferModal.vue';
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

function setPhotoInputRef(el) {
    photoInputRef.value = el;
}

</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-items' as *;
</style>
