<template>
  <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm pointer-events-none font-sans" role="region" aria-label="Notifications">
    <transition-group
      enter-active-class="transform ease-out duration-200 transition"
      enter-from-class="translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-2"
      enter-to-class="translate-y-0 opacity-100 sm:translate-x-0"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-for="toast in toastStore.toasts"
        :key="toast.id"
        class="pointer-events-auto p-3 rounded-lg bg-zinc-950/95 border border-zinc-800 text-xs shadow-2xl backdrop-blur flex items-center justify-between gap-3 text-zinc-100"
        :class="{
          'border-rose-900/50': toast.type === 'error',
          'border-emerald-900/50': toast.type === 'success',
          'border-sky-900/50': toast.type === 'loading'
        }"
      >
        <div class="flex items-center gap-2.5 min-w-0">
          <CheckCircle2 v-if="toast.type === 'success'" class="w-4 h-4 text-emerald-400 shrink-0" />
          <AlertCircle v-else-if="toast.type === 'error'" class="w-4 h-4 text-rose-400 shrink-0" />
          <Loader2 v-else-if="toast.type === 'loading'" class="w-4 h-4 text-sky-400 shrink-0 animate-spin" />
          <Info v-else class="w-4 h-4 text-zinc-400 shrink-0" />
          <span class="font-medium text-xs leading-snug break-words">{{ toast.message }}</span>
        </div>

        <div class="flex items-center gap-1.5 shrink-0">
          <button
            v-if="toast.action"
            type="button"
            :disabled="runningActionToastId === toast.id"
            @click.stop="handleAction(toast)"
            class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 active:bg-zinc-600 text-zinc-100 text-xs font-semibold border border-zinc-700 shadow-sm transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-wait"
          >
            <Loader2 v-if="runningActionToastId === toast.id" class="w-3 h-3 animate-spin text-zinc-300" />
            <span>{{ toast.action.label }}</span>
          </button>
          <button
            type="button"
            @click="toastStore.removeToast(toast.id)"
            class="text-zinc-500 hover:text-zinc-300 transition-colors p-1 rounded hover:bg-zinc-900"
            aria-label="Dismiss notification"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToastStore, type ToastItem } from '../../stores/toast'
import {
  CheckCircle2,
  AlertCircle,
  Info,
  Loader2,
  X
} from 'lucide-vue-next'

const toastStore = useToastStore()
const runningActionToastId = ref<string | null>(null)

async function handleAction(toast: ToastItem) {
  if (!toast.action || runningActionToastId.value === toast.id) return
  const action = toast.action
  runningActionToastId.value = toast.id
  try {
    await action.onClick()
    toastStore.removeToast(toast.id)
  } catch (err) {
    console.error('Toast action failed:', err)
  } finally {
    runningActionToastId.value = null
  }
}
</script>
