<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans pb-16">
    <!-- Top Bar -->
    <div class="pb-4 border-b border-zinc-800/80">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2.5 flex-wrap">
            <h1 class="text-xl font-semibold text-zinc-100 tracking-tight">
              {{ account?.name || 'Loading...' }}
            </h1>
            <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 font-semibold">
              {{ account?.account_type || 'BANK' }}
            </span>
            <span v-if="account?.is_default" class="text-[10px] font-mono text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 rounded font-semibold">
              Default
            </span>
          </div>

          <div class="flex items-center gap-3 text-xs text-zinc-400 font-mono mt-1 flex-wrap">
            <span>{{ account?.institution_name || 'Wallet' }}</span>
            <span v-if="account?.account_number">• Ref: {{ account.account_number }}</span>
            <span>• Currency: {{ account?.currency || 'THB' }}</span>
          </div>
        </div>

        <div class="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            @click="handleRecalculate"
            :disabled="isRecalculating"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 hover:border-zinc-700 border border-zinc-800 text-xs font-mono text-zinc-300 transition-all active:scale-[0.98] flex items-center gap-1.5 disabled:opacity-50"
            title="Recalculate balance from all ledger transactions"
          >
            <RefreshCw class="w-3.5 h-3.5 text-zinc-400" :class="{ 'animate-spin': isRecalculating }" />
            <span>{{ isRecalculating ? 'Recalculating...' : 'Recalculate' }}</span>
          </button>

          <button
            @click="showTransferModal = true"
            class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-all active:scale-[0.98] flex items-center gap-1.5 shadow-sm hover:shadow-white/10"
          >
            <ArrowRightLeft class="w-3.5 h-3.5 text-zinc-950" />
            <span>Transfer</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Account Metric Strip -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Current Balance</span>
        <div class="text-2xl font-bold text-zinc-100 mt-2 tabular-nums tracking-tight">
          ฿{{ Number(account?.current_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5">Verified ledger balance</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Initial Opening Balance</span>
        <div class="text-2xl font-bold text-zinc-200 mt-2 tabular-nums tracking-tight">
          ฿{{ Number(account?.initial_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5">Base starting balance</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-emerald-500/40 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Total Inflows</span>
        <div class="text-2xl font-bold text-emerald-400 mt-2 tabular-nums tracking-tight">
          +฿{{ totalAccountInflows.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5">Cumulative incoming funds</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-rose-500/40 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 transition-all duration-200 font-mono text-xs">
        <span class="text-[10px] uppercase text-zinc-400 font-semibold block">Total Outflows</span>
        <div class="text-2xl font-bold text-rose-400 mt-2 tabular-nums tracking-tight">
          -฿{{ totalAccountOutflows.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[11px] text-zinc-400 block mt-1.5">Cumulative outgoing funds</span>
      </div>
    </div>

    <!-- Account Statement Activity Table -->
    <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Receipt class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Statement Ledger Entries
          </h2>
          <span class="text-[11px] font-mono text-zinc-500 ml-1">({{ accountTransactions.length }} items)</span>
        </div>
      </div>

      <div v-if="accountTransactions.length === 0" class="p-16 text-center text-xs font-mono text-zinc-500">
        No statement transactions found for this account.
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs font-mono">
          <thead>
            <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[10px] uppercase text-zinc-500 tracking-wider">
              <th class="py-3 px-4">Date</th>
              <th class="py-3 px-4">Description</th>
              <th class="py-3 px-4">Category</th>
              <th class="py-3 px-4 text-right">Charged (฿)</th>
              <th class="py-3 px-4 text-right">Type</th>
              <th class="py-3 px-4 text-right pr-4">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="tx in accountTransactions"
              :key="tx.id"
              class="hover:bg-zinc-800/50 transition-colors duration-150 group"
            >
              <td class="py-3 px-4 text-zinc-400 whitespace-nowrap">{{ tx.transaction_date }}</td>
              <td class="py-3 px-4 font-sans font-medium text-zinc-200 group-hover:text-zinc-100 transition-colors">
                <div class="flex items-center gap-2 flex-wrap">
                  <span>{{ tx.title }}</span>
                  <span
                    v-if="tx.is_split"
                    class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center gap-1 font-semibold"
                  >
                    <Users class="w-2.5 h-2.5" />
                    <span>Split</span>
                  </span>
                  <a
                    v-if="tx.attachments && tx.attachments.length > 0"
                    :href="tx.attachments[0].drive_view_link || tx.attachments[0].file_url"
                    target="_blank"
                    class="inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[9px] font-mono bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-300 hover:text-white transition-colors"
                    title="View Receipt Slip in Google Drive"
                  >
                    <FileText class="w-2.5 h-2.5 text-zinc-400" />
                    <span>Slip</span>
                    <ExternalLink class="w-2 h-2 text-zinc-500" />
                  </a>
                </div>
              </td>
              <td class="py-3 px-4 text-zinc-400 font-sans">
                <span class="px-2 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-800/80 group-hover:border-zinc-700 transition-colors">
                  {{ tx.category_name || 'General' }}
                </span>
              </td>
              <td class="py-3 px-4 text-right font-mono tabular-nums font-semibold">
                <span :class="tx.transaction_type === 'INFLOW' ? 'text-emerald-400' : 'text-zinc-200'">
                  {{ tx.transaction_type === 'INFLOW' ? '+' : '-' }}฿{{ Number(tx.gross_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </span>
              </td>
              <td class="py-3 px-4 text-right">
                <span
                  class="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded border font-semibold"
                  :class="tx.transaction_type === 'INFLOW' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-zinc-900 text-zinc-400 border-zinc-800'"
                >
                  {{ tx.transaction_type }}
                </span>
              </td>
              <td class="py-3 px-4 text-right pr-4">
                <button
                  @click="handleEditTransaction(tx)"
                  class="p-1.5 rounded-lg text-zinc-500 hover:text-indigo-400 hover:bg-indigo-500/10 active:scale-[0.95] transition-all"
                  title="Edit Transaction"
                >
                  <Edit2 class="w-3.5 h-3.5" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination Controls -->
        <div
          v-if="totalPages > 1"
          class="px-5 py-3 border-t border-zinc-800/80 bg-zinc-950/40 flex items-center justify-between font-mono text-xs"
        >
          <span class="text-zinc-500">
            Page <strong class="text-zinc-300">{{ currentPage }}</strong> of <strong class="text-zinc-300">{{ totalPages }}</strong> ({{ totalRecords }} statement items)
          </span>
          <div class="flex items-center gap-2">
            <button
              @click="changePage(currentPage - 1)"
              :disabled="currentPage <= 1"
              class="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white disabled:opacity-40 transition-colors"
            >
              Previous
            </button>
            <button
              @click="changePage(currentPage + 1)"
              :disabled="currentPage >= totalPages"
              class="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white disabled:opacity-40 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Transfer Modal -->
    <TransferModal
      :is-open="showTransferModal"
      :default-source-id="accountId"
      @close="showTransferModal = false"
      @transferred="loadAccountData"
    />

    <!-- Transaction Edit Modal -->
    <TransactionModal
      :is-open="showTransactionModal"
      :transaction-to-edit="editingTransaction"
      @close="showTransactionModal = false; editingTransaction = null"
      @created="handleTransactionSaved"
      @updated="handleTransactionSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useLedgerStore } from '../../stores/ledger'
import { useToastStore } from '../../stores/toast'
import type { LedgerTransaction } from '../../types/ledger'
import TransferModal from '../../components/ledger/TransferModal.vue'
import TransactionModal from '../../components/ledger/TransactionModal.vue'
import {
  ArrowRightLeft,
  RefreshCw,
  Receipt,
  Users,
  FileText,
  ExternalLink,
  Edit2
} from 'lucide-vue-next'

const route = useRoute()
const ledgerStore = useLedgerStore()
const toast = useToastStore()

const accountId = computed(() => route.params.id as string)
const account = computed(() =>
  ledgerStore.accounts.find((a) => a.id === accountId.value) || null
)

const accountTransactions = ref<LedgerTransaction[]>([])
const showTransferModal = ref(false)
const showTransactionModal = ref(false)
const editingTransaction = ref<LedgerTransaction | null>(null)
const isRecalculating = ref(false)
const currentPage = ref(1)
const totalRecords = ref(0)
const pageSize = 20

function handleEditTransaction(tx: LedgerTransaction) {
  editingTransaction.value = tx
  showTransactionModal.value = true
}

async function handleTransactionSaved() {
  await loadAccountData()
  await ledgerStore.fetchAccounts()
}

const totalPages = computed(() => Math.ceil(totalRecords.value / pageSize))

const totalAccountInflows = computed(() => {
  return accountTransactions.value
    .filter((t) => t.transaction_type === 'INFLOW')
    .reduce((sum, t) => sum + Number(t.gross_amount || 0), 0)
})

const totalAccountOutflows = computed(() => {
  return accountTransactions.value
    .filter((t) => t.transaction_type === 'OUTFLOW')
    .reduce((sum, t) => sum + Number(t.gross_amount || 0), 0)
})

onMounted(async () => {
  await loadAccountData()
})

async function loadAccountData() {
  await Promise.all([
    ledgerStore.fetchAccounts(),
    ledgerStore.fetchCategories()
  ])
  const res = await ledgerStore.fetchTransactions({
    account: accountId.value,
    page: currentPage.value
  })
  accountTransactions.value = res.results || []
  totalRecords.value = res.count || 0
}

function changePage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadAccountData()
}

async function handleRecalculate() {
  if (!account.value) return
  isRecalculating.value = true
  try {
    await ledgerStore.recalculateBalance(account.value.id)
    await loadAccountData()
    toast.success(`Balance recalculated: ฿${Number(account.value.current_balance).toLocaleString('en-US', { minimumFractionDigits: 2 })}`)
  } catch (err: any) {
    toast.error('Failed to recalculate account balance')
  } finally {
    isRecalculating.value = false
  }
}
</script>
