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

const app = createApp(App);

const pinia = createPinia();
pinia.use(persistedState);

app.use(pinia);
setupValidation();

const userStore = useUserStore(pinia);
api.interceptors.request.use((config) => {
    if (userStore.token) {
        config.headers.Authorization = `Bearer ${userStore.token}`;
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

app.use(router);
app.use(Toast, {
    position: POSITION.TOP_RIGHT,
    timeout: 3000,
});

if ('serviceWorker' in navigator && import.meta.env.PROD) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch(() => {});
    });
}

app.mount('#app');
