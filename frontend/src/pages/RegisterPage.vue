<template>
    <div class="auth-container">
        <h2 class="auth-container-heading">Регистрация</h2>
        <form @submit.prevent="handleRegister">
            <Input 
                v-model="registerLogin"
                @blur="checkLoginExists" 
                label="Введите логин из приглашения:" 
            />
            <div v-if="loginExists === true">
                <Input 
                    v-model="registerPassword" 
                    type="password" 
                    required 
                    label="Придумайте пароль:"
                />
            </div>
            <div v-if="loginExists === false" style="color:red">
                Такой логин не найден
            </div>
            <Button 
                type="submit"
                :disabled="!loginExists || !registerPassword"
            >
                Зарегистрироваться
            </Button>
        </form>
        <p class="auth-container-text">
            Есть аккаунт?
            <router-link 
                to="/login"
                class="link"
            >
                Войти
            </router-link>
        </p>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { api } from '@/api'
import Input from '@/components/UI-components/Input.vue'
import Button from '@/components/UI-components/Button.vue'

const registerLogin = ref('')
const loginExists = ref(null) 
const registerPassword = ref('')

async function checkLoginExists() {
    if (!registerLogin.value) {
        loginExists.value = null
        return
    }
    try {
        const resp = await axios.get(`${api}/check-login`, {
            params: { login: registerLogin.value },
        })
        loginExists.value = resp.data.exists
    } catch (e) {
        console.error('Ошибка проверки логина:', e)
        loginExists.value = false
    }
}

async function handleRegister() {
    if (!loginExists.value || !registerPassword.value) return
    try {
        await axios.post(`${serverUrl}/register`, {
            login: registerLogin.value,
            password: registerPassword.value,
        })
        alert('Регистрация успешна! Переходим в личный кабинет')
        window.location.href = '/profile'
    } catch (e) {
        alert('Ошибка регистрации')
        console.error(e)
    }
}
</script>

<style lang="scss">
.auth-container {
    height: 98vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-content: center;
    flex-wrap: wrap;

    &-heading {
        font-size: 26px;
        font-weight: 400;
        text-align: center;
    }

    &-text {
        margin-top: 12px;
        font-size: 16px;
    }
}
</style>
