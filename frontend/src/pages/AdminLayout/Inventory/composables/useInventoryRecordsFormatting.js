import { formatDateTimeValue } from '@/utils/format';

export function useInventoryRecordsFormatting() {
    function actionClass(actionType) {
        if (actionType === 'transfer') return 'is-transfer';
        if (actionType === 'writeoff') return 'is-writeoff';
        if (actionType === 'cost_changed' || actionType === 'item_updated') return 'is-update';
        if (actionType === 'item_created' || actionType === 'quantity_increase') return 'is-create';
        if (actionType === 'item_deleted' || actionType === 'record_deleted') return 'is-delete';
        return '';
    }

    function formatDateTime(value) {
        return formatDateTimeValue(value, {
            emptyValue: '—',
            invalidValue: '—',
            locale: 'ru-RU',
            timeZone: 'Europe/Moscow',
            options: {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
            },
        });
    }

    function formatObject(event) {
        const from = event.from_location_name;
        const to = event.to_location_name;
        if (from && to) {
            return `${from} → ${to}`;
        }
        if (to) {
            return to;
        }
        if (from) {
            return from;
        }
        return '—';
    }

    function formatQuantity(event) {
        if (event.quantity === null || event.quantity === undefined) {
            return '—';
        }
        const value = Number(event.quantity);
        if (!Number.isFinite(value)) {
            return '—';
        }
        if (event.action_type === 'writeoff') {
            return value > 0 ? `-${value}` : `${value}`;
        }
        if (value > 0 && ['quantity_increase', 'quantity_adjusted'].includes(event.action_type)) {
            return `+${value}`;
        }
        return `${value}`;
    }

    function formatField(field) {
        const map = {
            quantity: 'Количество',
            cost: 'Стоимость',
            default_cost: 'Базовая стоимость',
            code: 'Код',
            name: 'Название',
            group_id: 'Группа',
            category_id: 'Категория',
            kind_id: 'Вид',
            photo_url: 'Фото',
            note: 'Описание',
            record_id: 'Операция',
        };
        return map[field] || field || '';
    }

    function formatDetails(event) {
        const parts = [];
        const hasOldValue = event.old_value !== null && event.old_value !== undefined;
        const hasNewValue = event.new_value !== null && event.new_value !== undefined;
        if (event.field && (hasOldValue || hasNewValue)) {
            parts.push(`${formatField(event.field)}: ${event.old_value ?? '—'} → ${event.new_value ?? '—'}`);
        }
        if (event.comment) {
            parts.push(event.comment);
        }
        return parts.length ? parts.join(' · ') : '—';
    }

    return {
        actionClass,
        formatDateTime,
        formatDetails,
        formatObject,
        formatQuantity,
    };
}
