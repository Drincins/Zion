import { createRouter, createWebHistory } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { getAdminRouteMeta } from '@/router/adminNavigation';
import { KNOWLEDGE_BASE_VIEW_PERMISSIONS } from '@/accessPolicy';
import { isSuperAdminRole } from '@/utils/roles';

const routes = [
    { path: '/', name: 'user-login', component: () => import('@/pages/LoginUser.vue') },
    { path: '/login', name: 'login', component: () => import('@/pages/LoginPage.vue') },
    { path: '/time-tracking', name: 'time-tracking', component: () => import('@/pages/TimeTracking.vue') },
    {
        path: '/checklists/portal',
        name: 'checklist-portal',
        component: () => import('@/pages/ChecklistPortalPage.vue'),
    },
    {
        path: '/knowledge-base',
        name: 'knowledge-base',
        component: () => import('@/pages/KnowledgeBase/KnowledgeBasePage.vue'),
        meta: {
            permissions: KNOWLEDGE_BASE_VIEW_PERMISSIONS,
        },
    },
    {
        path: '/admin',
        component: () => import('@/layouts/AdminLayout.vue'),
        children: [
            {
                path: '',
                name: 'birthday',
                component: () => import('@/pages/AdminLayout/Birthday.vue'),
            },
            {
                path: 'fot',
                name: 'labor-fund',
                component: () => import('@/pages/AdminLayout/LaborFund.vue'),
                meta: getAdminRouteMeta('labor-fund'),
            },
            {
                path: 'staff',
                name: 'staff',
                component: () => import('@/pages/AdminLayout/Employees/EmployeesPage.vue'),
                meta: getAdminRouteMeta('staff'),
            },
            {
                path: 'trainings',
                name: 'trainings',
                component: () => import('@/pages/AdminLayout/Employees/TrainingManagementPage.vue'),
                meta: getAdminRouteMeta('trainings'),
            },
            {
                path: 'payroll-types',
                name: 'payroll-types',
                component: () => import('@/pages/AdminLayout/Employees/PayrollAdjustmentTypesPage.vue'),
                meta: getAdminRouteMeta('payroll-types'),
            },
            {
                path: 'permissions',
                name: 'permissions',
                component: () => import('@/pages/AdminLayout/Employees/AccessPermissionsPage.vue'),
                meta: getAdminRouteMeta('permissions'),
            },
            {
                path: 'positions',
                name: 'positions',
                component: () => import('@/pages/AdminLayout/Staff/PositionsPage.vue'),
                meta: getAdminRouteMeta('positions'),
            },
            {
                path: 'department',
                name: 'department',
                component: () => import('@/pages/AdminLayout/Staff/DepartmentsPage.vue'),
                meta: getAdminRouteMeta('department'),
            },
            {
                path: 'restaurants',
                name: 'restaurants',
                component: () => import('@/pages/AdminLayout/Staff/RestaurantsPage.vue'),
                meta: getAdminRouteMeta('restaurants'),
            },
            {
                path: 'employees',
                redirect: { name: 'staff' },
            },
            {
                path: 'employees/list',
                redirect: { name: 'staff' },
            },
            {
                path: 'employees/trainings',
                redirect: { name: 'trainings' },
            },
            {
                path: 'employees/payroll-types',
                redirect: { name: 'payroll-types' },
            },
            {
                path: 'employees/permissions',
                redirect: { name: 'permissions' },
            },
            {
                path: 'inventory',
                component: () => import('@/pages/AdminLayout/Inventory/InventoryLayout.vue'),
                meta: getAdminRouteMeta('inventory'),
                children: [
                    {
                        path: '',
                        name: 'inventory',
                        redirect: { name: 'inventory-catalog' },
                    },
                    {
                        path: 'groups',
                        name: 'inventory-groups',
                        component: () => import('@/pages/AdminLayout/Inventory/InventoryGroupsPage.vue'),
                        meta: getAdminRouteMeta('inventory-groups'),
                    },
                    {
                        path: 'catalog',
                        name: 'inventory-catalog',
                        component: () => import('@/pages/AdminLayout/Inventory/InventoryCatalogPage.vue'),
                        meta: getAdminRouteMeta('inventory-catalog'),
                    },
                    {
                        path: 'categories',
                        name: 'inventory-categories',
                        redirect: { name: 'inventory-groups' },
                    },
                    {
                        path: 'items',
                        name: 'inventory-items',
                        redirect: { name: 'inventory-catalog' },
                    },
                    {
                        path: 'operations',
                        name: 'inventory-operations',
                        redirect: { name: 'inventory-balance' },
                    },
                    {
                        path: 'records',
                        name: 'inventory-records',
                        redirect: { name: 'inventory-journal' },
                    },
                    {
                        path: 'journal',
                        name: 'inventory-journal',
                        component: () => import('@/pages/AdminLayout/Inventory/InventoryRecordsPage.vue'),
                        meta: getAdminRouteMeta('inventory-journal'),
                    },
                    {
                        path: 'tagged-items',
                        name: 'inventory-tagged-items',
                        redirect: { name: 'inventory-catalog' },
                    },
                    {
                        path: 'balance',
                        name: 'inventory-balance',
                        component: () => import('@/pages/AdminLayout/Inventory/InventoryBalancePage.vue'),
                        meta: getAdminRouteMeta('inventory-balance'),
                    },
                    {
                        path: 'settings',
                        name: 'inventory-settings',
                        component: () => import('@/pages/AdminLayout/Inventory/InventorySettingsPage.vue'),
                        meta: getAdminRouteMeta('inventory-settings'),
                    },
                ],
            },
            {
                path: 'control/checklists',
                name: 'control-checklists',
                component: () => import('@/pages/AdminLayout/Control/ChecklistsPage.vue'),
                meta: getAdminRouteMeta('control-checklists'),
            },
            {
                path: 'control/checklists/:id',
                name: 'control-checklists-manage',
                component: () => import('@/pages/AdminLayout/Control/ChecklistsManagePage.vue'),
                props: true,
                meta: getAdminRouteMeta('control-checklists'),
            },
            {
                path: 'activity',
                name: 'activity-log',
                component: () => import('@/pages/AdminLayout/ActivityLogPage.vue'),
                meta: getAdminRouteMeta('activity-log'),
            },
            {
                path: 'accounting',
                component: () => import('@/pages/AdminLayout/Accounting/AccountingLayout.vue'),
                meta: getAdminRouteMeta('accounting'),
                children: [
                    {
                        path: '',
                        name: 'accounting',
                        redirect: { name: 'accounting-invoices' },
                    },
                    {
                        path: 'invoices',
                        name: 'accounting-invoices',
                        component: () => import('@/pages/AdminLayout/Accounting/InvoicesPage.vue'),
                        meta: getAdminRouteMeta('accounting-invoices'),
                    },
                    {
                        path: 'advances',
                        name: 'accounting-advances',
                        component: () => import('@/pages/AdminLayout/Accounting/PayrollAdvancePage.vue'),
                        meta: getAdminRouteMeta('accounting-advances'),
                    },
                ],
            },
            {
                path: 'kpi',
                component: () => import('@/pages/AdminLayout/Kpi/KpiLayout.vue'),
                children: [
                    {
                        path: '',
                        redirect: { name: 'kpi-metrics' },
                    },
                    {
                        path: 'payouts',
                        name: 'kpi-payouts',
                        component: () => import('@/pages/AdminLayout/Kpi/KpiPayoutsPage.vue'),
                        meta: getAdminRouteMeta('kpi-payouts'),
                    },
                    {
                        path: 'metrics',
                        name: 'kpi-metrics',
                        component: () => import('@/pages/AdminLayout/Kpi/KpiMetricsPage.vue'),
                        meta: getAdminRouteMeta('kpi-metrics'),
                    },
                    {
                        path: 'plan-fact',
                        name: 'kpi-plan-fact',
                        component: () => import('@/pages/AdminLayout/Kpi/KpiPlanFactPage.vue'),
                        meta: getAdminRouteMeta('kpi-plan-fact'),
                    },
                    {
                        path: 'facts',
                        name: 'kpi-facts',
                        component: () => import('@/pages/AdminLayout/Kpi/KpiFactsPage.vue'),
                        meta: getAdminRouteMeta('kpi-facts'),
                    },
                    {
                        path: 'results',
                        name: 'kpi-results',
                        component: () => import('@/pages/AdminLayout/Kpi/KpiResultsPage.vue'),
                        meta: getAdminRouteMeta('kpi-plan-fact'),
                    },
                    {
                        path: 'settings',
                        redirect: { name: 'kpi-metrics' },
                    },
                ],
            },
            {
                path: 'kitchen',
                component: () => import('@/pages/AdminLayout/Kitchen/KitchenLayout.vue'),
                meta: getAdminRouteMeta('kitchen'),
                children: [
                    {
                        path: '',
                        name: 'kitchen-home',
                        component: () => import('@/pages/AdminLayout/Kitchen/KitchenDashboard.vue'),
                        meta: getAdminRouteMeta('kitchen-home'),
                    },
                    {
                        path: 'sales-report',
                        name: 'kitchen-sales-report',
                        component: () => import('@/pages/AdminLayout/Kitchen/KitchenSalesReport.vue'),
                        meta: getAdminRouteMeta('kitchen-sales-report'),
                    },
                    {
                        path: 'revenue-report',
                        name: 'kitchen-revenue-report',
                        component: () => import('@/pages/AdminLayout/Kitchen/KitchenRevenueReport.vue'),
                        meta: getAdminRouteMeta('kitchen-revenue-report'),
                    },
                    {
                        path: 'waiter-sales-report',
                        name: 'kitchen-waiter-sales-report',
                        redirect: { name: 'kitchen-sales-report' },
                    },
                    {
                        path: 'waiter-turnover-settings',
                        name: 'kitchen-waiter-turnover-settings',
                        redirect: { name: 'kitchen-settings-sales-accounting' },
                    },
                    {
                        path: 'settings',
                        component: () => import('@/pages/AdminLayout/Kitchen/KitchenSettingsPage.vue'),
                        meta: getAdminRouteMeta('kitchen-settings'),
                        children: [
                            {
                                path: 'nomenclature',
                                name: 'kitchen-settings-nomenclature',
                                component: () =>
                                    import('@/pages/AdminLayout/Kitchen/KitchenProductsDishes.vue'),
                                meta: getAdminRouteMeta('kitchen-settings-nomenclature'),
                            },
                            {
                                path: 'tables',
                                name: 'kitchen-settings-tables',
                                component: () => import('@/pages/AdminLayout/Kitchen/KitchenHallTablesPage.vue'),
                                meta: getAdminRouteMeta('kitchen-settings-tables'),
                            },
                            {
                                path: 'payment-types',
                                name: 'kitchen-settings-payment-types',
                                component: () =>
                                    import('@/pages/AdminLayout/Kitchen/KitchenPaymentMethodsPage.vue'),
                                meta: getAdminRouteMeta('kitchen-settings-payment-types'),
                            },
                            {
                                path: 'report-fields',
                                name: 'kitchen-settings-report-fields',
                                component: () =>
                                    import('@/pages/AdminLayout/Kitchen/KitchenSalesReportFieldsPage.vue'),
                                meta: getAdminRouteMeta('kitchen-settings-report-fields'),
                            },
                            {
                                path: 'sales-accounting',
                                name: 'kitchen-settings-sales-accounting',
                                component: () =>
                                    import('@/pages/AdminLayout/Kitchen/KitchenWaiterTurnoverSettingsPage.vue'),
                                meta: getAdminRouteMeta('kitchen-settings-sales-accounting'),
                            },
                            {
                                path: 'non-cash-limits',
                                name: 'kitchen-settings-non-cash-limits',
                                component: () =>
                                    import('@/pages/AdminLayout/Kitchen/KitchenNonCashLimitsPage.vue'),
                                meta: getAdminRouteMeta('kitchen-settings-non-cash-limits'),
                            },
                        ],
                    },
                    {
                        path: 'products-dishes',
                        name: 'kitchen-products-dishes',
                        redirect: { name: 'kitchen-settings-nomenclature' },
                    },
                    {
                        path: 'hall-tables',
                        name: 'kitchen-hall-tables',
                        redirect: { name: 'kitchen-settings-tables' },
                    },
                    {
                        path: 'payment-methods',
                        name: 'kitchen-payment-methods',
                        redirect: { name: 'kitchen-settings-payment-types' },
                    },
                    {
                        path: 'sales-locations',
                        name: 'kitchen-sales-locations',
                        redirect: { name: 'kitchen-settings-tables' },
                    },
                    {
                        path: 'non-cash-limits',
                        name: 'kitchen-non-cash-limits',
                        redirect: { name: 'kitchen-settings-non-cash-limits' },
                    },
                ],
            },
            { path: 'user', component: () => import('@/pages/UserInfo.vue') },
        ],
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior(to) {
        if (to.hash) {
            return { el: to.hash, behavior: 'smooth' };
        }
        return { top: 0 };
    },
});

function resolveAccessDeniedRedirect(to) {
    if (to.path.startsWith('/admin') && to.path !== '/admin/user') {
        return { path: '/admin/user' };
    }
    return { path: '/admin' };
}

router.beforeEach((to) => {
    const userStore = useUserStore();

    if (to.matched.some((record) => record.meta?.requiresSuperAdmin)) {
        if (!isSuperAdminRole(userStore.roleName)) {
            return resolveAccessDeniedRedirect(to);
        }
    }

    const isMissingAnyFrom = (codes) =>
        Array.isArray(codes) && codes.length > 0 && !userStore.hasAnyPermission(...codes);

    const hasForbiddenRoute = to.matched.some(
        (record) =>
            isMissingAnyFrom(record.meta?.permissions) || isMissingAnyFrom(record.meta?.sectionPermissions),
    );
    if (hasForbiddenRoute) {
        return resolveAccessDeniedRedirect(to);
    }

    return true;
});

export default router;
