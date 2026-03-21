<template>
    <Modal @close="emit('close')">
        <template #header>
            <h3 class="kb-modal__title">{{ title }}</h3>
        </template>

        <div class="kb-modal__body">
            <Input
                :model-value="nameValue"
                :placeholder="placeholder"
                @update:model-value="nameValue = String($event || '')"
            />

            <div v-if="showStylePicker" class="kb-modal__style-picker">
                <p class="kb-modal__style-label">Стиль папки</p>
                <div class="kb-modal__style-grid">
                    <button
                        v-for="style in styleOptions"
                        :key="style.key"
                        type="button"
                        class="kb-modal__style-chip"
                        :class="{ 'is-active': styleValue === style.key }"
                        :style="{ '--accent': style.accent }"
                        @click="styleValue = style.key"
                    >
                        <span class="kb-modal__style-dot" />
                        {{ style.label }}
                    </button>
                </div>
            </div>

            <div v-if="showAccessPicker" class="kb-modal__access-picker">
                <p class="kb-modal__style-label">Доступы</p>
                <KnowledgeBaseAccessSelector
                    v-model="accessValue"
                    :options="accessOptions"
                />
            </div>
        </div>

        <template #footer>
            <div class="kb-modal__footer">
                <Button color="ghost" @click="emit('close')">Отмена</Button>
                <Button color="primary" :disabled="!trimmedName" @click="handleSubmit">
                    {{ confirmLabel }}
                </Button>
            </div>
        </template>
    </Modal>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import Modal from '@/components/UI-components/Modal.vue';
import Input from '@/components/UI-components/Input.vue';
import Button from '@/components/UI-components/Button.vue';
import KnowledgeBaseAccessSelector from './KnowledgeBaseAccessSelector.vue';
import { normalizeKnowledgeBaseAccess } from '../utils/access';

const props = defineProps({
    title: {
        type: String,
        required: true,
    },
    placeholder: {
        type: String,
        default: 'Введите название',
    },
    confirmLabel: {
        type: String,
        default: 'Сохранить',
    },
    initialName: {
        type: String,
        default: '',
    },
    initialStyleKey: {
        type: String,
        default: 'amber',
    },
    showStylePicker: {
        type: Boolean,
        default: false,
    },
    styleOptions: {
        type: Array,
        default: () => [],
    },
    showAccessPicker: {
        type: Boolean,
        default: false,
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

const emit = defineEmits(['submit', 'close']);

const nameValue = ref(props.initialName || '');
const styleValue = ref(props.initialStyleKey || 'amber');
const accessValue = ref(normalizeAccess(props.initialAccess));

watch(
    () => props.initialName,
    (nextValue) => {
        nameValue.value = nextValue || '';
    },
    { immediate: true },
);

watch(
    () => props.initialStyleKey,
    (nextValue) => {
        styleValue.value = nextValue || 'amber';
    },
    { immediate: true },
);

watch(
    () => props.initialAccess,
    (nextValue) => {
        accessValue.value = normalizeAccess(nextValue);
    },
    { immediate: true, deep: true },
);

const trimmedName = computed(() => String(nameValue.value || '').trim());

function handleSubmit() {
    if (!trimmedName.value) {
        return;
    }
    emit('submit', {
        name: trimmedName.value,
        styleKey: styleValue.value,
        access: normalizeAccess(accessValue.value),
    });
}

function normalizeAccess(value) {
    return normalizeKnowledgeBaseAccess(value);
}
</script>

<style scoped lang="scss">
.kb-modal__title {
    margin: 0;
    font-size: 18px;
}

.kb-modal__body {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.kb-modal__style-label {
    margin: 0 0 6px;
    color: var(--color-text-secondary);
    font-size: 13px;
}

.kb-modal__style-grid {
    display: grid;
    grid-template-columns: repeat(8, minmax(0, 1fr));
    gap: 8px;
}

.kb-modal__style-chip {
    border: 1px solid color-mix(in srgb, var(--accent) 48%, var(--color-border) 52%);
    background: transparent;
    border-radius: 10px;
    color: var(--color-text);
    padding: 6px 8px;
    text-align: left;
    font-size: 13px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.kb-modal__style-chip.is-active {
    background: color-mix(in srgb, var(--accent) 16%, transparent);
}

.kb-modal__style-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--accent);
}

.kb-modal__access-picker {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.kb-modal__footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
}

@media (max-width: $mobile) {
    .kb-modal__style-grid {
        grid-template-columns: 1fr;
    }
}
</style>
