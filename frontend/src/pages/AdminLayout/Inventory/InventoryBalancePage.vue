<template>
    <div class="inventory-balance">
        <header class="inventory-balance__header">
            <div class="inventory-balance__header-main">
                <h1 class="inventory-balance__title">Баланс ресторана</h1>
                <p class="inventory-balance__subtitle">
                    Остатки, операции и карточки товара в выбранном ресторане и месте хранения.
                </p>
            </div>
            <div class="inventory-balance__header-actions">
                <router-link :to="{ name: 'inventory-journal' }" class="inventory-balance__journal-link">
                    Журнал операций
                </router-link>
                <Button color="secondary" size="sm" :loading="loading" :disabled="!selectedRestaurantId" @click="loadRestaurantItems">
                    Обновить
                </Button>
                <Button
                    v-if="canCreateMovement"
                    color="primary"
                    size="sm"
                    :disabled="!selectedRestaurantId"
                    @click="openOperationModal"
                >
                    Операция
                </Button>
            </div>
        </header>

        <section class="inventory-balance__filters-panel">
            <div class="inventory-balance__filters-row">
                <Select
                    v-model="selectedRestaurantId"
                    label="Ресторан"
                    :options="restaurantOptions"
                    placeholder="Выберите ресторан"
                    searchable
                    class="inventory-balance__restaurant-select"
                />
                <Select
                    v-model="selectedStoragePlaceId"
                    label="Место хранения"
                    :options="storagePlaceFilterOptions"
                    placeholder="Все места хранения"
                    :disabled="!selectedRestaurantId"
                    searchable
                    class="inventory-balance__storage-place-select"
                />
                <Input
                    v-model="searchQuery"
                    label=""
                    class="inventory-balance__search"
                    placeholder="Поиск по названию, описанию, коду"
                    :disabled="!selectedRestaurantId"
                />
                <p class="inventory-balance__summary">
                    {{ selectedStoragePlaceLabel }} · Найдено: <strong>{{ groupedItemsCount }}</strong>
                </p>
            </div>
        </section>

        <section class="inventory-balance__tree-card">
            <div v-if="!selectedRestaurantId" class="inventory-page__empty">
                Выберите ресторан, чтобы посмотреть баланс.
            </div>

            <div v-else-if="loading" class="inventory-page__loading">Загрузка баланса ресторана...</div>

            <InventoryBalanceWorkspace
                v-else-if="groupedCatalog.length"
                :collapse-all="collapseAll"
                :detail-entry="detailEntry"
                :expand-all-visible="expandAllVisible"
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
                :selected-storage-place-label="selectedStoragePlaceLabel"
                :toggle-category="toggleCategory"
                :toggle-detail-pane="toggleDetailPane"
                :toggle-group="toggleGroup"
                :toggle-kind="toggleKind"
            />

            <div v-else class="inventory-page__empty">По выбранному ресторану товаров не найдено.</div>
        </section>

        <InventoryBalanceItemCardModal
            v-if="isItemCardModalOpen && detailEntry"
            :close-item-card="closeItemCard"
            :current-instance-count="currentInstanceCount"
            :detail-arrivals="detailArrivals"
            :detail-card-loading="detailCardLoading"
            :detail-entry="detailEntry"
            :detail-tab="detailTab"
            :format-date-time="formatDateTime"
            :format-money="formatMoney"
            :get-catalog-path="getCatalogPath"
            :historical-instance-count="historicalInstanceCount"
            :instance-events="instanceEvents"
            :instance-events-loading="instanceEventsLoading"
            :instance-summaries="instanceSummaries"
            :instance-tracking-enabled="instanceTrackingEnabled"
            :open-instance-event-modal="openInstanceEventModal"
            :select-instance="selectInstance"
            :selected-instance-code="selectedInstanceCode"
            :selected-instance-summary="selectedInstanceSummary"
            :selected-restaurant-name="selectedRestaurantName"
            :selected-storage-place-label="selectedStoragePlaceLabel"
            @update:detail-tab="detailTab = $event"
        />

        <InventoryBalanceInstanceEventModal
            v-if="isInstanceEventModalOpen"
            :close-instance-event-modal="closeInstanceEventModal"
            :instance-event-form="instanceEventForm"
            :instance-event-submitting="instanceEventSubmitting"
            :instance-event-type-options="instanceEventTypeOptions"
            :selected-instance-summary="selectedInstanceSummary"
            :submit-instance-event="submitInstanceEvent"
        />

        <InventoryBalanceOperationModal
            v-if="isOperationModalOpen"
            :close-operation-modal="closeOperationModal"
            :is-income-operation="isIncomeOperation"
            :is-transfer-operation="isTransferOperation"
            :is-writeoff-operation="isWriteoffOperation"
            :operation-draft-record="operationDraftRecord"
            :operation-form="operationForm"
            :operation-item-options="operationItemOptions"
            :operation-submitting="operationSubmitting"
            :operation-target-storage-place-label="operationTargetStoragePlaceLabel"
            :operation-type="operationType"
            :operation-type-options="operationTypeOptions"
            :restaurant-options="restaurantOptions"
            :selected-operation-item="selectedOperationItem"
            :selected-restaurant-name="selectedRestaurantName"
            :selected-storage-place-label="selectedStoragePlaceLabel"
            :source-location-quantity="sourceLocationQuantity"
            :source-storage-place-options="sourceStoragePlaceOptions"
            :submit-operation="submitOperation"
            :target-storage-place-options="targetStoragePlaceOptions"
            @update:operation-type="operationType = $event"
        />
    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import InventoryBalanceInstanceEventModal from './components/InventoryBalanceInstanceEventModal.vue';
import InventoryBalanceItemCardModal from './components/InventoryBalanceItemCardModal.vue';
import InventoryBalanceOperationModal from './components/InventoryBalanceOperationModal.vue';
import InventoryBalanceWorkspace from './components/InventoryBalanceWorkspace.vue';
import { useInventoryBalancePage } from './composables/useInventoryBalancePage';

const {
    canCreateMovement,
    closeInstanceEventModal,
    closeItemCard,
    closeOperationModal,
    collapseAll,
    currentInstanceCount,
    detailArrivals,
    detailCardLoading,
    detailEntry,
    detailTab,
    expandAllVisible,
    formatDateTime,
    formatMoney,
    getCatalogPath,
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
    operationItemOptions,
    operationSubmitting,
    operationTargetStoragePlaceLabel,
    operationType,
    operationTypeOptions,
    restaurantOptions,
    searchQuery,
    selectInstance,
    selectedInstanceCode,
    selectedInstanceSummary,
    selectedItemId,
    selectedOperationItem,
    selectedRestaurantId,
    selectedRestaurantName,
    selectedStoragePlaceId,
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
} = useInventoryBalancePage();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-balance' as *;
</style>
