export const PHONE_FORMAT_ERROR = 'Номер телефона должен быть в формате +7XXXXXXXXXX';

function extractDigits(value) {
    const raw = (value ?? '').toString().trim();
    if (!raw) {
        return '';
    }
    return raw.replace(/\D/g, '');
}

function normalizeDigitsForInput(value) {
    let normalized = value;
    if (normalized.startsWith('8')) {
        normalized = `7${normalized.slice(1)}`;
    }
    if (!normalized.startsWith('7')) {
        normalized = `7${normalized}`;
    }
    return normalized.slice(0, 11);
}

function normalizeDigitsStrict(value) {
    let normalized = value;
    if (normalized.startsWith('8')) {
        normalized = `7${normalized.slice(1)}`;
    }
    return normalized;
}

export function sanitizePhoneInput(value) {
    const digits = extractDigits(value);
    if (!digits) {
        return '';
    }
    const normalized = normalizeDigitsForInput(digits);
    return normalized ? `+${normalized}` : '';
}

export function formatPhoneForInput(value) {
    const digits = extractDigits(value);
    if (!digits) {
        return '';
    }

    const normalized = normalizeDigitsForInput(digits);
    if (!normalized) {
        return '';
    }

    const rest = normalized.slice(1);
    if (!rest.length) {
        return '+7';
    }

    const area = rest.slice(0, 3);
    const firstBlock = rest.slice(3, 6);
    const secondBlock = rest.slice(6, 8);
    const thirdBlock = rest.slice(8, 10);

    let formatted = `+7(${area}`;
    if (area.length === 3) {
        formatted += ')';
    }
    if (firstBlock.length) {
        formatted += `-${firstBlock}`;
    }
    if (secondBlock.length) {
        formatted += `-${secondBlock}`;
    }
    if (thirdBlock.length) {
        formatted += `-${thirdBlock}`;
    }

    return formatted;
}

export function normalizePhoneForApi(value, { errorMessage = PHONE_FORMAT_ERROR } = {}) {
    const raw = (value ?? '').toString().trim();
    if (!raw) {
        return { phone: null, error: null };
    }

    const digits = extractDigits(raw);
    if (!digits) {
        return { phone: null, error: errorMessage };
    }

    const normalized = normalizeDigitsStrict(digits);
    if (!normalized.startsWith('7') || normalized.length !== 11) {
        return { phone: null, error: errorMessage };
    }

    return { phone: `+${normalized}`, error: null };
}

export function validatePhoneInput(value, { errorMessage = PHONE_FORMAT_ERROR } = {}) {
    const raw = (value ?? '').toString().trim();
    if (!raw) {
        return '';
    }

    const { error } = normalizePhoneForApi(raw, { errorMessage });
    return error || '';
}

export function formatPhoneForDisplay(value, { emptyValue = '—' } = {}) {
    if (value === null || value === undefined || value === '') {
        return emptyValue;
    }

    const digits = extractDigits(value);
    if (!digits) {
        return value;
    }

    const normalized = normalizeDigitsForInput(digits);
    if (normalized.length < 11) {
        return value;
    }

    const area = normalized.slice(1, 4);
    const firstBlock = normalized.slice(4, 7);
    const secondBlock = normalized.slice(7, 9);
    const thirdBlock = normalized.slice(9, 11);
    return `+7(${area})-${firstBlock}-${secondBlock}-${thirdBlock}`;
}
