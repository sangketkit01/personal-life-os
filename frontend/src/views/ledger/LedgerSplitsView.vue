<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans pb-16">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2 mb-2">
          <RouterLink
            to="/ledger"
            class="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft class="w-3.5 h-3.5" />
            <span>Cash Flow Radar</span>
          </RouterLink>
          <span class="text-zinc-600">/</span>
          <span class="text-xs font-mono text-zinc-300">Shared Bills & Splits</span>
        </div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Shared Bills & Split Receivables</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            RADAR TWO-WAY SYNC
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Track group meal & travel shares owed by friends, with one-click wallet deposit and automatic Radar debtor closure
        </p>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <RouterLink
          to="/finance/debts"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-300 transition-colors flex items-center gap-1.5"
        >
          <HandCoins class="w-3.5 h-3.5 text-zinc-400" />
          <span>Open Debtors Directory →</span>
        </RouterLink>
      </div>
    </div>

    <!-- Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-500 block">Total Pending Reimbursements</span>
        <div class="text-xl font-bold text-amber-400 mt-2 tabular-nums">
          ฿{{ pendingTotalAmount.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 block mt-1">{{ pendingCount }} friends currently owe you</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-500 block">Settled Friend Shares</span>
        <div class="text-xl font-bold text-emerald-400 mt-2 tabular-nums">
          ฿{{ settledTotalAmount.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 block mt-1">{{ settledCount }} shares repaid and deposited</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-500 block">Total Recorded Split Items</span>
        <div class="text-xl font-bold text-zinc-100 mt-2 tabular-nums">
          {{ splitsList.length }} Items
        </div>
        <span class="text-[10px] text-zinc-500 block mt-1">From group expenses</span>
      </div>
    </div>

    <!-- Filter Pills -->
    <div class="flex items-center gap-2 pb-1 border-b border-zinc-800/80 font-mono text-xs">
      <button
        @click="statusFilter = 'ALL'"
        type="button"
        class="px-3 py-1 rounded text-xs transition-colors"
        :class="statusFilter === 'ALL' ? 'bg-zinc-800 text-zinc-100 font-semibold shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
      >
        All ({{ splitsList.length }})
      </button>
      <button
        @click="statusFilter = 'PENDING'"
        type="button"
        class="px-3 py-1 rounded text-xs transition-colors"
        :class="statusFilter === 'PENDING' ? 'bg-zinc-800 text-amber-400 font-semibold shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
      >
        Pending Settlement ({{ pendingCount }})
      </button>
      <button
        @click="statusFilter = 'SETTLED'"
        type="button"
        class="px-3 py-1 rounded text-xs transition-colors"
        :class="statusFilter === 'SETTLED' ? 'bg-zinc-800 text-emerald-400 font-semibold shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
      >
        Settled ({{ settledCount }})
      </button>
    </div>

    <!-- Splits Table -->
    <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
      <div v-if="filteredSplits.length === 0" class="p-16 text-center text-xs font-mono text-zinc-500">
        No shared bill items match this status filter.
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs font-mono">
          <thead>
            <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[10px] uppercase text-zinc-500 tracking-wider">
              <th class="py-3 px-4">Friend / Debtor</th>
              <th class="py-3 px-4">Contact / PromptPay</th>
              <th class="py-3 px-4 text-right">Owed Amount</th>
              <th class="py-3 px-4 text-center">Status</th>
              <th class="py-3 px-4 text-right pr-4">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="s in filteredSplits"
              :key="s.id"
              class="hover:bg-zinc-900/40 transition-colors"
            >
              <!-- Friend Name & Parent Bill Reference -->
              <td class="py-3 px-4 font-sans font-medium text-zinc-100">
                <div class="flex items-center gap-2.5">
                  <span class="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700/60 flex items-center justify-center text-[10px] font-bold text-zinc-300 uppercase shrink-0">
                    {{ s.counterparty_name.slice(0, 1) }}
                  </span>
                  <div>
                    <div class="flex items-center gap-1.5">
                      <span>{{ s.counterparty_name }}</span>
                      <RouterLink
                        v-if="s.debtor_id"
                        :to="`/finance/debts/${s.debtor_id}`"
                        class="text-[9px] font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
                        title="View linked Radar Debtor dossier"
                      >
                        [Radar ↗]
                      </RouterLink>
                    </div>
                    <div class="text-[10px] font-mono text-zinc-500 mt-0.5">
                      <span>{{ s.transaction_title || 'Shared Bill' }}</span>
                      <span v-if="s.transaction_date"> • {{ s.transaction_date }}</span>
                      <span v-if="s.transaction_account_name"> • {{ s.transaction_account_name }}</span>
                    </div>
                  </div>
                </div>
              </td>

              <!-- Contact -->
              <td class="py-3 px-4 text-zinc-400">
                {{ s.counterparty_contact || '-' }}
              </td>

              <!-- Amount -->
              <td class="py-3 px-4 text-right font-mono tabular-nums font-semibold text-zinc-100">
                ฿{{ Number(s.amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </td>

              <!-- Status -->
              <td class="py-3 px-4 text-center">
                <span
                  class="text-[9px] font-mono px-2 py-0.5 rounded border uppercase font-medium"
                  :class="s.is_settled ? 'bg-zinc-900 text-emerald-400 border-zinc-800' : 'bg-zinc-900 text-amber-400 border-zinc-800'"
                >
                  {{ s.is_settled ? 'Settled' : 'Pending' }}
                </span>
              </td>

              <!-- Actions -->
              <td class="py-3 px-4 text-right pr-4">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    v-if="!s.is_settled"
                    type="button"
                    @click="copyReminder(s)"
                    class="p-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                    title="Copy friendly reminder message"
                  >
                    <Copy class="w-3.5 h-3.5" />
                  </button>
                  <button
                    v-if="!s.is_settled"
                    @click="openSettleModal(s)"
                    class="px-2.5 py-1 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-sans font-semibold transition-colors flex items-center gap-1 shadow-sm"
                  >
                    <Check class="w-3 h-3 text-zinc-950" />
                    <span>Settle & Deposit</span>
                  </button>
                  <span v-else class="text-[11px] text-zinc-500 font-sans">
                    Deposited
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Settle Modal -->
    <SettleSplitModal
      :is-open="showSettleModal"
      :split="selectedSplit"
      @close="showSettleModal = false"
      @settled="loadSplits"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ledgerApi } from '../../api/ledger'
import { useToastStore } from '../../stores/toast'
import type { TransactionSplitItem } from '../../types/ledger'
import SettleSplitModal from '../../components/ledger/SettleSplitModal.vue'
import {
  ArrowLeft,
  HandCoins,
  Check,
  Copy
} from 'lucide-vue-next'

const toast = useToastStore()
const splitsList = ref<TransactionSplitItem[]>([])
const statusFilter = ref<'ALL' | 'PENDING' | 'SETTLED'>('PENDING')
const showSettleModal = ref(false)
const selectedSplit = ref<TransactionSplitItem | null>(null)

const pendingCount = computed(() => splitsList.value.filter((s) => !s.is_settled).length)
const settledCount = computed(() => splitsList.value.filter((s) => s.is_settled).length)

const pendingTotalAmount = computed(() => {
  return splitsList.value
    .filter((s) => !s.is_settled)
    .reduce((sum, s) => sum + Number(s.amount || 0), 0)
})

const settledTotalAmount = computed(() => {
  return splitsList.value
    .filter((s) => s.is_settled)
    .reduce((sum, s) => sum + Number(s.amount || 0), 0)
})

const filteredSplits = computed(() => {
  if (statusFilter.value === 'PENDING') return splitsList.value.filter((s) => !s.is_settled)
  if (statusFilter.value === 'SETTLED') return splitsList.value.filter((s) => s.is_settled)
  return splitsList.value
})

onMounted(async () => {
  await loadSplits()
})

async function loadSplits() {
  const res = await ledgerApi.getSplits()
  splitsList.value = Array.isArray(res) ? res : res.results || []
}

function openSettleModal(split: TransactionSplitItem) {
  selectedSplit.value = split
  showSettleModal.value = true
}

function copyReminder(split: TransactionSplitItem) {
  const contactText = split.counterparty_contact ? ` (${split.counterparty_contact})` : ''
  const billTitle = split.transaction_title || 'shared expense'
  const text = `Hi ${split.counterparty_name}${contactText}, friendly reminder regarding your share of ฿${Number(split.amount).toLocaleString('en-US')} for "${billTitle}". When convenient, please transfer to PromptPay. Thank you!`
  navigator.clipboard.writeText(text)
  toast.success(`Copied reminder for ${split.counterparty_name}`)
}
</script>
