<template>
  <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm pointer-events-none font-sans">
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
      >
        <div class="flex items-center gap-2.5">
          <CheckCircle2 v-if="toast.type === 'success'" class="w-4 h-4 text-emerald-400 shrink-0" />
          <AlertCircle v-else-if="toast.type === 'error'" class="w-4 h-4 text-rose-400 shrink-0" />
          <Info v-else class="w-4 h-4 text-zinc-400 shrink-0" />
          <span class="font-medium text-xs leading-snug">{{ toast.message }}</span>
        </div>

        <button
          @click="toastStore.removeToast(toast.id)"
          class="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { useToastStore } from '../../stores/toast'
import {
  CheckCircle2,
  AlertCircle,
  Info,
  X
} from 'lucide-vue-next'

const toastStore = useToastStore()
</script>
