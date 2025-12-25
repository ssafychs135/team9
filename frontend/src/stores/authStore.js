import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || null)
  const username = ref(localStorage.getItem('username') || null)

  const isAuthenticated = computed(() => !!token.value)

  function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('access_token', newToken) // 브라우저 새로고침 대비
  }

  function setUsername(newUsername) {
    username.value = newUsername
    localStorage.setItem('username', newUsername)
  }

  function logout() {
    token.value = null
    username.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('username')
  }

  const signup = async (payload) => {
    const response = await axios.post('http://localhost:8000/accounts/signup/', payload)
    setToken(response.data.key)
    setUsername(payload.username)
    return response
  }

  const login = async (payload) => {
    const response = await axios.post('http://localhost:8000/accounts/signin/login/', payload)
    setToken(response.data.key)
    // 로그인 응답에 유저 정보가 포함되어 있다면 여기서 setUsername 호출 가능
    setUsername(payload.username)
    return response
  }

  return { token, username, isAuthenticated, setToken, setUsername, logout, signup, login }
})