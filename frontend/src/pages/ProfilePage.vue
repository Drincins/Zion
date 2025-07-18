<template>
  <div class="auth-container">
    
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { api } from '@/api'

const profile = ref({
  fullName: '',
  companyName: '',
})

async function saveProfile() {
  try {
    await axios.post(`${api}/save-profile`, profile.value)
    alert('Данные сохранены')
  } catch (e) {
    alert('Ошибка сохранения данных')
    console.error(e)
  }
}
</script>

<style lang="scss">
.auth-container {
  max-width: 400px;
  margin: 50px auto;
  font-family: Arial, sans-serif;
}

label {
  display: block;
  margin-top: 10px;
}

input {
  width: 100%;
  padding: 6px;
  margin-top: 4px;
  box-sizing: border-box;
}

button {
  margin-top: 15px;
  padding: 8px 16px;
}
</style>
