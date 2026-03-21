import { api, cachedGet, invalidateCacheScope } from './client';

const PAYROLL_ADJUSTMENT_TYPES_SCOPE = 'payroll-adjustment-types';

export async function fetchPayrollAdjustmentTypes() {
    return await cachedGet('/api/payroll/adjustment-types', {
        cacheScope: PAYROLL_ADJUSTMENT_TYPES_SCOPE,
        ttlMs: 60 * 60 * 1000
    });
}

export async function createPayrollAdjustmentType(payload) {
    const { data } = await api.post('/api/payroll/adjustment-types', payload);
    invalidateCacheScope(PAYROLL_ADJUSTMENT_TYPES_SCOPE);
    return data;
}

export async function updatePayrollAdjustmentType(typeId, payload) {
    const { data } = await api.put(`/api/payroll/adjustment-types/${typeId}`, payload);
    invalidateCacheScope(PAYROLL_ADJUSTMENT_TYPES_SCOPE);
    return data;
}

export async function deletePayrollAdjustmentType(typeId) {
    const { data } = await api.delete(`/api/payroll/adjustment-types/${typeId}`);
    invalidateCacheScope(PAYROLL_ADJUSTMENT_TYPES_SCOPE);
    return data;
}

export async function fetchPayrollAdjustments(params = {}) {
    const { data } = await api.get('/api/payroll/adjustments', { params });
    return data;
}

export async function createPayrollAdjustment(payload) {
    const { data } = await api.post('/api/payroll/adjustments', payload);
    return data;
}

export async function updatePayrollAdjustment(adjustmentId, payload) {
    const { data } = await api.put(`/api/payroll/adjustments/${adjustmentId}`, payload);
    return data;
}

export async function deletePayrollAdjustment(adjustmentId) {
    const { data } = await api.delete(`/api/payroll/adjustments/${adjustmentId}`);
    return data;
}

export async function exportPayrollRegister(params = {}) {
    const { data } = await api.get('/api/payroll/export', {
        params,
        responseType: 'blob'
    });
    return data;
}

export async function createPayrollAdjustmentsBulk(payload = {}) {
    const { data } = await api.post('/api/payroll/adjustments/bulk', payload);
    return data;
}
