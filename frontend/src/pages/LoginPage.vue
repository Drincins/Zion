<template>
    <div class="wrapper authorization">
        <h1 class="authorization-heading">
			Авторизация
		</h1>
        <form @submit.prevent="handleLogin">
            <Input v-model="login" label="Логин:" />
            <Input v-model="password" label="Пароль:" type="password" />
            <Button type="submit">
              	Войти
            </Button>
        </form>
        <p class="authorization-text">
			Нет аккаунта?
			<router-link
				to="/register"
				class="link"
			>
				Зарегистрироваться
			</router-link>
        </p>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { api } from '@/api'
import { useRouter } from 'vue-router'
import Input from '@/components/UI-components/Input.vue'
import Button from '@/components/UI-components/Button.vue'

const router = useRouter()

const login = ref('')
const password = ref('')

// ХАРДКОД ДЛЯ ТЕСТА, ПОТОМ УДАЛИТЬ
const users = [
  { login: 'admin', password: 'admin' },
  { login: 'admin1', password: 'admin1' },
]

// ВЕРНУТЬ
// async function handleLogin() {
//   try {
//     const resp = await axios.post(`${api}/login`, {
//       login: login.value,
//       password: password.value,
//     })
//     if (resp.data.success) {
//       alert('Вход выполнен успешно')
//       window.location.href = '/profile'
//     } else {
//       alert('Неверный логин или пароль')
//     }
//   } catch (e) {
//     alert('Ошибка входа')
//     console.error(e)
//   }
// }

// УДАЛИТЬ
function handleLogin() {
  const user = users.find(u => u.login === login.value && u.password === password.value)
  if (user) {
    alert('Вход успешен')
    router.push('/profile')
  } else {
    alert('Неверный логин или пароль')
  }
}
</script>

<style lang="scss">
@import '@/assets/styles/pages/login.scss';
</style>
