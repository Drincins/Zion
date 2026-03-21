import { normalizeMojibakeText } from '@/utils/textEncoding';

export const changeFieldLabels = {
    rate: 'Ставка',
    individual_rate: 'Индивидуальная ставка',
    position_rate: 'Ставка должности',
    position: 'Должность',
    position_id: 'Должность',
    role: 'Роль',
    role_id: 'Роль',
    company: 'Компания',
    company_id: 'Компания',
    restaurant_id: 'Ресторан',
    workplace_restaurant: 'Место работы',
    workplace_restaurant_id: 'Место работы',
    workplace_id: 'Место работы',
    restaurants: 'Доступы в рестораны',
    has_full_restaurant_access: 'Полный доступ к ресторанам',
    permissions: 'Права доступа',
    attendance: 'Смена',
    schedule: 'График',
    staff_code: 'Табельный номер',
    username: 'Логин',
    phone: 'Телефон',
    email: 'Почта',
    first_name: 'Имя',
    last_name: 'Фамилия',
    middle_name: 'Отчество',
    hire_date: 'Дата найма',
    fire_date: 'Дата увольнения',
    fired: 'Уволен'
};

const normalizeText = (value) => normalizeMojibakeText(String(value));

export function formatChangeField(field) {
    if (!field) {
        return '-';
    }
    return normalizeText(changeFieldLabels[field] || field);
}

export function parseChangeValue(value) {
    if (typeof value !== 'string') {
        return null;
    }

    const trimmed = value.trim();
    if (!trimmed || (trimmed[0] !== '{' && trimmed[0] !== '[')) {
        return null;
    }

    try {
        return JSON.parse(trimmed);
    } catch {
        return null;
    }
}

function formatDurationSummary(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }

    const minutes = Number(value);
    if (!Number.isFinite(minutes)) {
        return null;
    }

    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours && mins) {
        return `${hours} ч ${mins} мин`;
    }
    if (hours) {
        return `${hours} ч`;
    }
    return `${mins} мин`;
}

function formatParsedValue(value) {
    if (value === null || value === undefined) {
        return '-';
    }

    if (Array.isArray(value)) {
        return value.map(formatParsedValue).join(', ');
    }

    if (typeof value === 'object') {
        if ('attendance_id' in value || 'open_date' in value || 'open_time' in value) {
            const idPart = value.attendance_id ? `#${value.attendance_id}` : '';
            const open = [value.open_date, value.open_time].filter(Boolean).join(' ');
            const close = [value.close_date, value.close_time].filter(Boolean).join(' ');
            const range = close ? `${open} – ${close}` : open;
            const restaurant = value.restaurant_id ? `, рест. ${value.restaurant_id}` : '';
            const position = value.position_id ? `, должн. ${value.position_id}` : '';
            const base = `${idPart} ${range}${restaurant}${position}`.trim();

            const extras = [];
            const duration = formatDurationSummary(value.duration_minutes);
            if (duration) {
                extras.push(`длит. ${duration}`);
            }

            const night = formatDurationSummary(value.night_minutes);
            if (night) {
                extras.push(`ночн. ${night}`);
            }

            if (value.rate !== undefined && value.rate !== null) {
                extras.push(`ставка ${value.rate}`);
            }

            if (value.pay_amount !== undefined && value.pay_amount !== null) {
                extras.push(`сумма ${value.pay_amount}`);
            }

            if (extras.length) {
                return [base, extras.join(', ')].filter(Boolean).join(' • ') || '-';
            }

            return base || '-';
        }

        if (value.name) {
            return normalizeText(value.name);
        }

        if (value.id !== undefined && value.id !== null) {
            return `ID ${value.id}`;
        }

        return normalizeText(JSON.stringify(value));
    }

    return normalizeText(String(value));
}

export function formatChangeValue(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }

    const parsed = parseChangeValue(value);
    if (parsed !== null) {
        return formatParsedValue(parsed);
    }

    return normalizeText(String(value));
}
