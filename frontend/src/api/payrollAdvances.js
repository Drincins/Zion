import { api, buildQueryParams } from './client';

function parseContentDispositionFilename(contentDisposition) {
    if (!contentDisposition) return '';
    const encodedMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (encodedMatch?.[1]) {
        try {
            return decodeURIComponent(encodedMatch[1]);
        } catch {
            return encodedMatch[1];
        }
    }
    const plainMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
    return plainMatch?.[1] || '';
}

export async function fetchAdvanceStatements() {
    const { data } = await api.get('/api/payroll/advances');
    return data;
}

export async function fetchAdvanceStatement(statementId) {
    const { data } = await api.get(`/api/payroll/advances/${statementId}`);
    return data;
}

export async function fetchAdvanceStatementTotals(statementIds = []) {
    const ids = Array.isArray(statementIds)
        ? statementIds
              .map((value) => Number(value))
              .filter((value) => Number.isFinite(value) && value > 0)
        : [];
    if (!ids.length) {
        return { items: [], missing_ids: [] };
    }
    const params = buildQueryParams({ ids });
    const { data } = await api.get('/api/payroll/advances/totals', { params });
    return data;
}

export async function createAdvanceStatement(payload) {
    const { data } = await api.post('/api/payroll/advances', payload);
    return data;
}

export async function refreshAdvanceStatement(statementId) {
    const { data } = await api.post(`/api/payroll/advances/${statementId}/refresh`);
    return data;
}

export async function updateAdvanceItem(statementId, itemId, payload) {
    const { data } = await api.patch(`/api/payroll/advances/${statementId}/items/${itemId}`, payload);
    return data;
}

export async function updateAdvanceItemCompact(statementId, itemId, payload) {
    const { data } = await api.patch(
        `/api/payroll/advances/${statementId}/items/${itemId}/compact`,
        payload
    );
    return data;
}

export async function updateAdvanceItemsCompact(statementId, items = []) {
    const { data } = await api.patch(
        `/api/payroll/advances/${statementId}/items/bulk/update`,
        { items }
    );
    return data;
}

export async function changeAdvanceStatus(statementId, payload) {
    const { data } = await api.post(`/api/payroll/advances/${statementId}/status`, payload);
    return data;
}

export async function downloadAdvanceStatement(statementId) {
    const response = await api.get(`/api/payroll/advances/${statementId}/download`, {
        responseType: 'blob',
    });
    return {
        blob: response.data,
        filename: parseContentDispositionFilename(response.headers?.['content-disposition']),
    };
}

export async function postAdvanceStatement(statementId, payload) {
    const { data } = await api.post(`/api/payroll/advances/${statementId}/post`, payload);
    return data;
}

export async function downloadAdvanceConsolidated(statementIds = []) {
    const response = await api.post(
        '/api/payroll/advances/consolidated/download',
        { statement_ids: statementIds },
        { responseType: 'blob' }
    );
    return {
        blob: response.data,
        filename: parseContentDispositionFilename(response.headers?.['content-disposition']),
    };
}

export async function fetchAdvanceConsolidatedStatements() {
    const { data } = await api.get('/api/payroll/advances/consolidated');
    return data;
}

export async function createAdvanceConsolidatedStatement(payload) {
    const { data } = await api.post('/api/payroll/advances/consolidated', payload);
    return data;
}

export async function downloadAdvanceConsolidatedById(consolidatedId) {
    const response = await api.get(`/api/payroll/advances/consolidated/${consolidatedId}/download`, {
        responseType: 'blob'
    });
    return {
        blob: response.data,
        filename: parseContentDispositionFilename(response.headers?.['content-disposition']),
    };
}

export async function deleteAdvanceConsolidatedStatement(consolidatedId) {
    await api.delete(`/api/payroll/advances/consolidated/${consolidatedId}`);
}

export async function deleteAdvanceStatement(statementId) {
    await api.delete(`/api/payroll/advances/${statementId}`);
}
