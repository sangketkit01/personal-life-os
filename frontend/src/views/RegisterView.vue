<template>
  <div class="min-h-screen bg-[#090a0f] flex items-center justify-center p-4 font-sans selection:bg-zinc-800 selection:text-white">
    <div class="w-full max-w-sm bg-zinc-950 border border-zinc-800 rounded-xl p-7 shadow-2xl">
      <!-- Header -->
      <div class="mb-6 text-center">
        <div class="w-9 h-9 rounded-md bg-zinc-900 border border-zinc-700/80 flex items-center justify-center text-zinc-100 mx-auto mb-3">
          <Ticket class="w-4 h-4" />
        </div>
        <h1 class="text-base font-semibold text-zinc-100 tracking-tight">Register Access</h1>
        <p class="text-xs text-zinc-500 mt-1">Invitation-only access control</p>
      </div>

      <!-- Error Alert -->
      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-mono">
        {{ errorMessage }}
      </div>

      <!-- Form -->
      <form @submit.prevent="handleRegister" class="space-y-3.5">
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Invite Code</label>
          <input
            v-model="form.invite_code"
            type="text"
            required
            placeholder="e.g. LIFE-FOUNDER-2026"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors uppercase"
          />
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Username</label>
          <input
            v-model="form.username"
            type="text"
            required
            placeholder="Letters, numbers, and underscores"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Email</label>
          <input
            v-model="form.email"
            type="email"
            required
            placeholder="user@domain.com"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Password</label>
          <input
            v-model="form.password"
            type="password"
            required
            placeholder="Minimum 8 characters"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
          <p class="text-[10px] text-zinc-500 mt-1">Must be at least 8 characters, not entirely numeric</p>
        </div>

        <button
          type="submit"
          :disabled="isSubmitting"
          class="w-full py-2 px-4 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-semibold text-xs transition-colors disabled:opacity-50 mt-1"
        >
          {{ isSubmitting ? 'Creating Account...' : 'Complete Registration' }}
        </button>
      </form>

      <!-- Footer link to login -->
      <div class="mt-6 pt-5 border-t border-zinc-800/80 text-center text-xs text-zinc-500">
        Already have credentials?
        <RouterLink to="/login" class="text-zinc-300 hover:text-white font-medium ml-1 transition-colors">
          Sign In →
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Ticket } from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({
  invite_code: '',
  username: '',
  email: '',
  password: '',
})
const errorMessage = ref('')
const isSubmitting = ref(false)

async function handleRegister() {
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    await authStore.register(form.value)
    router.push('/')
  } catch (err: any) {
    const errorData = err.response?.data
    if (errorData) {
      if (typeof errorData === 'string') {
        errorMessage.value = errorData
      } else if (errorData.detail) {
        errorMessage.value = errorData.detail
      } else {
        const firstKey = Object.keys(errorData)[0]
        const firstVal = errorData[firstKey]
        errorMessage.value = Array.isArray(firstVal) ? `${firstKey}: ${firstVal[0]}` : `${firstKey}: ${firstVal}`
      }
    } else {
      errorMessage.value = 'Registration failed. Please check inputs.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>
