<template>
    <div :class="['inventory-catalog__workspace', { 'is-detail-hidden': !isDetailPaneVisible }]">
        <div class="inventory-catalog__tree-pane">
            <div class="inventory-catalog__tree-toolbar">
                <Button color="ghost" size="sm" @click="expandAllVisible">Развернуть всё</Button>
                <Button color="ghost" size="sm" @click="collapseAll">Свернуть всё</Button>
                <Button color="ghost" size="sm" @click="toggleDetailPane">
                    {{ isDetailPaneVisible ? 'Скрыть карточку' : 'Показать карточку' }}
                </Button>
            </div>

            <div class="inventory-catalog__tree">
                <div
                    v-for="groupNode in groupedCatalog"
                    :key="`g:${groupNode.id}`"
                    class="inventory-catalog__group"
                >
                    <button
                        type="button"
                        class="inventory-catalog__line inventory-catalog__line--group"
                        @click="toggleGroup(groupNode.id)"
                    >
                        <span class="inventory-catalog__arrow">{{ isGroupExpanded(groupNode.id) ? '⌄' : '›' }}</span>
                        <span class="inventory-catalog__line-title">
                            <template v-for="(part, partIndex) in getHighlightedParts(groupNode.name)" :key="`group:${groupNode.id}:${partIndex}`">
                                <mark v-if="part.match" class="inventory-catalog__match">{{ part.text }}</mark>
                                <span v-else>{{ part.text }}</span>
                            </template>
                        </span>
                        <span class="inventory-catalog__line-count">{{ groupNode.itemsCount }} товаров</span>
                    </button>

                    <template v-if="isGroupExpanded(groupNode.id)">
                        <div
                            v-for="categoryNode in groupNode.categories"
                            :key="`c:${categoryNode.id}`"
                            class="inventory-catalog__category"
                        >
                            <button
                                type="button"
                                class="inventory-catalog__line inventory-catalog__line--category"
                                @click="toggleCategory(categoryNode.id)"
                            >
                                <span class="inventory-catalog__arrow">{{ isCategoryExpanded(categoryNode.id) ? '⌄' : '›' }}</span>
                                <span class="inventory-catalog__line-title">
                                    <template v-for="(part, partIndex) in getHighlightedParts(categoryNode.name)" :key="`category:${categoryNode.id}:${partIndex}`">
                                        <mark v-if="part.match" class="inventory-catalog__match">{{ part.text }}</mark>
                                        <span v-else>{{ part.text }}</span>
                                    </template>
                                </span>
                                <span class="inventory-catalog__line-count">{{ categoryNode.itemsCount }} товаров</span>
                            </button>

                            <template v-if="isCategoryExpanded(categoryNode.id)">
                                <div
                                    v-for="kindNode in categoryNode.kinds"
                                    :key="`t:${kindNode.id}`"
                                    class="inventory-catalog__kind"
                                >
                                    <button
                                        type="button"
                                        class="inventory-catalog__line inventory-catalog__line--kind"
                                        @click="toggleKind(kindNode.id)"
                                    >
                                        <span class="inventory-catalog__arrow">{{ isKindExpanded(kindNode.id) ? '⌄' : '›' }}</span>
                                        <span class="inventory-catalog__line-title">
                                            <template v-for="(part, partIndex) in getHighlightedParts(kindNode.name)" :key="`kind:${kindNode.id}:${partIndex}`">
                                                <mark v-if="part.match" class="inventory-catalog__match">{{ part.text }}</mark>
                                                <span v-else>{{ part.text }}</span>
                                            </template>
                                        </span>
                                        <span class="inventory-catalog__line-count">{{ kindNode.items.length }} товаров</span>
                                    </button>

                                    <div v-if="isKindExpanded(kindNode.id)" class="inventory-catalog__items">
                                        <div
                                            v-for="item in kindNode.items"
                                            :key="item.id"
                                            :class="[
                                                'inventory-catalog__item-row',
                                                {
                                                    'is-selected': Number(selectedItemId) === Number(item.id),
                                                    'is-inactive': item.is_active === false
                                                }
                                            ]"
                                            role="button"
                                            tabindex="0"
                                            @click="openItemDetail(item)"
                                            @keydown.enter.prevent="openItemDetail(item)"
                                            @keydown.space.prevent="openItemDetail(item)"
                                        >
                                            <div class="inventory-catalog__item-main">
                                                <span class="inventory-catalog__item-name">
                                                    <template v-for="(part, partIndex) in getHighlightedParts(item.name)" :key="`item:${item.id}:name:${partIndex}`">
                                                        <mark v-if="part.match" class="inventory-catalog__match">{{ part.text }}</mark>
                                                        <span v-else>{{ part.text }}</span>
                                                    </template>
                                                </span>
                                                <span
                                                    v-if="item.is_active === false"
                                                    class="inventory-catalog__item-status inventory-catalog__item-status--inactive"
                                                >
                                                    Архив
                                                </span>
                                            </div>
                                            <div class="inventory-catalog__item-actions">
                                                <button
                                                    type="button"
                                                    class="inventory-catalog__icon-btn"
                                                    title="Информация"
                                                    aria-label="Информация"
                                                    @click.stop="openItemCard(item)"
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
                                </div>
                            </template>
                        </div>
                    </template>
                </div>
            </div>
        </div>

        <aside v-if="isDetailPaneVisible" class="inventory-catalog__detail-pane">
            <div v-if="detailItem" class="inventory-catalog__detail-stack">
                <div class="inventory-catalog__detail-shell inventory-catalog__detail-shell--head">
                    <div class="inventory-catalog__detail-head-layout">
                        <div
                            v-if="detailItem.photo_url"
                            class="inventory-catalog__detail-photo-tile"
                        >
                            <img :src="detailItem.photo_url" :alt="detailItem.name || 'Фото товара'" />
                        </div>
                        <div v-else class="inventory-catalog__detail-photo-tile is-empty">
                            <span class="inventory-catalog__detail-photo-empty">Нет фото</span>
                        </div>

                        <div class="inventory-catalog__detail-head-content">
                            <h3 class="inventory-catalog__detail-title">{{ detailItem.name }}</h3>
                            <p class="inventory-catalog__detail-path">{{ getCatalogPath(detailItem) }}</p>
                            <p class="inventory-catalog__detail-note">{{ detailItem.note || 'Описание не заполнено' }}</p>
                            <div class="inventory-catalog__detail-preview-meta">
                                <span class="inventory-catalog__detail-preview-pill">{{ detailItem.code }}</span>
                                <span class="inventory-catalog__detail-preview-pill">{{ formatMoney(detailItem.cost) }}</span>
                                <span class="inventory-catalog__detail-preview-pill">{{ detailItem.total_quantity || 0 }} шт.</span>
                                <span
                                    :class="[
                                        'inventory-catalog__detail-preview-pill',
                                        'inventory-catalog__status-pill',
                                        { 'is-inactive': detailItem.is_active === false }
                                    ]"
                                >
                                    {{ detailItem.is_active === false ? 'Архив' : 'Активный' }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="inventory-catalog__detail-shell inventory-catalog__detail-shell--specs">
                    <h4 class="inventory-catalog__detail-section-title">Дополнительно</h4>
                    <div class="inventory-catalog__detail-grid">
                        <div>
                            <span class="inventory-catalog__detail-label">Производитель</span>
                            <span class="inventory-catalog__detail-value">{{ detailItem.manufacturer || '—' }}</span>
                        </div>
                        <div>
                            <span class="inventory-catalog__detail-label">Условия хранения</span>
                            <span class="inventory-catalog__detail-value">{{ detailItem.storage_conditions || '—' }}</span>
                        </div>
                        <div>
                            <span class="inventory-catalog__detail-label">Дата создания</span>
                            <span class="inventory-catalog__detail-value">{{ formatItemCreatedAt(detailItem.created_at) }}</span>
                        </div>
                    </div>
                </div>

            </div>

            <div v-else class="inventory-catalog__detail-placeholder">
                Выберите товар в дереве слева, чтобы увидеть подробную карточку.
            </div>
        </aside>
    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';

defineProps({
    collapseAll: { type: Function, required: true },
    detailItem: { type: Object, default: null },
    expandAllVisible: { type: Function, required: true },
    formatItemCreatedAt: { type: Function, required: true },
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
    toggleCategory: { type: Function, required: true },
    toggleDetailPane: { type: Function, required: true },
    toggleGroup: { type: Function, required: true },
    toggleKind: { type: Function, required: true },
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-catalog' as *;
</style>
