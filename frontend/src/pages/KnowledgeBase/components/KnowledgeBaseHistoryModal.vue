<template>
    <Modal @close="emit('close')">
        <template #header>
            <h3 class="kb-history__title">{{ title }}</h3>
        </template>

        <div class="kb-history__body">
            <section class="kb-history__section">
                <h4 class="kb-history__section-title">Журнал действий</h4>
                <p v-if="!auditLogs.length" class="kb-history__empty">Записей нет</p>
                <div v-else class="kb-history__table-wrapper">
                    <table class="kb-history__table">
                        <thead>
                            <tr>
                                <th>Когда</th>
                                <th>Действие</th>
                                <th>Кто</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="entry in auditLogs" :key="`audit-${entry.id}`">
                                <td>{{ formatDate(entry.created_at) }}</td>
                                <td>{{ formatAction(entry) }}</td>
                                <td>{{ entry.created_by_name || '—' }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>

            <section v-if="versions.length" class="kb-history__section">
                <h4 class="kb-history__section-title">Версии документа</h4>
                <div class="kb-history__table-wrapper">
                    <table class="kb-history__table">
                        <thead>
                            <tr>
                                <th>Версия</th>
                                <th>Когда</th>
                                <th>Автор</th>
                                <th>Комментарий</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="version in versions" :key="`version-${version.id}`">
                                <td>{{ version.version_number }}</td>
                                <td>{{ formatDate(version.created_at) }}</td>
                                <td>{{ version.created_by_name || '—' }}</td>
                                <td>{{ formatVersionComment(version.comment) }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </section>
        </div>

        <template #footer>
            <div class="kb-history__footer">
                <Button color="primary" @click="emit('close')">Закрыть</Button>
            </div>
        </template>
    </Modal>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Modal from '@/components/UI-components/Modal.vue';
import { formatKnowledgeBaseDate } from '../utils/date';

defineProps({
    title: {
        type: String,
        default: 'История',
    },
    auditLogs: {
        type: Array,
        default: () => [],
    },
    versions: {
        type: Array,
        default: () => [],
    },
});

const emit = defineEmits(['close']);

const formatDate = formatKnowledgeBaseDate;

const ACTION_LABELS = {
    created: 'Создано',
    uploaded: 'Файл загружен',
    opened: 'Открыт',
    content_updated: 'Обновлено содержимое',
    deleted: 'Удалено',
    deleted_via_folder: 'Удалено при удалении папки',
    updated_name: 'Переименовано',
    updated_parent_id: 'Перемещено',
    updated_folder_id: 'Перемещено',
    updated_style_key: 'Изменен стиль папки',
    updated_access: 'Обновлены доступы',
};

function formatAction(entry) {
    const action = String(entry?.action || '').trim();
    if (!action) {
        return '—';
    }
    if (ACTION_LABELS[action]) {
        return ACTION_LABELS[action];
    }
    if (action.startsWith('updated_')) {
        return 'Изменено';
    }
    return action;
}

const VERSION_COMMENT_LABELS = {
    'Initial version': 'Первая версия',
    'Uploaded file': 'Файл загружен',
};

function formatVersionComment(comment) {
    const value = String(comment || '').trim();
    if (!value) {
        return '—';
    }
    return VERSION_COMMENT_LABELS[value] || value;
}
</script>

<style scoped lang="scss">
.kb-history__title {
    margin: 0;
    font-size: 18px;
}

.kb-history__body {
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-height: 60vh;
    overflow: auto;
}

.kb-history__section-title {
    margin: 0 0 8px;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.kb-history__empty {
    margin: 0;
    color: var(--color-text-secondary);
}

.kb-history__table-wrapper {
    overflow: auto;
    border-radius: 12px;
    border: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
}

.kb-history__table {
    width: 100%;
    border-collapse: collapse;
    min-width: 520px;
}

.kb-history__table th,
.kb-history__table td {
    padding: 8px 10px;
    border-bottom: 1px solid color-mix(in srgb, var(--color-border) 68%, transparent);
    text-align: left;
    font-size: 13px;
}

.kb-history__table thead th {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--color-text-secondary);
}

.kb-history__footer {
    display: flex;
    justify-content: flex-end;
}
</style>
