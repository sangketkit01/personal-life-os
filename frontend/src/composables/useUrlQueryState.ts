import { ref, watch, type Ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'

/**
 * useUrlQueryState
 * Syncs a reactive ref with a URL query parameter.
 * Keeps URLs bookmarkable, shareable, and refresh-resilient.
 */
export function useUrlQueryState<T extends string | number | boolean>(
  paramKey: string,
  defaultValue: T,
  options?: {
    parse?: (val: string) => T
    serialize?: (val: T) => string
  }
): Ref<T> {
  const router = useRouter()
  const route = useRoute()

  const parse = options?.parse || ((val: string) => {
    if (typeof defaultValue === 'number') return Number(val) as T
    if (typeof defaultValue === 'boolean') return (val === 'true') as T
    return val as T
  })

  const serialize = options?.serialize || ((val: T) => String(val))

  // Initial value from current route query or default
  const initialRaw = route.query[paramKey]
  const initialValue = initialRaw !== undefined && initialRaw !== null && initialRaw !== ''
    ? parse(String(initialRaw))
    : defaultValue

  const state = ref<T>(initialValue) as Ref<T>

  // Sync ref change -> URL query
  watch(state, (newVal) => {
    const currentQuery = { ...route.query }
    if (newVal === defaultValue || newVal === '' || newVal === undefined || newVal === null) {
      delete currentQuery[paramKey]
    } else {
      currentQuery[paramKey] = serialize(newVal)
    }

    router.replace({ query: currentQuery }).catch(() => {})
  })

  // Sync URL query change (e.g. browser back/forward) -> ref
  watch(
    () => route.query[paramKey],
    (newQueryVal) => {
      if (newQueryVal !== undefined && newQueryVal !== null && newQueryVal !== '') {
        const parsed = parse(String(newQueryVal))
        if (state.value !== parsed) {
          state.value = parsed
        }
      } else if (state.value !== defaultValue) {
        state.value = defaultValue
      }
    }
  )

  return state
}
