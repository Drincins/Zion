import { api, buildQueryParams } from './client';

export async function fetchInventoryGroups() {
    const { data } = await api.get('/api/inventory/groups');
    return data;
}

export async function createInventoryGroup(payload) {
    const { data } = await api.post('/api/inventory/groups', payload);
    return data;
}

export async function updateInventoryGroup(groupId, payload) {
    const { data } = await api.put(`/api/inventory/groups/${groupId}`, payload);
    return data;
}

export async function deleteInventoryGroup(groupId) {
    const { data } = await api.delete(`/api/inventory/groups/${groupId}`);
    return data;
}

export async function fetchInventoryCategories(params = {}) {
    const { data } = await api.get('/api/inventory/categories', { params });
    return data;
}

export async function createInventoryCategory(payload) {
    const { data } = await api.post('/api/inventory/categories', payload);
    return data;
}

export async function updateInventoryCategory(categoryId, payload) {
    const { data } = await api.put(`/api/inventory/categories/${categoryId}`, payload);
    return data;
}

export async function deleteInventoryCategory(categoryId) {
    const { data } = await api.delete(`/api/inventory/categories/${categoryId}`);
    return data;
}

export async function fetchInventoryDepartments() {
    const { data } = await api.get('/api/inventory/departments');
    return data;
}

export async function fetchInventoryTypes(params = {}) {
    const { data } = await api.get('/api/inventory/types', { params });
    return data;
}

export async function createInventoryType(payload) {
    const { data } = await api.post('/api/inventory/types', payload);
    return data;
}

export async function updateInventoryType(typeId, payload) {
    const { data } = await api.put(`/api/inventory/types/${typeId}`, payload);
    return data;
}

export async function deleteInventoryType(typeId) {
    const { data } = await api.delete(`/api/inventory/types/${typeId}`);
    return data;
}

export async function fetchInventoryItems(params = {}) {
    const query = buildQueryParams(params).toString();
    const url = query ? `/api/inventory/items?${query}` : '/api/inventory/items';
    const { data } = await api.get(url);
    return data;
}

export async function uploadInventoryItemPhoto(file) {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await api.post('/api/inventory/items/photo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
}

export async function createInventoryItem(payload) {
    const { data } = await api.post('/api/inventory/items', payload);
    return data;
}

export async function updateInventoryItem(itemId, payload) {
    const { data } = await api.put(`/api/inventory/items/${itemId}`, payload);
    return data;
}

export async function deleteInventoryItem(itemId) {
    const { data } = await api.delete(`/api/inventory/items/${itemId}`);
    return data;
}

export async function transferInventoryItem(itemId, payload) {
    const { data } = await api.post(`/api/inventory/items/${itemId}/transfer`, payload);
    return data;
}

export async function allocateInventoryItem(itemId, payload) {
    const { data } = await api.post(`/api/inventory/items/${itemId}/allocate`, payload);
    return data;
}

export async function updateInventoryItemQuantity(itemId, payload) {
    const { data } = await api.post(`/api/inventory/items/${itemId}/quantity`, payload);
    return data;
}

export async function fetchInventoryMovements(params = {}) {
    const query = buildQueryParams(params).toString();
    const url = query ? `/api/inventory/movements?${query}` : '/api/inventory/movements';
    const { data } = await api.get(url);
    return data;
}

export async function fetchInventoryMovementActions() {
    const { data } = await api.get('/api/inventory/movements/actions');
    return data;
}

export async function fetchInventoryBalance(params = {}) {
    const { data } = await api.get('/api/inventory/balance', { params });
    return data;
}

export async function fetchInventoryInstanceEventTypes(params = {}) {
    const { data } = await api.get('/api/inventory/settings/instance-event-types', { params });
    return data;
}

export async function createInventoryInstanceEventType(payload) {
    const { data } = await api.post('/api/inventory/settings/instance-event-types', payload);
    return data;
}

export async function updateInventoryInstanceEventType(eventTypeId, payload) {
    const { data } = await api.put(`/api/inventory/settings/instance-event-types/${eventTypeId}`, payload);
    return data;
}

export async function fetchInventoryStoragePlaces(params = {}) {
    const { data } = await api.get('/api/inventory/settings/storage-places', { params });
    return data;
}

export async function createInventoryStoragePlace(payload) {
    const { data } = await api.post('/api/inventory/settings/storage-places', payload);
    return data;
}

export async function updateInventoryStoragePlace(storagePlaceId, payload) {
    const { data } = await api.put(`/api/inventory/settings/storage-places/${storagePlaceId}`, payload);
    return data;
}

export async function deleteInventoryStoragePlace(storagePlaceId) {
    const { data } = await api.delete(`/api/inventory/settings/storage-places/${storagePlaceId}`);
    return data;
}

export async function fetchInventoryBalanceItemCard(restaurantId, itemId, params = {}) {
    const { data } = await api.get(`/api/inventory/balance/${restaurantId}/items/${itemId}/card`, { params });
    return data;
}

export async function fetchInventoryItemInstanceEvents(restaurantId, itemId, instanceCode, params = {}) {
    const { data } = await api.get(`/api/inventory/balance/${restaurantId}/items/${itemId}/instance-events`, {
        params: { instance_code: instanceCode, ...params }
    });
    return data;
}

export async function createInventoryItemInstanceEvent(restaurantId, itemId, instanceId, payload) {
    const { data } = await api.post(
        `/api/inventory/balance/${restaurantId}/items/${itemId}/instances/${instanceId}/events`,
        payload,
    );
    return data;
}
