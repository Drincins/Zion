export const serverUrl = import.meta.env.VITE_SERVER_URL

import axios from 'axios'

export const api = axios.create({
	baseURL: serverUrl,
})