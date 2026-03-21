export function persistedState(context) {
    const { store } = context;
    const key = `pinia-${store.$id}`;
    const fromStorage = localStorage.getItem(key);
    if (fromStorage) {
        try {
            store.$patch(JSON.parse(fromStorage));
        } catch {
            localStorage.removeItem(key);
        }
    }
    store.$subscribe((_, state) => {
        try {
            localStorage.setItem(key, JSON.stringify(state));
        } catch {
            // ignore quota or serialization errors
        }
    });
}
