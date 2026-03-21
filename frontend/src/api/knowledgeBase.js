import { api, buildQueryParams } from './client';

export async function fetchKnowledgeBaseBootstrap(options = {}) {
    const { data } = await api.get('/api/knowledge-base/bootstrap', { signal: options.signal });
    return data;
}

export async function fetchKnowledgeBaseTree(options = {}) {
    const { data } = await api.get('/api/knowledge-base/tree', { signal: options.signal });
    return data;
}

export async function fetchKnowledgeBaseTreeDocuments(params = {}, options = {}) {
    const query = buildQueryParams(params).toString();
    const path = query ? `/api/knowledge-base/tree/documents?${query}` : '/api/knowledge-base/tree/documents';
    const { data } = await api.get(path, { signal: options.signal });
    return data;
}

export async function fetchKnowledgeBaseItems(params = {}, options = {}) {
    const query = buildQueryParams(params).toString();
    const path = query ? `/api/knowledge-base/items?${query}` : '/api/knowledge-base/items';
    const { data } = await api.get(path, { signal: options.signal });
    return data;
}

export async function createKnowledgeBaseFolder(payload) {
    const { data } = await api.post('/api/knowledge-base/folders', payload);
    return data;
}

export async function updateKnowledgeBaseFolder(folderId, payload) {
    const { data } = await api.patch(`/api/knowledge-base/folders/${folderId}`, payload);
    return data;
}

export async function deleteKnowledgeBaseFolder(folderId, { force = false } = {}) {
    const query = buildQueryParams({ force }).toString();
    const path = query
        ? `/api/knowledge-base/folders/${folderId}?${query}`
        : `/api/knowledge-base/folders/${folderId}`;
    const { data } = await api.delete(path);
    return data;
}

export async function fetchKnowledgeBaseFolderInfo(folderId) {
    const { data } = await api.get(`/api/knowledge-base/folders/${folderId}`);
    return data;
}

export async function fetchKnowledgeBaseFolderHistory(folderId) {
    const { data } = await api.get(`/api/knowledge-base/folders/${folderId}/history`);
    return data;
}

export async function fetchKnowledgeBaseAccessOptions(options = {}) {
    const { data } = await api.get('/api/knowledge-base/access/options', { signal: options.signal });
    return data;
}

export async function fetchKnowledgeBaseFolderAccess(folderId) {
    const { data } = await api.get(`/api/knowledge-base/folders/${folderId}/access`);
    return data;
}

export async function updateKnowledgeBaseFolderAccess(folderId, payload) {
    const { data } = await api.put(`/api/knowledge-base/folders/${folderId}/access`, payload);
    return data;
}

export async function createKnowledgeBaseTextDocument(payload) {
    const { data } = await api.post('/api/knowledge-base/documents/text', payload);
    return data;
}

export async function uploadKnowledgeBaseFile({ folderId = null, name = '', file }) {
    const formData = new FormData();
    formData.append('file', file);
    if (folderId !== null && folderId !== undefined) {
        formData.append('folder_id', String(folderId));
    }
    if (name) {
        formData.append('name', name);
    }
    const { data } = await api.post('/api/knowledge-base/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
}

export async function fetchKnowledgeBaseDocument(documentId, options = {}) {
    const { data } = await api.get(`/api/knowledge-base/documents/${documentId}`, { signal: options.signal });
    return data;
}

export async function openKnowledgeBaseDocument(documentId, options = {}) {
    const { data } = await api.post(`/api/knowledge-base/documents/${documentId}/open`, null, { signal: options.signal });
    return data;
}

export async function updateKnowledgeBaseDocument(documentId, payload) {
    const { data } = await api.patch(`/api/knowledge-base/documents/${documentId}`, payload);
    return data;
}

export async function updateKnowledgeBaseDocumentContent(documentId, payload) {
    const { data } = await api.patch(`/api/knowledge-base/documents/${documentId}/content`, payload);
    return data;
}

export async function deleteKnowledgeBaseDocument(documentId) {
    const { data } = await api.delete(`/api/knowledge-base/documents/${documentId}`);
    return data;
}

export async function fetchKnowledgeBaseDocumentDownload(documentId) {
    const { data } = await api.get(`/api/knowledge-base/documents/${documentId}/download`);
    return data;
}

export async function fetchKnowledgeBaseDocumentHistory(documentId) {
    const { data } = await api.get(`/api/knowledge-base/documents/${documentId}/history`);
    return data;
}
