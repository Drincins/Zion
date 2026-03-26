<template>
    <section class="inventory-settings__tabs" role="tablist" aria-label="Технические настройки склада">
        <button
            v-for="tab in visibleTabs"
            :key="tab.path"
            type="button"
            class="inventory-settings__tab"
            :class="{ 'is-active': isTabActive(tab.path) }"
            @click="goToTab(tab.path)"
        >
            {{ tab.label }}
        </button>
    </section>
</template>

<script setup>
import { computed, watchEffect } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
    INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS,
    SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS,
} from '@/accessPolicy';
import { useUserStore } from '@/stores/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const allTabs = [
    {
        label: 'Справочники',
        path: '/admin/inventory/settings',
        permissions: INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS,
    },
    {
        label: 'Группы товаров',
        path: '/admin/inventory/groups',
        permissions: INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS,
    },
];

const visibleTabs = computed(() =>
    allTabs.filter(
        (tab) =>
            userStore.hasAnyPermission(...(tab.permissions || []))
            && userStore.hasAnyPermission(...(tab.sectionPermissions || [])),
    ),
);

function isTabActive(path) {
    return route.path === path || route.path.startsWith(`${path}/`);
}

function goToTab(path) {
    if (route.path === path) {
        return;
    }
    router.push({ path });
}

watchEffect(() => {
    const tabs = visibleTabs.value;
    if (!tabs.length) {
        return;
    }
    const isCurrentAllowed = tabs.some((tab) => isTabActive(tab.path));
    if (!isCurrentAllowed) {
        router.replace({ path: tabs[0].path });
    }
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-settings' as *;
</style>
