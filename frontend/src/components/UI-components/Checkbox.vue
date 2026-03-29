<template>
    <div class="checkbox">
        <label class="checkbox-label" :for="fieldId">
            <input
                :id="fieldId"
                type="checkbox"
                :checked="modelValue"
                v-bind="attrs"
                :name="fieldName"
                class="checkbox-input"
                @change="$emit('update:modelValue', $event.target.checked)"
            />
            <span v-if="label">{{ label }}</span>
        </label>
    </div>
</template>

<script setup>
import { computed, useAttrs } from 'vue';

defineOptions({ inheritAttrs: false });

defineProps({
    modelValue: Boolean,
    label: {
        type: String,
        default: '',
    },
});
defineEmits(['update:modelValue']);
const attrs = useAttrs();
const fieldUid = `checkbox-${Math.random().toString(36).slice(2, 9)}`;
const fieldId = computed(() => {
    const currentId = attrs.id;
    if (currentId !== undefined && currentId !== null && String(currentId).trim() !== '') {
        return String(currentId);
    }
    return fieldUid;
});
const fieldName = computed(() => {
    const currentName = attrs.name;
    if (currentName !== undefined && currentName !== null && String(currentName).trim() !== '') {
        return String(currentName);
    }
    return fieldId.value;
});
</script>

<style lang="scss">
@use '@/assets/styles/components/ui-components/checkbox.scss' as *;
</style>
