<template>
    <div class="input">
        <label v-if="label" class="input-label">
            {{ label }}
        </label>
        <input
            v-bind="attrs"
            class="input-field"
            :type="type"
            :value="modelValue"
            :placeholder="placeholder"
            @input="onInput"
        />
    </div>
</template>

<script setup>
import { useAttrs } from 'vue';

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
