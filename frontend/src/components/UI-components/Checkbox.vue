<template>
    <div class="checkbox">
        <label class="checkbox-label">
            <input
                type="checkbox"
                :checked="modelValue"
                v-bind="$attrs"
                class="checkbox-input"
                @change="$emit('update:modelValue', $event.target.checked)"
            />
            <span v-if="label">{{ label }}</span>
        </label>
    </div>
</template>

<script setup>
defineProps({
    modelValue: Boolean,
    label: {
        type: String,
        default: '',
    },
});
defineEmits(['update:modelValue']);
</script>

<style lang="scss">
@use '@/assets/styles/components/ui-components/checkbox.scss' as *;
</style>
