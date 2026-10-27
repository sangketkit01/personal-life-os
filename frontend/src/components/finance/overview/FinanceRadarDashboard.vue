<template>
  <div class="space-y-6 font-sans">
    <!-- 4 High-Level Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      <!-- 1. Monthly Outflow Burn -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-400">
          <span>Fixed Monthly Burn</span>
          <span class="px-1.5 py-0.5 rounded text-[9px] bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">Outflow</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5 font-mono">
          <span class="text-xl font-bold text-zinc-100 tabular-nums">
            ฿{{ Number(financeStore.overview?.confirmed_burn_rate || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
          <span class="text-[11px] text-zinc-500">/ mo</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span>Monthly recurring burn</span>
          <button @click="emit('switchTab', 'SUBSCRIPTION')" class="text-zinc-400 hover:text-zinc-200 active:scale-95 transition-all font-mono text-[10px]">
            Subscriptions &rarr;
          </button>
        </div>
      </div>

      <!-- 2. Expected Inflow -->
      <div
        @click="showInflowModal = true"
        class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-emerald-600/60 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md cursor-pointer group"
      >
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-400">
          <span class="group-hover:text-emerald-300 transition-colors">{{ t('fin.expectedInflow') }}</span>
          <div class="flex items-center gap-1">
            <span class="px-1 py-0.2 rounded text-[9px] bg-zinc-800 text-zinc-400 border border-zinc-700 font-mono">THB</span>
            <span class="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">{{ t('fin.inflowBadge') }}</span>
          </div>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5 font-mono">
          <span class="text-xl font-bold text-emerald-400 tabular-nums">
            +฿{{ Number(financeStore.overview?.expected_inflow_amount || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
          <span class="text-[11px] text-zinc-500">({{ expectedInflowSourcesCount }} {{ t('fin.inflowItemsCount', { n: String(expectedInflowSourcesCount) }) }})</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span class="truncate max-w-[140px] font-mono text-[10px]">{{ inflowSummarySnippet }}</span>
          <button
            type="button"
            @click.stop="showInflowModal = true"
            class="text-emerald-400 hover:text-emerald-300 active:scale-95 transition-all font-mono text-[10px] flex items-center gap-1"
          >
            <span>{{ t('fin.viewBreakdown') }}</span> &rarr;
          </button>
        </div>
      </div>

      <!-- 3. Due in 7 Days -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-400">
          <span>Due In Next 7 Days</span>
          <span class="px-1.5 py-0.5 rounded text-[9px] bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">Upcoming</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5 font-mono">
          <span class="text-xl font-bold text-zinc-100 tabular-nums">
            {{ financeStore.overview?.upcoming_7_days_count || 0 }}
          </span>
          <span class="text-[11px] text-zinc-500">settlements</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          <span>Settlements due this week</span>
        </div>
      </div>

      <!-- 4. Trial Trap Risk -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-400">
          <span>Trial Risk</span>
          <span class="px-1.5 py-0.5 rounded text-[9px] bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">Liability</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5 font-mono">
          <span class="text-xl font-bold text-zinc-100 tabular-nums">
            ฿{{ Number(financeStore.overview?.potential_risk_amount || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
          <span class="text-[11px] text-zinc-500">({{ financeStore.overview?.active_trials_count || 0 }} trials)</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span :class="(financeStore.overview?.critical_trials_count || 0) > 0 ? 'text-rose-400 font-semibold' : ''">
            {{ (financeStore.overview?.critical_trials_count || 0) > 0 ? 'Critical trial expiry risk' : 'Auto-renew liability exposure' }}
          </span>
          <button @click="emit('switchTab', 'SUBSCRIPTION')" class="text-zinc-400 hover:text-zinc-200 active:scale-95 transition-all font-mono text-[10px]">
            Hunter &rarr;
          </button>
        </div>
      </div>
    </div>

    <!-- Active Radar Alerts: Settlements Due in Next 7 Days -->
    <div
      v-if="financeStore.overview?.upcoming_7_days && financeStore.overview.upcoming_7_days.length > 0"
      class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3"
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
          class="p-3 rounded-lg bg-zinc-900/80 border border-zinc-800/80 flex items-center justify-between gap-3 text-xs font-mono hover:border-zinc-700 hover:bg-zinc-800/50 transition-all duration-150"
        >
          <div class="space-y-0.5 truncate">
            <div class="font-medium text-zinc-100 font-sans truncate">{{ item.title }}</div>
            <div class="text-[10px] text-zinc-400 flex items-center gap-1.5">
              <span>{{ new Date(item.due_date).toLocaleDateString('en-GB') }}</span>
              <span>•</span>
              <span
                class="px-1.5 py-0.2 rounded text-[9px] uppercase font-semibold border"
                :class="item.days_left <= 1 ? 'bg-rose-950/40 text-rose-400 border-rose-500/30' : (item.days_left <= 3 ? 'bg-amber-950/30 text-amber-300 border-amber-500/30' : 'bg-zinc-950 text-zinc-400 border-zinc-800')"
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
              class="mt-1 px-2.5 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-[10px] text-zinc-200 active:scale-95 transition-all shadow-sm"
            >
              {{ item.direction === 'INFLOW' ? 'Record' : 'Pay' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Navigation Category Hubs -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 pt-2">
      <!-- Hub 1: Installments -->
      <div
        @click="emit('switchTab', 'INSTALLMENT')"
        class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/70 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200 cursor-pointer group space-y-2.5 shadow-sm hover:shadow-md"
      >
        <div class="flex items-center justify-between">
          <div class="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 group-hover:scale-105 transition-transform">
            <Car class="w-4 h-4" />
          </div>
          <span class="text-xs font-mono font-semibold text-zinc-400 group-hover:text-zinc-200 transition-colors">{{ installmentCount }} active</span>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-zinc-200 group-hover:text-white transition-colors">Installments & Contracts</h3>
          <p class="text-xs text-zinc-500 mt-0.5">Vehicle & product amortization schedules and statutory payoff math</p>
        </div>
      </div>

      <!-- Hub 2: BNPL -->
      <div
        @click="emit('switchTab', 'BNPL')"
        class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/70 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200 cursor-pointer group space-y-2.5 shadow-sm hover:shadow-md"
      >
        <div class="flex items-center justify-between">
          <div class="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 group-hover:scale-105 transition-transform">
            <CreditCard class="w-4 h-4" />
          </div>
          <span class="text-xs font-mono font-semibold text-zinc-400 group-hover:text-zinc-200 transition-colors">{{ bnplAccountCount }} accounts</span>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-zinc-200 group-hover:text-white transition-colors">Shopping Credit & BNPL</h3>
          <p class="text-xs text-zinc-500 mt-0.5">E-commerce credit lines, statements, and sub-order schedules</p>
        </div>
      </div>

      <!-- Hub 3: Subscriptions -->
      <div
        @click="emit('switchTab', 'SUBSCRIPTION')"
        class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/70 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200 cursor-pointer group space-y-2.5 shadow-sm hover:shadow-md"
      >
        <div class="flex items-center justify-between">
          <div class="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 group-hover:scale-105 transition-transform">
            <Repeat class="w-4 h-4" />
          </div>
          <span class="text-xs font-mono font-semibold text-zinc-400 group-hover:text-zinc-200 transition-colors">{{ subscriptionCount }} services</span>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-zinc-200 group-hover:text-white transition-colors">Subscriptions & Trials</h3>
          <p class="text-xs text-zinc-500 mt-0.5">Monthly SaaS commitments and pre-billing trial alarms</p>
        </div>
      </div>

      <!-- Hub 4: Two-Way Debts -->
      <div
        @click="emit('switchTab', 'DEBT')"
        class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/70 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200 cursor-pointer group space-y-2.5 shadow-sm hover:shadow-md"
      >
        <div class="flex items-center justify-between">
          <div class="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 group-hover:scale-105 transition-transform">
            <HandCoins class="w-4 h-4" />
          </div>
          <span class="text-xs font-mono font-semibold text-zinc-400 group-hover:text-zinc-200 transition-colors">
            {{ activeDebtorsCount }} {{ t('fin.debtorRecordsCount', { n: String(activeDebtorsCount) }) }} · {{ debtTotalCount }} records
          </span>
        </div>
        <div>
          <h3 class="text-sm font-semibold text-zinc-200 group-hover:text-white transition-colors">Two-Way Debt Ledger</h3>
          <p class="text-xs text-zinc-500 mt-0.5">Debtors receivable, liabilities payable, and settlements</p>
        </div>
      </div>
    </div>

    <!-- Expected Inflow Breakdown Modal -->
    <ExpectedInflowBreakdownModal
      :is-open="showInflowModal"
      :target-month="financeStore.overview?.target_month"
      :breakdown="financeStore.overview?.expected_inflow_breakdown"
      :total-amount="financeStore.overview?.expected_inflow_amount"
      @close="showInflowModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useFinanceStore } from '../../../stores/finance'
import { t } from '../../../i18n'
import type { FinancialObligation, UpcomingBill } from '../../../types/finance'
import ExpectedInflowBreakdownModal from './ExpectedInflowBreakdownModal.vue'
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
const showInflowModal = ref(false)

const activeDebtorsCount = computed(() => {
  if (financeStore.overview?.active_debtor_records_count !== undefined) {
    return financeStore.overview.active_debtor_records_count
  }
  return props.obligations.filter(o =>
    o.type === 'DEBT' &&
    o.direction === 'INFLOW' &&
    o.status === 'ACTIVE' &&
    Number(o.summary?.remaining_balance ?? o.amount ?? 0) > 0
  ).length
})

const debtTotalCount = computed(() => {
  if (financeStore.overview?.debt_total_count !== undefined) {
    return financeStore.overview.debt_total_count
  }
  return props.obligations.filter(o => o.type === 'DEBT').length
})

const expectedInflowSourcesCount = computed(() => {
  const items = financeStore.overview?.expected_inflow_breakdown?.items
  if (items) return items.length
  return props.obligations.filter(o => o.direction === 'INFLOW' && o.status === 'ACTIVE').length
})

const inflowSummarySnippet = computed(() => {
  const bd = financeStore.overview?.expected_inflow_breakdown
  if (!bd || !bd.items || bd.items.length === 0) {
    return t('fin.expectedThisMonth')
  }
  const parts: string[] = []
  if (Number(bd.ma_amount || 0) > 0) parts.push(`MA: ฿${Number(bd.ma_amount).toLocaleString('th-TH')}`)
  if (Number(bd.debt_amount || 0) > 0) parts.push(`Debt: ฿${Number(bd.debt_amount).toLocaleString('th-TH')}`)
  if (Number(bd.recurring_amount || 0) > 0) parts.push(`Recurring: ฿${Number(bd.recurring_amount).toLocaleString('th-TH')}`)
  return parts.length > 0 ? parts.join(' · ') : t('fin.expectedThisMonth')
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

function handlePayItem(item: UpcomingBill) {
  const match = props.obligations.find(o => o.id === item.id)
  if (match) {
    emit('openPay', match)
  }
}
</script>