<template>
  <div v-if="isOpen && portfolio" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl relative my-8">
      <!-- Close button -->
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- Modal Title -->
      <div class="mb-5">
        <div class="flex items-center gap-2">
          <Edit3 class="w-4 h-4 text-zinc-300" />
          <h2 class="text-base font-semibold text-zinc-100 tracking-tight">Edit Portfolio</h2>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Update portfolio details, tag colors, and investment strategy notes.
        </p>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Portfolio Name -->
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
            Portfolio Name <span class="text-rose-400">*</span>
          </label>
          <input
            v-model.trim="form.name"
            type="text"
            required
            maxlength="60"
            placeholder="e.g. US Tech Growth, Dividend DCA"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <!-- Currency & Color -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <!-- Currency Selection -->
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              Base Currency
            </label>
            <div class="grid grid-cols-2 gap-1 p-0.5 bg-zinc-900 border border-zinc-800 rounded-md">
              <button
                type="button"
                @click="form.currency = 'THB'"
                class="py-1.5 rounded text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1"
                :class="form.currency === 'THB' ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700/60 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
              >
                <span>฿ THB</span>
              </button>
              <button
                type="button"
                @click="form.currency = 'USD'"
                class="py-1.5 rounded text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1"
                :class="form.currency === 'USD' ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700/60 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
              >
                <span>$ USD</span>
              </button>
            </div>
          </div>

          <!-- Color Theme Accent -->
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              Color Tag
            </label>
            <div class="flex items-center gap-2 py-1.5">
              <button
                v-for="color in colorPalette"
                :key="color"
                type="button"
                @click="form.color = color"
                class="w-6 h-6 rounded-full border-2 transition-transform hover:scale-110 flex items-center justify-center"
                :style="{ backgroundColor: color }"
                :class="form.color === color ? 'border-zinc-100 ring-2 ring-zinc-700 ring-offset-2 ring-offset-zinc-950 scale-105' : 'border-transparent'"
              >
                <span v-if="form.color === color" class="w-1.5 h-1.5 rounded-full bg-white"></span>
              </button>
            </div>
          </div>
        </div>

        <!-- Description -->
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
            Description / Strategy (Optional)
          </label>
          <textarea
            v-model.trim="form.description"
            rows="2"
            maxlength="200"
            placeholder="e.g. Long-term DCA basket, core tech holdings..."
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors resize-none"
          ></textarea>
        </div>

        <!-- Submit Buttons -->
        <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting || !form.name"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {{ isSubmitting ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePortfolioStore } from '../../stores/portfolio'
import type { InvestmentPortfolio } from '../../types/portfolio'
import { X, Edit3 } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  portfolio: InvestmentPortfolio | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', portfolio: InvestmentPortfolio): void
}>()

const portfolioStore = usePortfolioStore()
const isSubmitting = ref(false)
const errorMessage = ref<string | null>(null)

const colorPalette = [
  '#3B82F6', // Blue
  '#10B981', // Emerald
  '#8B5CF6', // Purple
  '#F59E0B', // Amber
  '#EC4899', // Pink
  '#06B6D4'  // Cyan
]

const form = ref({
  name: '',
  description: '',
  currency: 'THB' as 'THB' | 'USD',
  color: '#3B82F6'
})

watch(
  () => [props.isOpen, props.portfolio],
  ([open, p]) => {
    if (open && p) {
      const port = p as InvestmentPortfolio
      errorMessage.value = null
      form.value = {
        name: port.name,
        description: port.description || '',
        currency: port.currency || 'THB',
        color: port.color || '#3B82F6'
      }
    }
  },
  { immediate: true }
)

const handleSubmit = async () => {
  if (!props.portfolio) return
  if (!form.value.name.trim()) {
    errorMessage.value = 'Portfolio name is required'
    return
  }

  isSubmitting.value = true
  errorMessage.value = null

  try {
    const updated = await portfolioStore.updatePortfolio(props.portfolio.id, {
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
      currency: form.value.currency,
      color: form.value.color
    })
    emit('saved', updated)
    emit('close')
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.name?.[0] ||
      err?.response?.data?.detail ||
      'Failed to update portfolio. Please check your inputs.'
  } finally {
    isSubmitting.value = false
  }
}
</script>
