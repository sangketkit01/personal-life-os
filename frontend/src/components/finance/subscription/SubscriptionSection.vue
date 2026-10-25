<template>
  <div class="space-y-6 font-sans">
    <!-- Summary Header Cards for Subscriptions -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <span class="text-[10px] font-mono uppercase text-zinc-500 block">Monthly Subscription Burn</span>
        <div class="mt-2 text-xl font-semibold font-mono text-zinc-100 tabular-nums">
          ฿{{ totalMonthlyBurn.toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">/ month (Annualized: ฿{{ (totalMonthlyBurn * 12).toLocaleString('th-TH', { maximumFractionDigits: 0 }) }}/yr)</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <span class="text-[10px] font-mono uppercase text-zinc-500 block">Active Subscriptions</span>
        <div class="mt-2 text-xl font-semibold font-mono text-zinc-100 tabular-nums">
          {{ subscriptionsList.length }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">Recurring services</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <span class="text-[10px] font-mono uppercase text-zinc-500 block">Trial Trap Liability</span>
        <div class="mt-2 text-xl font-semibold font-mono text-rose-400 tabular-nums">
          ฿{{ totalTrialRisk.toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">{{ freeTrialsList.length }} active free trials</span>
      </div>
    </div>

    <!-- 1. FREE TRIAL HUNTER ZONE (RED ALERT) -->
    <div v-if="freeTrialsList.length > 0" class="space-y-3">
      <div class="flex items-center justify-between pb-1 border-b border-zinc-800/80">
        <div class="flex items-center gap-2">
          <ShieldAlert class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Free Trial Hunter (Auto-Debit Protection)
          </h2>
        </div>
        <span class="text-[10px] font-mono text-zinc-500">Cancel before renewal date</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <div
          v-for="trial in freeTrialsList"
          :key="trial.id"
          class="p-4 rounded-xl border transition-all space-y-3"
          :class="[
            trial.summary?.urgency === 'CRITICAL'
              ? 'bg-zinc-900/80 border-rose-500/60 shadow-sm'
              : 'bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700'
          ]"
        >
          <div class="flex items-start justify-between">
            <div>
              <span
                class="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded font-mono border"
                :class="trial.summary?.urgency === 'CRITICAL' ? 'bg-zinc-900 text-rose-400 border-rose-500/30' : 'bg-zinc-900 text-zinc-400 border-zinc-800'"
              >
                {{ trial.summary?.urgency === 'CRITICAL' ? 'DUE TODAY' : `${trial.summary?.days_left ?? trial.summary?.days_remaining ?? 0} days left` }}
              </span>
              <h3 class="text-sm font-semibold text-zinc-100 mt-1 font-sans">{{ trial.title }}</h3>
            </div>

            <div class="text-right font-mono">
              <span class="text-xs font-semibold text-rose-400 tabular-nums">
                {{ currencySymbol(trial.currency) }}{{ Number(trial.amount).toLocaleString('th-TH') }}
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
              <span>Expires on:</span>
              <span class="text-zinc-300">{{ trial.due_date ? new Date(trial.due_date).toLocaleDateString('en-GB') : '-' }}</span>
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
              <span>Direct Cancel Link</span>
              <ExternalLink class="w-3 h-3 text-zinc-400" />
            </a>
            <span v-else class="text-[10px] text-zinc-600">No URL link</span>

            <button
              @click="emit('cancelTrial', trial.id)"
              class="px-2.5 py-1 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors"
            >
              Mark Cancelled
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. RECURRING SUBSCRIPTIONS TABLE -->
    <div class="space-y-3 pt-2">
      <div class="flex items-center justify-between pb-1 border-b border-zinc-800/80">
        <div class="flex items-center gap-2">
          <Repeat class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Active Recurring Subscriptions
          </h2>
        </div>
        <button
          @click="emit('openCreate')"
          class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          + Add Service
        </button>
      </div>

      <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-950/40">
                <th class="py-2.5 pl-4">Service / Plan</th>
                <th class="py-2.5">Billing Cycle</th>
                <th class="py-2.5 text-right">Cost</th>
                <th class="py-2.5">Linked Account</th>
                <th class="py-2.5">Next Renewal</th>
                <th class="py-2.5 text-right pr-4">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr
                v-for="sub in subscriptionsList"
                :key="sub.id"
                class="hover:bg-zinc-900/40 transition-colors"
              >
                <!-- Service Name -->
                <td class="py-2.5 pl-4 font-sans font-medium text-zinc-100">
                  <div class="flex items-center gap-2">
                    <span>{{ sub.title }}</span>
                    <span v-if="sub.metadata?.plan" class="text-[9px] font-mono px-1 py-0.2 rounded border border-zinc-800 bg-zinc-900 text-zinc-400">
                      {{ sub.metadata.plan }}
                    </span>
                  </div>
                </td>

                <!-- Billing Cycle -->
                <td class="py-2.5 text-zinc-400">
                  <span class="capitalize">{{ sub.metadata?.billing_cycle || 'Monthly' }}</span>
                </td>

                <!-- Cost -->
                <td class="py-2.5 text-right font-semibold text-zinc-100 tabular-nums">
                  {{ sub.currency === 'USD' ? '$' : '฿' }}{{ Number(sub.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
                </td>

                <!-- Linked Account -->
                <td class="py-2.5 text-zinc-400 truncate max-w-[180px]">
                  {{ sub.metadata?.account_email || '-' }}
                </td>

                <!-- Next Renewal -->
                <td class="py-2.5 text-zinc-300">
                  {{ sub.due_date ? new Date(sub.due_date).toLocaleDateString('en-GB') : `Day ${sub.billing_day || '-'}` }}
                </td>

                <!-- Actions -->
                <td class="py-2.5 text-right pr-4">
                  <div class="flex items-center justify-end gap-1.5">
                    <button
                      @click="emit('openHistory', sub)"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
                      title="History"
                    >
                      <History class="w-3.5 h-3.5" />
                    </button>
                    <button
                      @click="emit('openEdit', sub)"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
                      title="Edit"
                    >
                      <Edit2 class="w-3.5 h-3.5" />
                    </button>
                    <button
                      v-if="sub.status === 'ACTIVE'"
                      @click="emit('openPay', sub)"
                      class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] text-zinc-200 transition-colors"
                    >
                      Pay Bill
                    </button>
                    <button
                      @click="emit('delete', sub.id)"
                      class="p-1 rounded text-zinc-600 hover:text-rose-400 transition-colors"
                      title="Delete"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </td>
              </tr>

              <tr v-if="subscriptionsList.length === 0">
                <td colspan="6" class="py-8 text-center text-zinc-500 font-mono text-xs">
                  No active subscriptions tracked. Click "+ Add Service" to monitor your recurring expenses.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { currencySymbol } from '../../../utils/currency'
import { computed } from 'vue'
import type { FinancialObligation } from '../../../types/finance'
import {
  Repeat,
  ShieldAlert,
  ExternalLink,
  History,
  Edit2,
  Trash2
} from 'lucide-vue-next'

const props = defineProps<{
  obligations: FinancialObligation[]
}>()

const emit = defineEmits<{
  (e: 'openCreate'): void
  (e: 'openPay', ob: FinancialObligation): void
  (e: 'openHistory', ob: FinancialObligation): void
  (e: 'openEdit', ob: FinancialObligation): void
  (e: 'cancelTrial', id: string): void
  (e: 'delete', id: string): void
}>()

const freeTrialsList = computed(() => {
  return props.obligations.filter(o => o.type === 'FREE_TRIAL' && o.status === 'ACTIVE')
})

const subscriptionsList = computed(() => {
  return props.obligations.filter(o => o.type === 'SUBSCRIPTION' && o.status === 'ACTIVE')
})

const totalMonthlyBurn = computed(() => {
  return subscriptionsList.value.reduce((sum, s) => {
    let amt = Number(s.amount || 0)
    if (s.currency === 'USD') {
      amt = amt * 34.5
    }
    if (s.metadata?.billing_cycle === 'YEARLY') {
      amt = amt / 12
    }
    return sum + amt
  }, 0)
})

const totalTrialRisk = computed(() => {
  return freeTrialsList.value.reduce((sum, t) => {
    let amt = Number(t.amount || 0)
    if (t.currency === 'USD') {
      amt = amt * 34.5
    }
    return sum + amt
  }, 0)
})
</script>
