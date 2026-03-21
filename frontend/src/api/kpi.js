import { api, cachedGet, invalidateCacheScope } from './client';

const KPI_REFERENCE_TTL_MS = 45 * 1000;
const KPI_FACTS_TTL_MS = 5 * 1000;
const KPI_PAYOUTS_TTL_MS = 10 * 1000;

const KPI_METRIC_GROUPS_SCOPE = 'kpi:metric-groups';
const KPI_METRICS_SCOPE = 'kpi:metrics';
const KPI_RULES_SCOPE = 'kpi:rules';
const KPI_GROUP_RULES_SCOPE = 'kpi:group-rules';
const KPI_RESULTS_SCOPE = 'kpi:results';
const KPI_PLAN_FACT_SCOPE = 'kpi:plan-fact';
const KPI_GROUP_PLAN_FACT_SCOPE = 'kpi:group-plan-fact';
const KPI_PLAN_PREFERENCES_SCOPE = 'kpi:plan-preferences';
const KPI_GROUP_PLAN_PREFERENCES_SCOPE = 'kpi:group-plan-preferences';
const KPI_PAYOUTS_SCOPE = 'kpi:payouts';

function invalidateKpiReferenceScopes() {
    invalidateCacheScope(KPI_METRIC_GROUPS_SCOPE);
    invalidateCacheScope(KPI_METRICS_SCOPE);
    invalidateCacheScope(KPI_PLAN_PREFERENCES_SCOPE);
    invalidateCacheScope(KPI_GROUP_PLAN_PREFERENCES_SCOPE);
}

function invalidateKpiRuleScopes() {
    invalidateCacheScope(KPI_RULES_SCOPE);
    invalidateCacheScope(KPI_GROUP_RULES_SCOPE);
}

function invalidateKpiFactScopes() {
    invalidateCacheScope(KPI_PLAN_FACT_SCOPE);
    invalidateCacheScope(KPI_GROUP_PLAN_FACT_SCOPE);
    invalidateCacheScope(KPI_RESULTS_SCOPE);
}

function invalidateKpiPayoutScopes() {
    invalidateCacheScope(KPI_PAYOUTS_SCOPE);
}

export async function fetchKpiMetricGroups(params = {}) {
    return await cachedGet('/api/kpi/metric-groups', {
        params,
        cacheScope: KPI_METRIC_GROUPS_SCOPE,
        ttlMs: KPI_REFERENCE_TTL_MS,
    });
}

export async function createKpiMetricGroup(payload) {
    const { data } = await api.post('/api/kpi/metric-groups', payload);
    invalidateKpiReferenceScopes();
    return data;
}

export async function updateKpiMetricGroup(groupId, payload) {
    const { data } = await api.patch(`/api/kpi/metric-groups/${groupId}`, payload);
    invalidateKpiReferenceScopes();
    invalidateKpiRuleScopes();
    invalidateKpiFactScopes();
    return data;
}

export async function deleteKpiMetricGroup(groupId) {
    await api.delete(`/api/kpi/metric-groups/${groupId}`);
    invalidateKpiReferenceScopes();
    invalidateKpiRuleScopes();
    invalidateKpiFactScopes();
}

export async function fetchKpiMetricGroupRules(params = {}) {
    return await cachedGet('/api/kpi/group-rules', {
        params,
        cacheScope: KPI_GROUP_RULES_SCOPE,
        ttlMs: KPI_REFERENCE_TTL_MS,
    });
}

export async function createKpiMetricGroupRule(payload) {
    const { data } = await api.post('/api/kpi/group-rules', payload);
    invalidateKpiRuleScopes();
    invalidateKpiPayoutScopes();
    return data;
}

export async function updateKpiMetricGroupRule(ruleId, payload) {
    const { data } = await api.patch(`/api/kpi/group-rules/${ruleId}`, payload);
    invalidateKpiRuleScopes();
    invalidateKpiPayoutScopes();
    return data;
}

export async function deleteKpiMetricGroupRule(ruleId) {
    await api.delete(`/api/kpi/group-rules/${ruleId}`);
    invalidateKpiRuleScopes();
    invalidateKpiPayoutScopes();
}

export async function fetchKpiMetricGroupPlanFacts(params = {}) {
    return await cachedGet('/api/kpi/metric-group-plan-fact', {
        params,
        cacheScope: KPI_GROUP_PLAN_FACT_SCOPE,
        ttlMs: KPI_FACTS_TTL_MS,
    });
}

export async function fetchKpiMetricGroupPlanFactsBulk(params = {}) {
    return await cachedGet('/api/kpi/metric-group-plan-fact/bulk', {
        params,
        cacheScope: KPI_GROUP_PLAN_FACT_SCOPE,
        ttlMs: KPI_FACTS_TTL_MS,
    });
}

export async function upsertKpiMetricGroupPlanFactsBulk(payloads = []) {
    const { data } = await api.put('/api/kpi/metric-group-plan-fact/bulk', payloads);
    invalidateCacheScope(KPI_GROUP_PLAN_FACT_SCOPE);
    invalidateKpiPayoutScopes();
    return data;
}

export async function fetchKpiMetricGroupPlanPreferences(params = {}) {
    return await cachedGet('/api/kpi/metric-group-plan-preferences', {
        params,
        cacheScope: KPI_GROUP_PLAN_PREFERENCES_SCOPE,
        ttlMs: KPI_REFERENCE_TTL_MS,
    });
}

export async function upsertKpiMetricGroupPlanPreference(payload) {
    const { data } = await api.put('/api/kpi/metric-group-plan-preferences', payload);
    invalidateCacheScope(KPI_GROUP_PLAN_PREFERENCES_SCOPE);
    return data;
}

export async function fetchKpiMetrics(params = {}) {
    return await cachedGet('/api/kpi/metrics', {
        params,
        cacheScope: KPI_METRICS_SCOPE,
        ttlMs: KPI_REFERENCE_TTL_MS,
    });
}

export async function createKpiMetric(payload) {
    const { data } = await api.post('/api/kpi/metrics', payload);
    invalidateKpiReferenceScopes();
    invalidateKpiRuleScopes();
    invalidateKpiFactScopes();
    return data;
}

export async function updateKpiMetric(metricId, payload) {
    const { data } = await api.patch(`/api/kpi/metrics/${metricId}`, payload);
    invalidateKpiReferenceScopes();
    invalidateKpiRuleScopes();
    invalidateKpiFactScopes();
    return data;
}

export async function deleteKpiMetric(metricId) {
    await api.delete(`/api/kpi/metrics/${metricId}`);
    invalidateKpiReferenceScopes();
    invalidateKpiRuleScopes();
    invalidateKpiFactScopes();
    invalidateKpiPayoutScopes();
}

export async function fetchKpiRules(params = {}) {
    return await cachedGet('/api/kpi/rules', {
        params,
        cacheScope: KPI_RULES_SCOPE,
        ttlMs: KPI_REFERENCE_TTL_MS,
    });
}

export async function createKpiRule(payload) {
    const { data } = await api.post('/api/kpi/rules', payload);
    invalidateKpiRuleScopes();
    invalidateKpiPayoutScopes();
    return data;
}

export async function updateKpiRule(ruleId, payload) {
    const { data } = await api.patch(`/api/kpi/rules/${ruleId}`, payload);
    invalidateKpiRuleScopes();
    invalidateKpiPayoutScopes();
    return data;
}

export async function deleteKpiRule(ruleId) {
    await api.delete(`/api/kpi/rules/${ruleId}`);
    invalidateKpiRuleScopes();
    invalidateKpiPayoutScopes();
}

export async function fetchKpiResults(params = {}) {
    return await cachedGet('/api/kpi/results', {
        params,
        cacheScope: KPI_RESULTS_SCOPE,
        ttlMs: KPI_FACTS_TTL_MS,
    });
}

export async function createKpiResult(payload) {
    const { data } = await api.post('/api/kpi/results', payload);
    invalidateCacheScope(KPI_RESULTS_SCOPE);
    invalidateKpiPayoutScopes();
    return data;
}

export async function updateKpiResult(resultId, payload) {
    const { data } = await api.patch(`/api/kpi/results/${resultId}`, payload);
    invalidateCacheScope(KPI_RESULTS_SCOPE);
    invalidateKpiPayoutScopes();
    return data;
}

export async function deleteKpiResult(resultId) {
    await api.delete(`/api/kpi/results/${resultId}`);
    invalidateCacheScope(KPI_RESULTS_SCOPE);
    invalidateKpiPayoutScopes();
}

export async function fetchKpiPlanFacts(params = {}) {
    return await cachedGet('/api/kpi/plan-fact', {
        params,
        cacheScope: KPI_PLAN_FACT_SCOPE,
        ttlMs: KPI_FACTS_TTL_MS,
    });
}

export async function fetchKpiPlanFactsBulk(params = {}) {
    return await cachedGet('/api/kpi/plan-fact/bulk', {
        params,
        cacheScope: KPI_PLAN_FACT_SCOPE,
        ttlMs: KPI_FACTS_TTL_MS,
    });
}

export async function upsertKpiPlanFact(payload) {
    const { data } = await api.put('/api/kpi/plan-fact', payload);
    invalidateCacheScope(KPI_PLAN_FACT_SCOPE);
    invalidateKpiPayoutScopes();
    return data;
}

export async function upsertKpiPlanFactsBulk(payloads = []) {
    const { data } = await api.put('/api/kpi/plan-fact/bulk', payloads);
    invalidateCacheScope(KPI_PLAN_FACT_SCOPE);
    invalidateKpiPayoutScopes();
    return data;
}

export async function fetchKpiPlanPreferences(params = {}) {
    return await cachedGet('/api/kpi/plan-preferences', {
        params,
        cacheScope: KPI_PLAN_PREFERENCES_SCOPE,
        ttlMs: KPI_REFERENCE_TTL_MS,
    });
}

export async function upsertKpiPlanPreference(payload) {
    const { data } = await api.put('/api/kpi/plan-preferences', payload);
    invalidateCacheScope(KPI_PLAN_PREFERENCES_SCOPE);
    return data;
}

export async function fetchKpiPayoutBatches(params = {}) {
    return await cachedGet('/api/kpi/payouts', {
        params,
        cacheScope: KPI_PAYOUTS_SCOPE,
        ttlMs: KPI_PAYOUTS_TTL_MS,
    });
}

export async function fetchKpiPayoutBatch(batchId) {
    return await cachedGet(`/api/kpi/payouts/${batchId}`, {
        cacheScope: KPI_PAYOUTS_SCOPE,
        ttlMs: KPI_PAYOUTS_TTL_MS,
    });
}

export async function fetchKpiPayoutBatchesBulk(batchIds = []) {
    const ids = Array.isArray(batchIds)
        ? batchIds
              .map((value) => Number(value))
              .filter((value) => Number.isFinite(value) && value > 0)
        : [];
    if (!ids.length) {
        return { total: 0, items: [] };
    }

    const uniqueIds = Array.from(new Set(ids));
    const chunkSize = 100;
    const maxConcurrentChunks = 3;
    const chunks = [];
    for (let index = 0; index < uniqueIds.length; index += chunkSize) {
        chunks.push(uniqueIds.slice(index, index + chunkSize));
    }

    const itemsById = new Map();
    for (let index = 0; index < chunks.length; index += maxConcurrentChunks) {
        const chunkGroup = chunks.slice(index, index + maxConcurrentChunks);
        const responses = await Promise.all(
            chunkGroup.map((chunk) => {
                const searchParams = new URLSearchParams();
                chunk.forEach((id) => {
                    searchParams.append('ids', String(id));
                });
                return cachedGet(`/api/kpi/payouts/bulk?${searchParams.toString()}`, {
                    cacheScope: KPI_PAYOUTS_SCOPE,
                    ttlMs: KPI_PAYOUTS_TTL_MS,
                });
            }),
        );
        responses.forEach((data) => {
            const batchItems = Array.isArray(data?.items) ? data.items : [];
            batchItems.forEach((item) => {
                const batchId = Number(item?.id);
                if (!Number.isFinite(batchId) || batchId <= 0) return;
                itemsById.set(batchId, item);
            });
        });
    }

    const orderedItems = ids
        .map((id) => itemsById.get(id))
        .filter(Boolean);

    return {
        total: orderedItems.length,
        items: orderedItems,
    };
}

export async function deleteKpiPayoutBatch(batchId) {
    const { data } = await api.delete(`/api/kpi/payouts/${batchId}`);
    invalidateKpiPayoutScopes();
    return data;
}

export async function createKpiPayoutPreviewByMetric(payload) {
    const { data } = await api.post('/api/kpi/payouts/preview-metric', payload);
    invalidateKpiPayoutScopes();
    return data;
}

export async function updateKpiPayoutItem(batchId, itemId, payload) {
    const { data } = await api.patch(`/api/kpi/payouts/${batchId}/items/${itemId}`, payload);
    invalidateKpiPayoutScopes();
    return data;
}

export async function deleteKpiPayoutItem(batchId, itemId) {
    const { data } = await api.delete(`/api/kpi/payouts/${batchId}/items/${itemId}`);
    invalidateKpiPayoutScopes();
    return data;
}

export async function postKpiPayoutBatch(batchId, payload) {
    const { data } = await api.post(`/api/kpi/payouts/${batchId}/post`, payload);
    invalidateKpiPayoutScopes();
    return data;
}
