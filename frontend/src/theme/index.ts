/**
 * Reactive theme engine: Dark | Light | System with anti-FOUC persistence.
 * Applies <html data-theme> + color-scheme, syncs to localStorage + backend.
 */
import { computed, ref } from 'vue'
import apiClient from '../api/client'

export type ThemeMode = 'dark' | 'light' | 'system'
export type ResolvedTheme = 'dark' | 'light'

const THEME_STORAGE_KEY = 'life_os_theme'

function readInitialMode(): ThemeMode {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'dark' || stored === 'light' || stored === 'system') return stored
  } catch {
    /* localStorage unavailable */
  }
  return 'dark'
}

const mediaQuery = typeof window !== 'undefined'
  ? window.matchMedia('(prefers-color-scheme: light)')
  : null

export const themeMode = ref<ThemeMode>(readInitialMode())
const systemPrefersLight = ref<boolean>(mediaQuery?.matches ?? false)

export const resolvedTheme = computed<ResolvedTheme>(() => {
  if (themeMode.value === 'system') {
    return systemPrefersLight.value ? 'light' : 'dark'
  }
  return themeMode.value as ResolvedTheme
})

export const isLightTheme = computed(() => resolvedTheme.value === 'light')

function applyThemeToDom() {
  const root = document.documentElement
  root.dataset.theme = resolvedTheme.value
  root.dataset.themeMode = themeMode.value
  root.style.colorScheme = resolvedTheme.value
}

export function setThemeMode(nextMode: ThemeMode, options?: { syncBackend?: boolean }) {
  themeMode.value = nextMode
  try {
    localStorage.setItem(THEME_STORAGE_KEY, nextMode)
  } catch {
    /* localStorage unavailable */
  }
  applyThemeToDom()

  if (options?.syncBackend !== false) {
    apiClient.patch('/auth/me/', { preferred_theme: nextMode }).catch(() => {
      /* ignored when unauthenticated */
    })
  }
}

export function initTheme() {
  applyThemeToDom()
  mediaQuery?.addEventListener('change', (e: MediaQueryListEvent) => {
    systemPrefersLight.value = e.matches
    applyThemeToDom()
  })
}
