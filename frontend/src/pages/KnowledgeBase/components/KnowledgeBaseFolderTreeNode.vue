<template>
    <li class="kb-tree-node">
        <div
            class="kb-tree-node__row"
            :class="{ 'is-active': isActive }"
            role="button"
            tabindex="0"
            @click="handleOpen"
            @contextmenu.stop.prevent="handleContextMenu"
            @keydown.enter.prevent="handleOpen"
            @keydown.space.prevent="handleOpen"
        >
            <button
                v-if="isFolder && hasChildren"
                type="button"
                class="kb-tree-node__toggle"
                @click.stop="emit('toggle-folder', node.id)"
            >
                {{ isExpanded ? '▼' : '▶' }}
            </button>
            <span v-else class="kb-tree-node__toggle kb-tree-node__toggle--placeholder">•</span>
            <KnowledgeBaseFolderIcon
                v-if="isFolder"
                class="kb-tree-node__icon"
                :accent="folderAccent"
            />
            <KnowledgeBasePdfIcon
                v-else-if="node.preview_type === 'pdf'"
                class="kb-tree-node__doc-icon"
            />
            <KnowledgeBaseExcelIcon
                v-else-if="isSpreadsheetDocument(node)"
                class="kb-tree-node__doc-icon"
            />
            <KnowledgeBaseTextIcon
                v-else-if="node.document_type === 'text'"
                class="kb-tree-node__doc-icon"
            />
            <KnowledgeBaseWordIcon
                v-else-if="isWordDocument(node)"
                class="kb-tree-node__doc-icon"
            />
            <span v-else class="kb-tree-node__file-glyph">📄</span>
            <span class="kb-tree-node__name">{{ node.name }}</span>
        </div>
        <ul v-if="isFolder && hasChildren && isExpanded" class="kb-tree-node__children">
            <KnowledgeBaseFolderTreeNode
                v-for="child in node.children"
                :key="`${child.item_type || 'folder'}-${child.id}`"
                :node="child"
                :active-folder-id="activeFolderId"
                :expanded-folder-id-set="expandedFolderIdSet"
                :folder-style-map="folderStyleMap"
                @toggle-folder="emit('toggle-folder', $event)"
                @open-folder="emit('open-folder', $event)"
                @open-document="emit('open-document', $event)"
                @context-folder="emit('context-folder', $event)"
                @context-item="emit('context-item', $event)"
            />
        </ul>
    </li>
</template>

<script setup>
import { computed } from 'vue';
import KnowledgeBaseFolderIcon from './KnowledgeBaseFolderIcon.vue';
import KnowledgeBasePdfIcon from './KnowledgeBasePdfIcon.vue';
import KnowledgeBaseTextIcon from './KnowledgeBaseTextIcon.vue';
import KnowledgeBaseWordIcon from './KnowledgeBaseWordIcon.vue';
import KnowledgeBaseExcelIcon from './KnowledgeBaseExcelIcon.vue';
import { isKnowledgeBaseSpreadsheetDocument, isKnowledgeBaseWordDocument } from '../utils/documents';

defineOptions({
    name: 'KnowledgeBaseFolderTreeNode',
});

const props = defineProps({
    node: {
        type: Object,
        required: true,
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

const emit = defineEmits(['toggle-folder', 'open-folder', 'open-document', 'context-folder', 'context-item']);

const isFolder = computed(() => (props.node?.item_type || 'folder') === 'folder');
const hasDocuments = computed(() => Boolean(props.node?.has_documents));
const hasChildren = computed(() => {
    const hasNested = Array.isArray(props.node?.children) && props.node.children.length > 0;
    return hasNested || (isFolder.value && hasDocuments.value);
});
const isExpanded = computed(() => props.expandedFolderIdSet?.has?.(Number(props.node.id)) || false);
const isActive = computed(() => isFolder.value && Number(props.activeFolderId) === Number(props.node.id));
const folderAccent = computed(() => {
    const styleKey = props.node?.style_key;
    if (!styleKey) {
        return 'var(--color-primary)';
    }
    return props.folderStyleMap?.[styleKey]?.accent || 'var(--color-primary)';
});

const isWordDocument = isKnowledgeBaseWordDocument;
const isSpreadsheetDocument = isKnowledgeBaseSpreadsheetDocument;

function handleOpen() {
    if (isFolder.value) {
        emit('open-folder', props.node.id);
        return;
    }
    emit('open-document', {
        ...props.node,
        item_type: 'document',
    });
}

function handleContextMenu(event) {
    if (isFolder.value) {
        emit('context-folder', { event, folder: props.node });
        return;
    }
    emit('context-item', {
        event,
        item: {
            ...props.node,
            item_type: 'document',
        },
    });
}
</script>

<style scoped lang="scss">
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
    width: 4px;
    text-align: center;
    cursor: pointer;
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
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.kb-tree-node__children {
    margin: 0 0 0 18px;
    padding: 0;
    border-left: 1px dashed color-mix(in srgb, var(--color-primary) 20%, transparent);
}
</style>

