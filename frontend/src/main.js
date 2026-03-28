import { createApp } from 'vue';
import { createPinia } from 'pinia';
import '@/assets/styles/base.scss';
import App from './App.vue';
import router from './router';
import Toast, { POSITION } from 'vue-toastification';
import 'vue-toastification/dist/index.css';
import { persistedState } from './plugins/persist';
import { setupValidation } from './plugins/validation';
import { api } from './api';
import { useUserStore } from './stores/user';
import { useThemeStore } from './stores/theme';
import { fetchCurrentSessionUser } from './api/auth';

const app = createApp(App);

const pinia = createPinia();
pinia.use(persistedState);

app.use(pinia);
setupValidation();

const userStore = useUserStore(pinia);
const themeStore = useThemeStore(pinia);
api.interceptors.request.use((config) => {
    if (userStore.token) {
        config.headers.Authorization = `Bearer ${userStore.token}`;
    } else if (config.headers?.Authorization) {
        delete config.headers.Authorization;
    }
    return config;
});
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error?.response?.status === 403) {
            userStore.setFiredFromDetail(error?.response?.data?.detail);
        }
        return Promise.reject(error);
    },
);

async function bootstrapUserSession() {
    if (userStore.isAuthenticated) {
        return;
    }

    try {
        const user = await fetchCurrentSessionUser();
        if (!user?.id) {
            return;
        }
        userStore.setUser({
            id: user.id,
            login: user.username ?? '',
            firstName: user.first_name ?? '',
            lastName: user.last_name ?? '',
            fullName: `${user.first_name ?? ''} ${user.last_name ?? ''}`.trim(),
            isFired: false,
        });
        await userStore.fetchUserFromApi();
    } catch (error) {
        if (error?.response?.status && error.response.status !== 401) {
            console.error('Ошибка восстановления сессии:', error);
        }
        userStore.clearUser();
        localStorage.removeItem('pinia-user');
        sessionStorage.removeItem('pinia-user');
    }
}

app.use(Toast, {
    position: POSITION.TOP_RIGHT,
    timeout: 3000,
});

if ('serviceWorker' in navigator && import.meta.env.PROD) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch(() => {});
    });
}

themeStore.resetTheme();
await bootstrapUserSession();
if (userStore.isAuthenticated) {
    await themeStore.bootstrapTheme();
}

app.use(router);

app.mount('#app');
