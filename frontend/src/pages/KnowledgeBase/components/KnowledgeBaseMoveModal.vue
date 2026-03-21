<template>
    <Modal @close="emit('close')">
        <template #header>
            <h3 class="kb-move-modal__title">Переместить</h3>
        </template>

        <div class="kb-move-modal__body">
            <p class="kb-move-modal__description">
                Выберите папку, куда нужно переместить элемент.
            </p>
            <Select
                :model-value="targetFolderId"
                :options="folderOptions"
                placeholder="Папка назначения"
                @update:model-value="targetFolderId = $event"
            />
        </div>

        <template #footer>
            <div class="kb-move-modal__footer">
                <Button color="ghost" @click="emit('close')">Отмена</Button>
                <Button color="primary" @click="emit('submit', targetFolderId)">Переместить</Button>
            </div>
        </template>
    </Modal>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import Modal from '@/components/UI-components/Modal.vue';
import Button from '@/components/UI-components/Button.vue';
import Select from '@/components/UI-components/Select.vue';

const props = defineProps({
    folders: {
        type: Array,
        default: () => [],
    },
    initialFolderId: {
        type: Number,
        default: null,
    },
});

const emit = defineEmits(['submit', 'close']);

const targetFolderId = ref(props.initialFolderId ?? null);

watch(
    () => props.initialFolderId,
    (nextValue) => {
        targetFolderId.value = nextValue ?? null;
    },
    { immediate: true },
);

const folderOptions = computed(() => [
    { value: null, label: 'Корень' },
    ...props.folders.map((folder) => ({
        value: folder.id,
        label: folder.label || folder.name || `Folder #${folder.id}`,
    })),
]);
</script>

<style scoped lang="scss">
.kb-move-modal__title {
    margin: 0;
    font-size: 18px;
}

.kb-move-modal__description {
    margin: 0 0 10px;
    color: var(--color-text-secondary);
}

.kb-move-modal__footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
}
</style>
