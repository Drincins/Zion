<template>
    <div class="kitchen-settings-page">
        <section class="kitchen-settings-page__tabs">
            <button
                v-for="tab in visibleTabs"
                :key="tab.path"
                type="button"
                class="kitchen-settings-page__tab"
                :class="{ 'is-active': isTabActive(tab.path) }"
                @click="goToTab(tab.path)"
            >
                {{ tab.label }}
            </button>
        </section>

        <router-view />
    </div>
</template>

<script setup>
import { computed, watchEffect } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const allTabs = [
    {
        label: 'Номенклатура',
        path: '/admin/kitchen/settings/nomenclature',
        permissions: ['sales.dishes.view', 'sales.dishes.manage', 'iiko.view', 'iiko.manage'],
        sectionPermissions: ['sections.sales.settings.nomenclature'],
    },
    {
        label: 'Столы',
        path: '/admin/kitchen/settings/tables',
        permissions: ['sales.tables.view', 'sales.tables.manage', 'iiko.view', 'iiko.manage'],
        sectionPermissions: ['sections.sales.settings.tables'],
    },
    {
        label: 'Типы оплат',
        path: '/admin/kitchen/settings/payment-types',
        permissions: ['iiko.view', 'iiko.manage'],
        sectionPermissions: ['sections.sales.settings.payment_types'],
    },
    {
        label: 'Поля отчетов',
        path: '/admin/kitchen/settings/report-fields',
        permissions: ['iiko.view', 'iiko.manage'],
        sectionPermissions: ['sections.sales.settings.report_fields'],
    },
    {
        label: 'Настройки учета продаж',
        path: '/admin/kitchen/settings/sales-accounting',
        permissions: ['iiko.view', 'iiko.manage'],
        sectionPermissions: ['sections.sales.settings.sales_accounting'],
    },
    {
        label: 'Лимиты безнала',
        path: '/admin/kitchen/settings/non-cash-limits',
        permissions: ['iiko.view', 'iiko.manage'],
        sectionPermissions: ['sections.sales.settings.non_cash_limits'],
    },
];

const visibleTabs = computed(() =>
    allTabs.filter(
        (tab) =>
            userStore.hasAnyPermission(...(tab.permissions || [])) &&
            userStore.hasAnyPermission(...(tab.sectionPermissions || [])),
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
@use '@/assets/styles/pages/kitchen-settings' as *;
</style>
