<template>
  <div v-if="isOpen && holding" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-hidden font-sans">
    <div class="relative bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col shadow-2xl overflow-hidden">
      <!-- Fixed Header -->
      <div class="shrink-0 px-4 sm:px-6 py-3.5 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2">
            <FolderInput class="w-4 h-4 text-zinc-300" />
            <h2 class="text-base font-semibold text-zinc-100 tracking-tight">Move Asset to Portfolio</h2>
          </div>
          <p class="text-xs text-zinc-500 mt-0.5">
            Transfer <span class="font-mono text-zinc-200 font-bold">{{ holding.ticker }}</span> and history
          </p>
        </div>
        <button
          @click="emit('close')"
          class="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <form @submit.prevent="handleMove" class="flex flex-col flex-1 min-h-0 overflow-hidden">
        <div class="flex-1 overflow-y-auto overscroll-contain min-h-0 p-4 sm:p-6 space-y-4">
          <!-- Current Asset Badge -->
          <div class="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-mono font-bold text-zinc-100 text-sm">{{ holding.ticker }}</span>
                <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/50">
                  {{ holding.asset_type }}
                </span>
                <span class="text-[10px] font-mono text-zinc-400">
                  {{ holding.currency }}
                </span>
              </div>
              <div class="text-[11px] text-zinc-400 mt-0.5 truncate max-w-[200px] sm:max-w-[240px]">
                {{ holding.name || holding.ticker }}
              </div>
            </div>

            <div class="text-right">
              <div class="text-[10px] font-mono uppercase text-zinc-500">Current Basket</div>
              <div class="text-xs font-semibold text-zinc-200 mt-0.5 flex items-center justify-end gap-1.5">
                <span
                  v-if="currentPortfolio"
                  class="w-2 h-2 rounded-full shrink-0 shadow-sm"
                  :style="{ backgroundColor: getPortfolioColor(currentPortfolio.color) }"
                ></span>
                <span>{{ currentPortfolioName }}</span>
              </div>
            </div>
          </div>

          <!-- Error message -->
          <div v-if="errorMessage" class="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {{ errorMessage }}
          </div>

          <!-- Target Portfolio Selector -->
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              Destination Portfolio <span class="text-rose-400">*</span>
            </label>
            <div class="relative flex items-center">
              <span
                v-if="selectedTargetPortfolio"
                class="w-2.5 h-2.5 rounded-full absolute left-3 pointer-events-none z-10 shadow-sm"
                :style="{ backgroundColor: getPortfolioColor(selectedTargetPortfolio.color) }"
              ></span>
              <select
                v-model="targetPortfolioId"
                class="w-full pl-8 pr-8 py-2.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-sans focus:outline-none focus:border-zinc-600 transition-colors appearance-none cursor-pointer"
              >
                <option
                  v-for="p in availablePortfolios"
                  :key="p.id"
                  :value="p.id"
                >
                  {{ p.name }} ({{ p.currency }}) {{ p.is_default ? '• Main Default' : '' }}
                </option>
              </select>
              <ChevronDown class="w-3.5 h-3.5 text-zinc-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          <!-- Automatic Merge Notice -->
          <div class="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800 text-xs text-zinc-300 space-y-1.5 font-sans leading-relaxed">
            <div class="flex items-center gap-1.5 font-semibold text-zinc-300 text-[11px] font-mono uppercase">
              <ArrowRightLeft class="w-3.5 h-3.5 text-zinc-400" />
              <span>Seamless Execution Merging</span>
            </div>
            <p class="text-[11px] text-zinc-400">
              If the destination portfolio already has <strong class="text-zinc-200">{{ holding.ticker }}</strong>, all trade history will be merged into that position automatically without duplicate tickers.
            </p>
          </div>
        </div>

        <!-- Submit Buttons (Sticky Footer) -->
        <div class="shrink-0 p-4 border-t border-zinc-800/80 bg-zinc-950/90 flex items-center justify-end gap-2.5">
          <button
            type="button"
            @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting || !targetPortfolioId || targetPortfolioId === holding.portfolio"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5 cursor-pointer"
          >
            <Loader2 v-if="isSubmitting" class="w-3 h-3 animate-spin" />
            <span>{{ isSubmitting ? 'Transferring...' : 'Transfer to Portfolio' }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import { getPortfolioColor, type StockHolding } from '../../types/portfolio'
import { X, FolderInput, ChevronDown, ArrowRightLeft, Loader2 } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  holding: StockHolding | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'moved'): void
}>()

useBodyScrollLock(() => props.isOpen)

const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const targetPortfolioId = ref('')
const isSubmitting = ref(false)
const errorMessage = ref<string | null>(null)

const currentPortfolio = computed(() => {
  if (!props.holding?.portfolio) return null
  return portfolioStore.portfolios.find(item => item.id === props.holding?.portfolio) || null
})

const currentPortfolioName = computed(() => {
  return currentPortfolio.value?.name || props.holding?.portfolio_name || 'Main Portfolio'
})

const availablePortfolios = computed(() => {
  return portfolioStore.portfolios
})

const selectedTargetPortfolio = computed(() => {
  return portfolioStore.portfolios.find(p => p.id === targetPortfolioId.value) || null
})

watch(
  () => [props.isOpen, props.holding],
  ([open, h]) => {
    if (open && h) {
      errorMessage.value = null
      const currentId = (h as StockHolding).portfolio || ''
      const other = portfolioStore.portfolios.find(p => p.id !== currentId)
      targetPortfolioId.value = other?.id || currentId
    }
  },
  { immediate: true }
)

const handleMove = async () => {
  if (!props.holding || !targetPortfolioId.value) return
  if (targetPortfolioId.value === props.holding.portfolio) {
    errorMessage.value = 'Asset is already in this portfolio'
    return
  }

  isSubmitting.value = true
  errorMessage.value = null

  try {
    const res = await portfolioStore.moveHolding(props.holding.id, targetPortfolioId.value)
    toast.success(res?.detail || `Moved ${props.holding.ticker} to new portfolio`)
    emit('moved')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.detail || 'Failed to move asset to target portfolio'
  } finally {
    isSubmitting.value = false
  }
}
</script>
