<template>
  <div class="max-w-4xl mx-auto space-y-6 font-sans">
    <!-- Breadcrumb & Back Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          @click="router.push('/portfolio/accounts')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Brokerage Accounts"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Brokerage Account</h1>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800 font-medium">
              ACCOUNT BASKET
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-0.5">
            Configure a dedicated brokerage account (Dime, InnovestX, Bitkub, Interactive Brokers) with independent cost basis and currency.
          </p>
        </div>
      </div>
    </div>

    <!-- Main Creation Layout: Form & Live Calculation Preview -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Left: Form Controls (7 cols) -->
      <form @submit.prevent="handleSubmit" class="lg:col-span-7 space-y-5">
        <!-- 1. Broker Presets -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3.5">
          <label class="block text-xs font-mono text-zinc-400 uppercase tracking-wider font-semibold">
            Brokerage Presets
          </label>

          <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            <button
              v-for="preset in brokerPresets"
              :key="preset.name"
              type="button"
              @click="applyPreset(preset)"
              class="p-3 rounded-lg border text-left transition-all space-y-1"
              :class="form.name === preset.name
                ? 'bg-zinc-900 border-zinc-600 text-zinc-100 shadow-sm'
                : 'bg-zinc-950/60 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200'"
            >
              <div class="font-semibold text-xs font-sans truncate">{{ preset.label }}</div>
              <div class="flex items-center justify-between text-[10px] font-mono text-zinc-500">
                <span>{{ preset.assetClass }}</span>
                <span class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">{{ preset.currency }}</span>
              </div>
            </button>
          </div>
        </div>

        <!-- 2. Account Information -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center gap-2 pb-2 border-b border-zinc-800/60">
            <Briefcase class="w-4 h-4 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Account Parameters
            </h2>
          </div>

          <!-- Account Name -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Account Display Name <span class="text-rose-400">*</span>
            </label>
            <input
              v-model="form.name"
              type="text"
              required
              placeholder="e.g. Dime US Tech Growth"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
            />
          </div>

          <!-- Base Currency Selector -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Base Account Currency <span class="text-rose-400">*</span>
            </label>
            <div class="grid grid-cols-2 gap-3">
              <button
                type="button"
                @click="form.currency = 'USD'"
                class="p-2.5 rounded-lg border text-left transition-colors flex items-center justify-between"
                :class="form.currency === 'USD'
                  ? 'bg-zinc-900 border-zinc-600 text-zinc-100'
                  : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700'"
              >
                <div>
                  <div class="text-xs font-semibold font-mono">USD ($)</div>
                  <div class="text-[10px] text-zinc-500 font-sans">US Equities & International</div>
                </div>
                <span class="text-xs font-mono font-bold">$</span>
              </button>

              <button
                type="button"
                @click="form.currency = 'THB'"
                class="p-2.5 rounded-lg border text-left transition-colors flex items-center justify-between"
                :class="form.currency === 'THB'
                  ? 'bg-zinc-900 border-zinc-600 text-zinc-100'
                  : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700'"
              >
                <div>
                  <div class="text-xs font-semibold font-mono">THB (฿)</div>
                  <div class="text-[10px] text-zinc-500 font-sans">Thai Stocks & Mutual Funds</div>
                </div>
                <span class="text-xs font-mono font-bold">฿</span>
              </button>
            </div>
          </div>

          <!-- Description & Strategy Thesis -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Investment Strategy & Target
            </label>
            <textarea
              v-model="form.description"
              rows="3"
              placeholder="e.g. S&P 500 DCA basket, focused on dividend reinvestment and core tech holdings..."
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors resize-none"
            ></textarea>
          </div>
        </div>

        <!-- Submission Actions -->
        <div class="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            @click="router.push('/portfolio/accounts')"
            class="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="px-5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
          >
            <Check class="w-3.5 h-3.5" />
            <span>{{ isSubmitting ? 'Creating Account...' : 'Create Brokerage Basket' }}</span>
          </button>
        </div>
      </form>

      <!-- Right: Live Simulation Preview (5 cols) -->
      <div class="lg:col-span-5 space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/60 border border-zinc-800/90 space-y-4 sticky top-6">
          <div class="flex items-center justify-between pb-2 border-b border-zinc-800/80">
            <div class="flex items-center gap-2">
              <FolderKanban class="w-4 h-4 text-zinc-300" />
              <h3 class="text-xs font-semibold font-mono uppercase text-zinc-300">
                Broker Card Preview
              </h3>
            </div>
            <span class="text-[10px] font-mono text-zinc-500 uppercase">
              LIVE PREVIEW
            </span>
          </div>

          <!-- Account Identity Card -->
          <div class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 space-y-3">
            <div class="flex items-start justify-between">
              <div>
                <span class="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 font-semibold">
                  {{ form.currency }} BROKERAGE
                </span>
                <h4 class="text-sm font-semibold text-zinc-100 font-sans mt-1.5">
                  {{ form.name || 'Untitled Account Basket' }}
                </h4>
              </div>
              <span class="text-[10px] font-mono text-zinc-500">
                0 holdings
              </span>
            </div>

            <!-- Numbers Simulation -->
            <div class="grid grid-cols-2 gap-2 pt-2 border-t border-zinc-800/60 font-mono text-xs">
              <div>
                <span class="text-[9px] text-zinc-500 uppercase block">Market Value</span>
                <span class="text-zinc-100 font-semibold">
                  {{ form.currency === 'USD' ? '$' : '฿' }}0.00
                </span>
              </div>
              <div>
                <span class="text-[9px] text-zinc-500 uppercase block">Unrealized PnL</span>
                <span class="text-zinc-500 font-semibold">
                  0.00%
                </span>
              </div>
            </div>

            <!-- Strategy note -->
            <div v-if="form.description" class="pt-2 border-t border-zinc-800/60 text-[11px] text-zinc-400 font-sans line-clamp-2">
              {{ form.description }}
            </div>
          </div>

          <div class="p-3.5 rounded-lg bg-zinc-950/80 border border-zinc-800/60 text-[11px] text-zinc-400 font-sans leading-relaxed">
            💡 After creating this brokerage basket, you can log buy/sell transactions, track cost basis via weighted average, record dividend cashflow, and monitor real-time market prices.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import {
  ArrowLeft,
  Briefcase,
  FolderKanban,
  Check
} from 'lucide-vue-next'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()
const isSubmitting = ref(false)

const brokerPresets = [
  { name: 'Dime US Growth', label: 'Dime! US Shares', currency: 'USD' as const, assetClass: 'US Stocks', desc: 'Dime fractional US shares & S&P 500 ETFs' },
  { name: 'InnovestX SET50', label: 'InnovestX (SCB)', currency: 'THB' as const, assetClass: 'Thai Stocks', desc: 'SET50 dividend leaders and domestic equities' },
  { name: 'Bitkub Crypto Vault', label: 'Bitkub Digital', currency: 'THB' as const, assetClass: 'Crypto', desc: 'Thai SEC-regulated crypto holding account' },
  { name: 'Binance Global', label: 'Binance / Bybit', currency: 'USD' as const, assetClass: 'Crypto', desc: 'Global digital assets, staking and spot portfolio' },
  { name: 'Interactive Brokers', label: 'IBKR Global', currency: 'USD' as const, assetClass: 'Multi-Asset', desc: 'Direct international equities, global ETFs and bonds' },
  { name: 'Physical Asset Vault', label: 'Physical Gold / Vault', currency: 'THB' as const, assetClass: 'Commodities', desc: 'Physical gold bullion and non-bank cash reserves' }
]

const form = reactive({
  name: '',
  currency: 'USD' as 'USD' | 'THB',
  description: ''
})

function applyPreset(preset: typeof brokerPresets[0]) {
  form.name = preset.name
  form.currency = preset.currency
  form.description = preset.desc
}

async function handleSubmit() {
  if (!form.name.trim()) {
    toast.error('Please enter a portfolio name')
    return
  }

  isSubmitting.value = true
  try {
    const created = await portfolioStore.createPortfolio({
      name: form.name.trim(),
      currency: form.currency,
      description: form.description.trim()
    })

    toast.success(`Brokerage account "${created.name}" created!`)
    router.push(`/portfolio/accounts/${created.id}`)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to create brokerage account')
  } finally {
    isSubmitting.value = false
  }
}
</script>
