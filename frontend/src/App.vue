<template>
    <div>
        <div class="theme-toggle-wrapper">
            <ThemeToggle />
        </div>
        <router-view />
        <Transition name="app-loader">
            <div v-if="isRouteLoading" class="app-loading-overlay" role="status" aria-live="polite">
                <span class="app-loading-overlay__spinner" aria-hidden="true" />
            </div>
        </Transition>
    </div>
</template>

<script setup>
import ThemeToggle from '@/components/ThemeToggle.vue';
import { useRouteLoadingState } from '@/stores/routeLoading';

const isRouteLoading = useRouteLoadingState();
</script>

<style lang="scss">
@use '@/assets/styles/app' as *;
</style>
