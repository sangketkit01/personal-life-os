<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-sm p-5 shadow-2xl relative">
      <div class="flex items-start gap-3">
        <div
          class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          :class="isDanger ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'"
        >
          <AlertTriangle class="w-4 h-4" />
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="text-sm font-semibold text-zinc-100 tracking-tight">{{ title }}</h3>
          <p class="text-xs text-zinc-400 mt-1 leading-relaxed">{{ message }}</p>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2.5 mt-5 pt-3 border-t border-zinc-800/80">
        <button
          type="button"
          @click="emit('cancel')"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
        >
          {{ cancelText || 'Cancel' }}
        </button>
        <button
          type="button"
          @click="emit('confirm')"
          class="px-3.5 py-1.5 rounded-md text-xs font-semibold transition-colors shadow-sm"
          :class="isDanger
            ? 'bg-rose-600 hover:bg-rose-500 text-white'
            : 'bg-zinc-100 hover:bg-white text-zinc-950'"
        >
          {{ confirmText || 'Confirm' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    isOpen: boolean
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    isDanger?: boolean
  }>(),
  {
    isDanger: true,
    confirmText: 'Delete',
    cancelText: 'Cancel'
  }
)

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()
</script>
