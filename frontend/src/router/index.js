import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '@/pages/LoginPage.vue'
import RegisterPage from '@/pages/RegisterPage.vue'
import ProfilePage from '@/pages/ProfilePage.vue'

const routes = [
	{ path: '/', redirect: '/login' },
	{ path: '/login', component: LoginPage },
	{ path: '/register', component: RegisterPage },
	{ path: '/profile', component: ProfilePage },
]

const router = createRouter({
	history: createWebHistory(),
	routes,
})

export default router