<template>
    <section class="filters-panel">
        <button
            v-if="collapsible"
            class="filters-panel__toggle"
            type="button"
            @click="toggle"
        >
            {{ title }}
            <span :class="['filters-panel__icon', { 'is-open': modelValue }]">▼</span>
        </button>
        <p v-else class="filters-panel__title">
            {{ title }}
        </p>

        <div v-if="!collapsible || modelValue" class="filters-panel__content">
            <slot />
        </div>
    </section>
</template>

<script setup>
const { modelValue, title, collapsible } = defineProps({
    modelValue: { type: Boolean, default: true },
    title: { type: String, default: 'Фильтры' },
    collapsible: { type: Boolean, default: true },
});

const emit = defineEmits(['update:modelValue']);

function toggle() {
    emit('update:modelValue', !modelValue);
}
</script>

<style lang="scss">
@use '@/assets/styles/components/ui-components/filters-panel' as *;
</style>
