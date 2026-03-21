const STORAGE_KEY = 'kitchen_sales_report_field_settings_v1';
const UPDATE_EVENT = 'kitchen-sales-report-field-settings-updated';

const FILTER_FIELDS = [
    { value: 'dish_group', label: 'Группа меню' },
    { value: 'dish_category', label: 'Категория меню' },
    { value: 'dish_name', label: 'Позиция' },
    { value: 'payment_type', label: 'Тип оплаты' },
    { value: 'waiter_name', label: 'Сотрудник' },
    { value: 'restaurant_name', label: 'Ресторан' },
    { value: 'hall_name', label: 'Зал' },
    { value: 'department', label: 'Подразделение' },
    { value: 'table', label: 'Стол' },
];

const DIMENSION_FIELDS = [
    { key: 'restaurant_name', label: 'Ресторан' },
    { key: 'open_date', label: 'Дата продажи' },
    { key: 'department', label: 'Подразделение' },
    { key: 'hall_name', label: 'Зал' },
    { key: 'zone_name', label: 'Зона' },
    { key: 'table_num', label: 'Стол' },
    { key: 'dish_group', label: 'Группа меню' },
    { key: 'dish_category', label: 'Категория меню' },
    { key: 'dish_name', label: 'Позиция' },
    { key: 'dish_code', label: 'Код позиции' },
    { key: 'payment_type', label: 'Тип оплаты' },
    { key: 'employee_name', label: 'Сотрудник' },
    { key: 'auth_user_name', label: 'Автор позиции' },
    { key: 'is_deleted', label: 'Удалено' },
];

const METRIC_FIELDS = [
    { key: 'items_count', label: 'Позиции', format: 'number' },
    { key: 'qty', label: 'Количество', format: 'number' },
    { key: 'kitchen_load_qty', label: 'Нагрузка кухни', format: 'number' },
    { key: 'hall_load_qty', label: 'Нагрузка зала', format: 'number' },
    { key: 'sum', label: 'Продажи, руб', format: 'money' },
    { key: 'discount_sum', label: 'Скидки, руб', format: 'money' },
];

function buildEnabledMap(keys) {
    const map = {};
    for (const key of keys) {
        map[key] = true;
    }
    return map;
}

function collectKeys(items, keyName) {
    return items.map((item) => item[keyName]).filter(Boolean);
}

function normalizeSection(rawSection, keys) {
    const enabled = buildEnabledMap(keys);
    if (!rawSection || typeof rawSection !== 'object') {
        return enabled;
    }
    for (const key of keys) {
        if (Object.prototype.hasOwnProperty.call(rawSection, key)) {
            enabled[key] = rawSection[key] !== false;
        }
    }
    return enabled;
}

export const SALES_REPORT_FIELD_CATALOG = {
    filters: FILTER_FIELDS,
    dimensions: DIMENSION_FIELDS,
    metrics: METRIC_FIELDS,
};

export function getDefaultSalesReportFieldSettings() {
    return {
        filters: buildEnabledMap(collectKeys(FILTER_FIELDS, 'value')),
        dimensions: buildEnabledMap(collectKeys(DIMENSION_FIELDS, 'key')),
        metrics: buildEnabledMap(collectKeys(METRIC_FIELDS, 'key')),
    };
}

export function normalizeSalesReportFieldSettings(rawValue) {
    const defaults = getDefaultSalesReportFieldSettings();
    if (!rawValue || typeof rawValue !== 'object') {
        return defaults;
    }

    return {
        filters: normalizeSection(rawValue.filters, Object.keys(defaults.filters)),
        dimensions: normalizeSection(rawValue.dimensions, Object.keys(defaults.dimensions)),
        metrics: normalizeSection(rawValue.metrics, Object.keys(defaults.metrics)),
    };
}

export function loadSalesReportFieldSettings() {
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return getDefaultSalesReportFieldSettings();
        }
        return normalizeSalesReportFieldSettings(JSON.parse(raw));
    } catch {
        return getDefaultSalesReportFieldSettings();
    }
}

export function saveSalesReportFieldSettings(value) {
    const normalized = normalizeSalesReportFieldSettings(value);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    window.dispatchEvent(new CustomEvent(UPDATE_EVENT, { detail: normalized }));
    return normalized;
}

export const SALES_REPORT_FIELD_SETTINGS_STORAGE_KEY = STORAGE_KEY;
export const SALES_REPORT_FIELD_SETTINGS_EVENT = UPDATE_EVENT;
