import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'info' | 'loading'

export interface ToastAction {
  label: string
  onClick: () => any | Promise<any>
}

export interface ToastItem {
  id: string
  message: string
  type: ToastType
  duration?: number
  action?: ToastAction
}

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<ToastItem[]>([])
  const timeoutMap = new Map<string, ReturnType<typeof setTimeout>>()

  function showToast(
    message: string,
    type: ToastType = 'info',
    duration: number = 3000,
    action?: ToastAction,
    customId?: string
  ): string {
    const id = customId || Math.random().toString(36).substring(2, 9)

    // Clear existing timer if customId already had one
    if (timeoutMap.has(id)) {
      clearTimeout(timeoutMap.get(id)!)
      timeoutMap.delete(id)
    }

    const existingIndex = toasts.value.findIndex(t => t.id === id)
    const item: ToastItem = { id, message, type, duration, action }

    if (existingIndex >= 0) {
      toasts.value[existingIndex] = item
    } else {
      toasts.value.push(item)
    }

    if (duration > 0) {
      const timer = setTimeout(() => {
        removeToast(id)
      }, duration)
      timeoutMap.set(id, timer)
    }

    return id
  }

  function updateToast(id: string, updates: Partial<Omit<ToastItem, 'id'>>): boolean {
    const existingIndex = toasts.value.findIndex(t => t.id === id)
    if (existingIndex === -1) {
      return false
    }

    if (timeoutMap.has(id)) {
      clearTimeout(timeoutMap.get(id)!)
      timeoutMap.delete(id)
    }

    const current = toasts.value[existingIndex]
    const nextDuration = updates.duration !== undefined ? updates.duration : current.duration

    const updated: ToastItem = {
      ...current,
      ...updates,
      duration: nextDuration
    }
    toasts.value[existingIndex] = updated

    if (nextDuration !== undefined && nextDuration > 0) {
      const timer = setTimeout(() => {
        removeToast(id)
      }, nextDuration)
      timeoutMap.set(id, timer)
    }

    return true
  }

  function removeToast(id: string) {
    if (timeoutMap.has(id)) {
      clearTimeout(timeoutMap.get(id)!)
      timeoutMap.delete(id)
    }
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  function loading(message: string, id?: string, action?: ToastAction): string {
    if (id && toasts.value.some(t => t.id === id)) {
      updateToast(id, { message, type: 'loading', duration: 0, action })
      return id
    }
    return showToast(message, 'loading', 0, action, id)
  }

  function success(message: string, duration = 3000, action?: ToastAction, id?: string): string {
    if (id && toasts.value.some(t => t.id === id)) {
      updateToast(id, { message, type: 'success', duration, action })
      return id
    }
    return showToast(message, 'success', duration, action, id)
  }

  function error(message: string, duration = 4000, action?: ToastAction, id?: string): string {
    if (id && toasts.value.some(t => t.id === id)) {
      updateToast(id, { message, type: 'error', duration, action })
      return id
    }
    return showToast(message, 'error', duration, action, id)
  }

  function info(message: string, duration = 3000, action?: ToastAction, id?: string): string {
    if (id && toasts.value.some(t => t.id === id)) {
      updateToast(id, { message, type: 'info', duration, action })
      return id
    }
    return showToast(message, 'info', duration, action, id)
  }

  return {
    toasts,
    showToast,
    updateToast,
    removeToast,
    loading,
    success,
    error,
    info
  }
})
