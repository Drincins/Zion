import axios from 'axios';
import { serverUrl } from './client';

const checklistPortalApi = axios.create({
    baseURL: serverUrl,
    withCredentials: true,
});

export async function startChecklistPortalLogin(staffCode) {
    const { data } = await checklistPortalApi.post('/api/checklists/portal/login/start', {
        staff_code: staffCode,
    });
    return data;
}

export async function finishChecklistPortalLogin(payload) {
    const { data } = await checklistPortalApi.post('/api/checklists/portal/login/finish', payload);
    return data;
}

export async function logoutChecklistPortal() {
    await checklistPortalApi.post('/api/checklists/portal/logout');
}

export async function fetchChecklistPortalChecklists() {
    const { data } = await checklistPortalApi.get('/api/checklists/portal/checklists');
    return data;
}

export async function fetchChecklistPortalChecklist(checklistId) {
    const { data } = await checklistPortalApi.get(`/api/checklists/portal/checklists/${checklistId}`);
    return data;
}

export async function fetchChecklistPortalControlObjects(checklistId) {
    const { data } = await checklistPortalApi.get(
        `/api/checklists/portal/checklists/${checklistId}/control-objects`,
    );
    return data;
}

export async function fetchChecklistPortalDraft(checklistId) {
    const { data } = await checklistPortalApi.get(`/api/checklists/portal/checklists/${checklistId}/draft`);
    return data;
}

export async function upsertChecklistPortalDraft(checklistId, payload) {
    const { data } = await checklistPortalApi.post(
        `/api/checklists/portal/checklists/${checklistId}/draft`,
        payload,
    );
    return data;
}

export async function deleteChecklistPortalDraft(checklistId) {
    await checklistPortalApi.delete(`/api/checklists/portal/checklists/${checklistId}/draft`);
}

export async function exportChecklistPortalAttempt(attemptId, format = 'pdf') {
    return await checklistPortalApi.get(`/api/checklists/portal/attempts/${attemptId}/export`, {
        params: { format },
        responseType: 'blob',
    });
}

export async function fetchChecklistPortalAttempt(attemptId) {
    const { data } = await checklistPortalApi.get(`/api/checklists/portal/attempts/${attemptId}`);
    return data;
}

export async function uploadChecklistPortalPhoto(formData) {
    const { data } = await checklistPortalApi.post('/api/checklists/portal/photos', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
}

export async function submitChecklistPortalAttempt(payload) {
    const { data } = await checklistPortalApi.post('/api/checklists/portal/attempts', payload);
    return data;
}

export async function fetchChecklistPortalMe() {
    const { data } = await checklistPortalApi.get('/api/checklists/portal/me');
    return data;
}
