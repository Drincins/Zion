<template>
    <section
        class="kb-tree"
        @contextmenu.prevent="emit('context-empty', { event: $event, area: 'tree' })"
    >
        <header class="kb-tree__header">
            <h3 class="kb-tree__title">Папки</h3>
            <div class="kb-tree__actions">
                <button type="button" class="kb-tree__action" @click="emit('expand-all')">Развернуть</button>
                <button type="button" class="kb-tree__action" @click="emit('collapse-all')">Свернуть</button>
            </div>
        </header>
        <div v-if="loading" class="kb-tree__state">Загрузка дерева...</div>
        <div v-else-if="!flatNodes.length" class="kb-tree__state">Папок пока нет</div>
        <div
            v-else
            ref="viewportRef"
            class="kb-tree__list"
            @scroll.passive="handleScroll"
        >
            <ul class="kb-tree__rows" :style="listVirtualStyle">
                <li
                    v-for="row in visibleNodes"
                    :key="row.key"
                    class="kb-tree-node"
                >
                    <div
                        class="kb-tree-node__row"
                        :class="{ 'is-active': row.isFolder && Number(activeFolderId) === Number(row.id) }"
                        :style="{ '--kb-tree-indent': `${row.depth * 16}px` }"
                        role="button"
                        tabindex="0"
                        @click="handleOpen(row)"
                        @contextmenu.stop.prevent="handleContextMenu($event, row)"
                        @keydown.enter.prevent="handleOpen(row)"
                        @keydown.space.prevent="handleOpen(row)"
                    >
                        <button
                            v-if="row.isFolder && row.hasChildren"
                            type="button"
                            class="kb-tree-node__toggle"
                            @click.stop="emit('toggle-folder', row.id)"
                        >
                            {{ row.isExpanded ? '▼' : '▶' }}
                        </button>
                        <span v-else class="kb-tree-node__toggle kb-tree-node__toggle--placeholder">•</span>
                        <KnowledgeBaseFolderIcon
                            v-if="row.isFolder"
                            class="kb-tree-node__icon"
                            :accent="resolveFolderAccent(row.node)"
                        />
                        <KnowledgeBasePdfIcon
                            v-else-if="row.node.preview_type === 'pdf'"
                            class="kb-tree-node__doc-icon"
                        />
                        <KnowledgeBaseExcelIcon
                            v-else-if="isSpreadsheetDocument(row.node)"
                            class="kb-tree-node__doc-icon"
                        />
                        <KnowledgeBaseTextIcon
                            v-else-if="row.node.document_type === 'text'"
                            class="kb-tree-node__doc-icon"
                        />
                        <KnowledgeBaseWordIcon
                            v-else-if="isWordDocument(row.node)"
                            class="kb-tree-node__doc-icon"
                        />
                        <span v-else class="kb-tree-node__file-glyph">📄</span>
                        <span class="kb-tree-node__name">{{ row.name }}</span>
                    </div>
                </li>
            </ul>
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

const TREE_ROW_HEIGHT_PX = 32;
const TREE_OVERSCAN_ROWS = 6;
const TREE_VIRTUALIZATION_THRESHOLD = 220;

const props = defineProps({
    tree: {
        type: Array,
        default: () => [],
    },
    loading: {
        type: Boolean,
        default: false,
    },
    activeFolderId: {
        type: Number,
        default: null,
    },
    expandedFolderIdSet: {
        type: [Object, Set],
        default: () => new Set(),
    },
    folderStyleMap: {
        type: Object,
        default: () => ({}),
    },
});

const emit = defineEmits([
    'open-folder',
    'open-document',
    'toggle-folder',
    'context-folder',
    'context-item',
    'context-empty',
    'expand-all',
    'collapse-all',
]);

const viewportRef = ref(null);
const viewportHeight = ref(0);
const scrollTop = ref(0);
let resizeObserver = null;

const isWordDocument = isKnowledgeBaseWordDocument;
const isSpreadsheetDocument = isKnowledgeBaseSpreadsheetDocument;

const flatNodes = computed(() => flattenVisibleNodes(props.tree, props.expandedFolderIdSet));
const shouldVirtualize = computed(() => flatNodes.value.length > TREE_VIRTUALIZATION_THRESHOLD);
const viewportRowCapacity = computed(() => {
    const height = Math.max(Number(viewportHeight.value) || 0, TREE_ROW_HEIGHT_PX * 8);
    return Math.max(1, Math.ceil(height / TREE_ROW_HEIGHT_PX));
});
const startRow = computed(() => {
    if (!shouldVirtualize.value) {
        return 0;
    }
    const raw = Math.floor((Number(scrollTop.value) || 0) / TREE_ROW_HEIGHT_PX);
    return Math.max(0, raw - TREE_OVERSCAN_ROWS);
});
const endRowExclusive = computed(() => {
    if (!shouldVirtualize.value) {
        return flatNodes.value.length;
    }
    const count = viewportRowCapacity.value + TREE_OVERSCAN_ROWS * 2;
    return Math.min(flatNodes.value.length, startRow.value + count);
});
const visibleNodes = computed(() => flatNodes.value.slice(startRow.value, endRowExclusive.value));
const topPadding = computed(() => (shouldVirtualize.value ? startRow.value * TREE_ROW_HEIGHT_PX : 0));
const bottomPadding = computed(() => {
    if (!shouldVirtualize.value) {
        return 0;
    }
    return Math.max(0, (flatNodes.value.length - endRowExclusive.value) * TREE_ROW_HEIGHT_PX);
});
const listVirtualStyle = computed(() => ({
    paddingTop: topPadding.value > 0 ? `${topPadding.value}px` : undefined,
    paddingBottom: bottomPadding.value > 0 ? `${bottomPadding.value}px` : undefined,
}));

watch(
    () => [flatNodes.value.length, props.loading],
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

function flattenVisibleNodes(nodes, expandedSet, depth = 0, result = []) {
    for (const node of nodes || []) {
        const isFolder = (node?.item_type || 'folder') === 'folder';
        const children = Array.isArray(node?.children) ? node.children : [];
        const hasDocuments = Boolean(node?.has_documents);
        const hasChildren = isFolder && (children.length > 0 || hasDocuments);
        const isExpanded = isFolder && Boolean(expandedSet?.has?.(Number(node.id)));

        result.push({
            key: `${node?.item_type || 'folder'}-${node?.id}`,
            id: node?.id,
            name: node?.name || '—',
            depth,
            isFolder,
            hasChildren,
            isExpanded,
            node,
        });

        if (isFolder && isExpanded && children.length > 0) {
            flattenVisibleNodes(children, expandedSet, depth + 1, result);
        }
    }
    return result;
}

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
}

function handleOpen(row) {
    if (!row?.node) {
        return;
    }
    if (row.isFolder) {
        emit('open-folder', row.id);
        return;
    }
    emit('open-document', {
        ...row.node,
        item_type: 'document',
    });
}

function handleContextMenu(event, row) {
    if (!row?.node) {
        return;
    }
    if (row.isFolder) {
        emit('context-folder', { event, folder: row.node });
        return;
    }
    emit('context-item', {
        event,
        item: {
            ...row.node,
            item_type: 'document',
        },
    });
}

function resolveFolderAccent(node) {
    const styleKey = node?.style_key;
    if (!styleKey) {
        return 'var(--color-primary)';
    }
    return props.folderStyleMap?.[styleKey]?.accent || 'var(--color-primary)';
}
</script>

<style scoped lang="scss">
.kb-tree {
    display: flex;
    flex-direction: column;
    min-height: 220px;
    padding: 8px;
    border-radius: 14px;
    background: color-mix(in srgb, var(--color-primary) 18%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-primary) 28%, transparent);
}

.kb-tree__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
}

.kb-tree__title {
    margin: 0;
    font-size: 14px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: color-mix(in srgb, var(--color-text) 94%, transparent);
}

.kb-tree__actions {
    display: flex;
    gap: 6px;
}

.kb-tree__action {
    border: 1px solid color-mix(in srgb, var(--color-primary) 16%, transparent);
    background: color-mix(in srgb, var(--color-primary) 6%, transparent);
    border-radius: 8px;
    color: color-mix(in srgb, var(--color-text) 86%, transparent);
    padding: 3px 8px;
    font-size: 12px;
    cursor: pointer;
}

.kb-tree__action:hover {
    color: var(--color-text);
    border-color: color-mix(in srgb, var(--color-primary) 42%, transparent);
}

.kb-tree__state {
    color: color-mix(in srgb, var(--color-text) 80%, transparent);
    font-size: 14px;
}

.kb-tree__list {
    flex: 1;
    min-height: 0;
    margin: 0;
    overflow: auto;
    padding-right: 6px;
}

.kb-tree__rows {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

.kb-tree-node {
    list-style: none;
}

.kb-tree-node__row {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 30px;
    border-radius: 8px;
    padding: 4px 8px;
    padding-left: calc(8px + var(--kb-tree-indent, 0px));
    cursor: pointer;
    transition: background-color 0.16s ease, transform 0.16s ease;
    color: color-mix(in srgb, var(--color-text) 94%, transparent);
}

.kb-tree-node__row:hover {
    background: color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.kb-tree-node__row.is-active {
    background: color-mix(in srgb, var(--color-primary) 14%, transparent);
}

.kb-tree-node__toggle {
    border: none;
    background: transparent;
    color: color-mix(in srgb, var(--color-text) 88%, transparent);
    width: 14px;
    text-align: center;
    cursor: pointer;
    padding: 0;
    flex: 0 0 14px;
}

.kb-tree-node__toggle--placeholder {
    opacity: 0.5;
}

.kb-tree-node__icon {
    width: 18px;
    height: 14px;
    display: block;
    flex: 0 0 auto;
}

.kb-tree-node__doc-icon {
    width: 13px;
    height: 16px;
    display: block;
    flex: 0 0 auto;
}

.kb-tree-node__file-glyph {
    font-size: 14px;
    line-height: 1;
    flex: 0 0 auto;
}

.kb-tree-node__name {
    min-width: 0;
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
