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
          <span class="text-xs font-mono text-zinc-300">Transaction Ledger</span>
        </div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Transaction Ledger</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            AUDIT TRAIL
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Historical log of all inflows, outflows, internal transfers, and group split bills
        </p>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <button
          @click="showTransactionModal = true"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>Record Transaction</span>
        </button>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3 font-mono text-xs">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <!-- Search Query -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-500 mb-1">Search</label>
          <div class="relative">
            <Search class="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-2 pointer-events-none" />
            <input
              v-model="filters.search"
              @input="handleSearchInput"
              type="text"
              placeholder="Filter by title..."
              class="w-full pl-8 pr-3 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500 outline-none focus:border-zinc-700 font-mono text-xs"
            />
          </div>
        </div>

        <!-- Account Filter -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-500 mb-1">Account</label>
          <select
            v-model="filters.account"
            @change="handleFilterChange"
            class="w-full px-2.5 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 outline-none focus:border-zinc-700 font-mono text-xs"
          >
            <option value="">All Accounts</option>
            <option
              v-for="acc in ledgerStore.accounts"
              :key="acc.id"
              :value="acc.id"
            >
              {{ acc.name }}
            </option>
          </select>
        </div>

        <!-- Type Filter -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-500 mb-1">Type</label>
          <select
            v-model="filters.type"
            @change="handleFilterChange"
            class="w-full px-2.5 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 outline-none focus:border-zinc-700 font-mono text-xs"
          >
            <option value="">All Types</option>
            <option value="OUTFLOW">Expenses (Outflow)</option>
            <option value="INFLOW">Income (Inflow)</option>
            <option value="TRANSFER">Transfers</option>
          </select>
        </div>

        <!-- Start Date -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-500 mb-1">Start Date</label>
          <input
            v-model="filters.start_date"
            @change="handleFilterChange"
            type="date"
            class="w-full px-2.5 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 outline-none focus:border-zinc-700 font-mono text-xs"
          />
        </div>

        <!-- End Date -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-500 mb-1">End Date</label>
          <input
            v-model="filters.end_date"
            @change="handleFilterChange"
            type="date"
            class="w-full px-2.5 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 outline-none focus:border-zinc-700 font-mono text-xs"
          />
        </div>
      </div>

      <div v-if="hasActiveFilters" class="flex justify-end pt-1">
        <button
          @click="resetFilters"
          type="button"
          class="text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1 font-mono"
        >
          <X class="w-3 h-3" />
          <span>Reset Filters</span>
        </button>
      </div>
    </div>

    <!-- Transactions Table -->
    <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
      <div v-if="ledgerStore.isLoading" class="p-16 text-center text-xs font-mono text-zinc-500">
        Loading transactions...
      </div>

      <div v-else-if="ledgerStore.transactions.length === 0" class="p-16 text-center text-xs font-mono text-zinc-500">
        No transactions match the selected filter criteria.
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs font-mono">
          <thead>
            <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[10px] uppercase text-zinc-500 tracking-wider">
              <th class="py-3 px-4">Date</th>
              <th class="py-3 px-4">Title / Description</th>
              <th class="py-3 px-4">Account</th>
              <th class="py-3 px-4">Category</th>
              <th class="py-3 px-4 text-right">Gross Amount</th>
              <th class="py-3 px-4 text-right">Net Share</th>
              <th class="py-3 px-4 text-right pr-4">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="tx in ledgerStore.transactions"
              :key="tx.id"
              class="hover:bg-zinc-900/40 transition-colors"
            >
              <td class="py-3 px-4 text-zinc-400 whitespace-nowrap">{{ tx.transaction_date }}</td>
              <td class="py-3 px-4 font-sans font-medium text-zinc-200">
                <div class="flex items-center gap-2 flex-wrap">
                  <span>{{ tx.title }}</span>
                  <span
                    v-if="tx.is_split"
                    class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center gap-1"
                  >
                    <Users class="w-2.5 h-2.5" />
                    <span>Split ({{ tx.splits?.length || 0 }} friends)</span>
                  </span>
                  <span
                    v-if="tx.transfer_destination || tx.transfer_peer"
                    class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400"
                  >
                    Transfer
                  </span>
                </div>
              </td>
              <td class="py-3 px-4 text-zinc-400 font-sans">{{ tx.account_name || 'Account' }}</td>
              <td class="py-3 px-4 text-zinc-400 font-sans">
                <span class="px-2 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-800/80">
                  {{ tx.category_name || 'General' }}
                </span>
              </td>
              <td class="py-3 px-4 text-right font-mono tabular-nums font-semibold">
                <span :class="tx.transaction_type === 'INFLOW' ? 'text-emerald-400' : 'text-zinc-200'">
                  {{ tx.transaction_type === 'INFLOW' ? '+' : '-' }}฿{{ Number(tx.gross_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </span>
              </td>
              <td class="py-3 px-4 text-right font-mono tabular-nums text-zinc-400">
                ฿{{ Number(tx.net_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </td>
              <td class="py-3 px-4 text-right pr-4">
                <button
                  @click="handleDelete(tx.id)"
                  class="p-1 rounded text-zinc-600 hover:text-rose-400 transition-colors"
                  title="Delete Transaction"
                >
                  <Trash2 class="w-3.5 h-3.5" />
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
            Page <strong class="text-zinc-300">{{ currentPage }}</strong> of <strong class="text-zinc-300">{{ totalPages }}</strong> ({{ ledgerStore.totalTransactionsCount }} items)
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

    <!-- Record Modal -->
    <TransactionModal
      :is-open="showTransactionModal"
      @close="showTransactionModal = false"
      @created="fetchFiltered"
    />

    <!-- Confirm Modal -->
    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      @confirm="executeConfirmAction"
      @cancel="confirmModal.isOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useLedgerStore } from '../../stores/ledger'
import TransactionModal from '../../components/ledger/TransactionModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import {
  ArrowLeft,
  Plus,
  Search,
  Users,
  Trash2,
  X
} from 'lucide-vue-next'

const ledgerStore = useLedgerStore()
const showTransactionModal = ref(false)
const currentPage = ref(1)
const pageSize = 20

const filters = reactive({
  search: '',
  account: '',
  type: '',
  start_date: '',
  end_date: ''
})

const hasActiveFilters = computed(() => {
  return Boolean(
    filters.search ||
    filters.account ||
    filters.type ||
    filters.start_date ||
    filters.end_date
  )
})

const totalPages = computed(() => {
  return Math.ceil((ledgerStore.totalTransactionsCount || 0) / pageSize)
})

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  action: () => {}
})

function executeConfirmAction() {
  confirmModal.isOpen = false
  confirmModal.action()
}

onMounted(async () => {
  await Promise.all([
    ledgerStore.fetchAccounts(),
    ledgerStore.fetchCategories(),
    fetchFiltered()
  ])
})

async function fetchFiltered() {
  await ledgerStore.fetchTransactions({
    account: filters.account || undefined,
    type: filters.type || undefined,
    start_date: filters.start_date || undefined,
    end_date: filters.end_date || undefined,
    search: filters.search || undefined,
    page: currentPage.value
  })
}

let debounceTimer: any = null
function handleSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    currentPage.value = 1
    fetchFiltered()
  }, 300)
}

function handleFilterChange() {
  currentPage.value = 1
  fetchFiltered()
}

function resetFilters() {
  filters.search = ''
  filters.account = ''
  filters.type = ''
  filters.start_date = ''
  filters.end_date = ''
  currentPage.value = 1
  fetchFiltered()
}

function changePage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  fetchFiltered()
}

function handleDelete(id: string) {
  confirmModal.title = 'Delete Transaction'
  confirmModal.message = 'Are you sure you want to delete this transaction? The corresponding account balance will be restored automatically.'
  confirmModal.confirmText = 'Delete Transaction'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    await ledgerStore.deleteTransaction(id)
    await fetchFiltered()
  }
  confirmModal.isOpen = true
}
</script>
