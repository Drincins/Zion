import { api } from './client';

export async function fetchAccountingInvoices(params = {}, options = {}) {
    const { data } = await api.get('/api/accounting/invoices', {
        params,
        signal: options?.signal
    });
    return data;
}

export async function createAccountingInvoice(formData) {
    const { data } = await api.post('/api/accounting/invoices', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
}

export async function updateAccountingInvoice(invoiceId, payload) {
    const { data } = await api.put(`/api/accounting/invoices/${invoiceId}`, payload);
    return data;
}

export async function updateAccountingInvoiceStatus(invoiceId, payload) {
    const { data } = await api.put(`/api/accounting/invoices/${invoiceId}/status`, payload);
    return data;
}

export async function deleteAccountingInvoice(invoiceId) {
    const { data } = await api.delete(`/api/accounting/invoices/${invoiceId}`);
    return data;
}

export async function fetchAccountingInvoiceChanges(invoiceId) {
    const { data } = await api.get(`/api/accounting/invoices/${invoiceId}/changes`);
    return data;
}

export async function fetchAccountingInvoiceEvents(invoiceId) {
    const { data } = await api.get(`/api/accounting/invoices/${invoiceId}/events`);
    return data;
}

export async function uploadAccountingInvoiceFile(invoiceId, file) {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post(`/api/accounting/invoices/${invoiceId}/invoice-file`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
}

export async function uploadAccountingPaymentOrder(invoiceId, file) {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post(`/api/accounting/invoices/${invoiceId}/payment-order`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
}

export async function uploadAccountingClosingDocument(invoiceId, file) {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post(
        `/api/accounting/invoices/${invoiceId}/closing-documents`,
        formData,
        {
            headers: { 'Content-Type': 'multipart/form-data' }
        }
    );
    return data;
}

export async function analyzeAccountingInvoiceLLM(file) {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/api/accounting/invoices/ocr-llm', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
}
