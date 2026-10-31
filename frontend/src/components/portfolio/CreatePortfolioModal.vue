<template>
  <div v-if="isOpen" :class="inline ? 'font-sans' : 'fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-hidden font-sans'">
    <div class="relative bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col shadow-2xl overflow-hidden">
      <!-- Fixed Header -->
      <div class="shrink-0 px-4 sm:px-6 py-3.5 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2">
            <FolderPlus class="w-4 h-4 text-zinc-300" />
            <h2 class="text-base font-semibold text-zinc-100 tracking-tight">{{ t('portfolio.ui.create') }}</h2>
          </div>
          <p class="text-xs text-zinc-500 mt-0.5">
            {{ t('portfolio.ui.createHelp') }}
          </p>
        </div>
        <button
          @click="emit('close')"
          class="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="flex flex-col flex-1 min-h-0 overflow-hidden">
        <div class="flex-1 overflow-y-auto overscroll-contain min-h-0 p-4 sm:p-6 space-y-4">
          <!-- Error message -->
          <div v-if="errorMessage" class="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {{ errorMessage }}
          </div>

          <!-- Portfolio Name -->
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              {{ t('portfolio.ui.name') }} <span class="text-rose-400">*</span>
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
                {{ t('portfolio.ui.baseCurrency') }}
              </label>
              <div class="grid grid-cols-2 gap-1 p-0.5 bg-zinc-900 border border-zinc-800 rounded-md">
                <button
                  type="button"
                  @click="form.currency = 'THB'"
                  class="py-1.5 rounded text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1 cursor-pointer"
                  :class="form.currency === 'THB' ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700/60 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
                >
                  <span>฿ THB</span>
                </button>
                <button
                  type="button"
                  @click="form.currency = 'USD'"
                  class="py-1.5 rounded text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1 cursor-pointer"
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
                  class="w-6 h-6 rounded-full border-2 transition-transform hover:scale-110 flex items-center justify-center cursor-pointer"
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
              placeholder="e.g. Long-term DCA portfolio, core tech holdings..."
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors resize-none"
            ></textarea>
          </div>
        </div>

        <!-- Submit Buttons (Sticky Footer) -->
        <div class="shrink-0 p-4 border-t border-zinc-800/80 bg-zinc-950/90 flex items-center justify-end gap-2.5">
          <button
            type="button"
            @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors cursor-pointer"
          >
            {{ t('portfolio.ui.cancel') }}
          </button>
          <button
            type="submit"
            :disabled="isSubmitting || !form.name"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
          >
            {{ isSubmitting ? t('portfolio.ui.creating') : t('portfolio.ui.create') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { t } from '../../i18n'
import { usePortfolioStore } from '../../stores/portfolio'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import type { InvestmentPortfolio } from '../../types/portfolio'
import { X, FolderPlus } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  inline?: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', portfolio: InvestmentPortfolio): void
}>()

useBodyScrollLock(() => props.isOpen && !props.inline)

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
  currency: '' as unknown as ('THB' | 'USD'),
  color: '#3B82F6'
})

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      errorMessage.value = null
      form.value = {
        name: '',
        description: '',
        currency: '' as unknown as ('THB' | 'USD'),
        color: '#3B82F6'
      }
    }
  }
)

const handleSubmit = async () => {
  if (isSubmitting.value) return
  if (!form.value.name.trim()) {
    errorMessage.value = t('portfolio.ui.nameRequired')
    return
  }
  if (!form.value.currency) {
    errorMessage.value = t('portfolio.ui.currencyRequired')
    return
  }

  isSubmitting.value = true
  errorMessage.value = null

  try {
    const created = await portfolioStore.createPortfolio({
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
      currency: form.value.currency,
      color: form.value.color
    })
    emit('created', created)
    emit('close')
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.name?.[0] ||
      err?.response?.data?.detail ||
      t('portfolio.ui.createFailed')
  } finally {
    isSubmitting.value = false
  }
}
</script>
