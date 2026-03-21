import {
    ACCESS_CONTROL_VIEW_PERMISSIONS,
    ACCOUNTING_ADVANCES_VIEW_PERMISSIONS,
    ACCOUNTING_INVOICES_VIEW_PERMISSIONS,
    ACCOUNTING_MODULE_VIEW_PERMISSIONS,
    IIKO_VIEW_PERMISSIONS,
    INVENTORY_MODULE_VIEW_PERMISSIONS,
    INVENTORY_BALANCE_VIEW_PERMISSIONS,
    INVENTORY_MOVEMENTS_VIEW_PERMISSIONS,
    INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS,
    LABOR_SUMMARY_VIEW_PERMISSIONS,
    KNOWLEDGE_BASE_VIEW_PERMISSIONS,
    PAYROLL_TYPES_VIEW_PERMISSIONS,
    POSITIONS_VIEW_PERMISSIONS,
    RESTAURANTS_VIEW_PERMISSIONS,
    SALES_DISHES_VIEW_PERMISSIONS,
    SALES_MODULE_VIEW_PERMISSIONS,
    SALES_REPORT_MONEY_VIEW_PERMISSIONS,
    SALES_REPORT_VIEW_PERMISSIONS,
    SALES_SETTINGS_VIEW_PERMISSIONS,
    SALES_TABLES_VIEW_PERMISSIONS,
    SECTION_ACCOUNTING_ADVANCES_PERMISSIONS,
    SECTION_ACCOUNTING_INVOICES_PERMISSIONS,
    SECTION_ACTIVITY_LOG_PERMISSIONS,
    SECTION_CONTROL_CHECKLISTS_PERMISSIONS,
    SECTION_INVENTORY_MOVEMENTS_PERMISSIONS,
    SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS,
    SECTION_KPI_FACTS_PERMISSIONS,
    SECTION_KPI_METRICS_PERMISSIONS,
    SECTION_KPI_PAYOUTS_PERMISSIONS,
    SECTION_KPI_PLAN_FACT_PERMISSIONS,
    SECTION_LABOR_FUND_PERMISSIONS,
    SECTION_SALES_HOME_PERMISSIONS,
    SECTION_SALES_REPORT_PERMISSIONS,
    SECTION_SALES_REVENUE_PERMISSIONS,
    SECTION_SALES_SETTINGS_NON_CASH_LIMITS_PERMISSIONS,
    SECTION_SALES_SETTINGS_NOMENCLATURE_PERMISSIONS,
    SECTION_SALES_SETTINGS_PAYMENT_TYPES_PERMISSIONS,
    SECTION_SALES_SETTINGS_REPORT_FIELDS_PERMISSIONS,
    SECTION_SALES_SETTINGS_SALES_ACCOUNTING_PERMISSIONS,
    SECTION_SALES_SETTINGS_PERMISSIONS,
    SECTION_SALES_SETTINGS_TABLES_PERMISSIONS,
    SECTION_SETTINGS_PAYROLL_TYPES_PERMISSIONS,
    SECTION_SETTINGS_RESTAURANTS_PERMISSIONS,
    SECTION_SETTINGS_SUBDIVISIONS_PERMISSIONS,
    SECTION_SETTINGS_TRAININGS_PERMISSIONS,
    SECTION_STAFF_ACCESS_PERMISSIONS,
    SECTION_STAFF_EMPLOYEES_PERMISSIONS,
    SECTION_STAFF_POSITIONS_PERMISSIONS,
    SETTINGS_SUBDIVISIONS_VIEW_PERMISSIONS,
    STAFF_VIEW_PERMISSIONS,
    TRAININGS_VIEW_PERMISSIONS,
} from '@/accessPolicy';

export const ADMIN_ROUTE_ACCESS = {
    'labor-fund': {
        permissions: LABOR_SUMMARY_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_LABOR_FUND_PERMISSIONS,
    },
    staff: {
        permissions: STAFF_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_STAFF_EMPLOYEES_PERMISSIONS,
    },
    trainings: {
        permissions: TRAININGS_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SETTINGS_TRAININGS_PERMISSIONS,
    },
    'payroll-types': {
        permissions: PAYROLL_TYPES_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SETTINGS_PAYROLL_TYPES_PERMISSIONS,
    },
    permissions: {
        permissions: ACCESS_CONTROL_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_STAFF_ACCESS_PERMISSIONS,
    },
    positions: {
        permissions: POSITIONS_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_STAFF_POSITIONS_PERMISSIONS,
    },
    department: {
        permissions: SETTINGS_SUBDIVISIONS_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SETTINGS_SUBDIVISIONS_PERMISSIONS,
    },
    restaurants: {
        permissions: RESTAURANTS_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SETTINGS_RESTAURANTS_PERMISSIONS,
    },
    inventory: {
        permissions: INVENTORY_MODULE_VIEW_PERMISSIONS,
    },
    'inventory-groups': {
        permissions: INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS,
    },
    'inventory-catalog': {
        permissions: INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS,
    },
    'inventory-items': {
        permissions: INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS,
    },
    'inventory-records': {
        permissions: INVENTORY_MOVEMENTS_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_MOVEMENTS_PERMISSIONS,
    },
    'inventory-operations': {
        permissions: INVENTORY_MOVEMENTS_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_MOVEMENTS_PERMISSIONS,
    },
    'inventory-journal': {
        permissions: INVENTORY_MOVEMENTS_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_MOVEMENTS_PERMISSIONS,
    },
    'inventory-balance': {
        permissions: INVENTORY_BALANCE_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS,
    },
    'inventory-settings': {
        permissions: INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS,
    },
    'control-checklists': {
        sectionPermissions: SECTION_CONTROL_CHECKLISTS_PERMISSIONS,
    },
    'activity-log': {
        requiresSuperAdmin: true,
        sectionPermissions: SECTION_ACTIVITY_LOG_PERMISSIONS,
    },
    accounting: {
        permissions: ACCOUNTING_MODULE_VIEW_PERMISSIONS,
    },
    'accounting-invoices': {
        permissions: ACCOUNTING_INVOICES_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_ACCOUNTING_INVOICES_PERMISSIONS,
    },
    'accounting-advances': {
        permissions: ACCOUNTING_ADVANCES_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_ACCOUNTING_ADVANCES_PERMISSIONS,
    },
    'knowledge-base': {
        permissions: KNOWLEDGE_BASE_VIEW_PERMISSIONS,
    },
    'kpi-payouts': {
        sectionPermissions: SECTION_KPI_PAYOUTS_PERMISSIONS,
    },
    'kpi-metrics': {
        sectionPermissions: SECTION_KPI_METRICS_PERMISSIONS,
    },
    'kpi-plan-fact': {
        sectionPermissions: SECTION_KPI_PLAN_FACT_PERMISSIONS,
    },
    'kpi-facts': {
        sectionPermissions: SECTION_KPI_FACTS_PERMISSIONS,
    },
    kitchen: {
        permissions: SALES_MODULE_VIEW_PERMISSIONS,
    },
    'kitchen-home': {
        permissions: SALES_MODULE_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_HOME_PERMISSIONS,
    },
    'kitchen-sales-report': {
        permissions: SALES_REPORT_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_REPORT_PERMISSIONS,
    },
    'kitchen-revenue-report': {
        permissions: SALES_REPORT_MONEY_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_REVENUE_PERMISSIONS,
    },
    'kitchen-settings': {
        permissions: SALES_SETTINGS_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_SETTINGS_PERMISSIONS,
    },
    'kitchen-settings-nomenclature': {
        permissions: SALES_DISHES_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_SETTINGS_NOMENCLATURE_PERMISSIONS,
    },
    'kitchen-settings-tables': {
        permissions: SALES_TABLES_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_SETTINGS_TABLES_PERMISSIONS,
    },
    'kitchen-settings-payment-types': {
        permissions: IIKO_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_SETTINGS_PAYMENT_TYPES_PERMISSIONS,
    },
    'kitchen-settings-report-fields': {
        permissions: IIKO_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_SETTINGS_REPORT_FIELDS_PERMISSIONS,
    },
    'kitchen-settings-sales-accounting': {
        permissions: IIKO_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_SETTINGS_SALES_ACCOUNTING_PERMISSIONS,
    },
    'kitchen-settings-non-cash-limits': {
        permissions: IIKO_VIEW_PERMISSIONS,
        sectionPermissions: SECTION_SALES_SETTINGS_NON_CASH_LIMITS_PERMISSIONS,
    },
};

export function getAdminRouteMeta(key, extraMeta = {}) {
    return {
        ...(ADMIN_ROUTE_ACCESS[key] || {}),
        ...extraMeta,
    };
}

function createMenuItem({ key, label, to, accessKey, openInNew = false }) {
    return {
        key,
        label,
        to,
        openInNew,
        ...getAdminRouteMeta(accessKey),
    };
}

export const SIDEBAR_MENU_GROUPS = [
    {
        key: 'staff',
        label: 'Персонал',
        icon: '👥',
        items: [
            createMenuItem({ key: 'employees', label: 'Сотрудники', to: { name: 'staff' }, accessKey: 'staff' }),
            createMenuItem({ key: 'positions', label: 'Должности', to: { name: 'positions' }, accessKey: 'positions' }),
            createMenuItem({ key: 'permissions', label: 'Права доступа', to: { name: 'permissions' }, accessKey: 'permissions' }),
        ],
    },
    {
        key: 'settings',
        label: 'Настройки',
        icon: '⚙️',
        items: [
            createMenuItem({ key: 'trainings', label: 'Обучения', to: { name: 'trainings' }, accessKey: 'trainings' }),
            createMenuItem({
                key: 'payroll-types',
                label: 'Виды выплат',
                to: { name: 'payroll-types' },
                accessKey: 'payroll-types',
            }),
            createMenuItem({
                key: 'subdivisions',
                label: 'Подразделения',
                to: { name: 'department' },
                accessKey: 'department',
            }),
            createMenuItem({
                key: 'restaurants',
                label: 'Рестораны',
                to: { name: 'restaurants' },
                accessKey: 'restaurants',
            }),
        ],
    },
    {
        key: 'inventory',
        label: 'Склад',
        icon: '📦',
        items: [
            createMenuItem({
                key: 'catalog',
                label: 'Каталог товаров',
                to: { name: 'inventory-catalog' },
                accessKey: 'inventory-catalog',
            }),
            createMenuItem({
                key: 'balance',
                label: 'Баланс ресторана',
                to: { name: 'inventory-balance' },
                accessKey: 'inventory-balance',
            }),
            createMenuItem({
                key: 'settings',
                label: 'Настройки',
                to: { name: 'inventory-settings' },
                accessKey: 'inventory-settings',
            }),
        ],
    },
    {
        key: 'control',
        label: 'Контроль',
        icon: '✅',
        items: [
            createMenuItem({
                key: 'checklists',
                label: 'Чек-листы',
                to: { name: 'control-checklists' },
                accessKey: 'control-checklists',
            }),
            createMenuItem({
                key: 'checklists-portal',
                label: 'Пройти чек-лист',
                to: { name: 'checklist-portal' },
                accessKey: 'control-checklists',
                openInNew: true,
            }),
        ],
    },
    {
        key: 'accounting',
        label: 'Бухгалтерия',
        icon: '💼',
        items: [
            createMenuItem({
                key: 'invoices',
                label: 'Счета',
                to: { name: 'accounting-invoices' },
                accessKey: 'accounting-invoices',
            }),
            createMenuItem({
                key: 'advances',
                label: 'Ведомости',
                to: { name: 'accounting-advances' },
                accessKey: 'accounting-advances',
            }),
        ],
    },
    {
        key: 'knowledge-base',
        label: 'База знаний',
        icon: '🗂️',
        directTo: { name: 'knowledge-base' },
        items: [
            createMenuItem({
                key: 'knowledge-base-home',
                label: 'Файлы',
                to: { name: 'knowledge-base' },
                accessKey: 'knowledge-base',
            }),
        ],
    },
    {
        key: 'kpi',
        label: 'KPI',
        icon: '📈',
        items: [
            createMenuItem({
                key: 'kpi-metrics',
                label: 'Показатели KPI',
                to: { name: 'kpi-metrics' },
                accessKey: 'kpi-metrics',
            }),
            createMenuItem({
                key: 'kpi-plan-fact',
                label: 'Результаты',
                to: { name: 'kpi-plan-fact' },
                accessKey: 'kpi-plan-fact',
            }),
            createMenuItem({
                key: 'kpi-facts',
                label: 'Факт KPI',
                to: { name: 'kpi-facts' },
                accessKey: 'kpi-facts',
            }),
            createMenuItem({
                key: 'kpi-payouts',
                label: 'Выплаты KPI',
                to: { name: 'kpi-payouts' },
                accessKey: 'kpi-payouts',
            }),
        ],
    },
    {
        key: 'kitchen',
        label: 'Продажи',
        icon: '🧾',
        items: [
            createMenuItem({
                key: 'sales-report',
                label: 'Продажи',
                to: { name: 'kitchen-sales-report' },
                accessKey: 'kitchen-sales-report',
            }),
            createMenuItem({
                key: 'revenue-report',
                label: 'Выручка',
                to: { name: 'kitchen-revenue-report' },
                accessKey: 'kitchen-revenue-report',
            }),
            createMenuItem({
                key: 'settings',
                label: 'Настройки',
                to: { path: '/admin/kitchen/settings' },
                accessKey: 'kitchen-settings',
            }),
        ],
    },
    {
        key: 'dashboard',
        label: 'Дашборд',
        icon: '📊',
        items: [
            createMenuItem({
                key: 'labor-fund',
                label: 'Фонд оплаты труда',
                to: { name: 'labor-fund' },
                accessKey: 'labor-fund',
            }),
        ],
    },
    {
        key: 'activity',
        label: 'Журнал',
        icon: '🧾',
        requiresSuperAdmin: true,
        items: [
            createMenuItem({
                key: 'activity-log',
                label: 'Действия',
                to: { name: 'activity-log' },
                accessKey: 'activity-log',
            }),
        ],
    },
];
