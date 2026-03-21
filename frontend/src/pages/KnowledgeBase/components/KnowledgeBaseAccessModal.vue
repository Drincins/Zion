<template>
    <Modal @close="emit('close')">
        <template #header>
            <h3 class="kb-access-modal__title">{{ title }}</h3>
        </template>

        <div class="kb-access-modal__body">
            <KnowledgeBaseAccessSelector
                v-model="accessValue"
                :options="accessOptions"
            />
        </div>

        <template #footer>
            <div class="kb-access-modal__footer">
                <Button color="ghost" @click="emit('close')">Отмена</Button>
                <Button color="primary" @click="emit('submit', normalizeAccess(accessValue))">
                    {{ confirmLabel }}
                </Button>
            </div>
        </template>
    </Modal>
</template>

<script setup>
import { ref, watch } from 'vue';
import Modal from '@/components/UI-components/Modal.vue';
import Button from '@/components/UI-components/Button.vue';
import KnowledgeBaseAccessSelector from './KnowledgeBaseAccessSelector.vue';
import { normalizeKnowledgeBaseAccess } from '../utils/access';

const props = defineProps({
    title: {
        type: String,
        default: 'Доступы папки',
    },
    confirmLabel: {
        type: String,
        default: 'Сохранить',
    },
    accessOptions: {
        type: Object,
        default: () => ({
            roles: [],
            positions: [],
            users: [],
            restaurants: [],
        }),
    },
    initialAccess: {
        type: Object,
        default: () => ({
            role_ids: [],
            position_ids: [],
            user_ids: [],
            restaurant_ids: [],
        }),
    },
});

const emit = defineEmits(['close', 'submit']);

const accessValue = ref(normalizeAccess(props.initialAccess));

watch(
    () => props.initialAccess,
    (nextValue) => {
        accessValue.value = normalizeAccess(nextValue);
    },
    { immediate: true, deep: true },
);

function normalizeAccess(value) {
    return normalizeKnowledgeBaseAccess(value);
}
</script>

<style scoped lang="scss">
.kb-access-modal__title {
    margin: 0;
    font-size: 18px;
}

.kb-access-modal__body {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.kb-access-modal__footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
}
</style>
