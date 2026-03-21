export function extractApiErrorMessage(error, fallbackMessage = '') {
    const detail = error?.response?.data?.detail;
    const message = error?.response?.data?.message;

    if (typeof detail === 'string' && detail.trim()) {
        return detail.trim();
    }
    if (typeof message === 'string' && message.trim()) {
        return message.trim();
    }
    if (typeof error?.message === 'string' && error.message.trim()) {
        return error.message.trim();
    }
    return fallbackMessage;
}
