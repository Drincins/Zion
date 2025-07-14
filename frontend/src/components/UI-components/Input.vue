<template>
    <div class="input">
        <label 
            v-if="label"
            class="input-label"
        >
            {{ label }}
        </label>
        <input
            v-bind="$attrs"
            :class="['input-field']"
            :type="type"
            :value="modelValue"
            @input="$emit('update:modelValue', $event.target.value)"
        />
    </div>
</template>

<script setup>
defineProps({
    modelValue: String,
    label: String,
    type: {
        type: String,
        default: 'text',
    },
})
defineEmits(['update:modelValue'])
</script>

<style lang="scss">
@import '@/assets/styles/components/ui-components/input.scss';
</style>