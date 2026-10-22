<template>
  <div class="space-y-6 font-sans">
    <!-- 4 High-Level Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      <!-- 1. Monthly Outflow Burn -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Fixed Monthly Burn</span>
          <span class="text-rose-400/80">Outflow</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5 font-mono">
          <span class="text-xl font-semibold text-zinc-100 tabular-nums">
            ฿{{ Number(financeStore.overview?.confirmed_burn_rate || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
          <span class="text-[11px] text-zinc-500">/ mo</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span>Fixed commitments</span>
          <button @click="emit('switchTab', 'SUBSCRIPTION')" class="text-zinc-400 hover:text-zinc-200 transition-colors font-mono text-[10px]">
            View Subscriptions &rarr;
          </button>
        </div>
      </div>

      <!-- 2. Expected Inflow (Debtors) -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Expected Inflow</span>
          <span class="text-emerald-400/80">Receivables</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5 font-mono">
          <span class="text-xl font-semibold text-emerald-400 tabular-nums">
            +฿{{ Number(financeStore.overview?.expected_inflow_amount || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
          <span class="text-[11px] text-zinc-500">({{ activeDebtorsCount }} debtors)</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span>Money lent to others</span>
          <button @click="emit('switchTab', 'DEBT')" class="text-zinc-400 hover:text-zinc-200 transition-colors font-mono text-[10px]">
            Manage Debtors &rarr;
          </button>
        </div>
      </div>

      <!-- 3. Due in 7 Days -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Due In Next 7 Days</span>
          <span class="text-zinc-400">Upcoming</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5 font-mono">
          <span class="text-xl font-semibold text-zinc-100 tabular-nums">
            {{ financeStore.overview?.upcoming_7_days_count || 0 }}
          </span>
          <span class="text-[11px] text-zinc-500">settlements</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
          <span>Requires settlement action</span>
        </div>
      </div>

      <!-- 4. Trial Trap Risk -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Trial Risk</span>
          <span class="text-rose-400/80">Liability</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5 font-mono">
          <span class="text-xl font-semibold text-zinc-100 tabular-nums">
            ฿{{ Number(financeStore.overview?.potential_risk_amount || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
          <span class="text-[11px] text-zinc-500">({{ financeStore.overview?.active_trials_count || 0 }} trials)</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span :class="(financeStore.overview?.critical_trials_count || 0) > 0 ? 'text-rose-400 font-semibold' : ''">
            {{ (financeStore.overview?.critical_trials_count || 0) > 0 ? 'Urgent trial expiring' : 'No critical trials' }}
          </span>
          <button @click="emit('switchTab', 'SUBSCRIPTION')" class="text-zinc-400 hover:text-zinc-200 transition-colors font-mono text-[10px]">
            Hunter &rarr;
          </button>
        </div>
      </div>
    </div>

    <!-- Active Radar Alerts: Settlements Due in Next 7 Days -->
    <div
      v-if="financeStore.overview?.upcoming_7_days && financeStore.overview.upcoming_7_days.length > 0"
      class="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80 space-y-3"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <CalendarClock class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Active Radar Alerts: Settlements Due in Next 7 Days ({{ financeStore.overview.upcoming_7_days.length }})
          </h2>
        </div>
        <span class="text-[10px] text-zinc-500 font-mono">Earliest settlement priority</span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        <div
          v-for="item in financeStore.overview.upcoming_7_days"
          :key="item.id"
          class="p-3 rounded-md bg-zinc-900/70 border border-zinc-800/80 flex items-center justify-between gap-3 text-xs font-mono hover:border-zinc-700/80 transition-colors"
        >
          <div class="space-y-0.5 truncate">
            <div class="font-medium text-zinc-100 font-sans truncate">{{ item.title }}</div>
            <div class="text-[10px] text-zinc-400 flex items-center gap-1.5">
              <span>{{ new Date(item.due_date).toLocaleDateString('en-GB') }}</span>
              <span>•</span>
              <span
                class="px-1.5 py-0.2 rounded text-[9px] uppercase font-semibold border"
                :class="item.days_left <= 1 ? 'bg-zinc-950 text-rose-400 border-zinc-800' : (item.days_left <= 3 ? 'bg-zinc-950 text-zinc-300 border-zinc-800' : 'bg-zinc-950 text-zinc-500 border-zinc-800')"
              >
                {{ item.days_left === 0 ? 'Due Today' : (item.days_left === 1 ? 'Tomorrow' : `${item.days_left}d left`) }}
              </span>
            </div>
          </div>

          <div class="text-right shrink-0">
            <div
              class="font-semibold tabular-nums"
              :class="item.direction === 'INFLOW' ? 'text-emerald-400' : 'text-zinc-100'"
            >
              {{ item.direction === 'INFLOW' ? '+' : '' }}{{ item.currency === 'USD' ? `$${Number(item.amount).toFixed(2)}` : `฿${Number(item.amount).toLocaleString('th-TH')}` }}
            </div>
            <button
              @click="handlePayItem(item)"
              class="mt-1 px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-[10px] text-zinc-200 transition-colors"
            >
              {{ item.direction === 'INFLOW' ? 'Record' : 'Pay' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Navigation Category Hubs -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3.5 pt-2">
      <!-- Hub 1: Installments -->
      <div
        @click="emit('switchTab', 'INSTALLMENT')"
        class="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/60 transition-all cursor-pointer group space-y-2"
      >
        <div class="flex items-center justify-between">
          <div class="p-2 rounded bg-zinc-800/60 border border-zinc-700/60 text-zinc-300 group-hover:scale-105 transition-transform">
            <Car class="w-4 h-4" />
          </div>
          <span class="text-xs font-mono font-semibold text-zinc-400">{{ installmentCount }} active</span>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-zinc-200">Installments & Contracts</h3>
          <p class="text-xs text-zinc-500 mt-0.5">Hire purchase contracts, amortization schedules, and statutory early payoff simulation</p>
        </div>
      </div>

      <!-- Hub 2: BNPL -->
      <div
        @click="emit('switchTab', 'BNPL')"
        class="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/60 transition-all cursor-pointer group space-y-2"
      >
        <div class="flex items-center justify-between">
          <div class="p-2 rounded bg-zinc-800/60 border border-zinc-700/60 text-zinc-300 group-hover:scale-105 transition-transform">
            <CreditCard class="w-4 h-4" />
          </div>
          <span class="text-xs font-mono font-semibold text-zinc-400">{{ bnplAccountCount }} accounts</span>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-zinc-200">Shopping Credit & BNPL</h3>
          <p class="text-xs text-zinc-500 mt-0.5">Revolving credit lines, SPayLater/LazPayLater, installment orders & statement reconciliation</p>
        </div>
      </div>

      <!-- Hub 3: Subscriptions -->
      <div
        @click="emit('switchTab', 'SUBSCRIPTION')"
        class="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/60 transition-all cursor-pointer group space-y-2"
      >
        <div class="flex items-center justify-between">
          <div class="p-2 rounded bg-zinc-800/60 border border-zinc-700/60 text-zinc-300 group-hover:scale-105 transition-transform">
            <Repeat class="w-4 h-4" />
          </div>
          <span class="text-xs font-mono font-semibold text-zinc-400">{{ subscriptionCount }} services</span>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-zinc-200">Subscriptions & Trials</h3>
          <p class="text-xs text-zinc-500 mt-0.5">Recurring subscriptions, annual plans, and Free Trial Hunter auto-debit protection</p>
        </div>
      </div>

      <!-- Hub 4: Two-Way Debts -->
      <div
        @click="emit('switchTab', 'DEBT')"
        class="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/60 transition-all cursor-pointer group space-y-2"
      >
        <div class="flex items-center justify-between">
          <div class="p-2 rounded bg-zinc-800/60 border border-zinc-700/60 text-zinc-300 group-hover:scale-105 transition-transform">
            <HandCoins class="w-4 h-4" />
          </div>
          <span class="text-xs font-mono font-semibold text-zinc-400">{{ debtTotalCount }} records</span>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-zinc-200">Two-Way Debt Ledger</h3>
          <p class="text-xs text-zinc-500 mt-0.5">Personal liabilities vs. debtor receivables with quick recall message templates</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useFinanceStore } from '../../../stores/finance'
import type { FinancialObligation, UpcomingBill } from '../../../types/finance'
import {
  CalendarClock,
  Car,
  CreditCard,
  Repeat,
  HandCoins
} from 'lucide-vue-next'

const props = defineProps<{
  obligations: FinancialObligation[]
}>()

const emit = defineEmits<{
  (e: 'switchTab', tab: string): void
  (e: 'openPay', ob: FinancialObligation): void
}>()

const financeStore = useFinanceStore()

const activeDebtorsCount = computed(() => {
  return props.obligations.filter(o => o.direction === 'INFLOW' && o.status === 'ACTIVE').length
})

const installmentCount = computed(() => {
  return props.obligations.filter(o => o.type === 'INSTALLMENT' && o.subtype !== 'BNPL_ACCOUNT' && !o.parent).length
})

const bnplAccountCount = computed(() => {
  return props.obligations.filter(o => o.subtype === 'BNPL_ACCOUNT').length
})

const subscriptionCount = computed(() => {
  return props.obligations.filter(o => o.type === 'SUBSCRIPTION' || o.type === 'FREE_TRIAL').length
})

const debtTotalCount = computed(() => {
  return props.obligations.filter(o => o.type === 'DEBT' || o.direction === 'INFLOW').length
})

function handlePayItem(item: UpcomingBill) {
  const match = props.obligations.find(o => o.id === item.id)
  if (match) {
    emit('openPay', match)
  }
}
</script>