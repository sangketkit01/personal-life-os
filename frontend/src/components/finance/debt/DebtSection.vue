<template>
  <div class="space-y-6 font-sans">
    <!-- Two-Way Debt Balance Position Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
      <!-- Liabilities (Outflow) -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm">
        <span class="text-[10px] font-mono uppercase text-zinc-400 block">My Liabilities</span>
        <div class="mt-2 text-xl font-bold font-mono text-rose-400 tabular-nums">
          -฿{{ totalMyDebtsRemaining.toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">{{ myDebtsList.length }} active debt obligations</span>
      </div>

      <!-- Receivables (Inflow) -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm">
        <span class="text-[10px] font-mono uppercase text-zinc-400 block">Debtors Receivables</span>
        <div class="mt-2 text-xl font-bold font-mono text-emerald-400 tabular-nums">
          +฿{{ totalDebtorsRemaining.toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">{{ debtorsList.length }} active debtors to collect</span>
      </div>

      <!-- Net Position -->
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm">
        <span class="text-[10px] font-mono uppercase text-zinc-400 block">Net Debt Position</span>
        <div
          class="mt-2 text-xl font-bold font-mono tabular-nums"
          :class="netDebtPosition >= 0 ? 'text-emerald-400' : 'text-rose-400'"
        >
          {{ netDebtPosition >= 0 ? '+' : '' }}฿{{ netDebtPosition.toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">
          {{ netDebtPosition >= 0 ? 'Net positive: receivables exceed liabilities' : 'Net liability: outstanding debts to settle' }}
        </span>
      </div>
    </div>

    <!-- Segmented Tab: Choose between Liabilities vs Debtors Directory -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/80">
      <div class="flex items-center gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-lg overflow-x-auto">
        <button
          type="button"
          @click="activeSubTab = 'DEBTORS'"
          class="px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-2 whitespace-nowrap"
          :class="[
            activeSubTab === 'DEBTORS'
              ? 'bg-zinc-800 text-emerald-400 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          ]"
        >
          <UserCheck class="w-3.5 h-3.5" />
          <span>Debtors Directory</span>
          <span class="text-[10px] font-mono px-1 py-0.2 rounded bg-zinc-950 border border-zinc-800 text-zinc-400">
            {{ debtorsList.length }}
          </span>
        </button>

        <button
          type="button"
          @click="activeSubTab = 'LIABILITIES'"
          class="px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-2 whitespace-nowrap"
          :class="[
            activeSubTab === 'LIABILITIES'
              ? 'bg-zinc-800 text-rose-400 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          ]"
        >
          <HandCoins class="w-3.5 h-3.5" />
          <span>My Liabilities</span>
          <span class="text-[10px] font-mono px-1 py-0.2 rounded bg-zinc-950 border border-zinc-800 text-zinc-400">
            {{ myDebtsList.length }}
          </span>
        </button>
      </div>

      <button
        @click="emit('openCreate')"
        class="self-start sm:self-auto px-3 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>{{ activeSubTab === 'DEBTORS' ? 'Add Debtor' : 'Add Liability' }}</span>
      </button>
    </div>

    <!-- SUB-TAB 1: DEBTORS DIRECTORY (INFLOW) -->
    <div v-if="activeSubTab === 'DEBTORS'" class="space-y-4">
      <div
        v-if="debtorsList.length === 0"
        class="p-12 rounded-lg bg-zinc-900/30 border border-zinc-800 text-center space-y-3 font-mono text-xs text-zinc-500"
      >
        <p>No active debtors recorded. Everyone has paid you back!</p>
        <button
          @click="emit('openCreate')"
          class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-sans transition-colors inline-block"
        >
          + Record Money Lent
        </button>
      </div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div
          v-for="debtor in debtorsList"
          :key="debtor.id"
          class="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 space-y-4 hover:border-zinc-700/80 hover:bg-zinc-900/70 transition-all duration-200 shadow-sm hover:shadow-md"
        >
          <!-- Debtor Header -->
          <div class="flex items-start justify-between">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                  Debtor
                </span>
                <span v-if="debtor.metadata?.contact" class="text-xs text-zinc-400 font-mono">
                  <Phone class="w-3 h-3 inline" /> {{ debtor.metadata.contact }}
                </span>
              </div>
              <h3 class="text-sm font-semibold text-zinc-100 mt-1 font-sans">
                {{ debtor.metadata?.counterparty || debtor.title }}
              </h3>
            </div>

            <!-- Header Actions -->
            <div class="flex items-center gap-1.5">
              <RouterLink
                :to="`/finance/debts/${debtor.id}`"
                class="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white transition-colors flex items-center gap-1 text-[10px] font-mono active:scale-95"
                title="Debtor Dossier & Timeline"
              >
                <span>Dossier</span>
                <ArrowRight class="w-3 h-3 text-zinc-500" />
              </RouterLink>
              <button
                @click="emit('openHistory', debtor)"
                class="p-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 active:scale-95 transition-all"
                title="Repayment History & Slips"
              >
                <History class="w-3.5 h-3.5" />
              </button>
              <button
                @click="emit('openEdit', debtor)"
                class="p-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 active:scale-95 transition-all"
                title="Edit Debtor Info"
              >
                <Edit2 class="w-3.5 h-3.5" />
              </button>
              <button
                @click="emit('openPay', debtor)"
                class="px-2.5 py-1 rounded bg-zinc-100 hover:bg-white active:scale-95 text-zinc-950 text-xs font-semibold transition-all shadow-sm"
              >
                Record Repay
              </button>
            </div>
          </div>

          <!-- Numbers Grid -->
          <div class="grid grid-cols-3 gap-2 p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/60 font-mono text-xs">
            <div>
              <span class="text-[9px] text-zinc-500 block uppercase">Total Lent</span>
              <span class="text-zinc-200 font-semibold">฿{{ Number(debtor.amount).toLocaleString('th-TH') }}</span>
            </div>
            <div>
              <span class="text-[9px] text-zinc-500 block uppercase">Paid Back</span>
              <span class="text-emerald-400 font-semibold">฿{{ Number(debtor.summary?.total_paid || 0).toLocaleString('th-TH') }}</span>
            </div>
            <div class="text-right">
              <span class="text-[9px] text-zinc-500 block uppercase">Remaining</span>
              <span class="text-amber-400 font-semibold">฿{{ Number(debtor.summary?.remaining_balance || debtor.amount).toLocaleString('th-TH') }}</span>
            </div>
          </div>

          <!-- INLINE QUICK RECALL TOOL -->
          <div class="p-3 rounded-lg bg-zinc-950 border border-emerald-500/20 space-y-2.5 font-mono text-xs">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-1.5 text-emerald-400 font-semibold text-[11px]">
                <MessageSquare class="w-3.5 h-3.5" />
                <span>One-Click LINE/SMS Recall Template</span>
              </div>
              <span class="text-[9px] text-zinc-500">
                Due: {{ debtor.due_date ? new Date(debtor.due_date).toLocaleDateString('en-GB') : 'Flexible' }}
              </span>
            </div>

            <!-- Message Preview -->
            <div class="p-2.5 rounded bg-zinc-900/80 border border-zinc-800/80 text-zinc-300 font-sans text-xs select-all leading-relaxed">
              {{ getRecallText(debtor) }}
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center gap-2 pt-1 font-sans">
              <button
                @click="copyRecallMessage(debtor)"
                class="flex-1 py-1 px-2.5 rounded bg-zinc-800 hover:bg-zinc-700 active:scale-95 text-zinc-200 text-xs font-medium transition-all flex items-center justify-center gap-1.5"
              >
                <Check v-if="copiedIds[debtor.id]" class="w-3.5 h-3.5 text-zinc-300" />
                <Copy v-else class="w-3.5 h-3.5 text-zinc-400" />
                <span>{{ copiedIds[debtor.id] ? 'Copied!' : 'Copy Text' }}</span>
              </button>

              <a
                :href="getLineShareUrl(debtor)"
                target="_blank"
                class="py-1 px-3 rounded bg-[#06C755] hover:bg-[#05b34c] active:scale-95 text-white text-xs font-medium transition-all flex items-center justify-center gap-1.5 shadow-sm"
              >
                <Send class="w-3.5 h-3.5" />
                <span>Share LINE</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- SUB-TAB 2: MY LIABILITIES (OUTFLOW) -->
    <div v-else class="space-y-4">
      <div
        v-if="myDebtsList.length === 0"
        class="p-12 rounded-lg bg-zinc-900/30 border border-zinc-800 text-center space-y-3 font-mono text-xs text-zinc-500"
      >
        <p>No active liabilities recorded. You have zero debt!</p>
        <button
          @click="emit('openCreate')"
          class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-sans transition-colors inline-block"
        >
          + Record Liability
        </button>
      </div>

      <div v-else class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-950/40">
                <th class="py-2.5 pl-4">Creditor / Counterparty</th>
                <th class="py-2.5">Debt Type</th>
                <th class="py-2.5 text-right">Original Borrowed</th>
                <th class="py-2.5 text-right">Remaining Balance</th>
                <th class="py-2.5">Settlement Due</th>
                <th class="py-2.5 text-right pr-4">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr
                v-for="debt in myDebtsList"
                :key="debt.id"
                class="hover:bg-zinc-800/40 transition-colors"
              >
                <td class="py-2.5 pl-4 font-sans font-medium text-zinc-100">
                  <div>{{ debt.title }}</div>
                  <div class="text-[10px] text-zinc-500 font-mono">{{ debt.metadata?.counterparty || '-' }}</div>
                </td>
                <td class="py-2.5">
                  <span class="text-[9px] uppercase px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
                    {{ debt.subtype === 'FORMAL_LOAN' ? 'Formal Bank Loan' : 'Informal' }}
                  </span>
                </td>
                <td class="py-2.5 text-right text-zinc-400 tabular-nums">
                  ฿{{ Number(debt.amount).toLocaleString('th-TH') }}
                </td>
                <td class="py-2.5 text-right font-semibold text-rose-400 tabular-nums">
                  ฿{{ Number(debt.summary?.remaining_balance || debt.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
                </td>
                <td class="py-2.5 text-zinc-400">
                  {{ debt.due_date ? new Date(debt.due_date).toLocaleDateString('en-GB') : 'N/A' }}
                </td>
                <td class="py-2.5 text-right pr-4">
                  <div class="flex items-center justify-end gap-1.5">
                    <RouterLink
                      :to="`/finance/debts/${debt.id}`"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 active:scale-95 transition-all"
                      title="Debt Dossier & Ledger"
                    >
                      <ArrowRight class="w-3.5 h-3.5" />
                    </RouterLink>
                    <button
                      @click="emit('openHistory', debt)"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 active:scale-95 transition-all"
                      title="Settlement History & Slips"
                    >
                      <History class="w-3.5 h-3.5" />
                    </button>
                    <button
                      @click="emit('openEdit', debt)"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 active:scale-95 transition-all"
                      title="Edit Debt"
                    >
                      <Edit2 class="w-3.5 h-3.5" />
                    </button>
                    <button
                      v-if="debt.status === 'ACTIVE'"
                      @click="emit('openPay', debt)"
                      class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 active:scale-95 border border-zinc-800 text-[10px] text-zinc-200 transition-all"
                    >
                      Pay
                    </button>
                    <button
                      @click="emit('delete', debt.id)"
                      class="p-1 rounded text-zinc-600 hover:text-rose-400 active:scale-95 transition-all"
                      title="Delete"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
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
import {
 ref, computed } from 'vue'
import { useToastStore } from '../../../stores/toast'
import type { FinancialObligation } from '../../../types/finance'
import {
  Phone,

  UserCheck,
  HandCoins,
  Plus,
  History,
  Edit2,
  Trash2,
  MessageSquare,
  Copy,
  Check,
  Send,
  ArrowRight
} from 'lucide-vue-next'

const props = defineProps<{
  obligations: FinancialObligation[]
}>()

const emit = defineEmits<{
  (e: 'openCreate'): void
  (e: 'openPay', ob: FinancialObligation): void
  (e: 'openHistory', ob: FinancialObligation): void
  (e: 'openEdit', ob: FinancialObligation): void
  (e: 'delete', id: string): void
}>()

const toast = useToastStore()
const activeSubTab = ref<'DEBTORS' | 'LIABILITIES'>('DEBTORS')
const copiedIds = ref<Record<string, boolean>>({})

const debtorsList = computed(() => {
  return props.obligations.filter(o => o.direction === 'INFLOW' && o.status === 'ACTIVE')
})

const myDebtsList = computed(() => {
  return props.obligations.filter(o => o.type === 'DEBT' && o.direction !== 'INFLOW' && o.status === 'ACTIVE')
})

const totalDebtorsRemaining = computed(() => {
  return debtorsList.value.reduce((sum, d) => sum + Number(d.summary?.remaining_balance || d.amount || 0), 0)
})

const totalMyDebtsRemaining = computed(() => {
  return myDebtsList.value.reduce((sum, d) => sum + Number(d.summary?.remaining_balance || d.amount || 0), 0)
})

const netDebtPosition = computed(() => {
  return totalDebtorsRemaining.value - totalMyDebtsRemaining.value
})

function getRecallText(debtor: FinancialObligation) {
  const counterparty = debtor.metadata?.counterparty || debtor.title || 'Friend'
  const remaining = Number(debtor.summary?.remaining_balance ?? debtor.amount ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })
  const dueDateStr = debtor.due_date ? new Date(debtor.due_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : 'soon'
  const pp = debtor.metadata?.promptpay || localStorage.getItem('finance_promptpay_default') || ''
  const ppText = pp ? `PromptPay: ${pp}` : 'the designated account'
  const curSymbol = debtor.currency === 'USD' ? '$' : '฿'
  return `Hi ${counterparty}, friendly reminder regarding the outstanding balance of ${curSymbol}${remaining} (due: ${dueDateStr}). When convenient, please transfer to ${ppText}. Thank you!`
}

function getLineShareUrl(debtor: FinancialObligation) {
  return `https://line.me/R/msg/text/?${encodeURIComponent(getRecallText(debtor))}`
}

async function copyRecallMessage(debtor: FinancialObligation) {
  try {
    await navigator.clipboard.writeText(getRecallText(debtor))
    copiedIds.value[debtor.id] = true
    toast.success('Recall message copied to clipboard!')
    setTimeout(() => {
      copiedIds.value[debtor.id] = false
    }, 2500)
  } catch (err) {
    toast.error('Failed to copy to clipboard')
  }
}
</script>