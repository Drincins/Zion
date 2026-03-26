<template>
    <div class="knowledge-base-page">
        <section class="knowledge-base-page__workspace">
            <aside
                class="knowledge-base-page__sidebar"
                :class="{ 'is-mobile-collapsed': !mobileSidebarExpanded }"
            >
                <div class="knowledge-base-page__sidebar-brand">
                    <span class="knowledge-base-page__sidebar-icon">🗂️</span>
                    <span class="knowledge-base-page__sidebar-label">База знаний</span>
                        <RouterLink to="/admin" class="knowledge-base-page__admin-link">
                        В админку
                    </RouterLink>
                    <button
                        type="button"
                        class="knowledge-base-page__mobile-toggle knowledge-base-page__mobile-toggle--sidebar"
                        @click="mobileSidebarExpanded = !mobileSidebarExpanded"
                    >
                        {{ mobileSidebarExpanded ? 'Свернуть' : 'Развернуть' }}
                    </button>
                </div>
                <div class="knowledge-base-page__sidebar-panel">
                    <KnowledgeBaseFolderTree
                        :tree="folderTree"
                        :loading="treeLoading"
                        :active-folder-id="activeFolderId"
                        :expanded-folder-id-set="expandedFolderIdSet"
                        :folder-style-map="folderStyleMap"
                        @toggle-folder="toggleFolderExpanded"
                        @open-folder="openFolder"
                        @open-document="openDocumentFromItem"
                        @context-folder="onContextFolder"
                        @context-item="onContextItem"
                        @context-empty="onContextEmpty"
                        @expand-all="expandAllFolders"
                        @collapse-all="collapseAllFolders"
                    />
                </div>
            </aside>

            <div class="knowledge-base-page__content">
                <button
                    type="button"
                    class="knowledge-base-page__mobile-toggle knowledge-base-page__mobile-toggle--toolbar"
                    @click="mobileToolbarExpanded = !mobileToolbarExpanded"
                >
                    {{ mobileToolbarExpanded ? 'Скрыть фильтры' : 'Показать фильтры' }}
                </button>
                <div
                    class="knowledge-base-page__toolbar-panel"
                    :class="{ 'is-mobile-collapsed': !mobileToolbarExpanded }"
                >
                    <KnowledgeBaseToolbar
                        :search="searchQuery"
                        :item-kind="itemKind"
                        :document-type="documentType"
                        :view-mode="viewMode"
                        :can-manage="canManage"
                        :can-upload="canUpload"
                        :selected-item="selectedItem"
                        :busy="loadingItems || treeLoading || documentLoading"
                        @update:search="searchQuery = $event"
                        @update:item-kind="itemKind = $event"
                        @update:document-type="documentType = $event"
                        @update:view-mode="viewMode = $event"
                        @refresh="refreshWorkspace"
                        @create-folder="openCreateFolderModal(activeFolderId)"
                        @create-document="openCreateDocumentModal(activeFolderId)"
                        @upload-file="triggerUploadForFolder(activeFolderId)"
                        @delete-selected="openDeleteModalForSelected()"
                    />
                </div>
                <KnowledgeBaseItemsPane
                    :items="items"
                    :breadcrumbs="breadcrumbs"
                    :selected-item-id="selectedItem?.id ?? null"
                    :active-folder-id="activeFolderId"
                    :loading="loadingItems"
                    :loading-more="itemsLoadingMore"
                    :has-more="itemsHasMore"
                    :view-mode="viewMode"
                    :icon-size="iconSize"
                    :folder-style-map="folderStyleMap"
                    @navigate-breadcrumb="openFolder"
                    @select-item="selectItem"
                    @open-folder="openFolderFromItem"
                    @open-document="openDocumentFromItem"
                    @context-item="onContextItem"
                    @context-empty="onContextEmpty"
                    @load-more="loadMoreItems"
                />
            </div>
        </section>
        <Transition name="kb-preview-slide">
            <KnowledgeBasePreviewPane
                v-if="previewVisible"
                class="knowledge-base-page__preview-drawer"
                :selected-item="selectedItem"
                :active-document="activeDocument"
                :loading="documentLoading"
                :can-manage="canManage"
                :fullscreen="previewFullscreen"
                @save-text="saveTextDocument"
                @download-document="downloadCurrentDocument"
                @open-history="openHistoryModal"
                @open-info="openInfoModal"
                @toggle-fullscreen="previewFullscreen = !previewFullscreen"
                @close="closePreview"
                @delete-item="openDeleteModalForSelected()"
            />
        </Transition>

        <input
            ref="uploadInputRef"
            type="file"
            class="knowledge-base-page__hidden-upload"
            @change="onUploadInputChanged"
        >

        <KnowledgeBaseContextMenu
            :visible="contextMenu.visible"
            :x="contextMenu.x"
            :y="contextMenu.y"
            :items="contextMenuItems"
            @select="onContextMenuAction"
            @close="closeContextMenu"
        />

        <KnowledgeBaseNameModal
            v-if="showCreateFolderModal"
            title="Создать папку"
            confirm-label="Создать"
            placeholder="Название папки"
            :show-style-picker="true"
            :show-access-picker="true"
            :style-options="folderStyles"
            :initial-style-key="defaultFolderStyleKey"
            :access-options="accessOptions"
            :initial-access="emptyAccessSelection"
            @close="showCreateFolderModal = false"
            @submit="createFolder"
        />

        <KnowledgeBaseNameModal
            v-if="showCreateDocumentModal"
            title="Создать текстовый документ"
            confirm-label="Создать"
            placeholder="Название документа"
            @close="showCreateDocumentModal = false"
            @submit="createTextDocument"
        />

        <KnowledgeBaseNameModal
            v-if="showRenameModal"
            title="Переименовать"
            confirm-label="Сохранить"
            :initial-name="pendingItem?.name || ''"
            :show-style-picker="pendingItem?.item_type === 'folder'"
            :style-options="folderStyles"
            :initial-style-key="pendingItem?.style_key || defaultFolderStyleKey"
            @close="showRenameModal = false"
            @submit="renamePendingItem"
        />

        <KnowledgeBaseMoveModal
            v-if="showMoveModal"
            :folders="moveTargetFolders"
            :initial-folder-id="pendingItem?.parent_id ?? null"
            @close="showMoveModal = false"
            @submit="movePendingItem"
        />

        <KnowledgeBaseAccessModal
            v-if="showAccessModal"
            title="Доступы папки"
            confirm-label="Сохранить"
            :access-options="accessOptions"
            :initial-access="accessModalSelection"
            @close="showAccessModal = false"
            @submit="saveFolderAccess"
        />

        <KnowledgeBaseConfirmModal
            v-if="showDeleteModal"
            title="Удаление"
            :message="deleteMessage"
            confirm-label="Удалить"
            :danger="true"
            :show-force-option="pendingItem?.item_type === 'folder'"
            :force-value="deleteRecursive"
            force-label="Удалить папку вместе с содержимым"
            @update:force-value="deleteRecursive = $event"
            @close="showDeleteModal = false"
            @confirm="deletePendingItem"
        />

        <KnowledgeBaseInfoModal
            v-if="showInfoModal"
            :title="infoModalTitle"
            :rows="infoRows"
            @close="showInfoModal = false"
        />

        <KnowledgeBaseHistoryModal
            v-if="showHistoryModal"
            :title="historyModalTitle"
            :audit-logs="historyAuditLogs"
            :versions="historyVersions"
            @close="showHistoryModal = false"
        />
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import {
    createKnowledgeBaseFolder,
    createKnowledgeBaseTextDocument,
    deleteKnowledgeBaseDocument,
    deleteKnowledgeBaseFolder,
    fetchKnowledgeBaseAccessOptions,
    fetchKnowledgeBaseBootstrap,
    fetchKnowledgeBaseDocument,
    fetchKnowledgeBaseDocumentDownload,
    fetchKnowledgeBaseDocumentHistory,
    fetchKnowledgeBaseFolderAccess,
    fetchKnowledgeBaseFolderHistory,
    fetchKnowledgeBaseFolderInfo,
    fetchKnowledgeBaseItems,
    fetchKnowledgeBaseTree,
    fetchKnowledgeBaseTreeDocuments,
    openKnowledgeBaseDocument,
    updateKnowledgeBaseDocument,
    updateKnowledgeBaseDocumentContent,
    updateKnowledgeBaseFolderAccess,
    updateKnowledgeBaseFolder,
    uploadKnowledgeBaseFile,
} from '@/api';
import { useDebounce } from '@/composables/useDebounce';
import { useUserStore } from '@/stores/user';
import { extractApiErrorMessage } from '@/utils/apiErrors';
import { DEFAULT_FOLDER_STYLE_OPTIONS } from './constants';
import { normalizeKnowledgeBaseAccess, summarizeKnowledgeBaseAccess } from './utils/access';
import { formatKnowledgeBaseDate } from './utils/date';
import KnowledgeBaseToolbar from './components/KnowledgeBaseToolbar.vue';
import KnowledgeBaseFolderTree from './components/KnowledgeBaseFolderTree.vue';
import KnowledgeBaseItemsPane from './components/KnowledgeBaseItemsPane.vue';
import KnowledgeBasePreviewPane from './components/KnowledgeBasePreviewPane.vue';
import KnowledgeBaseContextMenu from './components/KnowledgeBaseContextMenu.vue';
import KnowledgeBaseNameModal from './components/KnowledgeBaseNameModal.vue';
import KnowledgeBaseMoveModal from './components/KnowledgeBaseMoveModal.vue';
import KnowledgeBaseAccessModal from './components/KnowledgeBaseAccessModal.vue';
import KnowledgeBaseConfirmModal from './components/KnowledgeBaseConfirmModal.vue';
import KnowledgeBaseInfoModal from './components/KnowledgeBaseInfoModal.vue';
import KnowledgeBaseHistoryModal from './components/KnowledgeBaseHistoryModal.vue';

const toast = useToast();
const userStore = useUserStore();
const router = useRouter();
const route = useRoute();

const loadingItems = ref(false);
const treeLoading = ref(false);
const documentLoading = ref(false);

const folderTree = ref([]);
const expandedFolderIds = ref([]);
const activeFolderId = ref(null);
const breadcrumbs = ref([]);
const items = ref([]);
const itemsHasMore = ref(false);
const itemsNextOffset = ref(0);
const itemsLoadingMore = ref(false);

const selectedItem = ref(null);
const activeDocument = ref(null);
const previewFullscreen = ref(false);
const previewVisible = ref(false);
const mobileSidebarExpanded = ref(true);
const mobileToolbarExpanded = ref(true);

const folderStyles = ref(DEFAULT_FOLDER_STYLE_OPTIONS);
const accessOptions = ref({
    roles: [],
    positions: [],
    users: [],
    restaurants: [],
});
const searchQuery = ref('');
const itemKind = ref('all');
const documentType = ref('all');
const viewMode = ref('tile');
const iconSize = ref('lg');

const showCreateFolderModal = ref(false);
const createFolderParentId = ref(null);
const showCreateDocumentModal = ref(false);
const createDocumentFolderId = ref(null);
const showRenameModal = ref(false);
const showMoveModal = ref(false);
const showAccessModal = ref(false);
const showDeleteModal = ref(false);
const showInfoModal = ref(false);
const showHistoryModal = ref(false);
const deleteRecursive = ref(false);

const infoModalTitle = ref('Информация');
const infoRows = ref([]);
const historyModalTitle = ref('История');
const historyAuditLogs = ref([]);
const historyVersions = ref([]);

const pendingItem = ref(null);
const uploadInputRef = ref(null);
const uploadTargetFolderId = ref(null);
const accessModalSelection = ref({
    role_ids: [],
    position_ids: [],
    user_ids: [],
    restaurant_ids: [],
});

const contextMenu = reactive({
    visible: false,
    x: 0,
    y: 0,
    targetType: 'empty',
    targetItem: null,
});

const treeRequestController = ref(null);
const itemsRequestController = ref(null);
const documentRequestController = ref(null);
const treeDocumentLoadingKeys = ref(new Set());
const treeDocumentLoadedFolderIds = ref(new Set());
const treeRootDocumentsLoaded = ref(false);

let treeRequestSequence = 0;
let itemsRequestSequence = 0;
let documentRequestSequence = 0;
const ITEMS_PAGE_LIMIT = 120;
const LINK_QUERY_FOLDER_KEY = 'folder';
const LINK_QUERY_DOCUMENT_KEY = 'document';
const syncingDeepLinkQuery = ref(false);
const applyingDeepLinkQuery = ref(false);

const canManage = computed(() => userStore.hasAnyPermission('knowledge_base.section'));
const canUpload = computed(() => userStore.hasAnyPermission('knowledge_base.section'));
const formatDate = formatKnowledgeBaseDate;

const folderStyleMap = computed(() =>
    Object.fromEntries((folderStyles.value || []).map((style) => [style.key, style])),
);
const expandedFolderIdSet = computed(() => new Set((expandedFolderIds.value || []).map((value) => Number(value))));
const defaultFolderStyleKey = computed(() => folderStyles.value?.[0]?.key || 'amber');
const emptyAccessSelection = computed(() => ({
    role_ids: [],
    position_ids: [],
    user_ids: [],
    restaurant_ids: [],
}));

const moveTargetFolders = computed(() => {
    const rows = [];
    const skipIds = new Set();
    if (pendingItem.value?.item_type === 'folder') {
        collectTreeIdsByRoot(pendingItem.value.id, folderTree.value, skipIds);
    }

    function walk(nodes, prefix = '') {
        nodes.forEach((node) => {
            if (!isFolderNode(node)) {
                return;
            }
            if (!skipIds.has(node.id)) {
                rows.push({
                    id: node.id,
                    label: prefix ? `${prefix}/${node.name}` : node.name,
                });
            }
            walk(node.children || [], prefix ? `${prefix}/${node.name}` : node.name);
        });
    }
    walk(folderTree.value || []);
    return rows;
});

const deleteMessage = computed(() => {
    if (!pendingItem.value) {
        return '';
    }
    if (pendingItem.value.item_type === 'folder') {
        return `Удалить папку "${pendingItem.value.name}"?`;
    }
    return `Удалить документ "${pendingItem.value.name}"?`;
});

const contextMenuItems = computed(() => {
    const item = contextMenu.targetItem;
    const isFolder = item?.item_type === 'folder';
    const isDocument = item?.item_type === 'document';
    const entries = [];

    if (!item) {
        entries.push(
            { key: 'refresh', label: 'Обновить' },
            { key: 'create-folder', label: 'Создать папку', disabled: !canManage.value },
            { key: 'create-document', label: 'Создать документ', disabled: !canManage.value },
            { key: 'upload-file', label: 'Загрузить файл', disabled: !canUpload.value },
        );
        return entries;
    }

    entries.push({ key: 'open', label: 'Открыть' });
    entries.push({ key: 'copy-link', label: 'Copy link' });
    if (isDocument && item.document_type === 'file') {
        entries.push({ key: 'download', label: 'Скачать' });
    }
    entries.push(
        { key: 'rename', label: 'Переименовать', disabled: !canManage.value },
        { key: 'move', label: 'Переместить', disabled: !canManage.value },
    );
    if (isFolder) {
        entries.push(
            { key: 'create-folder', label: 'Новая подпапка', disabled: !canManage.value },
            { key: 'create-document', label: 'Новый документ', disabled: !canManage.value },
            { key: 'upload-file', label: 'Загрузить в папку', disabled: !canUpload.value },
            { key: 'access', label: 'Доступы', disabled: !canManage.value },
        );
    }
    entries.push(
        { key: 'info', label: 'Информация' },
        { key: 'history', label: 'История' },
        { key: 'delete', label: 'Удалить', danger: true, disabled: !canManage.value },
    );
    return entries;
});

const debouncedReloadItems = useDebounce(() => {
    void loadItems();
}, 280);

watch([searchQuery, itemKind, documentType], () => {
    debouncedReloadItems();
});

watch(
    () => [route.query?.[LINK_QUERY_FOLDER_KEY], route.query?.[LINK_QUERY_DOCUMENT_KEY]],
    () => {
        if (syncingDeepLinkQuery.value) {
            return;
        }
        void applyDeepLinkFromRoute();
    },
);

onBeforeUnmount(() => {
    abortRequest(treeRequestController);
    abortRequest(itemsRequestController);
    abortRequest(documentRequestController);
});

onMounted(async () => {
    await Promise.all([loadBootstrap(), loadAccessOptions()]);
    await loadTree();
    await loadItems();
    await applyDeepLinkFromRoute();
});

function abortRequest(controllerRef) {
    if (!controllerRef?.value) {
        return;
    }
    controllerRef.value.abort();
    controllerRef.value = null;
}

function startRequest(controllerRef) {
    abortRequest(controllerRef);
    const controller = new AbortController();
    controllerRef.value = controller;
    return controller;
}

function isCanceledRequest(error) {
    return error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError';
}

function hasSetValue(setRef, key) {
    return Boolean(setRef?.value?.has?.(key));
}

function addSetValue(setRef, key) {
    const next = new Set(setRef.value || []);
    next.add(key);
    setRef.value = next;
}

function deleteSetValue(setRef, key) {
    const next = new Set(setRef.value || []);
    next.delete(key);
    setRef.value = next;
}

function resolveQueryId(rawValue) {
    const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
    return normalizeFolderId(value);
}

function getDeepLinkStateFromRoute() {
    return {
        folderId: resolveQueryId(route.query?.[LINK_QUERY_FOLDER_KEY]),
        documentId: resolveQueryId(route.query?.[LINK_QUERY_DOCUMENT_KEY]),
    };
}

function buildDeepLinkQuery({ folderId = null, documentId = null } = {}) {
    const nextQuery = { ...(route.query || {}) };
    delete nextQuery[LINK_QUERY_FOLDER_KEY];
    delete nextQuery[LINK_QUERY_DOCUMENT_KEY];
    if (folderId !== null) {
        nextQuery[LINK_QUERY_FOLDER_KEY] = String(folderId);
    }
    if (documentId !== null) {
        nextQuery[LINK_QUERY_DOCUMENT_KEY] = String(documentId);
    }
    return nextQuery;
}

async function syncDeepLinkQuery({ folderId = activeFolderId.value, documentId = null } = {}) {
    if (applyingDeepLinkQuery.value) {
        return;
    }
    const normalizedFolderId = normalizeFolderId(folderId);
    const normalizedDocumentId = normalizeFolderId(documentId);
    const currentState = getDeepLinkStateFromRoute();
    if (currentState.folderId === normalizedFolderId && currentState.documentId === normalizedDocumentId) {
        return;
    }
    syncingDeepLinkQuery.value = true;
    try {
        await router.replace({
            path: route.path,
            query: buildDeepLinkQuery({
                folderId: normalizedFolderId,
                documentId: normalizedDocumentId,
            }),
        });
    } finally {
        syncingDeepLinkQuery.value = false;
    }
}

async function applyDeepLinkFromRoute() {
    if (applyingDeepLinkQuery.value) {
        return;
    }
    applyingDeepLinkQuery.value = true;
    try {
        const { folderId, documentId } = getDeepLinkStateFromRoute();

        if (documentId !== null) {
            if (folderId !== null && Number(folderId) !== Number(activeFolderId.value)) {
                await openFolder(folderId, { syncRoute: false });
            }
            const openedDocument = await openDocumentById(documentId, false, {
                syncRoute: false,
                openParentFolder: folderId === null,
            });
            if (openedDocument) {
                previewVisible.value = true;
            }
            return;
        }

        if (folderId !== null) {
            if (Number(folderId) !== Number(activeFolderId.value)) {
                await openFolder(folderId, { syncRoute: false });
            } else {
                ensureFolderPathExpanded(folderId);
                await Promise.all([
                    loadItems({ append: false }),
                    ensureTreeDocumentsLoaded(folderId),
                ]);
            }
            selectedItem.value = null;
            activeDocument.value = null;
            previewVisible.value = false;
            previewFullscreen.value = false;
            return;
        }

        if (activeFolderId.value !== null || activeDocument.value) {
            await openFolder(null, { syncRoute: false });
        }
    } finally {
        applyingDeepLinkQuery.value = false;
    }
}

async function loadBootstrap() {
    try {
        const data = await fetchKnowledgeBaseBootstrap();
        if (Array.isArray(data?.folder_styles) && data.folder_styles.length) {
            folderStyles.value = data.folder_styles;
        }
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить настройки базы знаний'));
    }
}

async function loadAccessOptions() {
    if (!canManage.value) {
        return;
    }
    try {
        const data = await fetchKnowledgeBaseAccessOptions();
        accessOptions.value = {
            roles: Array.isArray(data?.roles) ? data.roles : [],
            positions: Array.isArray(data?.positions) ? data.positions : [],
            users: Array.isArray(data?.users) ? data.users : [],
            restaurants: Array.isArray(data?.restaurants) ? data.restaurants : [],
        };
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить варианты доступов'));
    }
}

async function loadTree() {
    const requestId = ++treeRequestSequence;
    const controller = startRequest(treeRequestController);
    treeLoading.value = true;
    try {
        const data = await fetchKnowledgeBaseTree({ signal: controller.signal });
        if (requestId !== treeRequestSequence) {
            return;
        }
        folderTree.value = Array.isArray(data) ? data : [];
        treeDocumentLoadedFolderIds.value = new Set();
        treeRootDocumentsLoaded.value = false;
        const allFolderIds = new Set();
        collectAllTreeIds(folderTree.value, allFolderIds);
        expandedFolderIds.value = (expandedFolderIds.value || [])
            .map((value) => Number(value))
            .filter((id) => Number.isFinite(id) && allFolderIds.has(id));
        if (activeFolderId.value !== null && !treeContainsFolder(activeFolderId.value, folderTree.value)) {
            activeFolderId.value = null;
        }
        if (activeFolderId.value !== null) {
            ensureFolderPathExpanded(activeFolderId.value);
        }
        await ensureTreeDocumentsLoaded(null);
        if (activeFolderId.value !== null) {
            await ensureTreeDocumentsLoaded(activeFolderId.value);
        }
    } catch (error) {
        if (!isCanceledRequest(error)) {
            toast.error(extractApiErrorMessage(error, 'Не удалось загрузить дерево папок'));
        }
    } finally {
        if (requestId === treeRequestSequence) {
            treeLoading.value = false;
        }
        if (treeRequestController.value === controller) {
            treeRequestController.value = null;
        }
    }
}

async function ensureTreeDocumentsLoaded(folderId = null) {
    const normalizedFolderId = normalizeFolderId(folderId);
    const loadKey = normalizedFolderId === null ? 'root' : Number(normalizedFolderId);
    if (loadKey === 'root' ? treeRootDocumentsLoaded.value : hasSetValue(treeDocumentLoadedFolderIds, loadKey)) {
        return;
    }
    if (hasSetValue(treeDocumentLoadingKeys, loadKey)) {
        return;
    }
    addSetValue(treeDocumentLoadingKeys, loadKey);
    try {
        const params = { limit: 500 };
        if (normalizedFolderId !== null) {
            params.folder_id = normalizedFolderId;
        }
        const data = await fetchKnowledgeBaseTreeDocuments(params);
        const documents = (Array.isArray(data) ? data : []).filter((item) => item?.item_type === 'document');
        if (normalizedFolderId === null) {
            mergeRootTreeDocuments(documents);
            treeRootDocumentsLoaded.value = true;
            return;
        }
        replaceFolderTreeDocuments(normalizedFolderId, documents);
        addSetValue(treeDocumentLoadedFolderIds, Number(normalizedFolderId));
    } catch (error) {
        if (!isCanceledRequest(error)) {
            toast.error(extractApiErrorMessage(error, 'Не удалось загрузить документы для дерева'));
        }
    } finally {
        deleteSetValue(treeDocumentLoadingKeys, loadKey);
    }
}

function mergeRootTreeDocuments(documents) {
    const folders = (folderTree.value || []).filter((item) => isFolderNode(item));
    folderTree.value = [...folders, ...documents];
}

function replaceFolderTreeDocuments(folderId, documents) {
    const target = findFolderNode(folderTree.value, folderId);
    if (!target) {
        return;
    }
    const folderChildren = (target.children || []).filter((item) => isFolderNode(item));
    target.has_documents = documents.length > 0;
    target.children = [...folderChildren, ...documents];
    folderTree.value = [...folderTree.value];
}

function findFolderNode(nodes, folderId) {
    for (const node of nodes || []) {
        if (!isFolderNode(node)) {
            continue;
        }
        if (Number(node.id) === Number(folderId)) {
            return node;
        }
        const nested = findFolderNode(node.children || [], folderId);
        if (nested) {
            return nested;
        }
    }
    return null;
}

async function loadItems(options = {}) {
    const append = Boolean(options?.append);
    if (append && !itemsHasMore.value) {
        return;
    }
    const requestId = ++itemsRequestSequence;
    const controller = startRequest(itemsRequestController);
    const requestOffset = append ? Number(itemsNextOffset.value || items.value.length || 0) : 0;
    if (append) {
        itemsLoadingMore.value = true;
    } else {
        itemsLoadingMore.value = false;
        loadingItems.value = true;
    }
    try {
        const params = {
            folder_id: activeFolderId.value,
            item_kind: itemKind.value,
            document_type: documentType.value,
            search: searchQuery.value.trim() || undefined,
            offset: requestOffset,
            limit: ITEMS_PAGE_LIMIT,
        };
        const data = await fetchKnowledgeBaseItems(params, { signal: controller.signal });
        if (requestId !== itemsRequestSequence) {
            return;
        }
        const nextItems = Array.isArray(data?.items) ? data.items : [];
        items.value = append ? mergeKnowledgeBaseItems(items.value, nextItems) : nextItems;
        breadcrumbs.value = Array.isArray(data?.breadcrumbs) ? data.breadcrumbs : [];
        itemsHasMore.value = Boolean(data?.has_more);
        const nextOffset = Number(data?.next_offset);
        itemsNextOffset.value = Number.isFinite(nextOffset) ? nextOffset : requestOffset + nextItems.length;

        if (!append && selectedItem.value) {
            const nextSelected = items.value.find(
                (entry) => entry.item_type === selectedItem.value.item_type && Number(entry.id) === Number(selectedItem.value.id),
            );
            if (nextSelected) {
                selectedItem.value = nextSelected;
            }
        }
    } catch (error) {
        if (!isCanceledRequest(error)) {
            toast.error(extractApiErrorMessage(error, 'Не удалось загрузить элементы'));
        }
    } finally {
        if (requestId === itemsRequestSequence && !append && itemsRequestController.value === controller) {
            loadingItems.value = false;
        }
        if (requestId === itemsRequestSequence && append && itemsRequestController.value === controller) {
            itemsLoadingMore.value = false;
        }
        if (itemsRequestController.value === controller) {
            itemsRequestController.value = null;
        }
    }
}

function mergeKnowledgeBaseItems(currentItems, nextItems) {
    const result = [...(Array.isArray(currentItems) ? currentItems : [])];
    const seen = new Set(result.map((item) => `${item?.item_type || 'unknown'}-${item?.id}`));
    for (const item of Array.isArray(nextItems) ? nextItems : []) {
        const key = `${item?.item_type || 'unknown'}-${item?.id}`;
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);
        result.push(item);
    }
    return result;
}

async function loadMoreItems() {
    if (!itemsHasMore.value || loadingItems.value || itemsLoadingMore.value) {
        return;
    }
    await loadItems({ append: true });
}

async function refreshWorkspace() {
    await Promise.all([loadTree(), loadItems({ append: false })]);
    if (previewVisible.value && activeDocument.value?.id) {
        await openDocumentById(activeDocument.value.id, false);
    }
}

function openCreateFolderModal(parentId = null) {
    createFolderParentId.value = normalizeFolderId(parentId);
    showCreateFolderModal.value = true;
}

function openCreateDocumentModal(folderId = null) {
    createDocumentFolderId.value = normalizeFolderId(folderId);
    showCreateDocumentModal.value = true;
}

function selectItem(item) {
    if (!item) {
        return;
    }
    selectedItem.value = item;
    if (item.item_type === 'folder') {
        activeDocument.value = null;
        previewVisible.value = false;
        return;
    }
    if (previewVisible.value) {
        void openDocumentById(item.id, false);
    }
}

async function openFolder(folderId, options = {}) {
    const syncRoute = options?.syncRoute !== false;
    activeFolderId.value = normalizeFolderId(folderId);
    selectedItem.value = null;
    activeDocument.value = null;
    previewVisible.value = false;
    previewFullscreen.value = false;
    ensureFolderPathExpanded(activeFolderId.value);
    await Promise.all([
        loadItems({ append: false }),
        ensureTreeDocumentsLoaded(activeFolderId.value),
    ]);
    if (syncRoute) {
        await syncDeepLinkQuery({
            folderId: activeFolderId.value,
            documentId: null,
        });
    }
}

async function openFolderFromItem(item) {
    if (!item || item.item_type !== 'folder') {
        return;
    }
    await openFolder(item.id);
}

async function openDocumentFromItem(item) {
    if (!item || item.item_type !== 'document') {
        return;
    }
    selectedItem.value = item;
    await openDocumentById(item.id, true);
    previewVisible.value = true;
}

async function openDocumentById(documentId, registerOpen = false, options = {}) {
    if (!documentId) {
        return null;
    }
    const syncRoute = options?.syncRoute !== false;
    const openParentFolder = Boolean(options?.openParentFolder);
    const requestId = ++documentRequestSequence;
    const controller = startRequest(documentRequestController);
    documentLoading.value = true;
    let openedDocument = null;
    try {
        const documentData = registerOpen
            ? await openKnowledgeBaseDocument(documentId, { signal: controller.signal })
            : await fetchKnowledgeBaseDocument(documentId, { signal: controller.signal });
        if (requestId !== documentRequestSequence) {
            return null;
        }
        const documentFolderId = normalizeFolderId(documentData?.folder_id);
        if (openParentFolder && Number(documentFolderId) !== Number(activeFolderId.value)) {
            await openFolder(documentFolderId, { syncRoute: false });
        } else if (documentFolderId !== null) {
            ensureFolderPathExpanded(documentFolderId);
            await ensureTreeDocumentsLoaded(documentFolderId);
        }
        activeDocument.value = documentData;
        const selectedDocument = items.value.find(
            (entry) => entry.item_type === 'document' && Number(entry.id) === Number(documentData.id),
        );
        selectedItem.value = selectedDocument || {
            id: documentData.id,
            item_type: 'document',
            name: documentData.name,
            folder_id: documentData.folder_id,
            document_type: documentData.document_type,
            preview_type: documentData.preview_type,
        };
        if (syncRoute) {
            await syncDeepLinkQuery({
                folderId: documentFolderId,
                documentId: normalizeFolderId(documentData?.id),
            });
        }
        openedDocument = documentData;
    } catch (error) {
        if (!isCanceledRequest(error)) {
            toast.error(extractApiErrorMessage(error, 'Не удалось открыть документ'));
        }
    } finally {
        if (requestId === documentRequestSequence) {
            documentLoading.value = false;
        }
        if (documentRequestController.value === controller) {
            documentRequestController.value = null;
        }
    }
    return openedDocument;
}

async function createFolder(payload) {
    try {
        const created = await createKnowledgeBaseFolder({
            parent_id: createFolderParentId.value,
            name: payload.name,
            style_key: payload.styleKey || defaultFolderStyleKey.value,
            access: normalizeKnowledgeBaseAccess(payload.access),
        });
        showCreateFolderModal.value = false;
        toast.success('Папка создана');
        await loadTree();
        if (Number(activeFolderId.value) === Number(created.parent_id)) {
            await loadItems();
        }
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось создать папку'));
    }
}

async function createTextDocument(payload) {
    try {
        const created = await createKnowledgeBaseTextDocument({
            folder_id: createDocumentFolderId.value,
            name: payload.name,
            content: '',
        });
        showCreateDocumentModal.value = false;
        if (Number(activeFolderId.value) !== Number(created.folder_id)) {
            await openFolder(created.folder_id);
        } else {
            await loadItems();
        }
        const item = items.value.find((entry) => entry.item_type === 'document' && Number(entry.id) === Number(created.id));
        if (item) {
            selectedItem.value = item;
        }
        await openDocumentById(created.id, false);
        previewVisible.value = true;
        toast.success('Документ создан');
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось создать документ'));
    }
}

async function saveTextDocument(payload) {
    if (!activeDocument.value?.id) {
        return;
    }
    try {
        const updated = await updateKnowledgeBaseDocumentContent(activeDocument.value.id, payload);
        activeDocument.value = updated;
        await loadItems();
        toast.success('Изменения сохранены');
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось сохранить документ'));
    }
}

async function renamePendingItem(payload) {
    if (!pendingItem.value) {
        return;
    }
    try {
        if (pendingItem.value.item_type === 'folder') {
            await updateKnowledgeBaseFolder(pendingItem.value.id, {
                name: payload.name,
                style_key: payload.styleKey || pendingItem.value.style_key || defaultFolderStyleKey.value,
            });
            await loadTree();
        } else {
            await updateKnowledgeBaseDocument(pendingItem.value.id, { name: payload.name });
        }
        showRenameModal.value = false;
        await loadItems();
        toast.success('Название обновлено');
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось переименовать'));
    }
}

async function movePendingItem(targetFolderId) {
    if (!pendingItem.value) {
        return;
    }
    try {
        if (pendingItem.value.item_type === 'folder') {
            await updateKnowledgeBaseFolder(pendingItem.value.id, { parent_id: normalizeFolderId(targetFolderId) });
            await loadTree();
        } else {
            await updateKnowledgeBaseDocument(pendingItem.value.id, { folder_id: normalizeFolderId(targetFolderId) });
        }
        showMoveModal.value = false;
        await loadItems();
        toast.success('Элемент перемещен');
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось переместить элемент'));
    }
}

async function deletePendingItem() {
    if (!pendingItem.value) {
        return;
    }
    try {
        if (pendingItem.value.item_type === 'folder') {
            await deleteKnowledgeBaseFolder(pendingItem.value.id, { force: deleteRecursive.value });
            await loadTree();
        } else {
            await deleteKnowledgeBaseDocument(pendingItem.value.id);
        }
        if (selectedItem.value && Number(selectedItem.value.id) === Number(pendingItem.value.id)) {
            selectedItem.value = null;
            activeDocument.value = null;
            previewVisible.value = false;
        }
        showDeleteModal.value = false;
        deleteRecursive.value = false;
        await loadItems();
        toast.success('Элемент удален');
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось удалить элемент'));
    }
}

async function openInfoModal(targetItem = null) {
    const itemToOpen = targetItem || selectedItem.value;
    if (!itemToOpen) {
        return;
    }
    try {
        if (itemToOpen.item_type === 'folder') {
            const data = await fetchKnowledgeBaseFolderInfo(itemToOpen.id);
            infoModalTitle.value = `Папка: ${data.name}`;
            infoRows.value = [
                { label: 'Тип', value: 'Папка' },
                { label: 'Родитель', value: data.parent_id ?? 'Корень' },
                { label: 'Создал', value: data.created_by_name },
                { label: 'Изменил', value: data.updated_by_name },
                { label: 'Создано', value: formatDate(data.created_at) },
                { label: 'Изменено', value: formatDate(data.updated_at) },
                { label: 'Подпапок', value: data.children_count },
                { label: 'Документов', value: data.documents_count },
                { label: 'Доступы', value: summarizeKnowledgeBaseAccess(data.access) },
            ];
        } else {
            const data = await fetchKnowledgeBaseDocument(itemToOpen.id);
            infoModalTitle.value = `Документ: ${data.name}`;
            infoRows.value = [
                { label: 'Тип', value: data.document_type === 'text' ? 'Текстовый документ' : 'Файл' },
                { label: 'MIME', value: data.mime_type },
                { label: 'Расширение', value: data.extension },
                { label: 'Размер', value: data.file_size ? `${data.file_size} B` : '—' },
                { label: 'Версия', value: data.latest_version_number },
                { label: 'Создал', value: data.created_by_name },
                { label: 'Изменил', value: data.updated_by_name },
                { label: 'Создано', value: formatDate(data.created_at) },
                { label: 'Изменено', value: formatDate(data.updated_at) },
            ];
        }
        showInfoModal.value = true;
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить информацию'));
    }
}

async function openHistoryModal(targetItem = null) {
    const itemToOpen = targetItem || selectedItem.value;
    if (!itemToOpen) {
        return;
    }
    try {
        if (itemToOpen.item_type === 'folder') {
            const audit = await fetchKnowledgeBaseFolderHistory(itemToOpen.id);
            historyModalTitle.value = `История папки: ${itemToOpen.name}`;
            historyAuditLogs.value = Array.isArray(audit) ? audit : [];
            historyVersions.value = [];
        } else {
            const history = await fetchKnowledgeBaseDocumentHistory(itemToOpen.id);
            historyModalTitle.value = `История документа: ${itemToOpen.name}`;
            historyAuditLogs.value = Array.isArray(history?.audit_logs) ? history.audit_logs : [];
            historyVersions.value = Array.isArray(history?.versions) ? history.versions : [];
        }
        showHistoryModal.value = true;
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить историю'));
    }
}

async function downloadCurrentDocument(targetIdOverride = null) {
    const targetId = targetIdOverride || activeDocument.value?.id;
    if (!targetId) {
        return;
    }
    try {
        const response = await fetchKnowledgeBaseDocumentDownload(targetId);
        if (response?.download_url) {
            window.open(response.download_url, '_blank');
            return;
        }
        toast.error('Ссылка для скачивания не получена');
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось скачать документ'));
    }
}

function onContextEmpty({ event }) {
    openContextMenu(event, null);
}

function onContextFolder({ event, folder }) {
    openContextMenu(event, { ...folder, item_type: 'folder' });
}

function onContextItem({ event, item }) {
    openContextMenu(event, item);
}

function openContextMenu(event, item) {
    contextMenu.visible = true;
    contextMenu.x = event.clientX;
    contextMenu.y = event.clientY;
    contextMenu.targetType = item?.item_type || 'empty';
    contextMenu.targetItem = item || null;
}

function closeContextMenu() {
    contextMenu.visible = false;
    contextMenu.targetItem = null;
}

function closePreview() {
    previewVisible.value = false;
    previewFullscreen.value = false;
    abortRequest(documentRequestController);
    documentLoading.value = false;
    void syncDeepLinkQuery({
        folderId: activeFolderId.value,
        documentId: null,
    });
}

function resolveItemFolderId(item) {
    if (!item) {
        return normalizeFolderId(activeFolderId.value);
    }
    if (item.item_type === 'folder') {
        return normalizeFolderId(item.id);
    }
    const itemFolderId = normalizeFolderId(item.folder_id);
    if (itemFolderId !== null) {
        return itemFolderId;
    }
    if (activeDocument.value && Number(activeDocument.value.id) === Number(item.id)) {
        return normalizeFolderId(activeDocument.value.folder_id);
    }
    return null;
}

function buildItemShareLink(item) {
    if (!item) {
        return '';
    }
    const folderId = resolveItemFolderId(item);
    const documentId = item.item_type === 'document' ? normalizeFolderId(item.id) : null;
    const resolved = router.resolve({
        path: route.path || '/knowledge-base',
        query: buildDeepLinkQuery({
            folderId,
            documentId,
        }),
    });
    if (typeof window === 'undefined' || !window.location?.origin) {
        return resolved.href || '';
    }
    return new URL(resolved.href, window.location.origin).toString();
}

async function writeTextToClipboard(value) {
    const text = String(value || '');
    if (!text) {
        return false;
    }
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
    }
    if (typeof document === 'undefined') {
        return false;
    }
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', 'true');
    textarea.style.position = 'fixed';
    textarea.style.top = '-1000px';
    textarea.style.left = '-1000px';
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand('copy');
    document.body.removeChild(textarea);
    return copied;
}

async function copyItemLink(item) {
    if (!item) {
        return;
    }
    const link = buildItemShareLink(item);
    if (!link) {
        toast.error('Link could not be created');
        return;
    }
    try {
        const copied = await writeTextToClipboard(link);
        if (!copied) {
            throw new Error('Clipboard not available');
        }
        toast.success('Link copied');
    } catch {
        toast.error('Failed to copy link');
    }
}

function openDeleteModalForSelected(targetItem = null) {
    const item = targetItem || selectedItem.value;
    if (!item || !canManage.value) {
        return;
    }
    pendingItem.value = item;
    deleteRecursive.value = false;
    showDeleteModal.value = true;
}

async function openFolderAccessModal(targetItem) {
    if (!targetItem || targetItem.item_type !== 'folder' || !canManage.value) {
        return;
    }
    pendingItem.value = targetItem;
    try {
        const data = await fetchKnowledgeBaseFolderAccess(targetItem.id);
        accessModalSelection.value = normalizeKnowledgeBaseAccess(data);
        showAccessModal.value = true;
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить доступы папки'));
    }
}

async function saveFolderAccess(payload) {
    if (!pendingItem.value || pendingItem.value.item_type !== 'folder') {
        return;
    }
    try {
        await updateKnowledgeBaseFolderAccess(pendingItem.value.id, normalizeKnowledgeBaseAccess(payload));
        showAccessModal.value = false;
        toast.success('Доступы папки сохранены');
        await refreshWorkspace();
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось сохранить доступы папки'));
    }
}

async function onContextMenuAction(action) {
    const item = contextMenu.targetItem;
    closeContextMenu();
    switch (action) {
        case 'refresh':
            await refreshWorkspace();
            break;
        case 'create-folder':
            openCreateFolderModal(item?.item_type === 'folder' ? item.id : activeFolderId.value);
            break;
        case 'create-document':
            openCreateDocumentModal(item?.item_type === 'folder' ? item.id : activeFolderId.value);
            break;
        case 'upload-file':
            triggerUploadForFolder(item?.item_type === 'folder' ? item.id : activeFolderId.value);
            break;
        case 'open':
            if (item?.item_type === 'folder') {
                await openFolder(item.id);
            } else if (item?.item_type === 'document') {
                selectedItem.value = item;
                await openDocumentById(item.id, true);
                previewVisible.value = true;
            }
            break;
        case 'copy-link':
            await copyItemLink(item);
            break;
        case 'rename':
            pendingItem.value = item;
            showRenameModal.value = true;
            break;
        case 'move':
            pendingItem.value = item;
            showMoveModal.value = true;
            break;
        case 'access':
            await openFolderAccessModal(item);
            break;
        case 'delete':
            openDeleteModalForSelected(item);
            break;
        case 'info':
            await openInfoModal(item);
            break;
        case 'history':
            await openHistoryModal(item);
            break;
        case 'download':
            await downloadCurrentDocument(item?.id);
            break;
        default:
            break;
    }
}

function triggerUploadForFolder(folderId) {
    uploadTargetFolderId.value = normalizeFolderId(folderId);
    if (uploadInputRef.value) {
        uploadInputRef.value.value = '';
        uploadInputRef.value.click();
    }
}

async function onUploadInputChanged(event) {
    const file = event?.target?.files?.[0];
    if (!file) {
        return;
    }
    try {
        const created = await uploadKnowledgeBaseFile({
            folderId: uploadTargetFolderId.value,
            name: file.name,
            file,
        });
        if (Number(activeFolderId.value) !== Number(created.folder_id)) {
            await openFolder(created.folder_id);
        } else {
            await loadItems();
        }
        await loadTree();
        const item = items.value.find((entry) => entry.item_type === 'document' && Number(entry.id) === Number(created.id));
        if (item) {
            selectedItem.value = item;
        }
        toast.success('Файл загружен');
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось загрузить файл'));
    } finally {
        if (event?.target) {
            event.target.value = '';
        }
    }
}

function toggleFolderExpanded(folderId) {
    const id = Number(folderId);
    if (!Number.isFinite(id)) {
        return;
    }
    if (expandedFolderIds.value.includes(id)) {
        expandedFolderIds.value = expandedFolderIds.value.filter((value) => Number(value) !== id);
        return;
    }
    expandedFolderIds.value = [...expandedFolderIds.value, id];
    void ensureTreeDocumentsLoaded(id);
}

function expandAllFolders() {
    const ids = new Set();
    collectAllTreeIds(folderTree.value, ids);
    const allIds = Array.from(ids);
    expandedFolderIds.value = allIds;
    if (activeFolderId.value !== null) {
        void ensureTreeDocumentsLoaded(activeFolderId.value);
    }
}

function collapseAllFolders() {
    expandedFolderIds.value = [];
}

function collectAllTreeIds(nodes, set) {
    (nodes || []).forEach((node) => {
        if (!isFolderNode(node)) {
            return;
        }
        set.add(node.id);
        collectAllTreeIds(node.children || [], set);
    });
}

function collectTreeIdsByRoot(rootId, nodes, set) {
    (nodes || []).forEach((node) => {
        if (!isFolderNode(node)) {
            return;
        }
        if (Number(node.id) === Number(rootId)) {
            collectAllTreeIds([node], set);
            return;
        }
        collectTreeIdsByRoot(rootId, node.children || [], set);
    });
}

function ensureFolderPathExpanded(folderId) {
    const normalizedId = normalizeFolderId(folderId);
    if (normalizedId === null) {
        return;
    }
    const pathIds = [];
    const found = collectFolderPathIds(normalizedId, folderTree.value, pathIds);
    if (!found || !pathIds.length) {
        return;
    }
    const next = new Set((expandedFolderIds.value || []).map((value) => Number(value)).filter((id) => Number.isFinite(id)));
    pathIds.forEach((id) => next.add(Number(id)));
    expandedFolderIds.value = Array.from(next);
}

function collectFolderPathIds(targetId, nodes, path) {
    for (const node of nodes || []) {
        if (!isFolderNode(node)) {
            continue;
        }
        path.push(node.id);
        if (Number(node.id) === Number(targetId)) {
            return true;
        }
        if (collectFolderPathIds(targetId, node.children || [], path)) {
            return true;
        }
        path.pop();
    }
    return false;
}

function treeContainsFolder(folderId, nodes) {
    for (const node of nodes || []) {
        if (!isFolderNode(node)) {
            continue;
        }
        if (Number(node.id) === Number(folderId)) {
            return true;
        }
        if (treeContainsFolder(folderId, node.children || [])) {
            return true;
        }
    }
    return false;
}

function isFolderNode(node) {
    return (node?.item_type || 'folder') === 'folder';
}

function normalizeFolderId(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

</script>

<style scoped lang="scss">
.knowledge-base-page {
    position: relative;
    min-height: calc(100vh - 24px);
    display: flex;
    flex-direction: column;
    padding: 14px;
    color: var(--color-text);
    border-radius: 20px;
    overflow: hidden;
}

.knowledge-base-page__workspace {
    display: grid;
    grid-template-columns: 260px minmax(0, 1fr);
    gap: 14px;
    flex: 1;
    min-height: 0;
}

.knowledge-base-page__sidebar {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
    padding: 10px 10px 6px;
    border-radius: 14px;
    border: 1px solid color-mix(in srgb, var(--color-primary) 16%, transparent);
}

.knowledge-base-page__sidebar-panel {
    flex: 1;
    min-height: 0;
}

.knowledge-base-page__sidebar-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 36px;
    padding: 8px 10px;
    border-radius: 10px;
    color: var(--color-text);
    background: color-mix(in srgb, var(--color-primary) 6%, transparent);
}

.knowledge-base-page__sidebar-icon {
    font-size: 16px;
}

.knowledge-base-page__sidebar-label {
    font-size: 14px;
    font-weight: 600;
}

.knowledge-base-page__admin-link {
    margin-left: auto;
    border: 1px solid color-mix(in srgb, var(--color-primary) 10%, transparent);
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 12px;
    color: color-mix(in srgb, var(--color-text) 90%, transparent);
    text-decoration: none;
    background: color-mix(in srgb, var(--color-primary) 6%, transparent);
    transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease;
}

.knowledge-base-page__admin-link:hover {
    color: var(--color-text);
    border-color: color-mix(in srgb, var(--color-primary) 40%, transparent);
    background: color-mix(in srgb, var(--color-primary) 30%, transparent);
}

.knowledge-base-page__sidebar :deep(.kb-tree) {
    flex: 1;
    min-height: 0;
    border: none;
    border-radius: 12px;
    background: transparent;
    padding: 0;
}

.knowledge-base-page__content {
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    border-radius: 14px;
    border: 1px solid color-mix(in srgb, var(--color-primary) 16%, transparent);
    padding: 14px;
}

.knowledge-base-page__toolbar-panel {
    min-height: 0;
}

.knowledge-base-page__mobile-toggle {
    display: none;
    border: 1px solid color-mix(in srgb, var(--color-primary) 34%, transparent);
    border-radius: 8px;
    padding: 5px 9px;
    font-size: 12px;
    color: color-mix(in srgb, var(--color-text) 92%, transparent);
    background: color-mix(in srgb, var(--color-primary) 16%, transparent);
    cursor: pointer;
    transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.knowledge-base-page__mobile-toggle:hover {
    color: var(--color-text);
    border-color: color-mix(in srgb, var(--color-primary) 42%, transparent);
    background: color-mix(in srgb, var(--color-primary) 30%, transparent);
}

.knowledge-base-page__mobile-toggle--toolbar {
    align-self: flex-start;
}

.knowledge-base-page__title {
    margin: 0;
    font-size: clamp(28px, 2.5vw, 36px);
    line-height: 1.1;
    color: color-mix(in srgb, var(--color-text) 96%, transparent);
    letter-spacing: 0.01em;
}

.knowledge-base-page__subtitle {
    margin: 5px 0 0;
    color: color-mix(in srgb, var(--color-text) 72%, transparent);
}

.knowledge-base-page__content :deep(.kb-toolbar) {
    grid-template-columns: minmax(240px, 1.2fr) minmax(280px, 1fr) auto;
    align-items: center;
}

@media (max-width: 1260px) {
    .knowledge-base-page__content :deep(.kb-toolbar) {
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
}

.knowledge-base-page__content :deep(.kb-items) {
    flex: 1;
    min-height: 0;
}

.knowledge-base-page__content :deep(.kb-items__breadcrumbs) {
    margin-top: 2px;
}

.knowledge-base-page__content :deep(.kb-items__crumb) {
    color: color-mix(in srgb, var(--color-text) 84%, transparent);
    border-color: color-mix(in srgb, var(--color-primary) 10%, transparent);
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
}

.knowledge-base-page__content :deep(.kb-items__crumb.is-active) {
    background: color-mix(in srgb, var(--color-primary) 26%, transparent);
    color: var(--color-text);
}

.knowledge-base-page__content :deep(.kb-items__grid--tile) {
    grid-template-columns: repeat(auto-fill, minmax(124px, 1fr));
    gap: 12px;
}

.knowledge-base-page__content :deep(.kb-items__card) {
    overflow: hidden;
    min-height: 96px;
    flex-direction: column;
    align-items: flex-start;
    justify-content: flex-start;
    gap: 8px;
    padding: 8px;
    border-radius: 13px;
    border: 1px solid color-mix(in srgb, var(--color-primary) 16%, transparent);
    background: linear-gradient(
        180deg,
        color-mix(in srgb, #bb926594 16%, transparent) 0%,
        color-mix(in srgb, #00000000 10%, transparent) 100%
    );
}

.knowledge-base-page__content :deep(.kb-items__grid--list .kb-items__card),
.knowledge-base-page__content :deep(.kb-items__grid--compact .kb-items__card) {
    min-height: unset;
    flex-direction: row;
    align-items: center;
    gap: 10px;
}

.knowledge-base-page__content :deep(.kb-items__card:hover) {
    transform: translateY(-2px);
    border-color: color-mix(in srgb, var(--color-primary) 26%, transparent);
}

.knowledge-base-page__content :deep(.kb-items__card.is-selected) {
    border-color: color-mix(in srgb, var(--color-primary) 26%, transparent);
    background: linear-gradient(
        180deg,
        color-mix(in srgb, var(--color-primary) 18%, transparent) 0%,
        color-mix(in srgb, var(--color-primary) 12%, transparent) 100%
    );
}

.knowledge-base-page__content :deep(.kb-items__icon) {
    font-size: 28px;
    line-height: 1;
}

.knowledge-base-page__content :deep(.kb-items__name) {
    color: var(--color-text);
    font-size: 14px;
    line-height: 1.08;
}

.knowledge-base-page__content :deep(.kb-items__grid--tile .kb-items__meta) {
    width: 100%;
}

.knowledge-base-page__content :deep(.kb-items__grid--tile .kb-items__name),
.knowledge-base-page__content :deep(.kb-items__grid--compact .kb-items__name) {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.knowledge-base-page__content :deep(.kb-items__grid--list .kb-items__name),
.knowledge-base-page__content :deep(.kb-items__grid--compact .kb-items__name) {
    font-size: 14px;
}

.knowledge-base-page__content :deep(.kb-items__subline) {
    color: color-mix(in srgb, var(--color-text) 76%, transparent);
}

.knowledge-base-page__preview-drawer {
    position: fixed;
    top: 14px;
    right: 13px;
    bottom: 38px;
    width: min(602px, 46vw);
    z-index: 120;
}

.knowledge-base-page__preview-drawer.kb-preview.is-fullscreen {
    top: 14px !important;
    right: 14px !important;
    bottom: 14px !important;
    left: 14px !important;
    width: auto !important;
    max-width: none !important;
}

.knowledge-base-page__hidden-upload {
    display: none;
}

.kb-preview-slide-enter-active,
.kb-preview-slide-leave-active {
    transition: transform 0.28s ease, opacity 0.28s ease;
}

.kb-preview-slide-enter-from,
.kb-preview-slide-leave-to {
    transform: translateX(108%);
    opacity: 0;
}

@media (max-width: $desktop-s) {
    .knowledge-base-page {
        padding: 10px;
        border-radius: 14px;
    }

    .knowledge-base-page__workspace {
        grid-template-columns: 1fr;
    }

    .knowledge-base-page__sidebar {
        max-height: 300px;
    }

    .knowledge-base-page__sidebar-brand {
        flex-wrap: wrap;
        row-gap: 6px;
    }

    .knowledge-base-page__mobile-toggle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }

    .knowledge-base-page__sidebar-panel,
    .knowledge-base-page__toolbar-panel {
        overflow: hidden;
        max-height: 420px;
        opacity: 1;
        transition: max-height 0.24s ease, opacity 0.2s ease, margin 0.2s ease;
    }

    .knowledge-base-page__sidebar.is-mobile-collapsed .knowledge-base-page__sidebar-panel {
        max-height: 0;
        opacity: 0;
        pointer-events: none;
    }

    .knowledge-base-page__toolbar-panel.is-mobile-collapsed {
        max-height: 0;
        opacity: 0;
        margin-bottom: -4px;
        pointer-events: none;
    }

    .knowledge-base-page__preview-drawer {
        top: 10px;
        right: 10px;
        bottom: 10px;
        width: min(640px, calc(100vw - 20px));
    }

    .knowledge-base-page__preview-drawer.kb-preview.is-fullscreen {
        top: 8px !important;
        right: 8px !important;
        bottom: 8px !important;
        left: 8px !important;
        width: auto !important;
    }

    .knowledge-base-page__content :deep(.kb-toolbar) {
        grid-template-columns: 1fr;
    }

    .knowledge-base-page__content :deep(.kb-items__grid--tile) {
        grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
    }

    .knowledge-base-page__content :deep(.kb-items__card) {
        min-height: 118px;
    }

    .knowledge-base-page__content :deep(.kb-items__icon) {
        font-size: 36px;
    }

    .knowledge-base-page__content :deep(.kb-items__name) {
        font-size: 18px;
    }
}
</style>
