import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '../api/client'
import type { User } from '../types'
import { setLocale } from '../i18n'
import { setThemeMode } from '../theme'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isLoading = ref<boolean>(true)
  let proactiveRefreshTimer: ReturnType<typeof setInterval> | null = null
  let lastRefreshedAt = Date.now()

  const isAuthenticated = computed(() => !!user.value)

  function startProactiveRefresh() {
    stopProactiveRefresh()
    lastRefreshedAt = Date.now()
    // Proactive refresh every 10 minutes (access token lifetime is 15 minutes)
    proactiveRefreshTimer = setInterval(async () => {
      if (!isAuthenticated.value) return
      try {
        await apiClient.post('/auth/refresh/')
        lastRefreshedAt = Date.now()
      } catch (e) {
        console.warn('Proactive token refresh attempt failed:', e)
      }
    }, 10 * 60 * 1000)
  }

  function stopProactiveRefresh() {
    if (proactiveRefreshTimer) {
      clearInterval(proactiveRefreshTimer)
      proactiveRefreshTimer = null
    }
  }

  // Check refresh on window focus / tab visibility change if tab was in background > 10m
  if (typeof window !== 'undefined') {
    document.addEventListener('visibilitychange', async () => {
      if (document.visibilityState === 'visible' && isAuthenticated.value) {
        const elapsedMinutes = (Date.now() - lastRefreshedAt) / (1000 * 60)
        if (elapsedMinutes >= 10) {
          try {
            await apiClient.post('/auth/refresh/')
            lastRefreshedAt = Date.now()
          } catch (e) {
            console.warn('Visibility change token refresh failed:', e)
          }
        }
      }
    })
  }

  async function fetchMe() {
    isLoading.value = true
    try {
      const response = await apiClient.get<User>('/auth/me/')
      user.value = response.data
      if (user.value?.preferred_language) {
        setLocale(user.value.preferred_language, { syncBackend: false })
      }
      if (user.value?.preferred_theme) {
        setThemeMode(user.value.preferred_theme, { syncBackend: false })
      }
      startProactiveRefresh()
      return user.value
    } catch {
      user.value = null
      stopProactiveRefresh()
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function login(credentials: { username: string; password: string }) {
    const response = await apiClient.post<{ message: string; user: User }>('/auth/login/', credentials)
    user.value = response.data.user
    if (user.value?.preferred_language) {
      setLocale(user.value.preferred_language, { syncBackend: false })
    }
    if (user.value?.preferred_theme) {
      setThemeMode(user.value.preferred_theme, { syncBackend: false })
    }
    startProactiveRefresh()
    return response.data
  }

  async function register(data: { username: string; email: string; password: string; invite_code: string }) {
    const response = await apiClient.post<{ message: string; user: User }>('/auth/register/', data)
    user.value = response.data.user
    if (user.value?.preferred_language) {
      setLocale(user.value.preferred_language, { syncBackend: false })
    }
    if (user.value?.preferred_theme) {
      setThemeMode(user.value.preferred_theme, { syncBackend: false })
    }
    startProactiveRefresh()
    return response.data
  }

  async function logout() {
    try {
      await apiClient.post('/auth/logout/')
    } finally {
      user.value = null
      stopProactiveRefresh()
    }
  }

  async function generateTelegramConnect() {
    const response = await apiClient.post<{ connect_token: string; deep_link: string; instructions: string }>('/auth/telegram/connect-token/')
    return response.data
  }

  async function disconnectTelegram() {
    const response = await apiClient.post<{ message: string; user: User }>('/auth/telegram/disconnect/')
    user.value = response.data.user
    return response.data
  }

  async function changePassword(payload: { current_password: string; new_password: string }) {
    const response = await apiClient.post<{ message: string; revoked_sessions_count: number }>('/auth/password/change/', payload)
    return response.data
  }

  async function updatePreferences(payload: { preferred_language?: 'en' | 'th'; preferred_theme?: 'dark' | 'light' | 'system' }) {
    const response = await apiClient.patch<User>('/auth/me/', payload)
    user.value = response.data
    return user.value
  }

  return {
    updatePreferences,
    user,
    isLoading,
    isAuthenticated,
    fetchMe,
    login,
    register,
    logout,
    generateTelegramConnect,
    disconnectTelegram,
    changePassword,
  }
})
