<template>
    <section class="kb-items" @contextmenu.prevent="emit('context-empty', { event: $event, area: 'items' })">
        <nav class="kb-items__breadcrumbs">
            <button
                v-for="(crumb, index) in breadcrumbs"
                :key="`crumb-${index}-${crumb.id ?? 'root'}`"
                type="button"
                class="kb-items__crumb"
                :class="{ 'is-active': Number(crumb.id) === Number(activeFolderId) || (!crumb.id && activeFolderId === null) }"
                @click="emit('navigate-breadcrumb', crumb.id ?? null)"
            >
                {{ crumb.name }}
            </button>
        </nav>

        <div v-if="loading" class="kb-items__state">Загрузка элементов...</div>
        <div v-else-if="!items.length" class="kb-items__state">Здесь пока пусто</div>

        <div
            v-else
            ref="viewportRef"
            class="kb-items__viewport"
            @scroll.passive="handleScroll"
        >
            <div
                :class="[
                    'kb-items__grid',
                    `kb-items__grid--${viewMode}`,
                    `kb-items__grid--icon-${iconSize}`
                ]"
                :style="gridVirtualStyle"
            >
                <article
                    v-for="item in visibleItems"
                    :key="`${item.item_type}-${item.id}`"
                    class="kb-items__card"
                    :class="{
                        'is-selected': Number(selectedItemId) === Number(item.id),
                        'is-folder': item.item_type === 'folder',
                        'is-document': item.item_type === 'document',
                    }"
                    role="button"
                    tabindex="0"
                    @click="emit('select-item', item)"
                    @dblclick="handleOpen(item)"
                    @contextmenu.stop.prevent="emit('context-item', { event: $event, item })"
                    @keydown.enter.prevent="handleOpen(item)"
                    @keydown.space.prevent="emit('select-item', item)"
                >
                    <div
                        class="kb-items__icon"
                        :class="{ 'kb-items__icon--custom': item.item_type === 'folder' || item.preview_type === 'pdf' || item.document_type === 'text' || isWordDocument(item) || isSpreadsheetDocument(item) }"
                        :style="{ '--folder-accent': resolveAccent(item) }"
                    >
                        <KnowledgeBaseFolderIcon
                            v-if="item.item_type === 'folder'"
                            class="kb-items__folder-icon"
                            :accent="resolveAccent(item)"
                        />
                        <KnowledgeBasePdfIcon
                            v-else-if="item.preview_type === 'pdf'"
                            class="kb-items__pdf-icon"
                        />
                        <KnowledgeBaseExcelIcon
                            v-else-if="isSpreadsheetDocument(item)"
                            class="kb-items__excel-icon"
                        />
                        <KnowledgeBaseTextIcon
                            v-else-if="item.document_type === 'text'"
                            class="kb-items__text-icon"
                        />
                        <KnowledgeBaseWordIcon
                            v-else-if="isWordDocument(item)"
                            class="kb-items__word-icon"
                        />
                        <template v-else>
                            {{ resolveGlyph(item) }}
                        </template>
                    </div>
                    <div class="kb-items__meta">
                        <h4 class="kb-items__name">{{ item.name }}</h4>
                        <p class="kb-items__subline">{{ describeItem(item) }}</p>
                    </div>
                </article>
            </div>
        </div>

        <div v-if="hasMore" class="kb-items__footer">
            <button
                type="button"
                class="kb-items__load-more"
                :disabled="loadingMore"
                @click="emit('load-more')"
            >
                {{ loadingMore ? 'Загрузка...' : 'Показать еще' }}
            </button>
        </div>
    </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import KnowledgeBaseFolderIcon from './KnowledgeBaseFolderIcon.vue';
import KnowledgeBasePdfIcon from './KnowledgeBasePdfIcon.vue';
import KnowledgeBaseTextIcon from './KnowledgeBaseTextIcon.vue';
import KnowledgeBaseWordIcon from './KnowledgeBaseWordIcon.vue';
import KnowledgeBaseExcelIcon from './KnowledgeBaseExcelIcon.vue';
import { isKnowledgeBaseSpreadsheetDocument, isKnowledgeBaseWordDocument } from '../utils/documents';

const GRID_GAP_PX = 10;
const OVERSCAN_ROWS = 4;
const VIRTUALIZATION_THRESHOLD = 140;

const MODE_LAYOUT = Object.freeze({
    tile: {
        minWidth: 190,
        rowHeight: 124,
    },
    list: {
        minWidth: Infinity,
        rowHeight: 68,
    },
    compact: {
        minWidth: 250,
        rowHeight: 62,
    },
});

const props = defineProps({
    items: {
        type: Array,
        default: () => [],
    },
    breadcrumbs: {
        type: Array,
        default: () => [],
    },
    selectedItemId: {
        type: Number,
        default: null,
    },
    activeFolderId: {
        type: Number,
        default: null,
    },
    loading: {
        type: Boolean,
        default: false,
    },
    loadingMore: {
        type: Boolean,
        default: false,
    },
    hasMore: {
        type: Boolean,
        default: false,
    },
    viewMode: {
        type: String,
        default: 'tile',
    },
    iconSize: {
        type: String,
        default: 'md',
    },
    folderStyleMap: {
        type: Object,
        default: () => ({}),
    },
});

const emit = defineEmits([
    'navigate-breadcrumb',
    'select-item',
    'open-folder',
    'open-document',
    'context-item',
    'context-empty',
    'load-more',
]);

const viewportRef = ref(null);
const viewportHeight = ref(0);
const viewportWidth = ref(0);
const scrollTop = ref(0);

let resizeObserver = null;

const modeLayout = computed(() => MODE_LAYOUT[props.viewMode] || MODE_LAYOUT.tile);
const shouldVirtualize = computed(() => props.items.length > VIRTUALIZATION_THRESHOLD);

const columnCount = computed(() => {
    if (props.viewMode === 'list') {
        return 1;
    }
    const minWidth = Number(modeLayout.value.minWidth) || 1;
    const width = Math.max(Number(viewportWidth.value) || 0, minWidth);
    return Math.max(1, Math.floor((width + GRID_GAP_PX) / (minWidth + GRID_GAP_PX)));
});

const rowStride = computed(() => (Number(modeLayout.value.rowHeight) || 64) + GRID_GAP_PX);

const totalRows = computed(() => {
    if (!Array.isArray(props.items) || !props.items.length) {
        return 0;
    }
    return Math.ceil(props.items.length / Math.max(columnCount.value, 1));
});

const viewportRowCapacity = computed(() => {
    const height = Math.max(Number(viewportHeight.value) || 0, 300);
    return Math.max(1, Math.ceil(height / Math.max(rowStride.value, 1)));
});

const startRow = computed(() => {
    const raw = Math.floor((Number(scrollTop.value) || 0) / Math.max(rowStride.value, 1));
    return Math.max(0, raw - OVERSCAN_ROWS);
});

const endRowExclusive = computed(() => {
    const count = viewportRowCapacity.value + OVERSCAN_ROWS * 2;
    return Math.min(totalRows.value, startRow.value + count);
});

const startIndex = computed(() => startRow.value * columnCount.value);
const endIndex = computed(() => Math.min(props.items.length, endRowExclusive.value * columnCount.value));

const safeStartIndex = computed(() => (shouldVirtualize.value ? startIndex.value : 0));
const safeEndIndex = computed(() => (shouldVirtualize.value ? endIndex.value : props.items.length));
const visibleItems = computed(() => props.items.slice(safeStartIndex.value, safeEndIndex.value));

const topPadding = computed(() => (shouldVirtualize.value ? startRow.value * rowStride.value : 0));
const bottomPadding = computed(() => {
    if (!shouldVirtualize.value) {
        return 0;
    }
    return Math.max(0, (totalRows.value - endRowExclusive.value) * rowStride.value);
});
const gridVirtualStyle = computed(() => ({
    paddingTop: topPadding.value > 0 ? `${topPadding.value}px` : undefined,
    paddingBottom: bottomPadding.value > 0 ? `${bottomPadding.value}px` : undefined,
}));

watch(
    () => [props.viewMode, props.items.length],
    () => {
        updateViewportMetrics();
        clampScrollIfNeeded();
    },
    { flush: 'post' },
);

onMounted(() => {
    updateViewportMetrics();
});

onBeforeUnmount(() => {
    detachResizeObserver();
});

watch(
    () => viewportRef.value,
    (viewport, previousViewport) => {
        if (previousViewport && resizeObserver) {
            resizeObserver.unobserve(previousViewport);
        }
        if (!viewport || typeof ResizeObserver === 'undefined') {
            return;
        }
        if (!resizeObserver) {
            resizeObserver = new ResizeObserver(() => {
                updateViewportMetrics();
                clampScrollIfNeeded();
            });
        }
        resizeObserver.observe(viewport);
        updateViewportMetrics();
        clampScrollIfNeeded();
    },
    { flush: 'post' },
);

function detachResizeObserver() {
    if (!resizeObserver) {
        return;
    }
    resizeObserver.disconnect();
    resizeObserver = null;
}

function updateViewportMetrics() {
    const viewport = viewportRef.value;
    if (!viewport) {
        return;
    }
    viewportHeight.value = viewport.clientHeight || 0;
    viewportWidth.value = viewport.clientWidth || 0;
    scrollTop.value = viewport.scrollTop || 0;
}

function clampScrollIfNeeded() {
    const viewport = viewportRef.value;
    if (!viewport) {
        return;
    }
    const maxScrollTop = Math.max(0, viewport.scrollHeight - viewport.clientHeight);
    if (viewport.scrollTop > maxScrollTop) {
        viewport.scrollTop = maxScrollTop;
        scrollTop.value = maxScrollTop;
    }
}

function handleScroll(event) {
    const target = event?.target;
    if (!target) {
        return;
    }
    scrollTop.value = target.scrollTop || 0;

    if (!props.hasMore || props.loadingMore) {
        return;
    }
    const thresholdPx = 220;
    const nearBottom = (target.scrollTop + target.clientHeight) >= (target.scrollHeight - thresholdPx);
    if (nearBottom) {
        emit('load-more');
    }
}

function handleOpen(item) {
    if (!item) {
        return;
    }
    if (item.item_type === 'folder') {
        emit('open-folder', item);
        return;
    }
    emit('open-document', item);
}

const isWordDocument = isKnowledgeBaseWordDocument;
const isSpreadsheetDocument = isKnowledgeBaseSpreadsheetDocument;

function resolveGlyph(item) {
    if (item.item_type === 'folder') {
        return '📁';
    }
    if (item.preview_type === 'pdf') {
        return '📕';
    }
    if (isSpreadsheetDocument(item)) {
        return '📗';
    }
    if (item.document_type === 'text') {
        return '📝';
    }
    return '📄';
}

function describeItem(item) {
    if (item.item_type === 'folder') {
        return 'Папка';
    }
    if (item.document_type === 'text') {
        return 'Текстовый документ';
    }
    if (item.preview_type === 'pdf') {
        return 'PDF файл';
    }
    if (isSpreadsheetDocument(item)) {
        return 'Таблица / Excel';
    }
    return 'Файл';
}

function resolveAccent(item) {
    if (item.item_type !== 'folder') {
        return 'var(--color-primary)';
    }
    const styleKey = item.style_key;
    if (!styleKey) {
        return 'var(--color-primary)';
    }
    return props.folderStyleMap?.[styleKey]?.accent || 'var(--color-primary)';
}
</script>

<style scoped lang="scss">
.kb-items {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 220px;
}

.kb-items__breadcrumbs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.kb-items__crumb {
    border: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
    background: transparent;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 12px;
    color: var(--color-text-secondary);
    cursor: pointer;
}

.kb-items__crumb.is-active {
    color: var(--color-text);
    background: color-mix(in srgb, var(--color-primary) 20%, transparent);
}

.kb-items__state {
    color: var(--color-text-secondary);
    font-size: 14px;
}

.kb-items__viewport {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 2px 0;
}

.kb-items__grid {
    display: grid;
    gap: 10px;
    box-sizing: border-box;
}

.kb-items__grid--tile {
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
}

.kb-items__grid--list {
    grid-template-columns: 1fr;
}

.kb-items__grid--compact {
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
}

.kb-items__card {
    border: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
    background: color-mix(in srgb, var(--color-surface) 88%, transparent);
    border-radius: 14px;
    padding: 10px;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    transition: transform $duration, background-color $duration, border-color $duration;
}

.kb-items__card:hover {
    transform: translateY(-1px);
    border-color: color-mix(in srgb, var(--color-primary) 44%, var(--color-border) 56%);
}

.kb-items__card.is-selected {
    background: color-mix(in srgb, var(--color-primary) 16%, var(--color-surface) 84%);
    border-color: color-mix(in srgb, var(--color-primary) 45%, var(--color-border) 55%);
}

.kb-items__icon {
    flex: 0 0 auto;
    font-size: 20px;
    filter: drop-shadow(0 0 0 var(--folder-accent));
}

.kb-items__icon--custom {
    filter: none;
}

.kb-items__grid--icon-lg .kb-items__icon {
    font-size: 28px;
}

.kb-items__folder-icon {
    width: 1.35em;
    height: 1.3em;
    display: block;
}

.kb-items__pdf-icon {
    width: 1.05em;
    height: 1.3em;
    display: block;
}

.kb-items__text-icon {
    width: 1.05em;
    height: 1.3em;
    display: block;
}

.kb-items__word-icon {
    width: 1.05em;
    height: 1.3em;
    display: block;
}

.kb-items__excel-icon {
    width: 1.05em;
    height: 1.3em;
    display: block;
}

.kb-items__meta {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
}

.kb-items__name {
    margin: 0;
    font-size: 14px;
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.kb-items__subline {
    margin: 0;
    color: var(--color-text-secondary);
    font-size: 12px;
}

.kb-items__grid--compact .kb-items__card {
    padding: 8px 10px;
    border-radius: 10px;
}

.kb-items__footer {
    display: flex;
    justify-content: center;
    padding: 8px 0 2px;
}

.kb-items__load-more {
    border: 1px solid color-mix(in srgb, var(--color-primary) 40%, transparent);
    background: color-mix(in srgb, var(--color-primary) 14%, transparent);
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    color: var(--color-text);
    cursor: pointer;
    transition: border-color 0.16s ease, background-color 0.16s ease, opacity 0.16s ease;
}

.kb-items__load-more:hover {
    border-color: color-mix(in srgb, var(--color-primary) 58%, transparent);
    background: color-mix(in srgb, var(--color-primary) 22%, transparent);
}

.kb-items__load-more:disabled {
    opacity: 0.65;
    cursor: default;
}
</style>
