<template>
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
</template>

<script setup>
import BaseIcon from '@/components/UI-components/BaseIcon.vue';

defineProps({
    canCreateMovement: { type: Boolean, required: true },
    canEditNomenclature: { type: Boolean, required: true },
    formatMoney: { type: Function, required: true },
    getEntryTotalCost: { type: Function, required: true },
    getEntryUnitCost: { type: Function, required: true },
    groupedInventory: { type: Array, required: true },
    hasLoadedByFilters: { type: Boolean, required: true },
    loadingItems: { type: Boolean, required: true },
    openEditModal: { type: Function, required: true },
    openItemDetail: { type: Function, required: true },
    openItemPhoto: { type: Function, required: true },
    openTransferModal: { type: Function, required: true },
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-items' as *;
</style>
