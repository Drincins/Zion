const unique = (...groups) => Array.from(new Set(groups.flat()));

export const SYSTEM_ADMIN_PERMISSION = 'system.admin';
export const PAYROLL_EXPORT_PERMISSION = 'payroll.export';
export const PAYROLL_MANAGE_PERMISSION = 'payroll.manage';
export const TIMESHEET_EXPORT_PERMISSION = 'timesheet.export';
export const STAFF_EMPLOYEES_EXPORT_PERMISSION = 'staff_employees.export';

export const STAFF_VIEW_PERMISSIONS = [
    'staff.view_sensitive',
    'staff.manage_subordinates',
    'staff.manage_all',
    'staff_employees.view',
    'employees_card.view'
];

export const POSITIONS_VIEW_PERMISSIONS = [
    'positions.manage',
    'positions.edit',
    'positions.rate.manage',
    'positions.change_orders.manage'
];
export const POSITIONS_CHANGE_ORDERS_MANAGE_PERMISSIONS = [
    'positions.change_orders.manage',
    SYSTEM_ADMIN_PERMISSION
];

export const STAFF_VIEW_WITH_SYSTEM_PERMISSIONS = unique(
    STAFF_VIEW_PERMISSIONS,
    [SYSTEM_ADMIN_PERMISSION]
);

export const STAFF_MANAGE_PERMISSIONS = [
    'staff.manage_all',
    'staff.manage_subordinates',
    'staff_employees.manage',
    'employees_card.manage',
    SYSTEM_ADMIN_PERMISSION
];

export const STAFF_EDIT_ROLES_PERMISSIONS = ['staff.roles.assign', 'roles.manage', SYSTEM_ADMIN_PERMISSION];
export const STAFF_EDIT_RATES_PERMISSIONS = ['staff.rate.manage', 'staff.manage_all', SYSTEM_ADMIN_PERMISSION];
export const STAFF_CREATE_PERMISSIONS = ['users.manage', 'staff.manage_all', SYSTEM_ADMIN_PERMISSION];
export const STAFF_IIKO_SYNC_PERMISSIONS = ['staff_employees.iiko_sync', 'iiko.manage', SYSTEM_ADMIN_PERMISSION];
export const STAFF_AUTH_CREDENTIALS_VIEW_PERMISSIONS = ['users.manage', 'staff.manage_all', SYSTEM_ADMIN_PERMISSION];
export const STAFF_USER_PERMISSIONS_MANAGE_PERMISSIONS = ['roles.manage', SYSTEM_ADMIN_PERMISSION];
export const STAFF_LOAD_ROLES_PERMISSIONS = ['roles.manage', 'staff.roles.assign', SYSTEM_ADMIN_PERMISSION];
export const STAFF_LOAD_RESTAURANTS_PERMISSIONS = [
    'restaurants.manage',
    'restaurants.view',
    'staff.employee_orders.manage',
    'staff_portal.access',
    SYSTEM_ADMIN_PERMISSION
];
export const STAFF_LOAD_COMPANIES_PERMISSIONS = ['companies.manage', 'companies.view', SYSTEM_ADMIN_PERMISSION];
export const STAFF_LOAD_POSITIONS_PERMISSIONS = unique(
    POSITIONS_VIEW_PERMISSIONS,
    ['staff.employee_orders.manage'],
    STAFF_VIEW_PERMISSIONS,
    STAFF_MANAGE_PERMISSIONS,
    [SYSTEM_ADMIN_PERMISSION]
);
export const STAFF_EMPLOYEE_ORDERS_MANAGE_PERMISSIONS = [
    'staff.employee_orders.manage',
    SYSTEM_ADMIN_PERMISSION
];
export const STAFF_MEDICAL_CHECKS_VIEW_PERMISSIONS = [
    'medical_checks.view',
    'medical_checks.manage',
    'staff.manage_all',
    SYSTEM_ADMIN_PERMISSION
];

export const STAFF_CIS_DOCUMENTS_VIEW_PERMISSIONS = [
    'cis_documents.view',
    'cis_documents.manage',
    'staff.manage_all',
    SYSTEM_ADMIN_PERMISSION
];
export const STAFF_DOCUMENTS_VIEW_PERMISSIONS = unique(
    STAFF_MEDICAL_CHECKS_VIEW_PERMISSIONS,
    STAFF_CIS_DOCUMENTS_VIEW_PERMISSIONS
);
export const STAFF_MEDICAL_CHECKS_MANAGE_PERMISSIONS = ['medical_checks.manage', SYSTEM_ADMIN_PERMISSION];
export const STAFF_CIS_DOCUMENTS_MANAGE_PERMISSIONS = ['cis_documents.manage', SYSTEM_ADMIN_PERMISSION];
export const STAFF_CHANGES_VIEW_PERMISSIONS = [
    'employee_changes.view',
    'employee_changes.manage',
    'employee_changes.delete',
    SYSTEM_ADMIN_PERMISSION
];
export const STAFF_RESTORE_PERMISSIONS = ['staff_employees.restore', SYSTEM_ADMIN_PERMISSION];

export const ACCESS_CONTROL_VIEW_PERMISSIONS = [
    'roles.manage',
    'positions.manage',
    'positions.change_orders.manage',
    'access_control.read',
    'access_control.manage'
];
export const TRAININGS_VIEW_PERMISSIONS = ['training.view', 'training.manage'];
export const TRAININGS_MANAGE_PERMISSIONS = ['training.manage'];
export const PAYROLL_TYPES_VIEW_PERMISSIONS = ['payroll.view', PAYROLL_MANAGE_PERMISSION];
export const SETTINGS_SUBDIVISIONS_VIEW_PERMISSIONS = ['positions.manage'];

export const RESTAURANTS_VIEW_PERMISSIONS = [
    'restaurants.manage',
    'restaurants.view',
    'restaurants.settings.view',
    'restaurants.settings.manage'
];

export const INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS = [
    'inventory.view',
    'inventory.manage',
    'inventory.nomenclature.view',
    'inventory.nomenclature.manage',
    'inventory.nomenclature.create',
    'inventory.nomenclature.edit',
    'inventory.nomenclature.delete'
];

export const INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS = [
    'inventory.manage',
    'inventory.nomenclature.manage',
    'inventory.nomenclature.create'
];

export const INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS = [
    'inventory.manage',
    'inventory.nomenclature.manage',
    'inventory.nomenclature.edit'
];

export const INVENTORY_NOMENCLATURE_DELETE_PERMISSIONS = [
    'inventory.manage',
    'inventory.nomenclature.manage',
    'inventory.nomenclature.delete'
];

export const INVENTORY_MOVEMENTS_VIEW_PERMISSIONS = [
    'inventory.view',
    'inventory.manage',
    'inventory.movements.view',
    'inventory.movements.manage',
    'inventory.movements.create',
    'inventory.movements.edit',
    'inventory.movements.delete'
];

export const INVENTORY_MOVEMENTS_CREATE_PERMISSIONS = [
    'inventory.manage',
    'inventory.movements.manage',
    'inventory.movements.create'
];

export const INVENTORY_MOVEMENTS_EDIT_PERMISSIONS = [
    'inventory.manage',
    'inventory.movements.manage',
    'inventory.movements.edit'
];

export const INVENTORY_MOVEMENTS_DELETE_PERMISSIONS = [
    'inventory.manage',
    'inventory.movements.manage',
    'inventory.movements.delete'
];

export const INVENTORY_BALANCE_VIEW_PERMISSIONS = [
    'inventory.view',
    'inventory.manage',
    'inventory.balance.view'
];

export const INVENTORY_MODULE_VIEW_PERMISSIONS = unique(
    INVENTORY_NOMENCLATURE_VIEW_PERMISSIONS,
    INVENTORY_MOVEMENTS_VIEW_PERMISSIONS,
    INVENTORY_BALANCE_VIEW_PERMISSIONS
);

export const ACCOUNTING_INVOICES_VIEW_PERMISSIONS = [
    'accounting.invoices.view',
    'accounting.invoices.create',
    'accounting.invoices.edit',
    'accounting.invoices.status'
];

export const ACCOUNTING_ADVANCES_VIEW_PERMISSIONS = [
    'payroll.view',
    PAYROLL_MANAGE_PERMISSION,
    'payroll.advance.view',
    'payroll.advance.create',
    'payroll.advance.edit',
    'payroll.advance.status.review',
    'payroll.advance.status.confirm',
    'payroll.advance.status.ready',
    'payroll.advance.status.all',
    'payroll.advance.download',
    'payroll.advance.post',
    'payroll.advance.delete'
];

export const ACCOUNTING_MODULE_VIEW_PERMISSIONS = unique(
    ACCOUNTING_INVOICES_VIEW_PERMISSIONS,
    ACCOUNTING_ADVANCES_VIEW_PERMISSIONS
);

export const KNOWLEDGE_BASE_VIEW_PERMISSIONS = [
    'knowledge_base.section'
];
export const KNOWLEDGE_BASE_MANAGE_PERMISSIONS = ['knowledge_base.section'];
export const KNOWLEDGE_BASE_UPLOAD_PERMISSIONS = ['knowledge_base.section'];

export const LABOR_SUMMARY_VIEW_PERMISSIONS = ['labor.summary.dashboard.view', 'labor.summary.view'];

export const SALES_REPORT_VIEW_PERMISSIONS = [
    'sales.report.view_qty',
    'sales.report.view_money',
    'iiko.view',
    'iiko.manage'
];

export const SALES_REPORT_MONEY_VIEW_PERMISSIONS = ['sales.report.view_money', 'iiko.view', 'iiko.manage'];
export const SALES_DISHES_VIEW_PERMISSIONS = ['sales.dishes.view', 'sales.dishes.manage', 'iiko.view', 'iiko.manage'];
export const SALES_TABLES_VIEW_PERMISSIONS = ['sales.tables.view', 'sales.tables.manage', 'iiko.view', 'iiko.manage'];
export const IIKO_VIEW_PERMISSIONS = ['iiko.view', 'iiko.manage'];

export const SALES_SETTINGS_VIEW_PERMISSIONS = unique(
    SALES_DISHES_VIEW_PERMISSIONS,
    SALES_TABLES_VIEW_PERMISSIONS,
    IIKO_VIEW_PERMISSIONS
);

export const SALES_MODULE_VIEW_PERMISSIONS = unique(
    SALES_REPORT_VIEW_PERMISSIONS,
    SALES_SETTINGS_VIEW_PERMISSIONS
);

export const SECTION_STAFF_EMPLOYEES_PERMISSIONS = ['sections.staff.employees'];
export const SECTION_STAFF_POSITIONS_PERMISSIONS = ['sections.staff.positions'];
export const SECTION_STAFF_ACCESS_PERMISSIONS = ['sections.staff.permissions'];
export const SECTION_SETTINGS_TRAININGS_PERMISSIONS = ['sections.settings.trainings'];
export const SECTION_SETTINGS_PAYROLL_TYPES_PERMISSIONS = ['sections.settings.payroll_types'];
export const SECTION_SETTINGS_SUBDIVISIONS_PERMISSIONS = ['sections.settings.subdivisions'];
export const SECTION_SETTINGS_RESTAURANTS_PERMISSIONS = ['sections.settings.restaurants'];
export const SECTION_INVENTORY_NOMENCLATURE_PERMISSIONS = ['sections.inventory.nomenclature'];
export const SECTION_INVENTORY_MOVEMENTS_PERMISSIONS = ['sections.inventory.movements'];
export const SECTION_INVENTORY_TAGGED_ITEMS_PERMISSIONS = ['sections.inventory.tagged_items'];
export const SECTION_CONTROL_CHECKLISTS_PERMISSIONS = ['sections.control.checklists'];
export const SECTION_ACCOUNTING_INVOICES_PERMISSIONS = ['sections.accounting.invoices'];
export const SECTION_ACCOUNTING_ADVANCES_PERMISSIONS = ['sections.accounting.advances'];
export const SECTION_KPI_METRICS_PERMISSIONS = ['sections.kpi.metrics'];
export const SECTION_KPI_PLAN_FACT_PERMISSIONS = ['sections.kpi.plan_fact'];
export const SECTION_KPI_FACTS_PERMISSIONS = ['sections.kpi.facts'];
export const SECTION_KPI_PAYOUTS_PERMISSIONS = ['sections.kpi.payouts'];
export const SECTION_SALES_REPORT_PERMISSIONS = ['sections.sales.report'];
export const SECTION_SALES_REVENUE_PERMISSIONS = ['sections.sales.revenue'];
export const SECTION_SALES_SETTINGS_PERMISSIONS = ['sections.sales.settings'];
export const SECTION_SALES_SETTINGS_NOMENCLATURE_PERMISSIONS = ['sections.sales.settings.nomenclature'];
export const SECTION_SALES_SETTINGS_TABLES_PERMISSIONS = ['sections.sales.settings.tables'];
export const SECTION_SALES_SETTINGS_PAYMENT_TYPES_PERMISSIONS = ['sections.sales.settings.payment_types'];
export const SECTION_SALES_SETTINGS_REPORT_FIELDS_PERMISSIONS = ['sections.sales.settings.report_fields'];
export const SECTION_SALES_SETTINGS_SALES_ACCOUNTING_PERMISSIONS = ['sections.sales.settings.sales_accounting'];
export const SECTION_SALES_SETTINGS_NON_CASH_LIMITS_PERMISSIONS = ['sections.sales.settings.non_cash_limits'];
export const SECTION_LABOR_FUND_PERMISSIONS = ['sections.dashboard.labor_fund'];
export const SECTION_ACTIVITY_LOG_PERMISSIONS = ['sections.activity.log'];

export const SECTION_SALES_HOME_PERMISSIONS = unique(
    SECTION_SALES_REPORT_PERMISSIONS,
    SECTION_SALES_REVENUE_PERMISSIONS,
    SECTION_SALES_SETTINGS_PERMISSIONS
);
