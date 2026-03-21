<template>
    <Modal @close="emit('close')">
        <template #header>
            <h3 class="kb-info__title">{{ title }}</h3>
        </template>

        <div class="kb-info__body">
            <div v-if="!rows.length" class="kb-info__empty">Нет данных</div>
            <div v-else class="kb-info__rows">
                <div v-for="row in rows" :key="row.label" class="kb-info__row">
                    <span class="kb-info__label">{{ row.label }}</span>
                    <span class="kb-info__value">{{ row.value || '—' }}</span>
                </div>
            </div>
        </div>

        <template #footer>
            <div class="kb-info__footer">
                <Button color="primary" @click="emit('close')">Закрыть</Button>
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
        default: 'Информация',
    },
    rows: {
        type: Array,
        default: () => [],
    },
});

const emit = defineEmits(['close']);
</script>

<style scoped lang="scss">
.kb-info__title {
    margin: 0;
    font-size: 18px;
}

.kb-info__body {
    max-height: 52vh;
    overflow: auto;
}

.kb-info__rows {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.kb-info__row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 8px;
    border-bottom: 1px dashed color-mix(in srgb, var(--color-border) 72%, transparent);
}

.kb-info__label {
    color: var(--color-text-secondary);
}

.kb-info__value {
    text-align: right;
    max-width: 58%;
    overflow-wrap: anywhere;
}

.kb-info__empty {
    color: var(--color-text-secondary);
}

.kb-info__footer {
    display: flex;
    justify-content: flex-end;
}
</style>
