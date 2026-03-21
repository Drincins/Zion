<template>
    <aside class="kb-preview" :class="{ 'is-fullscreen': fullscreen }">
        <button
            type="button"
            class="kb-preview__close"
            aria-label="Close preview"
            @click="emit('close')"
        >
            &times;
        </button>

        <header class="kb-preview__header">
            <div class="kb-preview__heading">
                <h3 class="kb-preview__title">{{ panelTitle }}</h3>
                <p class="kb-preview__subtitle">{{ panelSubtitle }}</p>
            </div>
            <div class="kb-preview__actions">
                <Button
                    v-if="selectedItem"
                    class="kb-preview__action-button"
                    color="ghost"
                    size="sm"
                    @click="emit('open-info')"
                >
                    Инфо
                </Button>
                <Button
                    v-if="selectedItem"
                    class="kb-preview__action-button"
                    color="ghost"
                    size="sm"
                    @click="emit('open-history')"
                >
                    История
                </Button>
                <Button
                    v-if="isTextDocument && canManage"
                    class="kb-preview__action-button"
                    color="ghost"
                    size="sm"
                    @click="toggleEditMode"
                >
                    {{ isEditing ? 'Отменить' : 'Редактировать' }}
                </Button>
                <Button
                    v-if="selectedItem && canManage"
                    class="kb-preview__action-button"
                    color="danger"
                    size="sm"
                    @click="emit('delete-item')"
                >
                    Удалить
                </Button>
                <Button
                    v-if="activeDocument"
                    class="kb-preview__action-button"
                    color="ghost"
                    size="sm"
                    @click="emit('toggle-fullscreen')"
                >
                    {{ fullscreen ? 'Свернуть' : 'На весь экран' }}
                </Button>
            </div>
        </header>

        <div v-if="loading" class="kb-preview__state">Загрузка документа...</div>
        <div v-else-if="!selectedItem" class="kb-preview__state">
            Выберите папку или документ слева
        </div>

        <template v-else-if="selectedItem.item_type === 'folder'">
            <div class="kb-preview__folder">
                <p><strong>Тип:</strong> папка</p>
                <p><strong>Имя:</strong> {{ selectedItem.name }}</p>
                <p><strong>Создал:</strong> {{ selectedItem.created_by_name || '-' }}</p>
                <p><strong>Изменил:</strong> {{ selectedItem.updated_by_name || '-' }}</p>
            </div>
        </template>

        <template v-else-if="activeDocument">
            <div v-if="activeDocument.preview_type === 'text'" class="kb-preview__editor">
                <div v-if="canEditText" class="kb-preview__toolbar" role="toolbar" aria-label="Text formatting">
                    <button
                        type="button"
                        class="kb-preview__tool"
                        @mousedown.prevent="applyHeading('p')"
                    >
                        Текст
                    </button>
                    <button
                        type="button"
                        class="kb-preview__tool"
                        @mousedown.prevent="applyHeading('h1')"
                    >
                        Заголовок
                    </button>
                    <button
                        type="button"
                        class="kb-preview__tool"
                        @mousedown.prevent="openLinkEditor"
                    >
                        Ссылка
                    </button>
                    <div class="kb-preview__color-group">
                        <span class="kb-preview__color-label">Цвет:</span>
                        <button
                            type="button"
                            class="kb-preview__color-clear"
                            :class="{ 'is-active': !selectedColor }"
                            @mousedown.prevent="clearTextColor"
                        >
                            Убрать
                        </button>
                        <button
                            v-for="colorOption in CLASSIC_TEXT_COLORS"
                            :key="colorOption.value"
                            type="button"
                            class="kb-preview__color-swatch"
                            :class="{ 'is-active': selectedColor === colorOption.value }"
                            :title="colorOption.label"
                            :aria-label="`Цвет: ${colorOption.label}`"
                            :style="{ '--kb-color': colorOption.value }"
                            @mousedown.prevent="applyTextColor(colorOption.value)"
                        />
                    </div>
                </div>

                <div v-if="canEditText && linkEditorOpen" class="kb-preview__link-popover" @mousedown.stop>
                    <input
                        ref="linkInputRef"
                        v-model="linkDraft"
                        type="text"
                        class="kb-preview__link-input"
                        placeholder="https://example.com"
                        @keydown.enter.prevent="confirmLink"
                        @keydown.esc.prevent="closeLinkEditor"
                    >
                    <div class="kb-preview__link-actions">
                        <button
                            type="button"
                            class="kb-preview__link-button"
                            @mousedown.prevent="confirmLink"
                        >
                            OK
                        </button>
                        <button
                            type="button"
                            class="kb-preview__link-button kb-preview__link-button--ghost"
                            @mousedown.prevent="removeLink"
                        >
                            Убрать ссылку
                        </button>
                        <button
                            type="button"
                            class="kb-preview__link-button kb-preview__link-button--ghost"
                            @mousedown.prevent="closeLinkEditor"
                        >
                            Отмена
                        </button>
                    </div>
                    <p v-if="linkError" class="kb-preview__link-error">{{ linkError }}</p>
                </div>

                <div
                    v-if="canEditText"
                    ref="editorRef"
                    class="kb-preview__rich-editor"
                    contenteditable="true"
                    @focus="captureSelection"
                    @input="onEditorInput"
                    @keyup="captureSelection"
                    @mouseup="captureSelection"
                />

                <!-- eslint-disable-next-line vue/no-v-html -->
                <article v-else class="kb-preview__rich-view" v-html="renderedDocumentHtml" />

                <div v-if="canEditText" class="kb-preview__editor-footer">
                    <input
                        v-model="saveComment"
                        type="text"
                        class="kb-preview__comment"
                        placeholder="Комментарий к версии (опционально)"
                    >
                    <Button
                        color="primary"
                        size="sm"
                        :disabled="!hasChanges"
                        @click="handleSave"
                    >
                        Сохранить
                    </Button>
                </div>
            </div>

            <iframe
                v-else-if="activeDocument.preview_type === 'pdf' && activeDocument.download_url"
                class="kb-preview__pdf"
                :src="activeDocument.download_url"
                title="PDF preview"
            />

            <div v-else class="kb-preview__file">
                <p class="kb-preview__file-title">Предпросмотр недоступен</p>
                <p class="kb-preview__file-description">
                    Для этого типа файла доступно скачивание и просмотр метаданных.
                </p>
                <ul class="kb-preview__file-meta">
                    <li><strong>Расширение:</strong> {{ activeDocument.extension || '-' }}</li>
                    <li><strong>Размер:</strong> {{ fileSizeLabel }}</li>
                </ul>
                <Button color="outline" size="sm" @click="emit('download-document')">
                    Скачать файл
                </Button>
            </div>
        </template>
    </aside>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import Button from '@/components/UI-components/Button.vue';

const props = defineProps({
    selectedItem: {
        type: Object,
        default: null,
    },
    activeDocument: {
        type: Object,
        default: null,
    },
    loading: {
        type: Boolean,
        default: false,
    },
    canManage: {
        type: Boolean,
        default: false,
    },
    fullscreen: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits([
    'save-text',
    'download-document',
    'open-history',
    'open-info',
    'toggle-fullscreen',
    'close',
    'delete-item',
]);

const ALLOWED_HTML_TAGS = new Set([
    'A',
    'B',
    'BR',
    'DIV',
    'EM',
    'FONT',
    'H1',
    'H2',
    'H3',
    'I',
    'LI',
    'OL',
    'P',
    'SPAN',
    'STRONG',
    'U',
    'UL',
]);

const CLASSIC_TEXT_COLORS = Object.freeze([
    { label: 'Красный', value: '#dc2626' },
    { label: 'Синий', value: '#2563eb' },
    { label: 'Желтый', value: '#eab308' },
    { label: 'Зеленый', value: '#16a34a' },
]);

const draftContent = ref('');
const initialContent = ref('');
const saveComment = ref('');
const isEditing = ref(false);
const editorRef = ref(null);
const linkInputRef = ref(null);
const selectedColor = ref(CLASSIC_TEXT_COLORS[1].value);
const linkEditorOpen = ref(false);
const linkDraft = ref('https://');
const linkError = ref('');
const savedSelectionRange = ref(null);
const linkSelectionRange = ref(null);

const isTextDocument = computed(() => props.activeDocument?.preview_type === 'text');
const canEditText = computed(() => props.canManage && isTextDocument.value && isEditing.value);
const renderedDocumentHtml = computed(() => toEditorHtml(props.activeDocument?.content_text || ''));

const hasChanges = computed(() => {
    if (!props.activeDocument || props.activeDocument.preview_type !== 'text') {
        return false;
    }
    return draftContent.value !== initialContent.value;
});

watch(
    () => props.activeDocument,
    (nextDocument) => {
        draftContent.value = toEditorHtml(nextDocument?.content_text || '');
        initialContent.value = draftContent.value;
        saveComment.value = '';
        isEditing.value = false;
        savedSelectionRange.value = null;
        linkSelectionRange.value = null;
        linkEditorOpen.value = false;
        linkDraft.value = 'https://';
        linkError.value = '';
    },
    { immediate: true },
);

watch(isEditing, async (enabled) => {
    if (!enabled || !isTextDocument.value) {
        return;
    }
    await nextTick();
    ensureEditorContent();
});

const panelTitle = computed(() => {
    if (!props.selectedItem) {
        return 'Предпросмотр';
    }
    return props.selectedItem.name || 'Предпросмотр';
});

const panelSubtitle = computed(() => {
    if (!props.selectedItem) {
        return 'Откройте документ или папку';
    }
    if (props.selectedItem.item_type === 'folder') {
        return 'Папка';
    }
    if (props.activeDocument?.document_type === 'text') {
        return 'Текстовый документ';
    }
    return 'Файл';
});

const fileSizeLabel = computed(() => {
    const bytes = Number(props.activeDocument?.file_size);
    if (!Number.isFinite(bytes) || bytes <= 0) {
        return '-';
    }
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
});

function handleSave() {
    if (!canEditText.value || !hasChanges.value) {
        return;
    }
    emit('save-text', {
        content: normalizeSavedHtml(draftContent.value),
        comment: saveComment.value,
    });
}

function toggleEditMode() {
    if (!props.canManage || !isTextDocument.value) {
        return;
    }
    if (isEditing.value) {
        draftContent.value = initialContent.value;
        saveComment.value = '';
        isEditing.value = false;
        savedSelectionRange.value = null;
        closeLinkEditor();
        return;
    }
    isEditing.value = true;
}

function ensureEditorContent() {
    if (!editorRef.value) {
        return;
    }
    editorRef.value.innerHTML = draftContent.value || '<p><br></p>';
    editorRef.value.focus({ preventScroll: true });
}

function onEditorInput() {
    if (!editorRef.value) {
        return;
    }
    draftContent.value = editorRef.value.innerHTML;
    captureSelection();
}

function captureSelection() {
    if (!canEditText.value || typeof window === 'undefined') {
        return;
    }
    const selection = window.getSelection?.();
    if (!selection || selection.rangeCount === 0) {
        return;
    }
    savedSelectionRange.value = selection.getRangeAt(0).cloneRange();
}

function restoreSelection() {
    if (!canEditText.value || typeof window === 'undefined' || !savedSelectionRange.value) {
        return;
    }
    const selection = window.getSelection?.();
    if (!selection) {
        return;
    }
    selection.removeAllRanges();
    selection.addRange(savedSelectionRange.value);
}

function runEditorCommand(command, value = null) {
    if (!canEditText.value || typeof document === 'undefined') {
        return;
    }
    editorRef.value?.focus({ preventScroll: true });
    restoreSelection();
    if (command === 'foreColor') {
        document.execCommand('styleWithCSS', false, true);
    }
    document.execCommand(command, false, value);
    draftContent.value = editorRef.value?.innerHTML || '';
    captureSelection();
}

function applyHeading(tagName) {
    runEditorCommand('formatBlock', `<${String(tagName || 'p').toUpperCase()}>`);
}

function applyTextColor(colorValue) {
    const color = String(colorValue || '').trim();
    if (!color) {
        return;
    }
    selectedColor.value = color;
    runEditorCommand('foreColor', color);
}

function clearTextColor() {
    selectedColor.value = '';
    runEditorCommand('foreColor', 'inherit');
}

async function openLinkEditor() {
    if (!canEditText.value) {
        return;
    }
    const range = getCurrentEditorRange() || savedSelectionRange.value;
    linkSelectionRange.value = range ? range.cloneRange() : null;
    const selectedHref = getLinkHrefFromSelection();
    linkDraft.value = selectedHref || 'https://';
    linkError.value = '';
    linkEditorOpen.value = true;
    await nextTick();
    linkInputRef.value?.focus();
    linkInputRef.value?.select();
}

function confirmLink() {
    const href = sanitizeHref(linkDraft.value.trim());
    if (!href) {
        linkError.value = 'Введите корректную ссылку';
        return;
    }
    linkError.value = '';
    if (!applyLinkToSelection(href)) {
        linkError.value = 'Не удалось применить ссылку';
        return;
    }
    closeLinkEditor();
}

function removeLink() {
    linkError.value = '';
    if (!removeLinkFromSelection()) {
        linkError.value = 'Ссылка не найдена';
        return;
    }
    closeLinkEditor();
}

function closeLinkEditor() {
    linkEditorOpen.value = false;
    linkError.value = '';
    linkSelectionRange.value = null;
}

function getCurrentEditorRange() {
    if (typeof window === 'undefined') {
        return null;
    }
    const selection = window.getSelection?.();
    if (!selection || selection.rangeCount === 0) {
        return null;
    }
    const range = selection.getRangeAt(0);
    if (!editorRef.value?.contains(range.commonAncestorContainer)) {
        return null;
    }
    return range;
}

function applyLinkToSelection(href) {
    if (typeof document === 'undefined' || typeof window === 'undefined') {
        return false;
    }
    const sourceRange = linkSelectionRange.value || savedSelectionRange.value || getCurrentEditorRange();
    const range = sourceRange?.cloneRange?.();
    if (!range || !editorRef.value?.contains(range.commonAncestorContainer)) {
        return false;
    }
    const selection = window.getSelection?.();
    if (!selection) {
        return false;
    }

    editorRef.value.focus({ preventScroll: true });
    selection.removeAllRanges();
    selection.addRange(range);

    const anchor = document.createElement('a');
    anchor.setAttribute('href', href);
    anchor.setAttribute('target', '_blank');
    anchor.setAttribute('rel', 'noopener noreferrer');
    if (range.collapsed) {
        anchor.textContent = href;
        range.insertNode(anchor);
    } else {
        const fragment = range.extractContents();
        anchor.appendChild(fragment);
        range.insertNode(anchor);
    }

    const nextRange = document.createRange();
    nextRange.setStartAfter(anchor);
    nextRange.collapse(true);
    selection.removeAllRanges();
    selection.addRange(nextRange);

    draftContent.value = editorRef.value?.innerHTML || '';
    savedSelectionRange.value = nextRange.cloneRange();
    linkSelectionRange.value = nextRange.cloneRange();
    captureSelection();
    return true;
}

function removeLinkFromSelection() {
    if (typeof document === 'undefined' || typeof window === 'undefined') {
        return false;
    }
    const sourceRange = linkSelectionRange.value || savedSelectionRange.value || getCurrentEditorRange();
    const range = sourceRange?.cloneRange?.();
    if (!range || !editorRef.value?.contains(range.commonAncestorContainer)) {
        return false;
    }
    const selection = window.getSelection?.();
    if (!selection) {
        return false;
    }

    editorRef.value.focus({ preventScroll: true });
    selection.removeAllRanges();
    selection.addRange(range);

    const anchorBefore = findClosestAnchor(
        range.startContainer?.nodeType === 3 ? range.startContainer.parentNode : range.startContainer,
    );
    document.execCommand('unlink', false, null);

    if (range.collapsed && anchorBefore && editorRef.value?.contains(anchorBefore)) {
        unwrapAnchor(anchorBefore);
    }

    let nextRange = null;
    if (selection.rangeCount > 0) {
        nextRange = selection.getRangeAt(0).cloneRange();
    } else if (editorRef.value) {
        nextRange = document.createRange();
        nextRange.selectNodeContents(editorRef.value);
        nextRange.collapse(false);
        selection.addRange(nextRange);
    }

    draftContent.value = editorRef.value?.innerHTML || '';
    if (nextRange) {
        savedSelectionRange.value = nextRange.cloneRange();
        linkSelectionRange.value = nextRange.cloneRange();
    } else {
        savedSelectionRange.value = null;
        linkSelectionRange.value = null;
    }
    captureSelection();
    return true;
}

function getLinkHrefFromSelection() {
    const range = linkSelectionRange.value || savedSelectionRange.value;
    if (!range) {
        return '';
    }
    let node = range.commonAncestorContainer;
    if (node?.nodeType === 3) {
        node = node.parentNode;
    }
    const anchor = findClosestAnchor(node);
    return anchor?.getAttribute?.('href') || '';
}

function unwrapAnchor(anchorNode) {
    const anchor = anchorNode;
    const parent = anchor?.parentNode;
    if (!anchor || !parent) {
        return;
    }
    while (anchor.firstChild) {
        parent.insertBefore(anchor.firstChild, anchor);
    }
    parent.removeChild(anchor);
}

function findClosestAnchor(node) {
    let cursor = node;
    while (cursor) {
        if (cursor.nodeType === 1 && String(cursor.tagName || '').toUpperCase() === 'A') {
            return cursor;
        }
        cursor = cursor.parentNode;
    }
    return null;
}

function toEditorHtml(value) {
    const input = String(value || '');
    if (!input.trim()) {
        return '<p><br></p>';
    }
    if (hasHtmlMarkup(input)) {
        return sanitizeEditorHtml(input) || '<p><br></p>';
    }
    return plainTextToHtml(input);
}

function normalizeSavedHtml(value) {
    const sanitized = sanitizeEditorHtml(value || '');
    const text = htmlToText(sanitized);
    if (!text.trim()) {
        return '';
    }
    return sanitized;
}

function hasHtmlMarkup(value) {
    return /<\/?[a-z][\s\S]*>/i.test(String(value || ''));
}

function plainTextToHtml(value) {
    const lines = String(value || '').replace(/\r\n/g, '\n').split('\n');
    return lines
        .map((line) => (line ? `<p>${escapeHtml(line)}</p>` : '<p><br></p>'))
        .join('');
}

function htmlToText(value) {
    if (typeof DOMParser === 'undefined') {
        return String(value || '').replace(/<[^>]+>/g, ' ');
    }
    const parser = new DOMParser();
    const doc = parser.parseFromString(`<div>${value || ''}</div>`, 'text/html');
    return (doc.body?.textContent || '').replace(/\s+/g, ' ').trim();
}

function sanitizeEditorHtml(value) {
    if (typeof DOMParser === 'undefined') {
        return String(value || '');
    }
    const parser = new DOMParser();
    const documentNode = parser.parseFromString(`<div>${value || ''}</div>`, 'text/html');
    const container = documentNode.body.firstElementChild;
    if (!container) {
        return '';
    }

    const cleanRoot = documentNode.createElement('div');
    Array.from(container.childNodes).forEach((child) => {
        const sanitized = sanitizeHtmlNode(child, documentNode);
        if (sanitized) {
            cleanRoot.appendChild(sanitized);
        }
    });

    return cleanRoot.innerHTML.replace(/<p><\/p>/g, '<p><br></p>').trim();
}

function sanitizeHtmlNode(node, documentNode) {
    if (node.nodeType === 3) {
        return documentNode.createTextNode(node.textContent || '');
    }
    if (node.nodeType !== 1) {
        return null;
    }

    const tagName = String(node.nodeName || '').toUpperCase();
    if (!ALLOWED_HTML_TAGS.has(tagName)) {
        const fragment = documentNode.createDocumentFragment();
        Array.from(node.childNodes).forEach((child) => {
            const sanitized = sanitizeHtmlNode(child, documentNode);
            if (sanitized) {
                fragment.appendChild(sanitized);
            }
        });
        return fragment;
    }

    const normalizedTag = tagName === 'FONT' ? 'span' : tagName.toLowerCase();
    const element = documentNode.createElement(normalizedTag);

    if (tagName === 'A') {
        const href = sanitizeHref(node.getAttribute('href') || '');
        if (href) {
            element.setAttribute('href', href);
            element.setAttribute('target', '_blank');
            element.setAttribute('rel', 'noopener noreferrer');
        }
    }

    const color = extractColorValue(
        tagName === 'FONT' ? node.getAttribute('color') : '',
        node.getAttribute('style') || '',
    );
    if (color) {
        element.style.color = color;
    }

    Array.from(node.childNodes).forEach((child) => {
        const sanitized = sanitizeHtmlNode(child, documentNode);
        if (sanitized) {
            element.appendChild(sanitized);
        }
    });

    return element;
}

function sanitizeHref(rawHref) {
    const value = String(rawHref || '').trim();
    if (!value) {
        return '';
    }
    if (value.startsWith('#') || value.startsWith('/')) {
        return value;
    }
    try {
        const parsed = new URL(value, window.location.origin);
        if (['http:', 'https:', 'mailto:', 'tel:'].includes(parsed.protocol)) {
            return parsed.href;
        }
    } catch {
        return '';
    }
    return '';
}

function extractColorValue(fontColor, styleValue) {
    const direct = String(fontColor || '').trim();
    if (isSafeColorValue(direct)) {
        return direct;
    }
    const match = String(styleValue || '').match(/(?:^|;)\s*color\s*:\s*([^;]+)/i);
    const fromStyle = (match?.[1] || '').trim();
    return isSafeColorValue(fromStyle) ? fromStyle : '';
}

function isSafeColorValue(value) {
    const color = String(value || '').trim();
    if (!color) {
        return false;
    }
    return (
        /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i.test(color)
        || /^rgba?\(\s*\d{1,3}(?:\.\d+)?\s*,\s*\d{1,3}(?:\.\d+)?\s*,\s*\d{1,3}(?:\.\d+)?(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)$/i.test(color)
        || /^hsla?\(\s*\d{1,3}(?:\.\d+)?\s*,\s*\d{1,3}%\s*,\s*\d{1,3}%(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)$/i.test(color)
    );
}

function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
</script>

<style scoped lang="scss">
.kb-preview {
    position: relative;
    border-radius: 16px;
    border: 1px solid color-mix(in srgb, var(--color-border) 78%, transparent);
    background: color-mix(in srgb, var(--color-surface) 96%, transparent);
    padding: 14px;
    min-height: 420px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.kb-preview.is-fullscreen {
    position: fixed;
    inset: 24px;
    z-index: 70;
    backdrop-filter: blur(6px);
    width: auto !important;
    max-width: none !important;
}

.kb-preview__header {
    display: inline-grid;
    gap: 10px;
    padding-right: 40px;
}

.kb-preview__close {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 28px;
    height: 28px;
    border: 1px solid color-mix(in srgb, var(--color-border) 78%, transparent);
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-surface) 92%, transparent);
    color: var(--color-text-secondary);
    font-size: 20px;
    line-height: 1;
    display: grid;
    place-items: center;
    cursor: pointer;
    transition: color 0.18s ease, border-color 0.18s ease, background-color 0.18s ease;
}

.kb-preview__close:hover {
    color: var(--color-text);
    border-color: color-mix(in srgb, var(--color-primary) 45%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary) 14%, var(--color-surface));
}

.kb-preview__title {
    margin: 0;
    font-size: 20px;
}

.kb-preview__subtitle {
    margin: 4px 0 0;
    color: var(--color-text-secondary);
    font-size: 13px;
}

.kb-preview__actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.kb-preview__action-button {
    padding: 4px 14px;
    height: 30px;
}

.kb-preview__state {
    color: var(--color-text-secondary);
    font-size: 14px;
}

.kb-preview__folder p {
    margin: 0 0 8px;
}

.kb-preview__editor {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
    flex: 1;
}

.kb-preview__toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.kb-preview__tool {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 36px;
    height: 32px;
    border: 1px solid color-mix(in srgb, var(--color-border) 75%, transparent);
    border-radius: 10px;
    background: color-mix(in srgb, var(--color-background) 86%, var(--color-surface) 14%);
    color: var(--color-text);
    padding: 0 10px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: border-color 0.16s ease, background-color 0.16s ease, color 0.16s ease;
}

.kb-preview__tool:hover {
    border-color: color-mix(in srgb, var(--color-primary) 42%, transparent);
    background: color-mix(in srgb, var(--color-primary) 14%, var(--color-surface));
}

.kb-preview__color-group {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0 4px 0 2px;
}

.kb-preview__color-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-text-secondary);
}

.kb-preview__color-clear {
    height: 22px;
    border: 1px solid color-mix(in srgb, var(--color-border) 78%, transparent);
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-background) 86%, var(--color-surface) 14%);
    color: var(--color-text-secondary);
    padding: 0 8px;
    font-size: 11px;
    line-height: 1;
    cursor: pointer;
    transition: border-color 0.12s ease, color 0.12s ease, background-color 0.12s ease;
}

.kb-preview__color-clear:hover {
    border-color: color-mix(in srgb, var(--color-primary) 46%, transparent);
    color: var(--color-text);
}

.kb-preview__color-clear.is-active {
    border-color: color-mix(in srgb, var(--color-primary) 70%, transparent);
    color: var(--color-text);
    background: color-mix(in srgb, var(--color-primary) 14%, var(--color-surface));
}

.kb-preview__color-swatch {
    width: 20px;
    height: 20px;
    border-radius: 999px;
    border: 1px solid color-mix(in srgb, var(--color-border) 82%, transparent);
    background: var(--kb-color, var(--color-text));
    cursor: pointer;
    transition: transform 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
}

.kb-preview__color-swatch:hover {
    transform: translateY(-1px);
    border-color: color-mix(in srgb, var(--color-primary) 46%, transparent);
}

.kb-preview__color-swatch.is-active {
    border-color: color-mix(in srgb, var(--color-primary) 70%, transparent);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-primary) 20%, transparent);
}

.kb-preview__link-popover {
    display: grid;
    gap: 8px;
    padding: 10px;
    border: 1px solid color-mix(in srgb, var(--color-border) 75%, transparent);
    border-radius: 10px;
    background: color-mix(in srgb, var(--color-background) 86%, var(--color-surface) 14%);
}

.kb-preview__link-input {
    width: 100%;
    border: 1px solid color-mix(in srgb, var(--color-border) 80%, transparent);
    border-radius: 8px;
    background: transparent;
    color: var(--color-text);
    padding: 7px 10px;
    font-size: 13px;
}

.kb-preview__link-actions {
    display: flex;
    gap: 8px;
}

.kb-preview__link-button {
    height: 28px;
    border: 1px solid color-mix(in srgb, var(--color-primary) 45%, transparent);
    border-radius: 8px;
    background: color-mix(in srgb, var(--color-primary) 24%, var(--color-surface));
    color: var(--color-text);
    padding: 0 10px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
}

.kb-preview__link-button--ghost {
    border-color: color-mix(in srgb, var(--color-border) 80%, transparent);
    background: transparent;
    color: var(--color-text-secondary);
}

.kb-preview__link-error {
    margin: 0;
    font-size: 12px;
    color: var(--color-danger, #dc2626);
}

.kb-preview__rich-editor,
.kb-preview__rich-view {
    width: 100%;
    min-height: 320px;
    flex: 1;
    border: 1px solid color-mix(in srgb, var(--color-border) 80%, transparent);
    border-radius: 12px;
    background: color-mix(in srgb, var(--color-background) 80%, var(--color-surface) 20%);
    color: var(--color-text);
    padding: 12px;
    font-size: 14px;
    line-height: 1.45;
}

.kb-preview__rich-editor {
    overflow: auto;
    outline: none;
}

.kb-preview__rich-view {
    overflow: auto;
}

.kb-preview__rich-view :deep(p),
.kb-preview__rich-view :deep(h1),
.kb-preview__rich-view :deep(h2),
.kb-preview__rich-view :deep(h3),
.kb-preview__rich-view :deep(ul),
.kb-preview__rich-view :deep(ol) {
    margin: 0 0 8px;
}

.kb-preview__rich-view :deep(a) {
    color: color-mix(in srgb, var(--color-primary) 82%, var(--color-text));
    text-decoration: underline;
}

.kb-preview__rich-editor :deep(h1),
.kb-preview__rich-view :deep(h1) {
    margin: 0 0 10px;
    font-size: 28px;
    line-height: 1.2;
    font-weight: 700;
}

.kb-preview__rich-editor :deep(h2),
.kb-preview__rich-view :deep(h2) {
    margin: 0 0 9px;
    font-size: 22px;
    line-height: 1.25;
    font-weight: 700;
}

.kb-preview__rich-editor :deep(h3),
.kb-preview__rich-view :deep(h3) {
    margin: 0 0 8px;
    font-size: 18px;
    line-height: 1.3;
    font-weight: 700;
}

.kb-preview__editor-footer {
    display: flex;
    gap: 8px;
}

.kb-preview__comment {
    flex: 1;
    border: 1px solid color-mix(in srgb, var(--color-border) 78%, transparent);
    border-radius: 10px;
    background: transparent;
    padding: 8px 10px;
    color: var(--color-text);
}

.kb-preview__pdf {
    width: 100%;
    flex: 1;
    min-height: 420px;
    border: 1px solid color-mix(in srgb, var(--color-border) 80%, transparent);
    border-radius: 12px;
    background: var(--color-surface);
}

.kb-preview__file-title {
    margin: 0 0 6px;
    font-size: 16px;
}

.kb-preview__file-description {
    margin: 0 0 12px;
    color: var(--color-text-secondary);
}

.kb-preview__file-meta {
    margin: 0 0 12px;
    padding-left: 18px;
    color: var(--color-text-secondary);
}

@media (max-width: $desktop-s) {
    .kb-preview.is-fullscreen {
        inset: 10px;
    }
}

@media (max-width: $mobile) {
    .kb-preview__editor-footer {
        flex-direction: column;
    }
}
</style>

