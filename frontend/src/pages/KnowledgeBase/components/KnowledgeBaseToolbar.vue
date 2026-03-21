<template>
    <section class="kb-toolbar">
        <div class="kb-toolbar__search">
            <Input
                :model-value="search"
                placeholder="Поиск по папкам и документам"
                @update:model-value="emit('update:search', $event)"
            />
        </div>
        <div class="kb-toolbar__filters">
            <Select
                :model-value="itemKind"
                :options="itemKindOptions"
                placeholder="Тип"
                @update:model-value="emit('update:itemKind', $event)"
            />
            <Select
                :model-value="documentType"
                :options="documentTypeOptions"
                placeholder="Тип документа"
                @update:model-value="emit('update:documentType', $event)"
            />
            <Select
                :model-value="viewMode"
                :options="viewModeOptions"
                placeholder="Режим"
                @update:model-value="emit('update:viewMode', $event)"
            />
        </div>
        <div class="kb-toolbar__actions">
            <Button color="ghost" size="sm" :loading="busy" @click="emit('refresh')">Обновить</Button>
            <Button
                v-if="canManage && selectedItem"
                color="danger"
                size="sm"
                :disabled="busy"
                @click="emit('delete-selected')"
            >
                Удалить
            </Button>
            <Button
                v-if="canManage"
                color="secondary"
                size="sm"
                :disabled="busy"
                @click="emit('create-folder')"
            >
                Новая папка
            </Button>
            <Button
                v-if="canManage"
                color="primary"
                size="sm"
                :disabled="busy"
                @click="emit('create-document')"
            >
                Новый документ
            </Button>
            <Button
                v-if="canUpload"
                color="outline"
                size="sm"
                :disabled="busy"
                @click="emit('upload-file')"
            >
                Загрузить файл
            </Button>
        </div>
    </section>
</template>

<script setup>
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import Button from '@/components/UI-components/Button.vue';
import {
    KNOWLEDGE_BASE_DOCUMENT_TYPE_OPTIONS,
    KNOWLEDGE_BASE_ITEM_KIND_OPTIONS,
    KNOWLEDGE_BASE_VIEW_MODES
} from '@/pages/KnowledgeBase/constants';

defineProps({
    search: {
        type: String,
        default: '',
    },
    itemKind: {
        type: String,
        default: 'all',
    },
    documentType: {
        type: String,
        default: 'all',
    },
    viewMode: {
        type: String,
        default: 'tile',
    },
    canManage: {
        type: Boolean,
        default: false,
    },
    canUpload: {
        type: Boolean,
        default: false,
    },
    selectedItem: {
        type: Object,
        default: null,
    },
    busy: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits([
    'update:search',
    'update:itemKind',
    'update:documentType',
    'update:viewMode',
    'refresh',
    'create-folder',
    'create-document',
    'upload-file',
    'delete-selected',
]);

const itemKindOptions = KNOWLEDGE_BASE_ITEM_KIND_OPTIONS.map((option) => ({
    value: option.value,
    label: option.label,
}));
const documentTypeOptions = KNOWLEDGE_BASE_DOCUMENT_TYPE_OPTIONS.map((option) => ({
    value: option.value,
    label: option.label,
}));
const viewModeOptions = KNOWLEDGE_BASE_VIEW_MODES.map((option) => ({
    value: option.value,
    label: option.label,
}));
</script>

<style scoped lang="scss">
.kb-toolbar {
    display: grid;
    grid-template-columns: minmax(220px, 1.3fr) minmax(280px, 1fr) auto;
    gap: 12px;
    align-items: start;
}

.kb-toolbar__search {
    min-width: 0;
    width: 100%;
}

.kb-toolbar__search :deep(.input) {
    margin-bottom: 0;
}

.kb-toolbar__filters {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    min-width: 0;
}

.kb-toolbar__actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    flex-wrap: wrap;
    align-items: center;
}

.kb-toolbar__actions :deep(.button) {
    white-space: nowrap;
}

@media (max-width: 1260px) {
    .kb-toolbar {
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }

    .kb-toolbar__search {
        grid-column: 1 / -1;
    }

    .kb-toolbar__filters {
        grid-column: 1 / -1;
    }

    .kb-toolbar__actions {
        grid-column: 1 / -1;
        justify-content: flex-start;
    }
}

@media (max-width: $desktop-s) {
    .kb-toolbar {
        grid-template-columns: 1fr;
    }

    .kb-toolbar__filters {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .kb-toolbar__actions {
        justify-content: flex-start;
    }

    .kb-toolbar__actions :deep(.button) {
        flex: 1 1 calc(50% - 4px);
        min-width: 138px;
    }
}

@media (max-width: $mobile) {
    .kb-toolbar__filters {
        grid-template-columns: 1fr;
    }

    .kb-toolbar__actions :deep(.button) {
        flex-basis: 100%;
        min-width: 0;
    }
}
</style>
