<template>
    <div :class="['inventory-balance__workspace', { 'is-detail-hidden': !isDetailPaneVisible }]">
        <div class="inventory-balance__tree-pane">
            <div class="inventory-balance__tree-toolbar">
                <Button color="ghost" size="sm" @click="expandAllVisible">Развернуть всё</Button>
                <Button color="ghost" size="sm" @click="collapseAll">Свернуть всё</Button>
                <Button color="ghost" size="sm" @click="toggleDetailPane">
                    {{ isDetailPaneVisible ? 'Скрыть карточку' : 'Показать карточку' }}
                </Button>
            </div>

            <div class="inventory-balance__tree">
                <div
                    v-for="groupNode in groupedCatalog"
                    :key="`g:${groupNode.id}`"
                    class="inventory-balance__group"
                >
                    <button
                        type="button"
                        class="inventory-balance__line inventory-balance__line--group"
                        @click="toggleGroup(groupNode.id)"
                    >
                        <span class="inventory-balance__arrow">{{ isGroupExpanded(groupNode.id) ? '⌄' : '›' }}</span>
                        <span class="inventory-balance__line-title">
                            <template
                                v-for="(part, partIndex) in getHighlightedParts(groupNode.name)"
                                :key="`group:${groupNode.id}:${partIndex}`"
                            >
                                <mark v-if="part.match" class="inventory-balance__match">{{ part.text }}</mark>
                                <span v-else>{{ part.text }}</span>
                            </template>
                        </span>
                        <span class="inventory-balance__line-count">{{ groupNode.itemsCount }} товаров</span>
                    </button>

                    <template v-if="isGroupExpanded(groupNode.id)">
                        <div
                            v-for="categoryNode in groupNode.categories"
                            :key="`c:${categoryNode.id}`"
                            class="inventory-balance__category"
                        >
                            <button
                                type="button"
                                class="inventory-balance__line inventory-balance__line--category"
                                @click="toggleCategory(categoryNode.id)"
                            >
                                <span class="inventory-balance__arrow">{{ isCategoryExpanded(categoryNode.id) ? '⌄' : '›' }}</span>
                                <span class="inventory-balance__line-title">
                                    <template
                                        v-for="(part, partIndex) in getHighlightedParts(categoryNode.name)"
                                        :key="`category:${categoryNode.id}:${partIndex}`"
                                    >
                                        <mark v-if="part.match" class="inventory-balance__match">{{ part.text }}</mark>
                                        <span v-else>{{ part.text }}</span>
                                    </template>
                                </span>
                                <span class="inventory-balance__line-count">{{ categoryNode.itemsCount }} товаров</span>
                            </button>

                            <template v-if="isCategoryExpanded(categoryNode.id)">
                                <div
                                    v-for="kindNode in categoryNode.kinds"
                                    :key="`t:${kindNode.id}`"
                                    class="inventory-balance__kind"
                                >
                                    <button
                                        type="button"
                                        class="inventory-balance__line inventory-balance__line--kind"
                                        @click="toggleKind(kindNode.id)"
                                    >
                                        <span class="inventory-balance__arrow">{{ isKindExpanded(kindNode.id) ? '⌄' : '›' }}</span>
                                        <span class="inventory-balance__line-title">
                                            <template
                                                v-for="(part, partIndex) in getHighlightedParts(kindNode.name)"
                                                :key="`kind:${kindNode.id}:${partIndex}`"
                                            >
                                                <mark v-if="part.match" class="inventory-balance__match">{{ part.text }}</mark>
                                                <span v-else>{{ part.text }}</span>
                                            </template>
                                        </span>
                                        <span class="inventory-balance__line-count">{{ kindNode.items.length }} товаров</span>
                                    </button>

                                    <div v-if="isKindExpanded(kindNode.id)" class="inventory-balance__items">
                                        <div
                                            v-for="entry in kindNode.items"
                                            :key="entry.item.id"
                                            :class="[
                                                'inventory-balance__item-row',
                                                {
                                                    'is-selected': Number(selectedItemId) === Number(entry.item.id),
                                                    'is-inactive': entry.item.is_active === false
                                                }
                                            ]"
                                            role="button"
                                            tabindex="0"
                                            @click="openItemDetail(entry.item)"
                                            @keydown.enter.prevent="openItemDetail(entry.item)"
                                            @keydown.space.prevent="openItemDetail(entry.item)"
                                        >
                                            <div class="inventory-balance__item-main">
                                                <span class="inventory-balance__item-name">
                                                    <template
                                                        v-for="(part, partIndex) in getHighlightedParts(entry.item.name)"
                                                        :key="`item:${entry.item.id}:name:${partIndex}`"
                                                    >
                                                        <mark v-if="part.match" class="inventory-balance__match">{{ part.text }}</mark>
                                                        <span v-else>{{ part.text }}</span>
                                                    </template>
                                                </span>
                                                <span
                                                    v-if="entry.item.is_active === false"
                                                    class="inventory-balance__item-status inventory-balance__item-status--inactive"
                                                >
                                                    Архив
                                                </span>
                                            </div>

                                            <span class="inventory-balance__item-qty">{{ entry.quantity }} шт.</span>
                                            <button
                                                type="button"
                                                class="inventory-balance__icon-btn"
                                                title="Информация"
                                                aria-label="Информация"
                                                @click.stop="openItemCard(entry.item)"
                                            >
                                                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                                    <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8" />
                                                    <path
                                                        d="M12 10.25v5.25M12 7.75h.01"
                                                        stroke="currentColor"
                                                        stroke-width="1.8"
                                                        stroke-linecap="round"
                                                        stroke-linejoin="round"
                                                    />
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </template>
                        </div>
                    </template>
                </div>
            </div>
        </div>

        <aside v-if="isDetailPaneVisible" class="inventory-balance__detail-pane">
            <div v-if="detailEntry" class="inventory-balance__detail-stack">
                <div class="inventory-balance__detail-shell inventory-balance__detail-shell--head">
                    <div class="inventory-balance__detail-head-layout">
                        <div
                            v-if="detailEntry.item.photo_url"
                            class="inventory-balance__detail-photo-tile"
                        >
                            <img :src="detailEntry.item.photo_url" :alt="detailEntry.item.name || 'Фото товара'" />
                        </div>
                        <div v-else class="inventory-balance__detail-photo-tile is-empty">
                            <span class="inventory-balance__detail-photo-empty">Нет фото</span>
                        </div>

                        <div class="inventory-balance__detail-head-content">
                            <h3 class="inventory-balance__detail-title">{{ detailEntry.item.name }}</h3>
                            <p class="inventory-balance__detail-path">
                                {{ getCatalogPath(detailEntry.item) }} · {{ selectedStoragePlaceLabel }}
                            </p>
                            <p class="inventory-balance__detail-note">{{ detailEntry.item.note || 'Описание не заполнено' }}</p>
                            <div class="inventory-balance__detail-preview-meta">
                                <span class="inventory-balance__detail-preview-pill">{{ detailEntry.item.code }}</span>
                                <span class="inventory-balance__detail-preview-pill">{{ detailEntry.quantity }} шт.</span>
                                <span class="inventory-balance__detail-preview-pill">{{ formatMoney(detailEntry.avgCost ?? detailEntry.item.cost) }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div v-else class="inventory-balance__detail-placeholder">
                Выберите товар в дереве слева, чтобы открыть карточку.
            </div>
        </aside>
    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';

defineProps({
    collapseAll: { type: Function, required: true },
    detailEntry: { type: Object, default: null },
    expandAllVisible: { type: Function, required: true },
    formatMoney: { type: Function, required: true },
    getCatalogPath: { type: Function, required: true },
    getHighlightedParts: { type: Function, required: true },
    groupedCatalog: { type: Array, required: true },
    isCategoryExpanded: { type: Function, required: true },
    isDetailPaneVisible: { type: Boolean, required: true },
    isGroupExpanded: { type: Function, required: true },
    isKindExpanded: { type: Function, required: true },
    openItemCard: { type: Function, required: true },
    openItemDetail: { type: Function, required: true },
    selectedItemId: { type: [Number, String], default: null },
    selectedStoragePlaceLabel: { type: String, required: true },
    toggleCategory: { type: Function, required: true },
    toggleDetailPane: { type: Function, required: true },
    toggleGroup: { type: Function, required: true },
    toggleKind: { type: Function, required: true },
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-balance' as *;
</style>
