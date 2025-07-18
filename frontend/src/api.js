import axios from 'axios'

export const serverUrl = import.meta.env.VITE_SERVER_URL

export const api = axios.create({
	baseURL: serverUrl,
})