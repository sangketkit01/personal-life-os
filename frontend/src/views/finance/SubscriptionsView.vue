<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans pb-12">
    <!-- View Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Subscriptions & Trial Watchdog</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            RECURRING BURN & ALARMS
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Track monthly/yearly SaaS commitments and pre-billing free trial expiration alarms
        </p>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <RouterLink
          to="/finance/subscriptions/new"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white active:scale-95 text-zinc-950 text-xs font-semibold transition-all flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>New Subscription</span>
        </RouterLink>
      </div>
    </div>

    <!-- Summary KPI Header Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- 1. Monthly Subscription Burn -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-400">Monthly Burn Rate</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center justify-center">
            <Flame class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2 tabular-nums">
          ฿{{ formatNumber(totalMonthlyBurnTHB) }}
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          USD: ${{ formatNumber(totalMonthlyBurnUSD) }}/mo
        </p>
      </div>

      <!-- 2. Annualized Cost Burn -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-400">Annualized Burn</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center justify-center">
            <Clock class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-200 mt-2 tabular-nums">
          ฿{{ formatNumber(totalMonthlyBurnTHB * 12) }}
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          USD: ${{ formatNumber(totalMonthlyBurnUSD * 12) }}/yr
        </p>
      </div>

      <!-- 3. Active Recurring Services -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-400">Active Services</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center justify-center">
            <Repeat class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2">
          {{ activeSubscriptionsList.length }} Services
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          Across {{ uniqueCategoriesCount }} categories
        </p>
      </div>

      <!-- 4. Trial Trap Risk Liability -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-400">Trial Trap Risk</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center justify-center">
            <ShieldAlert class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-rose-400 mt-2 tabular-nums">
          ฿{{ formatNumber(totalTrialLiabilityTHB) }}
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          {{ activeTrialsList.length }} active free trial alarms
        </p>
      </div>
    </div>

    <!-- FREE TRIAL HUNTER ZONE (ACTIVE WATCHDOG ALARMS) -->
    <div v-if="activeTrialsList.length > 0" class="space-y-3">
      <div class="flex items-center justify-between pb-1 border-b border-zinc-800/80">
        <div class="flex items-center gap-2">
          <ShieldAlert class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Active Free Trial Watchdogs (Auto-Debit Protection)
          </h2>
          <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">
            {{ activeTrialsList.length }} ALARMS
          </span>
        </div>
        <span class="text-[10px] font-mono text-zinc-500">Cancel before renewal to avoid auto-charge</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <div
          v-for="trial in activeTrialsList"
          :key="trial.id"
          class="p-4 rounded-xl border transition-all space-y-3 relative overflow-hidden"
          :class="[
            getTrialDaysLeft(trial) <= 1
              ? 'bg-rose-950/20 border-rose-500/50 shadow-sm'
              : 'bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700'
          ]"
        >
          <div class="flex items-start justify-between">
            <div>
              <span
                class="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded border font-semibold"
                :class="getTrialDaysLeft(trial) <= 1 ? 'bg-zinc-900 text-rose-400 border-rose-500/40' : 'bg-zinc-900 text-zinc-400 border-zinc-800'"
              >
                {{ getTrialDaysLeft(trial) <= 0 ? 'EXPIRES TODAY' : `${getTrialDaysLeft(trial)} DAYS LEFT` }}
              </span>
              <RouterLink
                :to="`/finance/subscriptions/${trial.id}`"
                class="text-sm font-semibold text-zinc-100 hover:text-white hover:underline mt-1 block font-sans"
              >
                {{ trial.title }}
              </RouterLink>
            </div>

            <div class="text-right font-mono">
              <span class="text-xs font-semibold text-rose-400 tabular-nums">
                {{ trial.currency === 'USD' ? '$' : '฿' }}{{ formatNumber(trial.amount) }}
              </span>
              <span class="text-[9px] text-zinc-500 block">if renewed</span>
            </div>
          </div>

          <!-- Account & Due Date -->
          <div class="space-y-1 text-xs font-mono text-zinc-400 bg-zinc-950 p-2.5 rounded-lg border border-zinc-800/60">
            <div v-if="trial.metadata?.account_email" class="truncate text-[11px]">
              Account: <strong class="text-zinc-200">{{ trial.metadata.account_email }}</strong>
            </div>
            <div class="flex justify-between text-[10px] text-zinc-500">
              <span>Expiry Date:</span>
              <span class="text-zinc-300">{{ formatDate(trial.due_date) }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-between pt-1">
            <a
              v-if="trial.metadata?.cancel_url"
              :href="trial.metadata.cancel_url"
              target="_blank"
              class="text-[11px] text-zinc-400 hover:text-white transition-colors flex items-center gap-1 font-sans"
            >
              <span>Direct Link</span>
              <ExternalLink class="w-3 h-3 text-zinc-400" />
            </a>
            <RouterLink
              v-else
              :to="`/finance/subscriptions/${trial.id}`"
              class="text-[11px] text-zinc-400 hover:text-white transition-colors"
            >
              View Dossier →
            </RouterLink>

            <button
              @click="handleCancelTrial(trial.id)"
              class="px-2.5 py-1 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors"
            >
              Mark Cancelled
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- RECURRING SUBSCRIPTIONS MASTER TABLE -->
    <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <Repeat class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Recurring Subscriptions Ledger
          </h2>
          <span class="text-[11px] font-mono text-zinc-500 ml-1">({{ filteredSubscriptions.length }} Services)</span>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          <!-- Search input -->
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Filter service / email..."
              class="bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs rounded-md pl-7 pr-2.5 py-1 font-mono outline-none focus:border-zinc-700 w-36 sm:w-44"
            />
            <Search class="w-3.5 h-3.5 text-zinc-500 absolute left-2 top-1.5" />
          </div>

          <!-- Type filter tabs -->
          <div class="flex items-center bg-zinc-950/80 border border-zinc-800/80 rounded-md p-0.5">
            <button
              v-for="f in typeFilters"
              :key="f.value"
              @click="selectedTypeFilter = f.value"
              type="button"
              class="px-2 py-0.5 rounded text-[11px] font-mono transition-colors"
              :class="selectedTypeFilter === f.value ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
            >
              {{ f.label }}
            </button>
          </div>
        </div>
      </div>

      <!-- Table Container -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[10px] font-mono uppercase text-zinc-500">
              <th class="py-3 px-4 font-semibold">Service / Plan</th>
              <th class="py-3 px-4 font-semibold">Category</th>
              <th class="py-3 px-4 font-semibold">Billing Cycle</th>
              <th class="py-3 px-4 font-semibold text-right">Fee</th>
              <th class="py-3 px-4 font-semibold text-right">Monthly Burn</th>
              <th class="py-3 px-4 font-semibold">Linked Account</th>
              <th class="py-3 px-4 font-semibold">Next Renewal</th>
              <th class="py-3 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="sub in filteredSubscriptions"
              :key="sub.id"
              class="hover:bg-zinc-800/40 transition-colors"
            >
              <!-- 1. Service / Plan -->
              <td class="py-3 px-4 font-mono">
                <RouterLink
                  :to="`/finance/subscriptions/${sub.id}`"
                  class="font-semibold text-zinc-100 hover:text-white hover:underline flex items-center gap-1.5"
                >
                  <span>{{ sub.title }}</span>
                  <span
                    v-if="sub.metadata?.plan_name"
                    class="text-[9px] px-1 py-0.2 rounded border border-zinc-800 bg-zinc-900 text-zinc-400 font-normal"
                  >
                    {{ sub.metadata.plan_name }}
                  </span>
                  <span
                    v-if="sub.type === 'FREE_TRIAL'"
                    class="text-[9px] px-1 py-0.2 rounded border border-rose-500/20 bg-rose-500/10 text-rose-400 font-normal"
                  >
                    TRIAL
                  </span>
                </RouterLink>
              </td>

              <!-- 2. Category -->
              <td class="py-3 px-4 font-mono text-zinc-400 text-[11px]">
                {{ sub.metadata?.category || 'GENERAL' }}
              </td>

              <!-- 3. Billing Cycle -->
              <td class="py-3 px-4 font-mono text-zinc-300">
                <span class="capitalize">{{ sub.metadata?.billing_cycle || 'Monthly' }}</span>
              </td>

              <!-- 4. Fee -->
              <td class="py-3 px-4 text-right font-mono tabular-nums text-zinc-100 font-medium">
                {{ sub.currency === 'USD' ? '$' : '฿' }}{{ formatNumber(sub.amount) }}
              </td>

              <!-- 5. Monthly Burn -->
              <td class="py-3 px-4 text-right font-mono tabular-nums text-zinc-300">
                {{ sub.currency === 'USD' ? '$' : '฿' }}{{ formatNumber(getMonthlyEquivalent(sub)) }}
              </td>

              <!-- 6. Linked Account -->
              <td class="py-3 px-4 font-mono text-zinc-400 text-[11px] truncate max-w-[160px]">
                {{ sub.metadata?.account_email || sub.metadata?.payment_method || '-' }}
              </td>

              <!-- 7. Next Renewal -->
              <td class="py-3 px-4 font-mono text-zinc-300 whitespace-nowrap">
                <div class="flex items-center gap-1.5">
                  <span>{{ formatDate(sub.due_date) || `Day ${sub.billing_day || '-'}` }}</span>
                  <span
                    v-if="getDaysRemaining(sub) !== null && getDaysRemaining(sub)! <= 3"
                    class="text-[9px] px-1 py-0.2 rounded font-semibold"
                    :class="getDaysRemaining(sub)! <= 1 ? 'bg-rose-950 text-rose-400 border border-rose-800' : 'bg-zinc-800 text-amber-400'"
                  >
                    {{ getDaysRemaining(sub)! <= 0 ? 'DUE' : `${getDaysRemaining(sub)}d` }}
                  </span>
                </div>
              </td>

              <!-- 8. Actions -->
              <td class="py-3 px-4 text-right">
                <div class="flex items-center justify-end gap-1.5">
                  <RouterLink
                    :to="`/finance/subscriptions/${sub.id}`"
                    class="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                    title="View Dossier"
                  >
                    <ArrowRight class="w-3.5 h-3.5" />
                  </RouterLink>
                  <button
                    @click="confirmDelete(sub.id)"
                    type="button"
                    class="p-1.5 rounded hover:bg-zinc-800 text-zinc-500 hover:text-rose-400 transition-colors"
                    title="Delete Subscription"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </td>
            </tr>

            <!-- Empty State -->
            <tr v-if="filteredSubscriptions.length === 0">
              <td colspan="8" class="py-12 text-center text-xs text-zinc-500 font-mono">
                <div class="flex flex-col items-center justify-center gap-2">
                  <Repeat class="w-6 h-6 text-zinc-600" />
                  <p>No subscriptions or trials found in this filter scope</p>
                  <RouterLink
                    to="/finance/subscriptions/new"
                    class="mt-2 px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-semibold text-xs"
                  >
                    Register New Service
                  </RouterLink>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Confirm Modal -->
    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      @confirm="handleConfirmAction"
      @cancel="confirmModal.isOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useSubscriptions } from '../../composables/finance/useSubscriptions'
import { useToastStore } from '../../stores/toast'
import type { FinancialObligation } from '../../types/finance'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import {
  Plus,
  Flame,
  Clock,
  Repeat,
  ShieldAlert,
  Search,
  ExternalLink,
  ArrowRight,
  Trash2
} from 'lucide-vue-next'

const { subscriptions, fetchSubscriptions, cancelTrial, deleteSubscription } = useSubscriptions()
const toast = useToastStore()

const searchQuery = ref('')
const selectedTypeFilter = ref<'ALL' | 'ACTIVE' | 'TRIAL' | 'CANCELLED'>('ALL')

const typeFilters = [
  { value: 'ALL', label: 'All' },
  { value: 'ACTIVE', label: 'Active SaaS' },
  { value: 'TRIAL', label: 'Free Trials' },
  { value: 'CANCELLED', label: 'Cancelled' }
] as const

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  action: () => {}
})

const activeSubscriptionsList = computed(() => {
  return subscriptions.value.filter(s => s.type === 'SUBSCRIPTION' && s.status === 'ACTIVE')
})

const activeTrialsList = computed(() => {
  return subscriptions.value.filter(s => s.type === 'FREE_TRIAL' && s.status === 'ACTIVE')
})

const uniqueCategoriesCount = computed(() => {
  const set = new Set<string>()
  subscriptions.value.forEach(s => {
    if (s.metadata?.category) set.add(s.metadata.category)
  })
  return set.size
})

const filteredSubscriptions = computed(() => {
  let list = [...subscriptions.value]

  if (selectedTypeFilter.value === 'ACTIVE') {
    list = list.filter(s => s.type === 'SUBSCRIPTION' && s.status === 'ACTIVE')
  } else if (selectedTypeFilter.value === 'TRIAL') {
    list = list.filter(s => s.type === 'FREE_TRIAL')
  } else if (selectedTypeFilter.value === 'CANCELLED') {
    list = list.filter(s => s.status === 'CANCELLED')
  }

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(s => {
      const title = s.title.toLowerCase()
      const email = (s.metadata?.account_email || '').toLowerCase()
      const cat = (s.metadata?.category || '').toLowerCase()
      return title.includes(q) || email.includes(q) || cat.includes(q)
    })
  }

  return list
})

function getMonthlyEquivalent(sub: FinancialObligation): number {
  const amt = Number(sub.amount || 0)
  const cycle = (sub.metadata?.billing_cycle || 'MONTHLY').toUpperCase()
  if (cycle === 'YEARLY') return amt / 12
  if (cycle === 'QUARTERLY') return amt / 3
  if (cycle === 'WEEKLY') return amt * 4.333
  return amt
}

const totalMonthlyBurnTHB = computed(() => {
  return activeSubscriptionsList.value
    .filter(s => (s.currency || 'THB').toUpperCase() === 'THB')
    .reduce((sum, s) => sum + getMonthlyEquivalent(s), 0)
})

const totalMonthlyBurnUSD = computed(() => {
  return activeSubscriptionsList.value
    .filter(s => (s.currency || 'THB').toUpperCase() === 'USD')
    .reduce((sum, s) => sum + getMonthlyEquivalent(s), 0)
})

const totalTrialLiabilityTHB = computed(() => {
  return activeTrialsList.value
    .reduce((sum, s) => sum + Number(s.amount || 0), 0)
})

function getTrialDaysLeft(trial: FinancialObligation): number {
  if (!trial.due_date) return 0
  const target = new Date(trial.due_date).getTime()
  const now = new Date(new Date().toISOString().split('T')[0]).getTime()
  return Math.round((target - now) / (1000 * 60 * 60 * 24))
}

function getDaysRemaining(sub: FinancialObligation): number | null {
  if (!sub.due_date) return null
  const target = new Date(sub.due_date).getTime()
  const now = new Date(new Date().toISOString().split('T')[0]).getTime()
  return Math.round((target - now) / (1000 * 60 * 60 * 24))
}

function formatDate(dateStr?: string | null) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

function formatNumber(val: any): string {
  const num = Number(val || 0)
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function handleCancelTrial(id: string) {
  try {
    await cancelTrial(id)
    toast.success('Free trial marked as cancelled')
  } catch {
    toast.error('Failed to cancel free trial')
  }
}

function confirmDelete(id: string) {
  confirmModal.title = 'Delete Subscription'
  confirmModal.message = 'Are you sure you want to delete this subscription record? All tracking and alarms will be removed.'
  confirmModal.confirmText = 'Delete'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await deleteSubscription(id)
      toast.info('Deleted subscription record')
    } catch {
      toast.error('Failed to delete subscription')
    }
  }
  confirmModal.isOpen = true
}

function handleConfirmAction() {
  confirmModal.isOpen = false
  confirmModal.action()
}

onMounted(async () => {
  await fetchSubscriptions()
})
</script>
