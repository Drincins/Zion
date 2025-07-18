import { createApp } from 'vue'
import '@/assets/styles/base.scss'
import App from './App.vue'
import router from './router'
import Toast, { POSITION } from 'vue-toastification'
import 'vue-toastification/dist/index.css'

createApp(App)
	.use(router)
	.use(Toast, {
		position: POSITION.TOP_RIGHT,
		timeout: 3000,
	})
	.mount('#app')