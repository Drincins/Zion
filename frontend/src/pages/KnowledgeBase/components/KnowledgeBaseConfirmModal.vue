<template>
    <Modal @close="emit('close')">
        <template #header>
            <h3 class="kb-confirm__title">{{ title }}</h3>
        </template>

        <p class="kb-confirm__message">{{ message }}</p>
        <label v-if="showForceOption" class="kb-confirm__force-option">
            <input
                type="checkbox"
                :checked="forceValue"
                @change="emit('update:forceValue', $event.target.checked)"
            >
            <span>{{ forceLabel }}</span>
        </label>

        <template #footer>
            <div class="kb-confirm__footer">
                <Button color="ghost" @click="emit('close')">Отмена</Button>
                <Button :color="danger ? 'danger' : 'primary'" @click="emit('confirm')">
                    {{ confirmLabel }}
                </Button>
            </div>
        </template>
    </Modal>
</template>

<script setup>
import Modal from '@/components/UI-components/Modal.vue';
import Button from '@/components/UI-components/Button.vue';

defineProps({
    title: {
        type: String,
        default: 'Подтверждение',
    },
    message: {
        type: String,
        default: '',
    },
    confirmLabel: {
        type: String,
        default: 'Подтвердить',
    },
    danger: {
        type: Boolean,
        default: false,
    },
    showForceOption: {
        type: Boolean,
        default: false,
    },
    forceValue: {
        type: Boolean,
        default: false,
    },
    forceLabel: {
        type: String,
        default: 'Удалить рекурсивно',
    },
});

const emit = defineEmits(['confirm', 'close', 'update:forceValue']);
</script>

<style scoped lang="scss">
.kb-confirm__title {
    margin: 0;
    font-size: 18px;
}

.kb-confirm__message {
    margin: 0;
    color: var(--color-text-secondary);
    line-height: 1.45;
}

.kb-confirm__force-option {
    margin-top: 10px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--color-text-secondary);
}

.kb-confirm__footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
}
</style>
