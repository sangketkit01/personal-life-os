<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Financial Radar</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            FIXED COSTS & TRIALS
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">Obligation tracker: Installment terms, subscription billing, debts, and trial hunter</p>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <!-- Dual-View Toggle (Cards vs Dense Table) -->
        <div class="flex items-center p-0.5 rounded-md bg-zinc-900 border border-zinc-800">
          <button
            @click="viewMode = 'CARDS'"
            class="p-1.5 rounded text-xs transition-colors"
            :class="viewMode === 'CARDS' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
            title="Card View"
          >
            <LayoutGrid class="w-3.5 h-3.5" />
          </button>
          <button
            @click="viewMode = 'TABLE'"
            class="p-1.5 rounded text-xs transition-colors"
            :class="viewMode === 'TABLE' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
            title="Dense Table View"
          >
            <Table class="w-3.5 h-3.5" />
          </button>
        </div>

        <button
          @click="showCreateModal = true"
          class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>New Obligation</span>
        </button>
      </div>
    </div>

    <!-- 4 Summary Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      <!-- 1. Monthly Burn Rate -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Monthly Burn Rate</span>
          <span>Confirmed</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            ฿{{ Number(financeStore.overview?.confirmed_burn_rate || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
          <span class="text-[11px] text-zinc-500 font-mono">/ mo</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
          <span>Fixed recurrent obligations</span>
        </div>
      </div>

      <!-- 2. Free Trial Hunter Risk -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Trial Liability</span>
          <span>Potential</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            ฿{{ Number(financeStore.overview?.potential_risk_amount || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
          <span class="text-[11px] text-zinc-500 font-mono">({{ financeStore.overview?.active_trials_count || 0 }} items)</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span
            class="w-1.5 h-1.5 rounded-full"
            :class="(financeStore.overview?.critical_trials_count || 0) > 0 ? 'bg-rose-400' : 'bg-zinc-500'"
          />
          <span>{{ (financeStore.overview?.critical_trials_count || 0) > 0 ? 'Urgent trial expiration pending' : 'No critical trials expiring' }}</span>
        </div>
      </div>

      <!-- 3. Due in 7 Days -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Due In 7 Days</span>
          <span>Upcoming</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ financeStore.overview?.upcoming_7_days_count || 0 }}
          </span>
          <span class="text-[11px] text-zinc-500 font-mono">settlements</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
          <span>1-day advance notice via Telegram</span>
        </div>
      </div>

      <!-- 4. Total Active Obligations -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Active Tracks</span>
          <span>Total</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ financeStore.obligations.length }}
          </span>
          <span class="text-[11px] text-zinc-500 font-mono">obligations</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>Automatic cycle verification active</span>
        </div>
      </div>
    </div>

    <!-- Filter Category Tabs (Cloudflare Segmented Control) -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800/80 pb-3">
      <div class="flex items-center gap-1.5 overflow-x-auto p-1 bg-zinc-900 border border-zinc-800 rounded-lg">
        <button
          v-for="tab in filterTabs"
          :key="tab.value"
          @click="currentTab = tab.value"
          class="px-2.5 py-1 rounded text-xs font-medium transition-colors flex items-center gap-2 shrink-0"
          :class="[
            currentTab === tab.value
              ? 'bg-zinc-800 text-zinc-100 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          ]"
        >
          <component :is="tab.icon" class="w-3.5 h-3.5" />
          <span>{{ tab.label }}</span>
          <span class="text-[10px] font-mono px-1 py-0.2 rounded bg-zinc-950 text-zinc-400 border border-zinc-800">
            {{ getCountForTab(tab.value) }}
          </span>
        </button>
      </div>

      <div class="flex items-center gap-2 text-xs text-zinc-400">
        <button
          @click="toggleStatusFilter"
          class="px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-300 font-mono text-[11px] transition-colors"
        >
          Status: {{ statusFilter === 'ACTIVE' ? 'Active Only' : 'All' }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="financeStore.isLoading" class="p-12 text-center text-xs font-mono text-zinc-500">
      Loading obligations...
    </div>

    <!-- Empty State -->
    <div
      v-else-if="filteredObligations.length === 0"
      class="p-12 rounded-lg bg-zinc-900/30 border border-zinc-800 text-center space-y-3 font-mono text-xs text-zinc-500"
    >
      <p>No obligations found for the selected category.</p>
      <button
        @click="showCreateModal = true"
        class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-sans transition-colors inline-block"
      >
        + Add first obligation
      </button>
    </div>

    <!-- VIEW 1: DENSE TABLE VIEW (Yahoo Finance / Ledger Style) -->
    <div v-else-if="viewMode === 'TABLE'" class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs font-mono">
          <thead>
            <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-950/40">
              <th class="py-2.5 pl-4">Title / Counterparty</th>
              <th class="py-2.5">Category</th>
              <th class="py-2.5">Billing Day / Due</th>
              <th class="py-2.5 text-right">Amount (฿)</th>
              <th class="py-2.5 text-right">Remaining / Term</th>
              <th class="py-2.5 text-center">Status</th>
              <th class="py-2.5 text-right pr-4">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="ob in filteredObligations"
              :key="ob.id"
              class="hover:bg-zinc-900/40 transition-colors"
            >
              <!-- Title -->
              <td class="py-2.5 pl-4">
                <div class="font-medium text-zinc-100 font-sans">{{ ob.title }}</div>
                <div v-if="ob.metadata?.lender || ob.metadata?.counterparty" class="text-[10px] text-zinc-500">
                  {{ ob.metadata.lender || ob.metadata.counterparty }}
                </div>
              </td>

              <!-- Category -->
              <td class="py-2.5">
                <span class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
                  {{ ob.type }}
                </span>
              </td>

              <!-- Billing Day / Due -->
              <td class="py-2.5 text-zinc-400">
                <span v-if="ob.billing_day">Day {{ ob.billing_day }} of month</span>
                <span v-else-if="ob.due_date">{{ new Date(ob.due_date).toLocaleDateString('en-GB') }}</span>
                <span v-else>-</span>
              </td>

              <!-- Amount -->
              <td class="py-2.5 text-right font-semibold text-zinc-100 tabular-nums">
                ฿{{ Number(ob.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
              </td>

              <!-- Remaining / Term -->
              <td class="py-2.5 text-right tabular-nums text-zinc-400">
                <span v-if="ob.type === 'INSTALLMENT'">
                  Term {{ ob.summary?.current_term }}/{{ ob.summary?.total_terms }} (฿{{ Number(ob.summary?.remaining_balance || 0).toLocaleString('th-TH') }})
                </span>
                <span v-else-if="ob.type === 'DEBT'">
                  ฿{{ Number(ob.summary?.remaining_balance || ob.amount).toLocaleString('th-TH') }}
                </span>
                <span v-else-if="ob.type === 'FREE_TRIAL'" :class="ob.summary?.urgency === 'CRITICAL' ? 'text-rose-400 font-semibold' : ''">
                  {{ ob.summary?.urgency === 'CRITICAL' ? 'DUE TODAY' : `${ob.summary?.days_left}d left` }}
                </span>
                <span v-else>
                  {{ ob.metadata?.billing_cycle || 'MONTHLY' }}
                </span>
              </td>

              <!-- Status -->
              <td class="py-2.5 text-center">
                <span
                  class="text-[9px] px-1.5 py-0.2 rounded border uppercase"
                  :class="getStatusBadgeClass(ob.status)"
                >
                  {{ ob.status }}
                </span>
              </td>

              <!-- Actions -->
              <td class="py-2.5 text-right pr-4">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    v-if="(ob.type === 'INSTALLMENT' || ob.type === 'DEBT') && ob.status === 'ACTIVE'"
                    @click="openPayModal(ob)"
                    class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] text-zinc-200 transition-colors"
                  >
                    Pay
                  </button>
                  <button
                    v-else-if="ob.type === 'FREE_TRIAL' && ob.status === 'ACTIVE'"
                    @click="handleCancelTrial(ob.id)"
                    class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] text-zinc-200 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    @click="handleDelete(ob.id)"
                    class="p-1 rounded text-zinc-600 hover:text-rose-400 transition-colors"
                    title="Delete"
                  >
                    <Trash2 class="w-3 h-3" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- VIEW 2: CARDS GRID VIEW -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
      <div
        v-for="ob in filteredObligations"
        :key="ob.id"
        class="p-4 rounded-lg bg-zinc-900/40 border transition-colors flex flex-col justify-between group"
        :class="[
          ob.status === 'COMPLETED' ? 'border-zinc-800/40 opacity-60' :
          (ob.type === 'FREE_TRIAL' && ob.summary?.urgency === 'CRITICAL' ? 'border-rose-500/50 bg-rose-950/10' : 'border-zinc-800/80 hover:border-zinc-700/80')
        ]"
      >
        <!-- Card Top Bar -->
        <div>
          <div class="flex items-start justify-between gap-2 mb-2">
            <div class="flex items-center gap-1.5">
              <span class="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border bg-zinc-900 text-zinc-400 border-zinc-800">
                {{ ob.type }}
              </span>
              <span v-if="ob.metadata?.lender" class="text-[10px] text-zinc-500 font-mono">
                • {{ ob.metadata.lender }}
              </span>
            </div>

            <!-- Delete Button -->
            <button
              @click="handleDelete(ob.id)"
              title="Delete obligation"
              class="text-zinc-600 hover:text-rose-400 transition-colors p-1 opacity-0 group-hover:opacity-100"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Title & Amount -->
          <h3 class="font-medium text-xs text-zinc-100 tracking-tight line-clamp-1 mb-1">{{ ob.title }}</h3>
          <div class="flex items-baseline gap-1.5 mb-3 font-mono">
            <span class="text-lg font-semibold text-zinc-100 tabular-nums">
              ฿{{ Number(ob.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
            </span>
            <span class="text-[10px] text-zinc-500">
              {{ ob.type === 'FREE_TRIAL' ? '(Liability)' : (ob.type === 'INSTALLMENT' ? '/ term' : (ob.metadata?.billing_cycle === 'YEARLY' ? '/ yr' : '/ mo')) }}
            </span>
          </div>

          <!-- 1. Installment Specific UI: Progress Bar & Terms -->
          <div v-if="ob.type === 'INSTALLMENT'" class="space-y-2 p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 mb-3 text-xs font-mono">
            <div class="flex justify-between text-zinc-400 text-[11px]">
              <span>Term: {{ ob.summary?.current_term }} / {{ ob.summary?.total_terms }}</span>
              <span>{{ ob.summary?.progress_percentage }}%</span>
            </div>
            <!-- Progress Bar -->
            <div class="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
              <div
                class="bg-zinc-300 h-full rounded-full transition-all duration-300"
                :style="{ width: `${ob.summary?.progress_percentage || 0}%` }"
              />
            </div>
            <div class="flex justify-between text-[10px] text-zinc-500 pt-1">
              <span>Remaining: ฿{{ Number(ob.summary?.remaining_balance || 0).toLocaleString('th-TH') }}</span>
              <span>Next: {{ ob.summary?.next_due_date ? new Date(ob.summary.next_due_date).toLocaleDateString('en-GB') : '-' }}</span>
            </div>
          </div>

          <!-- 2. Free Trial Specific UI -->
          <div v-else-if="ob.type === 'FREE_TRIAL'" class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 mb-3 text-xs font-mono space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-zinc-400 text-[11px]">Trial Expiration:</span>
              <span
                class="text-[10px] uppercase font-semibold"
                :class="ob.summary?.urgency === 'CRITICAL' ? 'text-rose-400' : 'text-zinc-300'"
              >
                {{ ob.summary?.urgency === 'CRITICAL' ? 'DUE TODAY' : `${ob.summary?.days_left} days left` }}
              </span>
            </div>
            <div v-if="ob.metadata?.account_email" class="text-[10px] text-zinc-500 truncate">
              Account: {{ ob.metadata.account_email }}
            </div>
            <div v-if="ob.metadata?.cancel_url" class="pt-1">
              <a
                :href="ob.metadata.cancel_url"
                target="_blank"
                class="inline-flex items-center gap-1 text-[10px] text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                <span>Direct Cancellation Link</span>
                <ExternalLink class="w-2.5 h-2.5" />
              </a>
            </div>
          </div>

          <!-- 3. Subscriptions Specific UI -->
          <div v-else-if="ob.type === 'SUBSCRIPTION'" class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 mb-3 text-xs font-mono space-y-1">
            <div class="flex justify-between text-[11px]">
              <span class="text-zinc-400">Billing Cycle:</span>
              <span class="text-zinc-200 uppercase">{{ ob.metadata?.billing_cycle || 'MONTHLY' }}</span>
            </div>
            <div class="flex justify-between text-[10px] text-zinc-500">
              <span>Next settlement:</span>
              <span>{{ ob.summary?.next_billing_date ? new Date(ob.summary.next_billing_date).toLocaleDateString('en-GB') : '-' }}</span>
            </div>
          </div>

          <!-- 4. Debt Specific UI -->
          <div v-else-if="ob.type === 'DEBT'" class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 mb-3 text-xs font-mono space-y-1.5">
            <div class="flex justify-between text-[11px]">
              <span class="text-zinc-400">Remaining Balance:</span>
              <span class="text-zinc-100 font-semibold">฿{{ Number(ob.summary?.remaining_balance || ob.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}</span>
            </div>
            <div class="flex justify-between text-[10px] text-zinc-500">
              <span>Principal: ฿{{ Number(ob.amount).toLocaleString('th-TH') }}</span>
              <span>Paid: ฿{{ Number(ob.summary?.paid_total || 0).toLocaleString('th-TH') }}</span>
            </div>
          </div>
        </div>

        <!-- Action Buttons Footer -->
        <div class="pt-2.5 border-t border-zinc-800/60 flex items-center justify-between text-xs">
          <!-- Status pill -->
          <span
            class="text-[9px] font-mono px-1.5 py-0.2 rounded border uppercase"
            :class="getStatusBadgeClass(ob.status)"
          >
            {{ ob.status }}
          </span>

          <!-- Contextual Action Buttons -->
          <div class="flex items-center gap-1.5">
            <!-- Installment Pay Button -->
            <button
              v-if="ob.type === 'INSTALLMENT' && ob.status === 'ACTIVE'"
              @click="openPayModal(ob)"
              class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] font-medium text-zinc-200 transition-colors"
            >
              Pay Term
            </button>

            <!-- Debt Partial Pay Button -->
            <button
              v-else-if="ob.type === 'DEBT' && ob.status === 'ACTIVE'"
              @click="openPayModal(ob)"
              class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] font-medium text-zinc-200 transition-colors"
            >
              Pay Balance
            </button>

            <!-- Free Trial Cancel Button -->
            <button
              v-else-if="ob.type === 'FREE_TRIAL' && ob.status === 'ACTIVE'"
              @click="handleCancelTrial(ob.id)"
              class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] font-medium text-zinc-200 transition-colors"
            >
              Mark Cancelled
            </button>

            <!-- Completed Indicator -->
            <span
              v-else-if="ob.status === 'COMPLETED'"
              class="text-[11px] font-mono text-zinc-500 flex items-center gap-1"
            >
              <CheckCircle2 class="w-3 h-3 text-zinc-500" />
              Settled
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <CreateObligationModal
      :is-open="showCreateModal"
      @close="showCreateModal = false"
      @created="handleCreated"
    />

    <PayModal
      :is-open="showPayModal"
      :obligation="selectedObligation"
      @close="showPayModal = false"
      @paid="handlePaid"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useFinanceStore } from '../stores/finance'
import { useToastStore } from '../stores/toast'
import type { FinancialObligation } from '../types/finance'
import CreateObligationModal from '../components/finance/CreateObligationModal.vue'
import PayModal from '../components/finance/PayModal.vue'
import {
  Layers,
  CalendarClock,
  ShieldAlert,
  Repeat,
  HandCoins,
  Plus,
  Trash2,
  ExternalLink,
  CheckCircle2,
  LayoutGrid,
  Table
} from 'lucide-vue-next'

const financeStore = useFinanceStore()
const toast = useToastStore()

const currentTab = ref<string>('ALL')
const statusFilter = ref<'ACTIVE' | 'ALL'>('ACTIVE')
const viewMode = ref<'CARDS' | 'TABLE'>('CARDS')
const showCreateModal = ref<boolean>(false)
const showPayModal = ref<boolean>(false)
const selectedObligation = ref<FinancialObligation | null>(null)

const filterTabs = [
  { value: 'ALL', label: 'All', icon: Layers },
  { value: 'INSTALLMENT', label: 'Installments', icon: CalendarClock },
  { value: 'FREE_TRIAL', label: 'Free Trials', icon: ShieldAlert },
  { value: 'SUBSCRIPTION', label: 'Subscriptions', icon: Repeat },
  { value: 'DEBT', label: 'Debts', icon: HandCoins },
]

onMounted(async () => {
  await Promise.all([
    financeStore.fetchOverview(),
    financeStore.fetchObligations()
  ])
})

const filteredObligations = computed(() => {
  return financeStore.obligations.filter(ob => {
    if (currentTab.value !== 'ALL' && ob.type !== currentTab.value) {
      return false
    }
    if (statusFilter.value === 'ACTIVE' && ob.status !== 'ACTIVE') {
      return false
    }
    return true
  })
})

const getCountForTab = (tabValue: string) => {
  if (tabValue === 'ALL') return financeStore.obligations.length
  return financeStore.obligations.filter(o => o.type === tabValue).length
}

const toggleStatusFilter = () => {
  statusFilter.value = statusFilter.value === 'ACTIVE' ? 'ALL' : 'ACTIVE'
}

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'ACTIVE':
      return 'bg-zinc-900 text-zinc-300 border-zinc-800'
    case 'COMPLETED':
      return 'bg-zinc-900 text-zinc-500 border-zinc-800'
    case 'CANCELLED':
      return 'bg-zinc-900 text-zinc-500 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

const openPayModal = (ob: FinancialObligation) => {
  selectedObligation.value = ob
  showPayModal.value = true
}

const handleCancelTrial = async (id: string) => {
  try {
    await financeStore.cancelTrial(id)
    await Promise.all([
      financeStore.fetchOverview(),
      financeStore.fetchObligations()
    ])
    toast.success('Free trial marked as cancelled')
  } catch (err: any) {
    toast.error('Failed to cancel trial')
  }
}

const handleDelete = async (id: string) => {
  try {
    await financeStore.deleteObligation(id)
    await Promise.all([
      financeStore.fetchOverview(),
      financeStore.fetchObligations()
    ])
    toast.info('Obligation deleted')
  } catch (err: any) {
    toast.error('Failed to delete obligation')
  }
}

const handleCreated = async () => {
  await Promise.all([
    financeStore.fetchOverview(),
    financeStore.fetchObligations()
  ])
  toast.success('Obligation created successfully')
}

// CRITICAL WORKFLOW FIX: fetchObligations is now called so the card updates immediately!
const handlePaid = async () => {
  await Promise.all([
    financeStore.fetchOverview(),
    financeStore.fetchObligations()
  ])
  toast.success('Payment settled successfully')
}
</script>
