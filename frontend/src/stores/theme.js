import { defineStore } from 'pinia';
import { fetchThemePreference, updateThemePreference } from '@/api';
import {
    DEFAULT_INTERFACE_THEME,
    DEFAULT_THEME_MODE,
    INTERFACE_THEME_CATALOG,
    THEME_MODE_KEYS,
    applyInterfaceThemeToDocument,
    applyThemeModeToDocument,
    normalizeInterfaceTheme,
    normalizeThemeMode,
} from '@/utils/theme';

export const useThemeStore = defineStore('theme', {
    state: () => ({
        mode: DEFAULT_THEME_MODE,
        interfaceTheme: DEFAULT_INTERFACE_THEME,
        canCustomizeInterfaceTheme: false,
        availableModes: [...THEME_MODE_KEYS],
        availableInterfaceThemes: [DEFAULT_INTERFACE_THEME],
        isLoaded: false,
        isSaving: false,
    }),
    getters: {
        interfaceThemeOptions(state) {
            const allowed = new Set(
                state.canCustomizeInterfaceTheme && state.availableInterfaceThemes.length
                    ? state.availableInterfaceThemes
                    : [DEFAULT_INTERFACE_THEME],
            );
            return INTERFACE_THEME_CATALOG
                .filter((item) => allowed.has(item.key))
                .map((item) => ({
                    value: item.key,
                    label: item.label,
                }));
        },
    },
    actions: {
        applyMode(mode, options = {}) {
            const normalized = applyThemeModeToDocument(mode, options);
            this.mode = normalized;
            return normalized;
        },
        applyInterfaceTheme(interfaceTheme, options = {}) {
            const normalized = applyInterfaceThemeToDocument(interfaceTheme, options);
            this.interfaceTheme = normalized;
            return normalized;
        },
        resetTheme() {
            this.canCustomizeInterfaceTheme = false;
            this.availableModes = [...THEME_MODE_KEYS];
            this.availableInterfaceThemes = [DEFAULT_INTERFACE_THEME];
            this.applyMode(DEFAULT_THEME_MODE);
            this.applyInterfaceTheme(DEFAULT_INTERFACE_THEME);
            this.isLoaded = true;
            this.isSaving = false;
        },
        applyThemePayload(payload = {}) {
            const availableModes = Array.from(
                new Set(
                    (Array.isArray(payload?.available_modes) ? payload.available_modes : [])
                        .map((mode) => normalizeThemeMode(mode, { fallback: '' }))
                        .filter(Boolean),
                ),
            );
            const canCustomizeInterfaceTheme = Boolean(payload?.can_customize_interface_theme);
            const availableInterfaceThemes = Array.from(
                new Set(
                    (Array.isArray(payload?.available_interface_themes) ? payload.available_interface_themes : [])
                        .map((theme) => normalizeInterfaceTheme(theme, { fallback: '' }))
                        .filter(Boolean),
                ),
            );

            const allowedModes = availableModes.length ? availableModes : [...THEME_MODE_KEYS];
            const allowedInterfaceThemes = canCustomizeInterfaceTheme && availableInterfaceThemes.length
                ? availableInterfaceThemes
                : [DEFAULT_INTERFACE_THEME];

            this.canCustomizeInterfaceTheme = canCustomizeInterfaceTheme;
            this.availableModes = allowedModes;
            this.availableInterfaceThemes = allowedInterfaceThemes;
            this.applyMode(payload?.mode, {
                fallback: DEFAULT_THEME_MODE,
                allowed: allowedModes,
            });
            this.applyInterfaceTheme(payload?.interface_theme, {
                fallback: DEFAULT_INTERFACE_THEME,
                allowed: allowedInterfaceThemes,
            });
            this.isLoaded = true;
        },
        async bootstrapTheme() {
            try {
                const payload = await fetchThemePreference();
                this.applyThemePayload(payload || {});
            } catch {
                this.resetTheme();
            }
        },
        async savePreferences(payload = {}) {
            const hasMode = Object.prototype.hasOwnProperty.call(payload, 'mode');
            const hasInterfaceTheme = Object.prototype.hasOwnProperty.call(payload, 'interface_theme');
            if (!hasMode && !hasInterfaceTheme) {
                return { ok: false };
            }

            const allowedModes = this.availableModes.length ? this.availableModes : [...THEME_MODE_KEYS];
            const allowedInterfaceThemes = this.canCustomizeInterfaceTheme && this.availableInterfaceThemes.length
                ? this.availableInterfaceThemes
                : [DEFAULT_INTERFACE_THEME];

            const requestedMode = hasMode
                ? normalizeThemeMode(payload.mode, {
                    fallback: this.mode,
                    allowed: allowedModes,
                })
                : this.mode;
            const requestedInterfaceTheme = hasInterfaceTheme
                ? normalizeInterfaceTheme(payload.interface_theme, {
                    fallback: this.interfaceTheme,
                    allowed: allowedInterfaceThemes,
                })
                : this.interfaceTheme;

            const modeChanged = requestedMode !== this.mode;
            const interfaceThemeChanged = requestedInterfaceTheme !== this.interfaceTheme;
            if (!modeChanged && !interfaceThemeChanged) {
                return {
                    ok: true,
                    mode: this.mode,
                    interfaceTheme: this.interfaceTheme,
                };
            }

            const previousMode = this.mode;
            const previousInterfaceTheme = this.interfaceTheme;
            this.isSaving = true;
            this.applyMode(requestedMode, {
                fallback: previousMode,
                allowed: allowedModes,
            });
            this.applyInterfaceTheme(requestedInterfaceTheme, {
                fallback: previousInterfaceTheme,
                allowed: allowedInterfaceThemes,
            });

            try {
                const nextPayload = {};
                if (modeChanged) {
                    nextPayload.mode = requestedMode;
                }
                if (interfaceThemeChanged) {
                    nextPayload.interface_theme = requestedInterfaceTheme;
                }
                const response = await updateThemePreference(nextPayload);
                this.applyThemePayload(response || {});
                return {
                    ok: true,
                    mode: this.mode,
                    interfaceTheme: this.interfaceTheme,
                };
            } catch (error) {
                this.applyMode(previousMode, {
                    fallback: DEFAULT_THEME_MODE,
                    allowed: allowedModes,
                });
                this.applyInterfaceTheme(previousInterfaceTheme, {
                    fallback: DEFAULT_INTERFACE_THEME,
                    allowed: allowedInterfaceThemes,
                });
                return { ok: false, error };
            } finally {
                this.isSaving = false;
            }
        },
        async saveMode(nextMode) {
            return await this.savePreferences({ mode: nextMode });
        },
        async saveInterfaceTheme(nextInterfaceTheme) {
            return await this.savePreferences({ interface_theme: nextInterfaceTheme });
        },
    },
});
