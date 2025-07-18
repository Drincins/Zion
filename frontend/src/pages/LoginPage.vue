<template>
    <div class="wrapper authorization">
        <h1 class="authorization-heading">
			Авторизация
		</h1>
        <form @submit.prevent="handleLogin">
            <Input v-model="username" label="Логин:" />
            <Input v-model="password" label="Пароль:" type="password" />
            <Button type="submit">
              	Войти
            </Button>
        </form>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { api } from '@/api'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import Input from '@/components/UI-components/Input.vue'
import Button from '@/components/UI-components/Button.vue'

const router = useRouter()
const toast = useToast()

const username = ref('')
const password = ref('')

async function handleLogin() {
    try {
        const resp = await api.post('/api/login', {
            username: username.value,
            password: password.value,
        })
        const token = resp.data.access_token
        if (token) {
            localStorage.setItem('token', token)
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`
            router.push('/profile')
        }
    } catch (e) {
        if (e.response?.status === 401) {
            toast.error('Неверный логин или пароль')
        } else {
            toast.error('Ошибка входа')
        }
        console.error(e)
    }
}
</script>

<style lang="scss">
@use '@/assets/styles/pages/login.scss' as *;
</style>
