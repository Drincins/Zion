<template>
    <button
        :type="type"
        class="button"
        :class="[
            `button--${color}`,
            `button--${size}`,
            {
                'is-block': block,
                'is-loading': loading
            }
        ]"
        :disabled="disabled || loading"
        :aria-busy="loading || undefined"
        v-bind="$attrs"
    >
        <slot />
    </button>
</template>

<script setup>
defineProps({
    type: {
        type: String,
        default: 'button'
    },
    disabled: {
        type: Boolean,
        default: false
    },
    color: {
        type: String,
        default: 'primary',
        validator: v => ['primary','secondary','success','danger','outline','ghost'].includes(v)
    },
    size: {
        type: String,
        default: 'md',
        validator: v => ['sm','md','lg'].includes(v)
    },
    block: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
});
</script>

<style lang="scss">
@use '@/assets/styles/components/ui-components/button.scss' as *;
</style>
