<template>
    <div class="input">
        <label v-if="label" class="input-label" :for="fieldId">
            {{ label }}
        </label>
        <input
            v-bind="attrs"
            :id="fieldId"
            :name="fieldName"
            class="input-field"
            :type="type"
            :value="modelValue"
            :placeholder="placeholder"
            @input="onInput"
        />
    </div>
</template>

<script setup>
import { computed, useAttrs } from 'vue';

defineOptions({ inheritAttrs: false });

const props = defineProps({
    modelValue: {
        type: [String, Number],
        default: '',
    },
    label: {
        type: String,
        default: '',
    },
    type: {
        type: String,
        default: 'text',
    },
    placeholder: {
        type: String,
        default: '',
    },
});

const emit = defineEmits(['update:modelValue']);
const attrs = useAttrs();
const fallbackId = `input-${Math.random().toString(36).slice(2, 9)}`;
const fieldId = computed(() => {
    const currentId = attrs.id;
    if (currentId !== undefined && currentId !== null && String(currentId).trim() !== '') {
        return String(currentId);
    }
    return fallbackId;
});
const fieldName = computed(() => {
    const currentName = attrs.name;
    if (currentName !== undefined && currentName !== null && String(currentName).trim() !== '') {
        return String(currentName);
    }
    return fieldId.value;
});

function onInput(event) {
    let value = event.target.value;

    if (props.type === 'number') {
        value = value === '' ? '' : Number(value);
    }

    emit('update:modelValue', value);
}
</script>

<style lang="scss">
@use '@/assets/styles/components/ui-components/input.scss' as *;
</style>
