<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans"
    role="dialog"
    aria-modal="true"
    aria-labelledby="confirm-modal-title"
    aria-describedby="confirm-modal-desc"
    @click.self="handleBackdropClick"
  >
    <div
      ref="modalCardRef"
      class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-sm p-5 shadow-2xl relative outline-none"
      tabindex="-1"
    >
      <div class="flex items-start gap-3">
        <div
          class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          :class="isDanger ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'"
        >
          <AlertTriangle class="w-4 h-4" />
        </div>
        <div class="flex-1 min-w-0">
          <h3 id="confirm-modal-title" class="text-sm font-semibold text-zinc-100 tracking-tight">{{ title }}</h3>
          <p id="confirm-modal-desc" class="text-xs text-zinc-400 mt-1 leading-relaxed">{{ message }}</p>
        </div>
      </div>

      <!-- Inline error message if operation failed -->
      <div
        v-if="errorMessage"
        class="mt-3.5 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/25 text-xs text-rose-300 flex items-start gap-2"
        role="alert"
      >
        <AlertCircle class="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
        <div class="flex-1 min-w-0 leading-relaxed">{{ errorMessage }}</div>
      </div>

      <div class="flex items-center justify-end gap-2.5 mt-5 pt-3 border-t border-zinc-800/80">
        <button
          ref="cancelBtnRef"
          type="button"
          :disabled="isLoading"
          @click="handleCancel"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-600 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ cancelText || 'Cancel' }}
        </button>
        <button
          ref="confirmBtnRef"
          type="button"
          :disabled="isLoading"
          @click="handleConfirm"
          class="inline-flex items-center justify-center px-3.5 py-1.5 rounded-md text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-zinc-400 transition-colors shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
          :class="isDanger
            ? 'bg-rose-600 hover:bg-rose-500 text-white focus:ring-rose-500'
            : 'bg-zinc-100 hover:bg-white text-zinc-950'"
        >
          <Loader2 v-if="isLoading" class="w-3.5 h-3.5 mr-1.5 animate-spin" />
          <span>{{ isLoading ? (loadingText || 'Processing...') : (confirmText || 'Confirm') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { AlertTriangle, AlertCircle, Loader2 } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    isOpen: boolean
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    isDanger?: boolean
    isLoading?: boolean
    loadingText?: string
    errorMessage?: string
  }>(),
  {
    isDanger: true,
    confirmText: 'Delete',
    cancelText: 'Cancel',
    isLoading: false,
    errorMessage: ''
  }
)

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const modalCardRef = ref<HTMLElement | null>(null)
const cancelBtnRef = ref<HTMLButtonElement | null>(null)
const confirmBtnRef = ref<HTMLButtonElement | null>(null)

let previouslyFocusedElement: HTMLElement | null = null

function handleBackdropClick() {
  if (!props.isLoading) {
    emit('cancel')
  }
}

function handleCancel() {
  if (!props.isLoading) {
    emit('cancel')
  }
}

function handleConfirm() {
  if (!props.isLoading) {
    emit('confirm')
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (!props.isOpen) return

  if (event.key === 'Escape' && !props.isLoading) {
    event.preventDefault()
    emit('cancel')
    return
  }

  if (event.key === 'Tab') {
    const focusableButtons = [cancelBtnRef.value, confirmBtnRef.value].filter(
      (btn): btn is HTMLButtonElement => Boolean(btn && !btn.disabled)
    )
    if (focusableButtons.length === 0) return

    const first = focusableButtons[0]
    const last = focusableButtons[focusableButtons.length - 1]

    if (event.shiftKey) {
      if (document.activeElement === first) {
        event.preventDefault()
        last.focus()
      }
    } else {
      if (document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
  }
}

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      previouslyFocusedElement = (document.activeElement as HTMLElement) || null
      window.addEventListener('keydown', handleKeydown)
      nextTick(() => {
        // Automatically focus Cancel button by default to avoid accidental confirmations
        if (cancelBtnRef.value && !cancelBtnRef.value.disabled) {
          cancelBtnRef.value.focus()
        } else if (confirmBtnRef.value && !confirmBtnRef.value.disabled) {
          confirmBtnRef.value.focus()
        } else {
          modalCardRef.value?.focus()
        }
      })
    } else {
      window.removeEventListener('keydown', handleKeydown)
      nextTick(() => {
        if (previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
          previouslyFocusedElement.focus()
        }
        previouslyFocusedElement = null
      })
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
    previouslyFocusedElement.focus()
  }
})
</script>
