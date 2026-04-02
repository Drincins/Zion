import axios from 'axios';
import { beginApiLoading, endApiLoading } from '@/stores/routeLoading';

// Base URL is resolved at runtime:
// 1) use Vite env value if it is not localhost/127.*;
// 2) otherwise fallback to current origin.
const envUrl = import.meta.env.VITE_SERVER_URL && import.meta.env.VITE_SERVER_URL.trim();
const isLocalEnv = envUrl && /localhost|127\.0\.0\.1/i.test(envUrl);
const runtimeServerUrl = envUrl && !isLocalEnv ? envUrl : window.location.origin;

export const serverUrl = runtimeServerUrl;

export const api = axios.create({
    baseURL: runtimeServerUrl,
    withCredentials: true,
});

function shouldTrackGlobalLoading(config) {
    if (!config) {
        return false;
    }
    if (config.skipGlobalLoading === true) {
        return false;
    }
    if (config.meta?.skipGlobalLoading === true) {
        return false;
    }
    return true;
}

function finishGlobalLoadingForConfig(config) {
    if (!config?.__globalLoadingTracked) {
        return;
    }
    config.__globalLoadingTracked = false;
    endApiLoading();
}

api.interceptors.request.use(
    (config) => {
        if (shouldTrackGlobalLoading(config)) {
            config.__globalLoadingTracked = true;
            beginApiLoading();
        }
        return config;
    },
    (error) => {
        finishGlobalLoadingForConfig(error?.config);
        return Promise.reject(error);
    },
);

api.interceptors.response.use(
    (response) => {
        finishGlobalLoadingForConfig(response?.config);
        return response;
    },
    (error) => {
        finishGlobalLoadingForConfig(error?.config);
        return Promise.reject(error);
    },
);

const API_CACHE_PREFIX = `zion-api-cache:v1:${runtimeServerUrl}:`;
const apiMemoryCache = new Map();
const apiInflight = new Map();
const apiCacheGenerations = new Map();

function getCacheUserKey() {
    try {
        const raw = sessionStorage.getItem('pinia-user') || localStorage.getItem('pinia-user');
        if (!raw) {
            return 'anon';
        }
        const parsed = JSON.parse(raw);
        const id = parsed?.id;
        return id !== null && id !== undefined ? String(id) : 'anon';
    } catch {
        return 'anon';
    }
}

function getCacheGenerationKey(scope) {
    return `${getCacheUserKey()}:${scope}`;
}

function bumpCacheGeneration(scope) {
    const key = getCacheGenerationKey(scope);
    apiCacheGenerations.set(key, (apiCacheGenerations.get(key) || 0) + 1);
    return apiCacheGenerations.get(key);
}

export function invalidateCacheScope(scope) {
    const userKey = getCacheUserKey();
    bumpCacheGeneration(scope);
    const prefix = `${API_CACHE_PREFIX}${userKey}:${scope}:`;

    for (const key of Array.from(apiMemoryCache.keys())) {
        if (key.startsWith(prefix)) {
            apiMemoryCache.delete(key);
        }
    }

    for (const key of Array.from(apiInflight.keys())) {
        if (key.startsWith(prefix)) {
            apiInflight.delete(key);
        }
    }

    if (typeof sessionStorage === 'undefined') {
        return;
    }
    try {
        for (let i = sessionStorage.length - 1; i >= 0; i--) {
            const key = sessionStorage.key(i);
            if (key && key.startsWith(prefix)) {
                sessionStorage.removeItem(key);
            }
        }
    } catch {
        // ignore quota / access issues
    }
}

function buildStableQueryString(params = {}) {
    const keys = Object.keys(params || {}).sort();
    const searchParams = new URLSearchParams();
    keys.forEach((key) => {
        const value = params[key];
        if (value === null || value === undefined) {
            return;
        }
        if (Array.isArray(value)) {
            value.forEach((item) => {
                if (item === null || item === undefined) {
                    return;
                }
                searchParams.append(key, String(item));
            });
            return;
        }
        searchParams.append(key, String(value));
    });
    return searchParams.toString();
}

function getApiCacheKey(scope, url, params) {
    const qs = buildStableQueryString(params);
    const userKey = getCacheUserKey();
    return `${API_CACHE_PREFIX}${userKey}:${scope}:${url}?${qs}`;
}

function readSessionCache(key) {
    if (typeof sessionStorage === 'undefined') {
        return null;
    }
    try {
        const raw = sessionStorage.getItem(key);
        if (!raw) {
            return null;
        }
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== 'object') {
            return null;
        }
        const expiresAt = typeof parsed.expiresAt === 'number' ? parsed.expiresAt : 0;
        if (expiresAt && Date.now() > expiresAt) {
            sessionStorage.removeItem(key);
            return null;
        }
        return parsed.value ?? null;
    } catch {
        return null;
    }
}

function writeSessionCache(key, value, ttlMs) {
    if (typeof sessionStorage === 'undefined') {
        return;
    }
    try {
        const expiresAt = ttlMs ? Date.now() + ttlMs : 0;
        sessionStorage.setItem(key, JSON.stringify({ expiresAt, value }));
    } catch {
        // ignore quota / serialization issues
    }
}

function readMemoryCache(key) {
    const entry = apiMemoryCache.get(key);
    if (!entry) {
        return null;
    }
    if (entry.expiresAt && Date.now() > entry.expiresAt) {
        apiMemoryCache.delete(key);
        return null;
    }
    return entry.value;
}

function writeMemoryCache(key, value, ttlMs) {
    const expiresAt = ttlMs ? Date.now() + ttlMs : 0;
    apiMemoryCache.set(key, { value, expiresAt });
}

function throwIfAborted(signal) {
    if (signal?.aborted) {
        throw new axios.CanceledError('Request canceled');
    }
}

export async function cachedGet(
    url,
    { params = {}, cacheScope = 'default', ttlMs = 0, signal, skipGlobalLoading = false } = {},
) {
    throwIfAborted(signal);
    const generationKey = getCacheGenerationKey(cacheScope);
    const generation = apiCacheGenerations.get(generationKey) || 0;
    const cacheKey = getApiCacheKey(cacheScope, url, params);

    const memValue = readMemoryCache(cacheKey);
    if (memValue !== null) {
        return memValue;
    }

    const sessionValue = readSessionCache(cacheKey);
    if (sessionValue !== null) {
        writeMemoryCache(cacheKey, sessionValue, ttlMs);
        return sessionValue;
    }

    if (!signal && apiInflight.has(cacheKey)) {
        return await apiInflight.get(cacheKey);
    }

    const requestFactory = () => api
        .get(url, { params, signal, skipGlobalLoading })
        .then(({ data }) => {
            if ((apiCacheGenerations.get(generationKey) || 0) === generation) {
                writeMemoryCache(cacheKey, data, ttlMs);
                writeSessionCache(cacheKey, data, ttlMs);
            }
            return data;
        });

    if (signal) {
        return await requestFactory();
    }

    const request = requestFactory().finally(() => {
        apiInflight.delete(cacheKey);
    });

    apiInflight.set(cacheKey, request);
    return await request;
}

export function buildQueryParams(params = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value === null || value === undefined) {
            return;
        }
        if (Array.isArray(value)) {
            value.forEach((item) => {
                if (item === null || item === undefined) {
                    return;
                }
                searchParams.append(key, String(item));
            });
            return;
        }
        searchParams.append(key, String(value));
    });
    return searchParams;
}
