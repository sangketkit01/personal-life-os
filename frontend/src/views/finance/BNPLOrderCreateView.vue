<template>
  <div class="max-w-xl mx-auto py-4 font-sans pb-16 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          type="button"
          @click="router.push(`/finance/bnpl/${accountId}`)"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
          title="Back to Account"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Purchase Order</h1>
          <p class="text-xs text-zinc-500 mt-0.5">
            Record an item order under {{ currentAccount?.title || 'BNPL Facility' }}
          </p>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="p-8 text-center text-xs font-mono text-zinc-500">
      Loading account details...
    </div>

    <!-- Main Clean Form -->
    <form v-else @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Item Title -->
      <div>
        <label class="block text-xs font-mono text-zinc-400 mb-1.5">
          Item / Purchase Title <span class="text-rose-400">*</span>
        </label>
        <input
          v-model="form.title"
          type="text"
          required
          placeholder="e.g. Wireless Headphones, Office Desk"
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
        />
      </div>

      <!-- Order Date (Purchase Month) -->
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label class="text-xs font-mono text-zinc-400">
            Purchase Date & Month <span class="text-rose-400">*</span>
          </label>
          <span class="text-[10px] text-zinc-500 font-mono">
            Billed starting next month onwards
          </span>
        </div>
        <input
          v-model="form.order_date"
          type="date"
          required
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
        />
      </div>

      <!-- Pricing & Hybrid Split (Pay Now vs Pay Later) -->
      <div class="space-y-3 p-3.5 rounded-lg bg-zinc-900/50 border border-zinc-800/80">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <!-- Total Price -->
          <div>
            <label class="block text-xs font-mono text-zinc-400 mb-1">
              Total Order Price (฿) <span class="text-rose-400">*</span>
            </label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">฿</span>
              <input
                v-model.number="form.total_price"
                type="number"
                step="0.01"
                min="1"
                required
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-7 pr-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>
          </div>

          <!-- Down Payment (Pay Now) -->
          <div>
            <label class="block text-xs font-mono text-zinc-400 mb-1">
              Down Payment (Pay Now)
            </label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">฿</span>
              <input
                v-model.number="form.down_payment"
                type="number"
                step="0.01"
                min="0"
                :max="form.total_price"
                placeholder="0.00"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-7 pr-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>
          </div>
        </div>

        <!-- Down Payment Account Selector (if Down Payment > 0) -->
        <div v-if="form.down_payment > 0" class="pt-2 border-t border-zinc-800/70 space-y-1.5">
          <label class="block text-xs font-mono text-zinc-300">
            Deduct Down Payment From Account <span class="text-rose-400">*</span>
          </label>
          <select
            v-model="form.down_payment_account_id"
            required
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option value="" disabled>Select cash/bank account</option>
            <option
              v-for="acc in ledgerStore.accounts"
              :key="acc.id"
              :value="acc.id"
            >
              {{ acc.name }} (฿{{ Number(acc.current_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }})
            </option>
          </select>

          <!-- Insufficient Balance Warning -->
          <div
            v-if="isDownPaymentInsufficient"
            class="p-2 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 text-[11px] font-mono flex items-center gap-1.5"
          >
            <span class="flex items-center gap-1"><AlertTriangle class="w-3.5 h-3.5" /> Insufficient account balance for this down payment.</span>
          </div>
        </div>

        <!-- Financed Amount & Term Selection -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-zinc-800/70">
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="text-xs font-mono text-zinc-400">Financed Amount</label>
              <span class="text-[10px] font-mono text-zinc-500">Pay Later</span>
            </div>
            <div class="px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs font-mono font-semibold text-zinc-200">
              ฿{{ computedFinancedAmount.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="text-xs font-mono text-zinc-400">Installment Terms</label>
              <div class="flex items-center gap-1">
                <button
                  v-for="tenor in [1, 2, 3, 5, 6, 12]"
                  :key="tenor"
                  type="button"
                  @click="form.total_terms = tenor"
                  class="px-1 py-0.2 rounded text-[10px] font-mono border transition-colors cursor-pointer"
                  :class="form.total_terms === tenor ? 'bg-zinc-800 text-zinc-100 border-zinc-600' : 'text-zinc-500 border-zinc-800 hover:text-zinc-300'"
                >
                  {{ tenor }}m
                </button>
              </div>
            </div>
            <input
              v-model.number="form.total_terms"
              type="number"
              min="1"
              max="60"
              required
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
            />
          </div>
        </div>

        <!-- Interest Rate % -->
        <div class="pt-1">
          <div class="flex items-center justify-between mb-1">
            <label class="text-xs font-mono text-zinc-400">Monthly Financing Interest Rate (%)</label>
            <span class="text-[10px] font-mono text-zinc-500">Flat monthly rate (e.g. 1.5% SPayLater)</span>
          </div>
          <input
            v-model.number="form.interest_rate_pct"
            type="number"
            step="0.01"
            min="0"
            max="100"
            placeholder="0.00"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>

        <!-- Dynamic Billing Timeline Summary Box -->
        <div class="pt-2.5 border-t border-zinc-800 space-y-1.5 text-xs font-mono">
          <div class="flex items-center justify-between text-zinc-400">
            <span>Monthly Installment:</span>
            <span class="font-semibold text-rose-400 text-sm">
              ฿{{ computedMonthlyInstallment.toLocaleString('en-US', { minimumFractionDigits: 2 }) }} / mo
            </span>
          </div>
          <div class="p-2 rounded bg-zinc-950/80 border border-zinc-800/80 text-[11px] text-zinc-400 space-y-1">
            <div class="flex justify-between">
              <span>First Installment Due:</span>
              <span class="text-zinc-200 font-medium">{{ computedFirstDueMonth }}</span>
            </div>
            <div class="flex justify-between">
              <span>Final Installment Due:</span>
              <span class="text-zinc-200 font-medium">{{ computedFinalDueMonth }}</span>
            </div>
            <div v-if="form.down_payment > 0" class="flex justify-between text-emerald-400 pt-1 border-t border-zinc-800/60">
              <span>Immediate Down Payment:</span>
              <span>฿{{ Number(form.down_payment).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Progressive Disclosure: Store & Tracking Info -->
      <div class="pt-1">
        <button
          type="button"
          @click="showAdvanced = !showAdvanced"
          class="text-xs font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <span>{{ showAdvanced ? '- Less Details' : '+ Store & Tracking Info (Optional)' }}</span>
        </button>

        <div v-if="showAdvanced" class="mt-3 space-y-3 pt-3 border-t border-zinc-800/60">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Merchant / Platform</label>
              <input
                v-model="form.store"
                type="text"
                placeholder="e.g. Shopee, Lazada, TikTok"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>

            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Order / Tracking Number</label>
              <input
                v-model="form.order_number"
                type="text"
                placeholder="e.g. 2410229988"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
        <button
          type="button"
          @click="router.push(`/finance/bnpl/${accountId}`)"
          class="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 font-medium transition-colors cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="submit"
          :disabled="isActionLoading || isDownPaymentInsufficient"
          class="px-5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50 cursor-pointer"
        >
          <Check class="w-3.5 h-3.5" />
          <span>{{ isActionLoading ? 'Saving...' : 'Record Order' }}</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import {
 reactive, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBNPL } from '../../composables/finance/useBNPL'
import { useLedgerStore } from '../../stores/ledger'
import { useToastStore } from '../../stores/toast'
import {
  AlertTriangle,
 ArrowLeft, Check } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const ledgerStore = useLedgerStore()
const { currentAccount, isLoading, isActionLoading, fetchAccountById, createSubOrder } = useBNPL()

const accountId = computed(() => route.params.id as string)
const showAdvanced = ref(false)

const form = reactive({
  title: '',
  store: '',
  order_number: '',
  order_date: new Date().toISOString().split('T')[0],
  total_price: 1500,
  down_payment: 0,
  down_payment_account_id: '',
  total_terms: 3,
  interest_rate_pct: 0
})

onMounted(async () => {
  if (accountId.value) {
    await fetchAccountById(accountId.value)
  }
  await ledgerStore.fetchAccounts()
  if (ledgerStore.accounts.length > 0 && !form.down_payment_account_id) {
    const defaultAcc = ledgerStore.accounts.find(a => a.is_default) || ledgerStore.accounts[0]
    form.down_payment_account_id = defaultAcc.id
  }
})

const computedFinancedAmount = computed(() => {
  return Math.max(0, Number(form.total_price || 0) - Number(form.down_payment || 0))
})

const computedMonthlyInstallment = computed(() => {
  const terms = Math.max(1, Number(form.total_terms || 1))
  const principalPerMonth = computedFinancedAmount.value / terms
  const monthlyInterest = computedFinancedAmount.value * (Number(form.interest_rate_pct || 0) / 100)
  return Number((principalPerMonth + monthlyInterest).toFixed(2))
})

const isDownPaymentInsufficient = computed(() => {
  if (Number(form.down_payment || 0) <= 0 || !form.down_payment_account_id) return false
  const targetAcc = ledgerStore.accounts.find(a => a.id === form.down_payment_account_id)
  if (!targetAcc) return false
  if (targetAcc.account_type === 'CREDIT_CARD') return false
  return Number(targetAcc.current_balance || 0) < Number(form.down_payment)
})

function formatMonthOffset(dateStr: string, offsetMonths: number) {
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '-'
  const target = new Date(d.getFullYear(), d.getMonth() + offsetMonths, 1)
  const dueDay = currentAccount.value?.metadata?.due_day || 10
  return `${target.toLocaleString('en-US', { month: 'long', year: 'numeric' })} (Day ${dueDay})`
}

const computedFirstDueMonth = computed(() => {
  return formatMonthOffset(form.order_date, 1)
})

const computedFinalDueMonth = computed(() => {
  return formatMonthOffset(form.order_date, Number(form.total_terms || 1))
})

async function handleSubmit() {
  if (!form.title.trim()) {
    toast.error('Please enter the purchase item title')
    return
  }

  if (computedFinancedAmount.value <= 0 && form.down_payment <= 0) {
    toast.error('Order total price must be greater than zero')
    return
  }

  if (isDownPaymentInsufficient.value) {
    toast.error('Insufficient balance in selected account for down payment')
    return
  }

  try {
    await createSubOrder(accountId.value, {
      title: form.title.trim(),
      monthly_amount: computedMonthlyInstallment.value,
      total_terms: Number(form.total_terms),
      current_term: 0,
      store: form.store.trim(),
      order_number: form.order_number.trim(),
      order_date: form.order_date,
      total_price: Number(form.total_price),
      down_payment: Number(form.down_payment || 0),
      financed_amount: computedFinancedAmount.value,
      interest_rate_pct: Number(form.interest_rate_pct || 0),
      down_payment_account_id: form.down_payment > 0 ? form.down_payment_account_id : null
    })
    toast.success(`Recorded order "${form.title}" successfully!`)
    router.push(`/finance/bnpl/${accountId.value}`)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to record purchase order')
  }
}
</script>