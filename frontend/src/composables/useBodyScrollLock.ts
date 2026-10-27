import { watch, onBeforeUnmount, type Ref, type ComputedRef } from 'vue'

let activeLockCount = 0
let originalBodyOverflow = ''
let originalHtmlOverflow = ''

export function lockBodyScroll() {
  activeLockCount++
  if (activeLockCount === 1 && typeof document !== 'undefined') {
    originalBodyOverflow = document.body.style.overflow || ''
    originalHtmlOverflow = document.documentElement.style.overflow || ''
    document.body.style.overflow = 'hidden'
    document.documentElement.style.overflow = 'hidden'
    document.body.classList.add('overflow-hidden')
    document.documentElement.classList.add('overflow-hidden')
  }
}

export function unlockBodyScroll() {
  activeLockCount = Math.max(0, activeLockCount - 1)
  if (activeLockCount === 0 && typeof document !== 'undefined') {
    document.body.style.overflow = originalBodyOverflow
    document.documentElement.style.overflow = originalHtmlOverflow
    document.body.classList.remove('overflow-hidden')
    document.documentElement.classList.remove('overflow-hidden')
  }
}

export function useBodyScrollLock(
  isOpen: Ref<boolean> | ComputedRef<boolean> | (() => boolean)
) {
  let isLockedByMe = false

  const sync = (open: boolean) => {
    if (open && !isLockedByMe) {
      lockBodyScroll()
      isLockedByMe = true
    } else if (!open && isLockedByMe) {
      unlockBodyScroll()
      isLockedByMe = false
    }
  }

  const getter = typeof isOpen === 'function' ? isOpen : () => isOpen.value

  watch(
    getter,
    (val) => {
      sync(Boolean(val))
    },
    { immediate: true }
  )

  onBeforeUnmount(() => {
    sync(false)
  })
}
