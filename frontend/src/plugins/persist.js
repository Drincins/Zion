function resolveStorage(storeId) {
    if (storeId === 'user') {
        return sessionStorage;
    }
    return localStorage;
}

function resolveLegacyStorage(storeId) {
    if (storeId === 'user') {
        return localStorage;
    }
    return null;
}

export function persistedState(context) {
    const { store } = context;
    if (store.$id === 'theme') {
        return;
    }
    const key = `pinia-${store.$id}`;
    const storage = resolveStorage(store.$id);
    const legacyStorage = resolveLegacyStorage(store.$id);
    const fromStorage = storage.getItem(key) || legacyStorage?.getItem(key);
    if (fromStorage) {
        try {
            store.$patch(JSON.parse(fromStorage));
            if (legacyStorage && legacyStorage !== storage) {
                legacyStorage.removeItem(key);
                storage.setItem(key, JSON.stringify(store.$state));
            }
        } catch {
            storage.removeItem(key);
            legacyStorage?.removeItem(key);
        }
    }
    store.$subscribe((_, state) => {
        try {
            storage.setItem(key, JSON.stringify(state));
            legacyStorage?.removeItem(key);
        } catch {
            // ignore quota or serialization errors
        }
    });
}
