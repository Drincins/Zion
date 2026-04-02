import { api, buildQueryParams, cachedGet, invalidateCacheScope } from './client';

const TRAINING_EVENT_TYPES_SCOPE = 'training-event-types';
const RESTAURANTS_BY_COMPANY_SCOPE = 'restaurants-by-company';

export async function fetchStaffAttendancesMonth(params) {
    const { data } = await api.get('/api/staff/attendances/month', { params });
    return data;
}

export async function fetchStaffPositions() {
    const { data } = await api.get('/api/staff/positions');
    return data;
}

export async function fetchStaffWaiterTurnoverMetric(params = {}) {
    const { data } = await api.get('/api/staff/metrics/waiter-turnover', { params });
    return data;
}

export async function openStaffAttendance(payload = {}) {
    const { data } = await api.post('/api/staff/attendances/open', payload);
    return data;
}

export async function closeStaffAttendance(payload = {}) {
    const { data } = await api.post('/api/staff/attendances/close', payload);
    return data;
}

export async function fetchEmployees(params = {}, options = {}) {
    const requestParams = { ...(params || {}) };
    const useCompactEndpoint = Boolean(requestParams.compact);
    delete requestParams.compact;
    const endpoint = useCompactEndpoint ? '/api/staff/employees/compact' : '/api/staff/employees';
    // FastAPI expects repeated keys for arrays like position_ids=1&position_ids=2.
    const query = buildQueryParams(requestParams).toString();
    const url = query ? `${endpoint}?${query}` : endpoint;
    const { data } = await api.get(url, {
        signal: options?.signal,
        skipGlobalLoading: options?.skipGlobalLoading === true,
    });
    return data;
}

export async function fetchAllEmployees(params = {}, options = {}) {
    const requestedLimit = Number(params?.limit);
    const pageSize = Number.isFinite(requestedLimit) && requestedLimit > 0
        ? Math.min(requestedLimit, 1000)
        : 250;
    const startOffsetRaw = Number(params?.offset);
    const startOffset = Number.isFinite(startOffsetRaw) && startOffsetRaw >= 0 ? startOffsetRaw : 0;
    const baseParams = {
        ...params,
        offset: startOffset,
        limit: pageSize,
    };

    const firstPage = await fetchEmployees(baseParams, options);
    const items = Array.isArray(firstPage?.items) ? [...firstPage.items] : [];
    let hasMore = Boolean(firstPage?.has_more);
    let nextOffsetRaw = Number(firstPage?.next_offset);
    let nextOffset = Number.isFinite(nextOffsetRaw) && nextOffsetRaw >= 0
        ? nextOffsetRaw
        : startOffset + items.length;

    while (hasMore) {
        const pageData = await fetchEmployees(
            {
                ...baseParams,
                offset: nextOffset,
            },
            options,
        );
        const pageItems = Array.isArray(pageData?.items) ? pageData.items : [];
        if (!pageItems.length) {
            break;
        }
        items.push(...pageItems);

        hasMore = Boolean(pageData?.has_more);
        nextOffsetRaw = Number(pageData?.next_offset);
        const fallbackOffset = nextOffset + pageItems.length;
        nextOffset = Number.isFinite(nextOffsetRaw) && nextOffsetRaw >= 0
            ? nextOffsetRaw
            : fallbackOffset;
        if (nextOffset <= fallbackOffset - pageItems.length) {
            break;
        }
    }

    return {
        items,
        offset: startOffset,
        limit: pageSize,
        has_more: false,
        next_offset: null,
    };
}

export async function fetchEmployeesBootstrap(params = {}, options = {}) {
    const query = buildQueryParams(params).toString();
    const url = query
        ? `/api/staff/employees/bootstrap?${query}`
        : '/api/staff/employees/bootstrap';
    const { data } = await api.get(url, {
        signal: options?.signal,
        skipGlobalLoading: options?.skipGlobalLoading === true,
    });
    return data;
}

export async function fetchLaborSummary(params = {}) {
    // Axios serializes arrays with brackets by default; FastAPI expects repeated keys.
    const query = buildQueryParams(params);
    const { data } = await api.get('/api/labor-summary', { params: query });
    return data;
}

export async function fetchLaborSummaryOptions(params = {}) {
    const query = buildQueryParams(params);
    const { data } = await api.get('/api/labor-summary/options', { params: query });
    return data;
}

export async function fetchLaborSummarySettings(params = {}) {
    const query = buildQueryParams(params);
    const { data } = await api.get('/api/labor-summary/settings', { params: query });
    return data;
}

export async function updateLaborSummarySettings(payload = {}, params = {}) {
    const query = buildQueryParams(params);
    const { data } = await api.put('/api/labor-summary/settings', payload, { params: query });
    return data;
}

export async function fetchEmployeeChangeEvents(params = {}) {
    const { data } = await api.get('/api/employee-change-events', { params });
    return data;
}

export async function fetchEmployeeCard(userId) {
    const { data } = await api.get(`/api/staff/employees/${userId}/card`);
    return data;
}

export async function fetchEmployeeDetail(userId, params = {}) {
    const { data } = await api.get(`/api/staff/employees/${userId}`, { params });
    return data;
}

export async function fetchEmployeeIikoSyncPreview(userId, params = {}) {
    const { data } = await api.get(`/api/staff/employees/${userId}/iiko-sync-preview`, { params });
    return data;
}

export async function fetchWaiterTurnoverRules(params = {}) {
    const { data } = await api.get('/api/iiko-sales/waiter-turnover-rules', { params });
    return data;
}

export async function fetchWaiterTurnoverRule(ruleId, params = {}) {
    const { data } = await api.get(
        `/api/iiko-sales/waiter-turnover-rules/${encodeURIComponent(ruleId)}`,
        { params }
    );
    return data;
}

export async function createWaiterTurnoverRule(payload = {}, params = {}) {
    const { data } = await api.post('/api/iiko-sales/waiter-turnover-rules', payload, { params });
    return data;
}

export async function patchWaiterTurnoverRule(ruleId, payload = {}, params = {}) {
    const { data } = await api.patch(
        `/api/iiko-sales/waiter-turnover-rules/${encodeURIComponent(ruleId)}`,
        payload,
        { params }
    );
    return data;
}

export async function deleteWaiterTurnoverRule(ruleId, params = {}) {
    const { data } = await api.delete(
        `/api/iiko-sales/waiter-turnover-rules/${encodeURIComponent(ruleId)}`,
        { params }
    );
    return data;
}

export async function fetchEmployeeAttendances(userId, params = {}) {
    const { data } = await api.get(`/api/staff/employees/${userId}/attendances`, { params });
    return data;
}

export async function createEmployeeAttendance(userId, payload = {}) {
    const { data } = await api.post(`/api/staff/employees/${userId}/attendances`, payload);
    return data;
}

export async function updateEmployeeAttendance(userId, attendanceId, payload = {}) {
    const { data } = await api.patch(
        `/api/staff/employees/${userId}/attendances/${attendanceId}`,
        payload
    );
    return data;
}

export async function deleteEmployeeAttendance(userId, attendanceId) {
    const { data } = await api.delete(`/api/staff/employees/${userId}/attendances/${attendanceId}`);
    return data;
}

export async function recalculateEmployeeNightMinutes(userId, payload = {}) {
    const { data } = await api.post(
        `/api/staff/employees/${userId}/attendances/recalculate-night`,
        payload
    );
    return data;
}

export async function uploadEmployeePhoto(userId, file) {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await api.post(`/api/staff/employees/${userId}/photo`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
}

export async function uploadCisDocumentAttachment(userId, file) {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await api.post(`/api/cis-documents/users/${userId}/attachment`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
}

export async function uploadEmploymentDocumentAttachment(userId, file) {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await api.post(`/api/employment-documents/users/${userId}/attachment`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
}

export async function updateStaffEmployee(userId, payload = {}) {
    const { data } = await api.put(`/api/staff/employees/${userId}`, payload);
    return data;
}

export async function deleteStaffEmployee(userId, deleteFromIiko = false, comment = '') {
    const params = deleteFromIiko ? { delete_from_iiko: true } : undefined;
    const payload = comment ? { comment } : undefined;
    const { data } = await api.delete(`/api/staff/employees/${userId}`, {
        params,
        data: payload
    });
    return data;
}

export async function restoreStaffEmployee(userId, comment = '') {
    const payload = comment ? { comment } : undefined;
    const { data } = await api.post(`/api/staff/employees/${userId}/restore`, payload);
    return data;
}

export async function fetchMedicalCheckTypes(params = {}) {
    const { data } = await api.get('/api/medical-checks/types', { params });
    return data;
}

export async function fetchMedicalCheckRecords(params = {}) {
    const { data } = await api.get('/api/medical-checks/records', { params });
    return data;
}

export async function createMedicalCheckRecord(payload = {}) {
    const { data } = await api.post('/api/medical-checks/records', payload);
    return data;
}

export async function updateMedicalCheckRecord(recordId, payload = {}) {
    const { data } = await api.put(`/api/medical-checks/records/${recordId}`, payload);
    return data;
}

export async function deleteMedicalCheckRecord(recordId) {
    const { data } = await api.delete(`/api/medical-checks/records/${recordId}`);
    return data;
}

export async function fetchCisDocumentTypes(params = {}) {
    const { data } = await api.get('/api/cis-documents/types', { params });
    return data;
}

export async function fetchCisDocumentRecords(params = {}) {
    const { data } = await api.get('/api/cis-documents/records', { params });
    return data;
}

export async function fetchEmploymentDocumentRecords(params = {}) {
    const { data } = await api.get('/api/employment-documents/records', { params });
    return data;
}

export async function createCisDocumentRecord(payload = {}) {
    const { data } = await api.post('/api/cis-documents/records', payload);
    return data;
}

export async function updateCisDocumentRecord(recordId, payload = {}) {
    const { data } = await api.put(`/api/cis-documents/records/${recordId}`, payload);
    return data;
}

export async function deleteCisDocumentRecord(recordId) {
    const { data } = await api.delete(`/api/cis-documents/records/${recordId}`);
    return data;
}

export async function createEmploymentDocumentRecord(payload = {}) {
    const { data } = await api.post('/api/employment-documents/records', payload);
    return data;
}

export async function updateEmploymentDocumentRecord(recordId, payload = {}) {
    const { data } = await api.put(`/api/employment-documents/records/${recordId}`, payload);
    return data;
}

export async function deleteEmploymentDocumentRecord(recordId) {
    const { data } = await api.delete(`/api/employment-documents/records/${recordId}`);
    return data;
}

export async function fetchTrainingEventTypes() {
    return await cachedGet('/api/training-events/types', {
        cacheScope: TRAINING_EVENT_TYPES_SCOPE,
        ttlMs: 60 * 60 * 1000
    });
}

export async function createTrainingEventType(payload) {
    const { data } = await api.post('/api/training-events/types', payload);
    invalidateCacheScope(TRAINING_EVENT_TYPES_SCOPE);
    return data;
}

export async function updateTrainingEventType(typeId, payload) {
    const { data } = await api.put(`/api/training-events/types/${typeId}`, payload);
    invalidateCacheScope(TRAINING_EVENT_TYPES_SCOPE);
    return data;
}

export async function deleteTrainingEventType(typeId) {
    const { data } = await api.delete(`/api/training-events/types/${typeId}`);
    invalidateCacheScope(TRAINING_EVENT_TYPES_SCOPE);
    return data;
}

export async function fetchTrainingEventRecords(params = {}) {
    const { data } = await api.get('/api/training-events', { params });
    return data;
}

export async function fetchTrainingRequirementSuggestions(positionId, userId) {
    const params = { position_id: positionId };
    if (userId) {
        params.user_id = userId;
    }
    const { data } = await api.get('/api/training-events/position-requirements/suggestions', {
        params
    });
    return data;
}

export async function createPositionTrainingRequirement(payload) {
    const { data } = await api.post('/api/training-events/position-requirements', payload);
    return data;
}

export async function updatePositionTrainingRequirement(requirementId, payload) {
    const { data } = await api.put(
        `/api/training-events/position-requirements/${requirementId}`,
        payload
    );
    return data;
}

export async function createTrainingEventRecord(payload) {
    const { data } = await api.post('/api/training-events', payload);
    return data;
}

export async function updateTrainingEventRecord(recordId, payload) {
    const { data } = await api.put(`/api/training-events/${recordId}`, payload);
    return data;
}

export async function deleteTrainingEventRecord(recordId) {
    const { data } = await api.delete(`/api/training-events/${recordId}`);
    return data;
}

export async function fetchTimesheetOptions() {
    const { data } = await api.get('/api/staff/employees/timesheet/options');
    return data;
}

export async function exportTimesheetReport(params = {}) {
    const query = buildQueryParams(params).toString();
    const url = query
        ? `/api/staff/employees/timesheet/export?${query}`
        : '/api/staff/employees/timesheet/export';
    const { data } = await api.get(url, { responseType: 'blob' });
    return data;
}

export async function exportEmployeesListXlsx(payload = {}) {
    const { data } = await api.post('/api/staff/employees/export', payload, {
        responseType: 'blob'
    });
    return data;
}

export async function createRestaurant(companyId, payload = {}) {
    const { data } = await api.post(`/api/restaurants/${companyId}`, payload);
    invalidateCacheScope(RESTAURANTS_BY_COMPANY_SCOPE);
    invalidateCacheScope('restaurants');
    return data;
}

export async function fetchRestaurantsByCompany(params = {}) {
    return await cachedGet('/api/restaurants/', {
        params,
        cacheScope: RESTAURANTS_BY_COMPANY_SCOPE,
        ttlMs: 2 * 60 * 1000
    });
}

export async function updateRestaurant(restaurantId, payload = {}) {
    const { data } = await api.put(`/api/restaurants/${restaurantId}`, payload);
    invalidateCacheScope(RESTAURANTS_BY_COMPANY_SCOPE);
    invalidateCacheScope('restaurants');
    return data;
}

export async function deleteRestaurant(restaurantId) {
    const { data } = await api.delete(`/api/restaurants/${restaurantId}`);
    invalidateCacheScope(RESTAURANTS_BY_COMPANY_SCOPE);
    invalidateCacheScope('restaurants');
    return data;
}

export async function fetchRestaurantSalesSyncSettings(restaurantId) {
    const { data } = await api.get(`/api/restaurants/${restaurantId}/sales-sync-settings`);
    return data;
}

export async function updateRestaurantSalesSyncSettings(restaurantId, payload = {}) {
    const { data } = await api.put(`/api/restaurants/${restaurantId}/sales-sync-settings`, payload);
    return data;
}

export async function runRestaurantSalesSync(restaurantId, payload = {}) {
    const { data } = await api.post(`/api/restaurants/${restaurantId}/sales-sync-settings/run`, payload);
    return data;
}

export async function fetchRestaurantSalesSyncOperations(restaurantId) {
    const { data } = await api.get(`/api/restaurants/${restaurantId}/sales-sync-settings/operations`);
    return data;
}

export async function cancelRestaurantSalesSyncOperation(restaurantId, payload = {}) {
    const { data } = await api.post(`/api/restaurants/${restaurantId}/sales-sync-settings/operations/cancel`, payload);
    return data;
}
