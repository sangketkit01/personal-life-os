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
            <span>Cash Flow Ledger</span>
          </RouterLink>
          <span class="text-zinc-600">/</span>
          <span class="text-xs font-mono text-zinc-300">Transactions</span>
        </div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Transaction Ledger</h1>
        </div>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <button
          @click="handleCreate"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-all active:scale-[0.98] flex items-center gap-1.5 shadow-sm hover:shadow-white/10"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>+ Record Transaction</span>
        </button>
      </div>
    </div>

    <!-- Filter Bar -->
    <div v-if="filters.currency || filters.report_kind || filters.category || filters.uncategorized" class="rounded-lg border border-zinc-800 p-3 text-xs text-zinc-400 flex flex-wrap justify-between gap-2"><span>จาก Dashboard · {{ filters.currency || 'ทุกสกุลเงิน' }} · {{ reportLabels[filters.report_kind] || 'ทุกรายการ' }}{{ filters.category ? ' · กรองหมวดที่เลือก' : '' }}{{ filters.uncategorized ? ' · ยังไม่จัดหมวด' : '' }}</span><button type="button" @click="resetFilters" class="underline text-zinc-200">ล้างตัวกรอง</button></div>
    <p v-if="loadError" role="alert" class="text-xs text-rose-300">{{ loadError }} <button type="button" @click="fetchFiltered" class="underline">ลองอีกครั้ง</button></p>
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
      <div v-if="ledgerStore.isLoading && ledgerStore.transactions.length === 0" class="p-4">
        <SkeletonLoader variant="table" :count="6" />
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
                    <span>Split ({{ tx.splits?.length || 0 }} friends)</span>
                  </span>
                  <span
                    v-if="tx.transfer_destination || tx.transfer_peer"
                    class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-semibold"
                  >
                    Transfer
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
              <td class="py-3 px-4 text-zinc-400 font-sans">{{ tx.account_name || 'Account' }}</td>
              <td class="py-3 px-4 text-zinc-400 font-sans">
                <span class="px-2 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-800/80 group-hover:border-zinc-700 transition-colors">
                  {{ tx.category_name || 'General' }}
                </span>
              </td>
              <td class="py-3 px-4 text-right font-mono tabular-nums font-semibold">
                <span :class="tx.transaction_type === 'INFLOW' ? 'text-emerald-400' : 'text-zinc-200'">
                  {{ tx.transaction_type === 'INFLOW' ? '+' : '-' }}{{ tx.account_currency || 'THB' }} {{ Number(tx.gross_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </span>
              </td>
              <td class="py-3 px-4 text-right font-mono tabular-nums text-zinc-400">
                {{ tx.account_currency || 'THB' }} {{ Number(tx.net_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </td>
              <td class="py-3 px-4 text-right pr-4">
                <button
                  @click="handleEdit(tx)"
                  class="p-1.5 rounded-lg text-zinc-500 hover:text-indigo-400 hover:bg-indigo-500/10 active:scale-[0.95] transition-all mr-1"
                  title="Edit Transaction"
                >
                  <Edit2 class="w-3.5 h-3.5" />
                </button>
                <button
                  @click="handleDelete(tx.id)"
                  class="p-1.5 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 active:scale-[0.95] transition-all"
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
          class="px-5 py-3 border-t border-zinc-800/80 bg-zinc-950/40 flex flex-wrap items-center justify-between gap-2 font-mono text-xs"
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

    <!-- Record / Edit Modal -->
    <TransactionModal
      :is-open="showTransactionModal"
      :transaction-to-edit="editingTransaction"
      @close="showTransactionModal = false; editingTransaction = null"
      @created="fetchFiltered"
      @updated="fetchFiltered"
    />

    <!-- Confirm Modal -->
    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      :is-loading="confirmModal.isLoading"
      :error-message="confirmModal.errorMessage"
      @confirm="executeConfirmAction"
      @cancel="confirmModal.isOpen = false; confirmModal.errorMessage = ''"
    />
  </div>
</template>

<script setup lang="ts">
import SkeletonLoader from '../../components/common/SkeletonLoader.vue'
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLedgerStore } from '../../stores/ledger'
import TransactionModal from '../../components/ledger/TransactionModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import {
  ArrowLeft,
  Plus,
  Search,
  Users,
  Trash2,
  X,
  FileText,
  ExternalLink,
  Edit2
} from 'lucide-vue-next'

const ledgerStore = useLedgerStore()
const route = useRoute(), router = useRouter(), loadError = ref('')
const reportLabels: Record<string,string> = { INCOME:'รายรับจริง', EXPENSE:'ค่าใช้จ่ายส่วนตัว', SURPLUS:'รายรับและรายจ่ายส่วนตัว', CASH:'เงินเข้าออกจากบัญชีที่พร้อมใช้', LOAN:'เงินต้นเงินกู้', INVESTMENT:'เงินลงทุน', REIMBURSEMENT:'เงินรับคืน', TRANSFER:'โอนเงิน', CARD_PAYMENT:'ชำระบัตร' }
const showTransactionModal = ref(false)
const editingTransaction = ref<any>(null)
const currentPage = ref(1)
const pageSize = 20

function handleCreate() {
  editingTransaction.value = null
  showTransactionModal.value = true
}

function handleEdit(tx: any) {
  editingTransaction.value = tx
  showTransactionModal.value = true
}

const filters = reactive({
  search: '',
  account: '',
  type: '',
  start_date: '',
  end_date: '',
  currency: '', report_kind: '', category: '', uncategorized: ''
})

const hasActiveFilters = computed(() => {
  return Boolean(
    filters.search ||
    filters.account ||
    filters.type ||
    filters.start_date ||
    filters.end_date || filters.currency || filters.report_kind || filters.category || filters.uncategorized
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
  isLoading: false,
  errorMessage: '',
  action: async () => {}
})

async function executeConfirmAction() {
  confirmModal.isLoading = true
  confirmModal.errorMessage = ''
  try {
    await confirmModal.action()
    confirmModal.isOpen = false
  } catch (err: any) {
    confirmModal.errorMessage = err?.response?.data?.error || err?.message || 'Operation failed'
  } finally {
    confirmModal.isLoading = false
  }
}

onMounted(async () => {
  applyQuery()
  await Promise.all([
    ledgerStore.fetchAccounts(),
    ledgerStore.fetchCategories(),
    fetchFiltered()
  ])
})

let listRequest = 0
async function fetchFiltered() {
  const request = ++listRequest
  loadError.value = ''
  try { await ledgerStore.fetchTransactions({
    account: filters.account || undefined,
    type: filters.type || undefined,
    start_date: filters.start_date || undefined,
    end_date: filters.end_date || undefined,
    search: filters.search || undefined,
    currency: filters.currency || undefined,
    report_kind: filters.report_kind || undefined,
    category: filters.category || undefined,
    uncategorized: filters.uncategorized || undefined,
    page: currentPage.value
  }) } catch { if (request === listRequest) loadError.value = 'โหลดรายการไม่สำเร็จ' }
}

function applyQuery() {
  for (const key of Object.keys(filters) as Array<keyof typeof filters>) filters[key] = typeof route.query[key] === 'string' ? route.query[key] as string : ''
  currentPage.value = 1
}
watch(() => route.query, () => { applyQuery(); void fetchFiltered() })
onUnmounted(() => clearTimeout(debounceTimer))

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
  filters.currency = ''; filters.report_kind = ''; filters.category = ''; filters.uncategorized = ''
  currentPage.value = 1
  if (Object.keys(route.query).length) void router.replace({ path:route.path, query:{} })
  else void fetchFiltered()
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
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    await ledgerStore.deleteTransaction(id)
    await fetchFiltered()
  }
  confirmModal.isOpen = true
}
</script>
