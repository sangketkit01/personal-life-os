/**
 * i18n entry point: reactive locale state, persistence, backend sync,
 * phrase translation helper and CE-era locale date formatting.
 */
import { computed, ref } from 'vue'
import apiClient from '../api/client'
import { applyDomTranslation, installI18nObserver } from './domTranslator'
import { translatePhraseToThai } from './dictionaries'
import { MESSAGES } from './messages'
import type { AppLocale, TranslationParams } from './types'

export type { AppLocale }
export { translatePhraseToThai }

const LOCALE_STORAGE_KEY = 'life_os_locale'

function readInitialLocale(): AppLocale {
  try {
    const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
    if (stored === 'th' || stored === 'en') return stored
  } catch {
    /* localStorage unavailable */
  }
  return 'en'
}

export const locale = ref<AppLocale>(readInitialLocale())
export const isThai = computed(() => locale.value === 'th')

function persistLocale(next: AppLocale) {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, next)
  } catch {
    /* localStorage unavailable */
  }
  document.documentElement.lang = next
}

/**
 * Switch the app language:
 * - updates the reactive locale (whole UI reacts instantly),
 * - persists to localStorage + <html lang>,
 * - runs the DOM translator now and again after Vue flushes,
 * - PATCHes the user's preferred_language on the backend by default.
 */
export function setLocale(nextLocale: AppLocale, options?: { syncBackend?: boolean }) {
  locale.value = nextLocale
  persistLocale(nextLocale)
  applyDomTranslation(nextLocale)
  requestAnimationFrame(() => applyDomTranslation(locale.value))
  // One late pass for views mounted by async route components
  window.setTimeout(() => applyDomTranslation(locale.value), 350)

  if (options?.syncBackend !== false) {
    apiClient.patch('/auth/me/', { preferred_language: nextLocale }).catch(() => {
      /* ignored when unauthenticated */
    })
  }
}

/** Mount the MutationObserver + initial translation pass. Call once in main.ts. */
export function initI18n() {
  document.documentElement.lang = locale.value
  installI18nObserver()
  applyDomTranslation(locale.value)
  requestAnimationFrame(() => applyDomTranslation(locale.value))
  window.setTimeout(() => applyDomTranslation(locale.value), 400)
}

/**
 * Translate a key or exact English phrase (TH mode), interpolating
 * {param} placeholders. Returns the input untouched in EN mode.
 */
export function t(keyOrPhrase: string, params?: TranslationParams): string {
  // 1. Explicit message key (dotted) - context-correct, wins always
  let out: string | undefined = MESSAGES[locale.value]?.[keyOrPhrase]
  if (out === undefined) {
    out = MESSAGES.en?.[keyOrPhrase]
  }
  // 2. Fallback: exact-phrase DOM dictionary (TH mode only)
  if (out === undefined && locale.value === 'th') {
    out = translatePhraseToThai(keyOrPhrase) ?? keyOrPhrase
  }
  if (out === undefined) {
    out = keyOrPhrase
  }
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      out = out.replaceAll(`{${key}}`, String(value))
    }
  }
  return out
}

const MONTH_SHORT_TH = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
const MONTH_LONG_TH = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
const MONTH_SHORT_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const MONTH_LONG_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

/**
 * Locale-aware date formatting with Christian Era years in BOTH languages
 * (never Buddhist Era 2569 - financial/market timelines stay CE-consistent).
 * - short:    24 Oct 2026      |  24 ต.ค. 2026
 * - long:     24 October 2026  |  24 ตุลาคม 2026
 * - datetime: 24 Oct 2026, 14:30 | 24 ต.ค. 2026, 14:30
 */
export function formatLocaleDate(
  dateInput: string | Date | null | undefined,
  style: 'short' | 'long' | 'datetime' = 'short'
): string {
  if (!dateInput) return ''
  const d = dateInput instanceof Date ? dateInput : new Date(dateInput)
  if (isNaN(d.getTime())) return ''

  const pad = (n: number) => String(n).padStart(2, '0')
  const day = d.getDate()
  // CE year via getFullYear() - NEVER d.getFullYear() + 543
  const year = d.getFullYear()
  const month = d.getMonth()
  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`

  if (locale.value === 'th') {
    if (style === 'datetime') return `${day} ${MONTH_SHORT_TH[month]} ${year}, ${time}`
    if (style === 'long') return `${day} ${MONTH_LONG_TH[month]} ${year}`
    return `${day} ${MONTH_SHORT_TH[month]} ${year}`
  }
  if (style === 'datetime') return `${day} ${MONTH_SHORT_EN[month]} ${year}, ${time}`
  if (style === 'long') return `${day} ${MONTH_LONG_EN[month]} ${year}`
  return `${day} ${MONTH_SHORT_EN[month]} ${year}`
}
