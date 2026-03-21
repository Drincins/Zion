import { api, cachedGet } from './client';

export async function fetchKitchenRestaurants(params = {}, options = {}) {
    const { data } = await api.get('/api/restaurants/', {
        params,
        signal: options?.signal
    });
    return data;
}

export async function fetchKitchenUsers(params = {}, options = {}) {
    const { data } = await api.get('/api/users/', {
        params,
        signal: options?.signal
    });
    return data;
}

export async function fetchKitchenSalesItems(params = {}, options = {}) {
    const { data } = await api.get('/api/iiko-sales/items', {
        params,
        timeout: 0,
        signal: options?.signal
    });
    return data;
}

export async function fetchKitchenWaiterSalesOptions(params = {}, options = {}) {
    return await cachedGet('/api/iiko-sales/waiter-sales-report/options', {
        params,
        cacheScope: 'kitchen:waiter-sales-options',
        ttlMs: 45 * 1000,
        signal: options?.signal
    });
}

export async function fetchKitchenWaiterSalesReport(params = {}, options = {}) {
    const { data } = await api.get('/api/iiko-sales/waiter-sales-report', {
        params,
        signal: options?.signal
    });
    return data;
}

export async function fetchKitchenWaiterSalesPositions(params = {}, options = {}) {
    const { data } = await api.get('/api/iiko-sales/waiter-sales-report/positions', {
        params,
        signal: options?.signal
    });
    return data;
}

export async function fetchKitchenRevenueByPaymentMethods(params = {}, options = {}) {
    const { data } = await api.get('/api/iiko-sales/revenue-by-payment-methods', {
        params,
        signal: options?.signal
    });
    return data;
}

export async function fetchKitchenPaymentMethods(params = {}) {
    const { data } = await api.get('/api/iiko-sales/payment-methods', { params });
    return data;
}

export async function patchKitchenPaymentMethod(guid, payload = {}) {
    const { data } = await api.patch(
        `/api/iiko-sales/payment-methods/${encodeURIComponent(guid)}`,
        payload
    );
    return data;
}

export async function fetchKitchenNonCashTypes(params = {}) {
    const { data } = await api.get('/api/iiko-sales/non-cash-types', { params });
    return data;
}

export async function fetchKitchenNonCashConsumption(params = {}) {
    const { data } = await api.get('/api/iiko-sales/non-cash-consumption', { params });
    return data;
}

export async function createKitchenNonCashType(payload = {}) {
    const { data } = await api.post('/api/iiko-sales/non-cash-types', payload);
    return data;
}

export async function patchKitchenNonCashType(typeId, payload = {}) {
    const { data } = await api.patch(
        `/api/iiko-sales/non-cash-types/${encodeURIComponent(typeId)}`,
        payload
    );
    return data;
}

export async function putKitchenNonCashEmployeeLimits(payload = {}) {
    const { data } = await api.put('/api/iiko-sales/non-cash-employee-limits', payload);
    return data;
}

export async function patchKitchenNonCashEmployeeLimit(limitId, payload = {}) {
    const { data } = await api.patch(
        `/api/iiko-sales/non-cash-employee-limits/${encodeURIComponent(limitId)}`,
        payload
    );
    return data;
}

export async function deleteKitchenNonCashEmployeeLimit(limitId) {
    const { data } = await api.delete(
        `/api/iiko-sales/non-cash-employee-limits/${encodeURIComponent(limitId)}`
    );
    return data;
}

export async function fetchKitchenSalesLocationMappings(params = {}) {
    const { data } = await api.get('/api/iiko-sales/sales-location-mappings', { params });
    return data;
}

export async function fetchKitchenSalesLocationCandidates(params = {}) {
    const { data } = await api.get('/api/iiko-sales/sales-location-candidates', { params });
    return data;
}

export async function createKitchenSalesLocationMapping(payload = {}) {
    const { data } = await api.put('/api/iiko-sales/sales-location-mappings', payload);
    return data;
}

export async function patchKitchenSalesLocationMapping(mappingId, payload = {}) {
    const { data } = await api.patch(
        `/api/iiko-sales/sales-location-mappings/${encodeURIComponent(mappingId)}`,
        payload
    );
    return data;
}

export async function deleteKitchenSalesLocationMapping(mappingId) {
    const { data } = await api.delete(
        `/api/iiko-sales/sales-location-mappings/${encodeURIComponent(mappingId)}`
    );
    return data;
}

export async function fetchKitchenSalesHalls(params = {}) {
    const { data } = await api.get('/api/iiko-sales/sales-halls', { params });
    return data;
}

export async function createKitchenSalesHall(payload = {}) {
    const { data } = await api.post('/api/iiko-sales/sales-halls', payload);
    return data;
}

export async function fetchKitchenSalesHallZones(params = {}) {
    const { data } = await api.get('/api/iiko-sales/sales-hall-zones', { params });
    return data;
}

export async function createKitchenSalesHallZone(payload = {}) {
    const { data } = await api.post('/api/iiko-sales/sales-hall-zones', payload);
    return data;
}

export async function fetchKitchenSalesHallTables(params = {}) {
    const { data } = await api.get('/api/iiko-sales/sales-hall-tables', { params });
    return data;
}

export async function fetchKitchenSalesHallTableCandidates(params = {}) {
    const { data } = await api.get('/api/iiko-sales/sales-hall-table-candidates', { params });
    return data;
}

export async function assignKitchenSalesHallZoneTables(zoneId, payload = {}) {
    const { data } = await api.post(
        `/api/iiko-sales/sales-hall-zones/${encodeURIComponent(zoneId)}/assign-tables`,
        payload
    );
    return data;
}

export async function deleteKitchenSalesHallTable(tableId) {
    const { data } = await api.delete(
        `/api/iiko-sales/sales-hall-tables/${encodeURIComponent(tableId)}`
    );
    return data;
}

export async function fetchKitchenProductRows(params = {}) {
    const { data } = await api.get('/api/iiko-products/rows', { params });
    return data;
}

export async function patchKitchenProductRowSettings(rowId, payload = {}) {
    const { data } = await api.patch(
        `/api/iiko-products/rows/${encodeURIComponent(rowId)}/settings`,
        payload
    );
    return data;
}

export async function syncKitchenProductsNetwork(payload = {}) {
    const { data } = await api.post('/api/iiko-olap-product/sync-products-network', payload);
    return data;
}
