<template>
    <component v-bind="$attrs" :is="iconComponent" />
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue';

const props = defineProps({
    name: {
        type: String,
        required: true,
    },
});

const icons = import.meta.glob('@/components/icons/*.vue');

const iconComponent = computed(() => {
    const path = `/src/components/icons/Icon${props.name}.vue`;
    return icons[path] ? defineAsyncComponent(() => icons[path]()) : null;
});
</script>
