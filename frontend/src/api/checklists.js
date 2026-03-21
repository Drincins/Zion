import { api, buildQueryParams } from './client';

export async function fetchChecklists() {
    const { data } = await api.get('/api/checklists');
    return data;
}

export async function fetchChecklist(checklistId) {
    const { data } = await api.get(`/api/checklists/${checklistId}`);
    return data;
}

export async function createChecklist(payload) {
    const { data } = await api.post('/api/checklists', payload);
    return data;
}

export async function updateChecklist(checklistId, payload) {
    const { data } = await api.patch(`/api/checklists/${checklistId}`, payload);
    return data;
}

export async function deleteChecklist(checklistId) {
    await api.delete(`/api/checklists/${checklistId}`);
}

export async function createChecklistSection(checklistId, payload) {
    const { data } = await api.post(`/api/checklists/${checklistId}/sections`, payload);
    return data;
}

export async function updateChecklistSection(checklistId, sectionId, payload) {
    const { data } = await api.patch(`/api/checklists/${checklistId}/sections/${sectionId}`, payload);
    return data;
}

export async function deleteChecklistSection(checklistId, sectionId) {
    await api.delete(`/api/checklists/${checklistId}/sections/${sectionId}`);
}

export async function createChecklistQuestion(checklistId, payload) {
    const { data } = await api.post(`/api/checklists/${checklistId}/questions`, payload);
    return data;
}

export async function updateChecklistQuestion(checklistId, questionId, payload) {
    const { data } = await api.patch(`/api/checklists/${checklistId}/questions/${questionId}`, payload);
    return data;
}

export async function deleteChecklistQuestion(checklistId, questionId) {
    await api.delete(`/api/checklists/${checklistId}/questions/${questionId}`);
}

export async function fetchChecklistReportSummary(params = {}) {
    const query = buildQueryParams(params);
    const { data } = await api.get('/api/checklists/reports/summary', { params: query });
    return data;
}

export async function fetchChecklistReportMetrics(params = {}) {
    const query = buildQueryParams(params);
    const { data } = await api.get('/api/checklists/reports/metrics', { params: query });
    return data;
}

export async function fetchChecklistAttempts(params = {}) {
    const query = buildQueryParams(params);
    const { data } = await api.get('/api/checklists/reports/attempts', { params: query });
    return data;
}

export async function fetchChecklistAttemptDetail(attemptId) {
    const { data } = await api.get(`/api/checklists/reports/attempts/${attemptId}`);
    return data;
}

export async function exportChecklistAttempt(attemptId, format = 'pdf') {
    const { data } = await api.get(`/api/checklists/reports/attempts/${attemptId}/export`, {
        params: { format },
        responseType: 'blob'
    });
    return data;
}

export async function deleteChecklistAttempt(attemptId) {
    await api.delete(`/api/checklists/reports/attempts/${attemptId}`);
}
