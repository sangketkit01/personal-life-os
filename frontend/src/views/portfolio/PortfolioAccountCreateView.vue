<template>
  <div class="max-w-xl mx-auto py-4 font-sans pb-16 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          type="button"
          @click="router.push('/portfolio/accounts')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
          title="Back to Portfolios"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Brokerage Account</h1>
          <p class="text-xs text-zinc-500 mt-0.5">
            Configure an independent portfolio basket with isolated cost basis
          </p>
        </div>
      </div>
    </div>

    <!-- Quick Suggestion Chips -->
    <div class="space-y-1.5">
      <span class="text-[11px] font-mono uppercase text-zinc-500">Popular Templates</span>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="preset in brokerPresets"
          :key="preset.name"
          type="button"
          @click="applyPreset(preset)"
          class="px-2.5 py-1 rounded text-xs font-mono border transition-colors cursor-pointer"
          :class="form.name === preset.name
            ? 'bg-zinc-800 text-zinc-100 border-zinc-600'
            : 'bg-zinc-950 text-zinc-400 border-zinc-800 hover:text-zinc-200 hover:border-zinc-700'"
        >
          {{ preset.label }}
        </button>
      </div>
    </div>

    <!-- Main Clean Form -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Account Name -->
      <div>
        <label class="block text-xs font-mono text-zinc-400 mb-1.5">
          Account Display Name <span class="text-rose-400">*</span>
        </label>
        <input
          v-model="form.name"
          type="text"
          required
          placeholder="e.g. Dime US Tech, InnovestX SET50"
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
        />
      </div>

      <!-- Currency Choice -->
      <div>
        <label class="block text-xs font-mono text-zinc-400 mb-1.5">
          Base Account Currency <span class="text-rose-400">*</span>
        </label>
        <div class="grid grid-cols-2 gap-3">
          <button
            type="button"
            @click="form.currency = 'USD'"
            class="p-3 rounded-lg border text-left transition-colors cursor-pointer flex items-center justify-between"
            :class="form.currency === 'USD'
              ? 'bg-zinc-800 border-zinc-600 text-zinc-100 shadow-sm'
              : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700'"
          >
            <div>
              <div class="text-xs font-semibold font-mono">USD ($)</div>
              <div class="text-[10px] text-zinc-500">US Equities & International</div>
            </div>
            <span class="text-xs font-mono font-bold">$</span>
          </button>

          <button
            type="button"
            @click="form.currency = 'THB'"
            class="p-3 rounded-lg border text-left transition-colors cursor-pointer flex items-center justify-between"
            :class="form.currency === 'THB'
              ? 'bg-zinc-800 border-zinc-600 text-zinc-100 shadow-sm'
              : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700'"
          >
            <div>
              <div class="text-xs font-semibold font-mono">THB (฿)</div>
              <div class="text-[10px] text-zinc-500">Thai Equities & Funds</div>
            </div>
            <span class="text-xs font-mono font-bold">฿</span>
          </button>
        </div>
      </div>

      <!-- Color Tag Accent -->
      <div>
        <label class="block text-xs font-mono text-zinc-400 mb-1.5">
          Color Tag Accent
        </label>
        <div class="flex items-center gap-2.5 py-1">
          <button
            v-for="color in PORTFOLIO_COLORS"
            :key="color"
            type="button"
            @click="form.color = color"
            class="w-7 h-7 rounded-full border-2 transition-transform hover:scale-110 flex items-center justify-center cursor-pointer"
            :style="{ backgroundColor: color }"
            :class="form.color === color ? 'border-zinc-100 ring-2 ring-zinc-700 ring-offset-2 ring-offset-zinc-950 scale-105' : 'border-transparent'"
          >
            <span v-if="form.color === color" class="w-1.5 h-1.5 rounded-full bg-white"></span>
          </button>
        </div>
      </div>

      <!-- Description / Strategy Notes -->
      <div>
        <label class="block text-xs font-mono text-zinc-400 mb-1.5">
          Strategy & Objective (Optional)
        </label>
        <textarea
          v-model="form.description"
          rows="2"
          placeholder="e.g. Long-term DCA basket, core tech holdings..."
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors resize-none"
        ></textarea>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
        <button
          type="button"
          @click="router.push('/portfolio/accounts')"
          class="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 font-medium transition-colors cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="submit"
          :disabled="isSubmitting"
          class="px-5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50 cursor-pointer"
        >
          <Check class="w-3.5 h-3.5" />
          <span>{{ isSubmitting ? 'Creating...' : 'Create Account' }}</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import { PORTFOLIO_COLORS } from '../../types/portfolio'
import { ArrowLeft, Check } from 'lucide-vue-next'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()
const isSubmitting = ref(false)

const brokerPresets = [
  { name: 'Dime US Growth', label: 'Dime! US Shares', currency: 'USD' as const, desc: 'Dime fractional US shares & S&P 500 ETFs' },
  { name: 'InnovestX SET50', label: 'InnovestX (SCB)', currency: 'THB' as const, desc: 'SET50 dividend leaders and domestic equities' },
  { name: 'Bitkub Crypto', label: 'Bitkub Digital', currency: 'THB' as const, desc: 'Thai regulated crypto holding account' },
  { name: 'Interactive Brokers', label: 'IBKR Global', currency: 'USD' as const, desc: 'Direct international equities & global ETFs' }
]

const form = reactive({
  name: '',
  currency: 'USD' as 'USD' | 'THB',
  color: PORTFOLIO_COLORS[0] as string,
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
      color: form.color,
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
