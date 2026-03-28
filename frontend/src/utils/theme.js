export const DEFAULT_THEME_MODE = 'dark';
export const DEFAULT_INTERFACE_THEME = 'classic';

export const THEME_MODE_KEYS = Object.freeze(['light', 'dark']);
export const INTERFACE_THEME_CATALOG = Object.freeze([
    { key: 'classic', label: 'Классическая' },
    { key: 'blue', label: 'Синяя' },
    { key: 'green', label: 'Зеленая' },
    { key: 'red', label: 'Красная' },
    { key: 'pink', label: 'Розовая' },
    { key: 'purple', label: 'Фиолетовая' },
]);
export const INTERFACE_THEME_KEYS = INTERFACE_THEME_CATALOG.map((theme) => theme.key);
export const INTERFACE_THEME_CLASS_NAMES = INTERFACE_THEME_KEYS.map((key) => `interface-${key}`);

export function normalizeThemeMode(value, { fallback = DEFAULT_THEME_MODE, allowed = THEME_MODE_KEYS } = {}) {
    const normalized = String(value || '').trim().toLowerCase();
    if (allowed.includes(normalized)) {
        return normalized;
    }
    return fallback;
}

export function normalizeInterfaceTheme(value, { fallback = DEFAULT_INTERFACE_THEME, allowed = INTERFACE_THEME_KEYS } = {}) {
    const normalized = String(value || '').trim().toLowerCase();
    if (allowed.includes(normalized)) {
        return normalized;
    }
    return fallback;
}

export function applyThemeModeToDocument(value, options = {}) {
    const normalized = normalizeThemeMode(value, options);
    if (typeof document === 'undefined') {
        return normalized;
    }
    const root = document.documentElement;
    root.classList.remove(...THEME_MODE_KEYS);
    root.classList.add(normalized);
    return normalized;
}

export function applyInterfaceThemeToDocument(value, options = {}) {
    const normalized = normalizeInterfaceTheme(value, options);
    if (typeof document === 'undefined') {
        return normalized;
    }
    const root = document.documentElement;
    root.classList.remove(...INTERFACE_THEME_CLASS_NAMES);
    root.classList.add(`interface-${normalized}`);
    return normalized;
}
