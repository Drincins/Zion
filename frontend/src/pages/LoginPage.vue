<template>
    <div class="wrapper authorization">
        <div class="authorization__logo">
            <img
                class="authorization__logo-image"
                src="@/assets/images/logo.png"
                alt="Logo"
            />
        </div>
        <form class="authorization-form" @submit.prevent="handleLogin">
            <div class="authorization-form-input">
                <Input v-model="username" placeholder="Логин:" />
                <Input v-model="password" placeholder="Пароль:" type="password" />
            </div>
            <Button type="submit" class="authorization-form-button"> Войти </Button>
        </form>
        <RouterLink to="/" class="authorization__link">
            Перейти к авторизации в Тайм трекер
        </RouterLink>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { loginUser } from '@/api';
import { useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Input from '@/components/UI-components/Input.vue';
import Button from '@/components/UI-components/Button.vue';

const router = useRouter();
const toast = useToast();
const userStore = useUserStore();

const username = ref('');
const password = ref('');

async function handleLogin() {
    try {
        const payload = await loginUser(username.value, password.value);
        const user = payload?.user || {};
        const userId = user.id;
        const login = user.username ?? username.value;
        const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim();

        if (userId) {
            userStore.setUser({
                id: userId,
                login,
                fullName,
                firstName: user.first_name ?? '',
                lastName: user.last_name ?? '',
                isFired: false,
            });
            await userStore.fetchUserFromApi();
            router.push('/admin');
        } else {
            toast.error('Ошибка: не удалось извлечь ID пользователя');
        }
    } catch (e) {
        if (e.response?.status === 401) {
            toast.error('Неверный логин или пароль');
        } else {
            toast.error('Ошибка входа');
        }
        console.error(e);
    }
}
</script>

<style lang="scss">
@use '@/assets/styles/pages/login.scss' as *;
</style>
