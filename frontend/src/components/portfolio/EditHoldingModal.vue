<template>
  <div v-if="isOpen && holding" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-hidden font-sans">
    <div class="relative bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col shadow-2xl overflow-hidden">
      <!-- Fixed Header -->
      <div class="shrink-0 px-4 sm:px-6 py-3.5 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="text-base font-semibold text-zinc-100 tracking-tight">Edit Asset Settings</h2>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-zinc-800 text-zinc-300 border border-zinc-700/60">
              {{ holding.ticker }}
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-0.5">Edit asset details and denomination</p>
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

          <!-- Currency Selection (THB vs USD) -->
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              Denomination Currency
            </label>
            <div class="grid grid-cols-2 gap-2 p-1 bg-zinc-900 border border-zinc-800 rounded-lg">
              <button
                type="button"
                :disabled="isCurrencyLocked"
                @click="!isCurrencyLocked && (form.currency = 'THB')"
                class="py-1.5 rounded text-xs font-mono transition-colors flex items-center justify-center gap-1.5"
                :class="[
                  form.currency === 'THB' ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700/60 shadow-sm' : 'text-zinc-500 hover:text-zinc-300',
                  isCurrencyLocked ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'
                ]"
              >
                <span>฿ THB (Thai Baht)</span>
              </button>
              <button
                type="button"
                :disabled="isCurrencyLocked"
                @click="!isCurrencyLocked && (form.currency = 'USD')"
                class="py-1.5 rounded text-xs font-mono transition-colors flex items-center justify-center gap-1.5"
                :class="[
                  form.currency === 'USD' ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700/60 shadow-sm' : 'text-zinc-500 hover:text-zinc-300',
                  isCurrencyLocked ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'
                ]"
              >
                <span>$ USD (US Dollar)</span>
              </button>
            </div>
            <p v-if="isCurrencyLocked" class="text-[10px] text-amber-500/80 font-mono mt-1">
              Currency is locked because trade history already exists for this holding.
            </p>
            <p v-else class="text-[10px] text-zinc-500 font-mono mt-1">
              Trades and cost basis will be denominated in {{ form.currency }}
            </p>
          </div>

          <!-- Asset Name -->
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Asset Name</label>
            <input
              v-model="form.name"
              type="text"
              placeholder="Asset full name"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>

          <!-- Asset Classification -->
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Asset Class</label>
            <select
              v-model="form.asset_type"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600 transition-colors"
            >
              <option value="STOCK">Stock (Equity)</option>
              <option value="CRYPTO">Crypto (Digital Asset)</option>
              <option value="FUND">Mutual Fund / ETF</option>
              <option value="OTHER">Other Asset</option>
            </select>
          </div>

          <!-- Target Portfolio (Move to Another Portfolio) -->
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              Target Portfolio
            </label>
            <div class="relative flex items-center">
              <span
                v-if="selectedPortfolio"
                class="w-2.5 h-2.5 rounded-full absolute left-3 pointer-events-none z-10 shadow-sm"
                :style="{ backgroundColor: getPortfolioColor(selectedPortfolio.color) }"
              ></span>
              <select
                v-model="form.portfolio"
                class="w-full pl-8 pr-8 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600 transition-colors cursor-pointer font-sans appearance-none"
              >
                <option
                  v-for="p in portfolioStore.portfolios"
                  :key="p.id"
                  :value="p.id"
                >
                  {{ p.name }} ({{ p.currency }}) {{ p.is_default ? '• Main Default' : '' }}
                </option>
              </select>
              <ChevronDown class="w-3.5 h-3.5 text-zinc-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
            <p
              v-if="form.portfolio && holding.portfolio && form.portfolio !== holding.portfolio"
              class="text-[10px] text-zinc-400 font-sans mt-1.5 flex items-center gap-1.5 p-2 rounded bg-zinc-900 border border-zinc-800"
            >
              <ArrowRightLeft class="w-3.5 h-3.5 flex-shrink-0 text-zinc-400" />
              <span>Moving this asset will transfer all trade history to the new portfolio. If the destination portfolio already holds this asset, their transactions will automatically merge.</span>
            </p>
          </div>

          <!-- Notes -->
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Notes (Optional)</label>
            <textarea
              v-model="form.notes"
              rows="2"
              placeholder="Investment thesis, DCA rules, target exit..."
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
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
            :disabled="isSubmitting"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
          >
            {{ isSubmitting ? 'Saving...' : 'Save Settings' }}
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
import { getPortfolioColor, type StockHolding, type AssetType } from '../../types/portfolio'
import { X, ChevronDown, ArrowRightLeft } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  holding: StockHolding | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

useBodyScrollLock(() => props.isOpen)

const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const errorMessage = ref<string | null>(null)
const isSubmitting = ref(false)

const form = ref({
  name: '',
  currency: 'THB',
  asset_type: 'STOCK' as AssetType,
  portfolio: '',
  notes: ''
})

const selectedPortfolio = computed(() => {
  return portfolioStore.portfolios.find(p => p.id === form.value.portfolio) || null
})

const isCurrencyLocked = computed(() => {
  if (!props.holding) return false
  const h = props.holding as any
  const txCount = h.transactions_count ?? h.recent_transactions?.length ?? 0
  const shares = Number(h.position?.shares || 0)
  const totalInvested = Number(h.position?.total_invested || 0)
  return txCount > 0 || shares > 0 || totalInvested > 0
})

watch(
  () => props.holding,
  (h) => {
    if (h) {
      form.value = {
        name: h.name || '',
        currency: (h.currency || 'THB').toUpperCase(),
        asset_type: h.asset_type || 'STOCK',
        portfolio: h.portfolio || '',
        notes: h.notes || ''
      }
    }
  },
  { immediate: true }
)

const handleSubmit = async () => {
  if (!props.holding) return
  errorMessage.value = null
  isSubmitting.value = true
  try {
    const payload: Record<string, any> = {
      name: form.value.name,
      currency: isCurrencyLocked.value ? (props.holding.currency || 'THB').toUpperCase() : form.value.currency,
      asset_type: form.value.asset_type,
      notes: form.value.notes
    }
    if (form.value.portfolio) {
      payload.portfolio = form.value.portfolio
    }

    // Atomic move + update holding in a single PATCH call
    await portfolioStore.updateHolding(props.holding.id, payload)
    toast.success(`Updated settings for ${props.holding.ticker}`)
    emit('saved')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.currency || err?.response?.data?.detail || 'Failed to update asset settings'
  } finally {
    isSubmitting.value = false
  }
}
</script>