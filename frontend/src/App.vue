<template>
    <div>
        <div class="theme-toggle-wrapper">
            <ThemeToggle />
        </div>
        <router-view />
    </div>
</template>

<script setup>
import ThemeToggle from '@/components/ThemeToggle.vue';
</script>

<style lang="scss">
@use '@/assets/styles/app' as *;
</style>
