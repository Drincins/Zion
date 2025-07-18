import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '@/pages/LoginPage.vue'
import ProfilePage from '@/pages/ProfilePage.vue'

const routes = [
	{ path: '/', redirect: '/login' },
	{ path: '/login', component: LoginPage },
	{ path: '/profile', component: ProfilePage },
]

const router = createRouter({
	history: createWebHistory(),
	routes,
})

export default router