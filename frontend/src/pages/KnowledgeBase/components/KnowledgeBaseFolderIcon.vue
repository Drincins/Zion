<template>
    <svg viewBox="0 0 64 48" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path
            d="M4 13a8 8 0 0 1 8-8h14.7a6 6 0 0 1 4.242 1.757l3.3 3.3A6 6 0 0 0 38.49 12H52a8 8 0 0 1 8 8v2H4v-9z"
            :fill="tabColor"
        />
        <rect x="4" y="16" width="56" height="28" rx="8" :fill="mainColor" />
        <path
            d="M7 22h50v15a7 7 0 0 1-7 7H14a7 7 0 0 1-7-7V22z"
            fill="color-mix(in srgb, var(--color-text) 8%, transparent)"
        />
    </svg>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
    accent: {
        type: String,
        default: 'var(--color-primary)',
    },
});

const mainColor = computed(() => props.accent || 'var(--color-primary)');
const tabColor = computed(() => props.accent || 'var(--color-primary)');
</script>
