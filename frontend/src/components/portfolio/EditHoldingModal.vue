<template>
  <div v-if="isOpen && holding" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
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
          <h2 class="text-base font-semibold text-zinc-100 tracking-tight">Edit Asset Settings</h2>
          <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-zinc-800 text-zinc-300 border border-zinc-700/60">
            {{ holding.ticker }}
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-0.5">Configure asset denomination currency, metadata, and asset classification</p>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Currency Selection (THB vs USD) -->
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
            Denomination Currency
          </label>
          <div class="grid grid-cols-2 gap-2 p-1 bg-zinc-900 border border-zinc-800 rounded-lg">
            <button
              type="button"
              @click="form.currency = 'THB'"
              class="py-1.5 rounded text-xs font-mono transition-colors flex items-center justify-center gap-1.5"
              :class="form.currency === 'THB' ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700/60 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
            >
              <span>฿ THB (Thai Baht)</span>
            </button>
            <button
              type="button"
              @click="form.currency = 'USD'"
              class="py-1.5 rounded text-xs font-mono transition-colors flex items-center justify-center gap-1.5"
              :class="form.currency === 'USD' ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700/60 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
            >
              <span>$ USD (US Dollar)</span>
            </button>
          </div>
          <p class="text-[10px] text-zinc-500 font-mono mt-1">
            Trades and cost basis will be denominated in {{ form.currency }}
          </p>
        </div>

        <!-- Asset Name -->
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Asset Name</label>
          <input
            v-model="form.name"
            type="text"
            placeholder="e.g. Apple Inc, PTT Public Company"
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
          <div class="relative">
            <select
              v-model="form.portfolio"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600 transition-colors cursor-pointer pr-8 font-sans"
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
            class="text-[10px] text-amber-400/90 font-sans mt-1.5 flex items-center gap-1.5 p-2 rounded bg-amber-500/10 border border-amber-500/20"
          >
            <ArrowRightLeft class="w-3.5 h-3.5 flex-shrink-0 text-amber-400" />
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
            :disabled="isSubmitting"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {{ isSubmitting ? 'Saving...' : 'Save Settings' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import type { StockHolding, AssetType } from '../../types/portfolio'
import { X, ChevronDown, ArrowRightLeft } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  holding: StockHolding | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

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
    // 1. If portfolio changed, call moveHolding
    if (form.value.portfolio && form.value.portfolio !== props.holding.portfolio) {
      await portfolioStore.moveHolding(props.holding.id, form.value.portfolio)
    }

    // 2. Update remaining holding details
    await portfolioStore.updateHolding(props.holding.id, {
      name: form.value.name,
      currency: form.value.currency,
      asset_type: form.value.asset_type,
      notes: form.value.notes
    })
    toast.success(`Updated settings for ${props.holding.ticker}`)
    emit('saved')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.detail || 'Failed to update asset settings'
  } finally {
    isSubmitting.value = false
  }
}
</script>