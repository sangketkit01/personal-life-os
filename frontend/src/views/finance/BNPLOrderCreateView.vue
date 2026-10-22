<template>
  <div class="max-w-4xl mx-auto space-y-6 font-sans">
    <!-- Breadcrumb & Back Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          @click="router.push(`/finance/bnpl/${accountId}`)"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Account Dossier"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Purchase Installment Order</h1>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800 font-medium">
              {{ currentAccount?.title || 'BNPL ORDER' }}
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-0.5">
            Record a new item order under this revolving credit line with monthly installment schedule.
          </p>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="p-12 text-center text-xs font-mono text-zinc-500">
      Loading account details...
    </div>

    <!-- Main Order Form & Credit Impact Preview -->
    <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Left: Order Form (7 cols) -->
      <form @submit.prevent="handleSubmit" class="lg:col-span-7 space-y-5">
        <!-- Card 1: Item & Merchant Details -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center gap-2 pb-2 border-b border-zinc-800/60">
            <ShoppingBag class="w-4 h-4 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Item & Merchant Details
            </h2>
          </div>

          <!-- Item Title -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Item Title / Purchase Name <span class="text-rose-400">*</span>
            </label>
            <input
              v-model="form.title"
              type="text"
              required
              placeholder="e.g. Sony WH-1000XM5 Wireless Headphones"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
            />
          </div>

          <!-- Store / Merchant & Order Reference -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Merchant / Store
              </label>
              <input
                v-model="form.store"
                type="text"
                placeholder="e.g. Sony Official Flagship Store"
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
              />
            </div>

            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Order / Tracking Number
              </label>
              <input
                v-model="form.order_number"
                type="text"
                placeholder="e.g. 241022998877A"
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
              />
            </div>
          </div>

          <!-- Purchase Date -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Purchase Order Date
            </label>
            <input
              v-model="form.order_date"
              type="date"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
            />
          </div>
        </div>

        <!-- Card 2: Installment Pricing & Term Math -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center justify-between pb-2 border-b border-zinc-800/60">
            <div class="flex items-center gap-2">
              <Calculator class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Installment Tenor & Pricing Math
              </h2>
            </div>

            <!-- Mode Selector Switch -->
            <div class="flex items-center gap-1 p-0.5 bg-zinc-950 border border-zinc-800 rounded-lg text-[10px] font-mono">
              <button
                type="button"
                @click="pricingMode = 'MONTHLY'"
                class="px-2 py-0.5 rounded transition-colors"
                :class="pricingMode === 'MONTHLY' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
              >
                Monthly Plan
              </button>
              <button
                type="button"
                @click="pricingMode = 'TOTAL_PRICE'"
                class="px-2 py-0.5 rounded transition-colors"
                :class="pricingMode === 'TOTAL_PRICE' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
              >
                Total Price Split
              </button>
            </div>
          </div>

          <!-- Quick Tenor Presets -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Common BNPL Tenors
            </label>
            <div class="flex items-center gap-2">
              <button
                v-for="tenor in [1, 3, 5, 6, 12]"
                :key="tenor"
                type="button"
                @click="form.total_terms = tenor"
                class="flex-1 py-1 px-2 rounded text-xs font-mono border transition-colors text-center"
                :class="form.total_terms === tenor
                  ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-semibold'
                  : 'bg-zinc-950 text-zinc-400 border-zinc-800 hover:border-zinc-700 hover:text-zinc-200'"
              >
                {{ tenor }} mo
              </button>
            </div>
          </div>

          <!-- Mode A: Monthly Amount Input -->
          <div v-if="pricingMode === 'MONTHLY'" class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Monthly Installment (฿) <span class="text-rose-400">*</span>
              </label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">฿</span>
                <input
                  v-model.number="form.monthly_amount"
                  type="number"
                  step="0.01"
                  min="1"
                  required
                  placeholder="890.00"
                  class="w-full pl-7 pr-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
                />
              </div>
            </div>

            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Total Tenor (Months) <span class="text-rose-400">*</span>
              </label>
              <input
                v-model.number="form.total_terms"
                type="number"
                min="1"
                required
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
              />
            </div>
          </div>

          <!-- Mode B: Total Price Input -->
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Total Purchase Price (฿) <span class="text-rose-400">*</span>
              </label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">฿</span>
                <input
                  v-model.number="form.total_price"
                  type="number"
                  step="0.01"
                  min="1"
                  required
                  placeholder="5340.00"
                  class="w-full pl-7 pr-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
                />
              </div>
            </div>

            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Total Tenor (Months) <span class="text-rose-400">*</span>
              </label>
              <input
                v-model.number="form.total_terms"
                type="number"
                min="1"
                required
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
              />
            </div>
          </div>

          <!-- Starting Term Status -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              Installments Already Paid (Starting Term)
            </label>
            <input
              v-model.number="form.current_term"
              type="number"
              min="0"
              :max="form.total_terms"
              placeholder="0"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
            />
            <span class="text-[10px] text-zinc-500 block">
              Set to 0 if newly ordered, or 1 if the first payment was deducted immediately at checkout.
            </span>
          </div>
        </div>

        <!-- Submission Actions -->
        <div class="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            @click="router.push(`/finance/bnpl/${accountId}`)"
            class="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isActionLoading || isOverCreditLimit"
            class="px-5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
          >
            <Check class="w-3.5 h-3.5" />
            <span>{{ isActionLoading ? 'Recording Order...' : 'Add Order to Credit Line' }}</span>
          </button>
        </div>
      </form>

      <!-- Right: Real-time Credit Impact Preview (5 cols) -->
      <div class="lg:col-span-5 space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/60 border border-zinc-800/90 space-y-4 sticky top-6">
          <div class="flex items-center justify-between pb-2 border-b border-zinc-800/80">
            <div class="flex items-center gap-2">
              <CreditCard class="w-4 h-4 text-zinc-300" />
              <h3 class="text-xs font-semibold font-mono uppercase text-zinc-300">
                Credit Line Impact
              </h3>
            </div>
            <span class="text-[10px] font-mono text-zinc-500 uppercase">
              SIMULATION
            </span>
          </div>

          <!-- Target Account Info -->
          <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-xs font-mono space-y-1">
            <div class="flex justify-between text-zinc-400">
              <span>Credit Facility:</span>
              <strong class="text-zinc-100">{{ currentAccount?.title }}</strong>
            </div>
            <div class="flex justify-between text-zinc-400">
              <span>Total Approved Limit:</span>
              <span class="text-zinc-200">฿{{ Number(currentAccount?.metadata?.credit_limit || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="flex justify-between text-zinc-400">
              <span>Current Available Power:</span>
              <span class="text-emerald-400 font-semibold">฿{{ currentAvailableCredit.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
          </div>

          <!-- Order Summary Breakdown -->
          <div class="space-y-2.5 font-mono text-xs">
            <div class="flex items-center justify-between text-zinc-400 py-1 border-b border-zinc-800/60">
              <span>Monthly Bill Add-on:</span>
              <strong class="text-rose-400 text-sm">
                +฿{{ computedMonthlyAmount.toLocaleString('en-US', { minimumFractionDigits: 2 }) }} / mo
              </strong>
            </div>

            <div class="flex items-center justify-between text-zinc-400 py-1 border-b border-zinc-800/60">
              <span>Total Principal Debt:</span>
              <span class="text-zinc-100 font-semibold">
                ฿{{ computedTotalOrderDebt.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </span>
            </div>

            <div class="flex items-center justify-between text-zinc-400 py-1 border-b border-zinc-800/60">
              <span>Tenor Schedule:</span>
              <span class="text-zinc-300">{{ form.total_terms }} monthly installments</span>
            </div>

            <div class="flex items-center justify-between text-zinc-400 py-1 border-b border-zinc-800/60">
              <span>New Available Buying Power:</span>
              <span
                class="font-semibold text-sm"
                :class="newAvailableCredit >= 0 ? 'text-zinc-100' : 'text-rose-400'"
              >
                ฿{{ newAvailableCredit.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </span>
            </div>
          </div>

          <!-- Overlimit Alert -->
          <div
            v-if="isOverCreditLimit"
            class="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-mono space-y-1"
          >
            <div class="flex items-center gap-1.5 font-semibold">
              <AlertCircle class="w-3.5 h-3.5" />
              <span>Credit Limit Exceeded</span>
            </div>
            <p class="text-[11px] leading-relaxed">
              This order of ฿{{ computedTotalOrderDebt.toLocaleString('en-US') }} exceeds your available credit line of ฿{{ currentAvailableCredit.toLocaleString('en-US') }}.
            </p>
          </div>

          <!-- Billing Info Note -->
          <div v-else class="p-3 rounded-lg bg-zinc-950/70 border border-zinc-800/80 text-[11px] font-sans text-zinc-400 leading-relaxed">
            📦 The first installment of ฿{{ computedMonthlyAmount.toLocaleString('en-US') }} will be billed on the next statement closing cycle (Day {{ currentAccount?.metadata?.cutoff_day || 25 }}).
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBNPL } from '../../composables/finance/useBNPL'
import { useToastStore } from '../../stores/toast'
import {
  ArrowLeft,
  ShoppingBag,
  Calculator,
  CreditCard,
  Check,
  AlertCircle
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const { currentAccount, isLoading, isActionLoading, fetchAccountById, createSubOrder } = useBNPL()

const accountId = computed(() => route.params.id as string)
const pricingMode = ref<'MONTHLY' | 'TOTAL_PRICE'>('MONTHLY')

const form = reactive({
  title: '',
  store: '',
  order_number: '',
  order_date: new Date().toISOString().split('T')[0],
  monthly_amount: 890,
  total_price: 5340,
  total_terms: 6,
  current_term: 0
})

onMounted(async () => {
  if (accountId.value) {
    await fetchAccountById(accountId.value)
  }
})

const computedMonthlyAmount = computed(() => {
  if (pricingMode.value === 'MONTHLY') {
    return Number(form.monthly_amount || 0)
  }
  const terms = Number(form.total_terms || 1)
  return terms > 0 ? Number((Number(form.total_price || 0) / terms).toFixed(2)) : 0
})

const computedTotalOrderDebt = computed(() => {
  if (pricingMode.value === 'MONTHLY') {
    return Number((Number(form.monthly_amount || 0) * Number(form.total_terms || 1)).toFixed(2))
  }
  return Number(form.total_price || 0)
})

const currentAvailableCredit = computed(() => {
  return Number(currentAccount.value?.summary?.available_credit ?? currentAccount.value?.metadata?.credit_limit ?? 0)
})

const newAvailableCredit = computed(() => {
  const remainingTermsToPay = Math.max(0, form.total_terms - form.current_term)
  const remainingDebtToAdd = computedMonthlyAmount.value * remainingTermsToPay
  return currentAvailableCredit.value - remainingDebtToAdd
})

const isOverCreditLimit = computed(() => {
  return newAvailableCredit.value < 0
})

async function handleSubmit() {
  if (!form.title) {
    toast.error('Please enter the purchase item title')
    return
  }

  if (computedMonthlyAmount.value <= 0) {
    toast.error('Monthly installment must be greater than zero')
    return
  }

  try {
    await createSubOrder(accountId.value, {
      title: form.title,
      monthly_amount: computedMonthlyAmount.value,
      total_terms: Number(form.total_terms),
      current_term: Number(form.current_term),
      store: form.store,
      order_number: form.order_number,
      order_date: form.order_date,
      total_principal: computedTotalOrderDebt.value
    })
    toast.success(`Recorded order "${form.title}" successfully!`)
    router.push(`/finance/bnpl/${accountId.value}`)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to record purchase order')
  }
}
</script>
