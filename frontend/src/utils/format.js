export function parseDate(value) {
    if (!value) {
        return null;
    }
    if (value instanceof Date) {
        return Number.isNaN(value.getTime()) ? null : value;
    }
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (!trimmed) {
            return null;
        }
        if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
            const [year, month, day] = trimmed.split('-').map((part) => Number(part));
            const parsed = new Date(year, month - 1, day);
            return Number.isNaN(parsed.getTime()) ? null : parsed;
        }
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatDateInputValue(value, { emptyValue = '' } = {}) {
    const date = parseDate(value);
    if (!date) {
        return emptyValue;
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

export function formatDateValue(
    value,
    {
        emptyValue = '—',
        invalidValue = '—',
        locale,
        options,
    } = {},
) {
    if (!value) {
        return emptyValue;
    }
    const date = parseDate(value);
    if (!date) {
        return invalidValue;
    }
    if (locale !== undefined) {
        return date.toLocaleDateString(locale, options);
    }
    if (options) {
        return date.toLocaleDateString(undefined, options);
    }
    return date.toLocaleDateString();
}

export function formatDateTimeValue(
    value,
    {
        emptyValue = '',
        invalidValue = '',
        locale = 'ru-RU',
        options,
        timeZone,
    } = {},
) {
    if (!value) {
        return emptyValue;
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return invalidValue;
    }
    const dateTimeOptions = { ...(options || {}) };
    if (timeZone) {
        dateTimeOptions.timeZone = timeZone;
    }
    return date.toLocaleString(locale, dateTimeOptions);
}

export function formatNumberValue(
    value,
    {
        emptyValue = '—',
        invalidValue = '—',
        locale = 'ru-RU',
        minimumFractionDigits = 2,
        maximumFractionDigits = 2,
        useGrouping = true,
    } = {},
) {
    if (value === null || value === undefined || value === '') {
        return emptyValue;
    }
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
        return invalidValue;
    }
    return numericValue.toLocaleString(locale, {
        minimumFractionDigits,
        maximumFractionDigits,
        useGrouping,
    });
}
