<template>
  <div class="min-h-[70vh] flex items-center justify-center p-4 font-sans">
    <div class="w-full max-w-md p-6 rounded-xl bg-zinc-950 border border-zinc-800 text-center space-y-4 shadow-xl">
      <div v-if="isProcessing" class="space-y-3">
        <div class="w-10 h-10 mx-auto rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-300 animate-pulse">
          <Loader2 class="w-5 h-5 animate-spin" />
        </div>
        <h2 class="text-sm font-semibold text-zinc-100 tracking-tight">Connecting Google Drive...</h2>
        <p class="text-xs text-zinc-500">
          Exchanging authorization credentials and initializing cloud directories.
        </p>
      </div>

      <div v-else-if="errorMessage" class="space-y-4">
        <div class="w-10 h-10 mx-auto rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400">
          <AlertCircle class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-sm font-semibold text-zinc-100">Connection Failed</h2>
          <p class="text-xs text-zinc-400 mt-1">{{ errorMessage }}</p>
        </div>
        <button
          @click="router.push('/settings')"
          type="button"
          class="px-4 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors"
        >
          Return to Settings
        </button>
      </div>

      <div v-else class="space-y-3">
        <div class="w-10 h-10 mx-auto rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-300">
          <Check class="w-5 h-5" />
        </div>
        <h2 class="text-sm font-semibold text-zinc-100">Google Drive Linked</h2>
        <p class="text-xs text-zinc-500">Redirecting to Settings...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStorageStore } from '../stores/storage'
import { Loader2, AlertCircle, Check } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const storageStore = useStorageStore()

const isProcessing = ref(true)
const errorMessage = ref<string | null>(null)

onMounted(async () => {
  const code = route.query.code as string
  const state = route.query.state as string
  const error = route.query.error as string

  if (error) {
    isProcessing.value = false
    errorMessage.value = `Google authorization was denied or failed: ${error}`
    return
  }

  if (!code) {
    isProcessing.value = false
    errorMessage.value = 'No authorization code received from Google.'
    return
  }

  try {
    const success = await storageStore.handleCallback(code, state)
    if (success) {
      setTimeout(() => {
        router.push('/settings')
      }, 1000)
    } else {
      isProcessing.value = false
      errorMessage.value = 'Failed to verify Google Drive credentials with backend.'
    }
  } catch (err: any) {
    isProcessing.value = false
    errorMessage.value = err?.message || 'Unexpected error during connection.'
  }
})
</script>
