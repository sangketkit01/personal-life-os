<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Trade Executions Log</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            AUDIT TRAIL
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Historical trade ledger with fees, weighted cost basis, and cash flow records
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
        <RouterLink
          to="/portfolio/executions/dividends"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <Coins class="w-3.5 h-3.5 text-zinc-400" />
          <span>Dividend Ledger</span>
        </RouterLink>

        <RouterLink
          to="/portfolio/executions/import"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <UploadCloud class="w-3.5 h-3.5 text-zinc-400" />
          <span>Import CSV</span>
        </RouterLink>

        <button
          @click="exportExecutionsCSV"
          :disabled="filteredTransactions.length === 0"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-40"
        >
          <Download class="w-3.5 h-3.5 text-zinc-400" />
          <span>Export CSV</span>
        </button>

        <button
          @click="openAddModal()"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>Record Trade</span>
        </button>
      </div>
    </div>

    <!-- Live Market Session & Currency Bar -->
    <MarketStatusBar />

    <!-- Summary KPI Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 flex items-center justify-between">
        <div>
          <span class="text-[10px] font-mono uppercase text-zinc-500">Total Executions</span>
          <div class="text-xl font-bold font-mono text-zinc-100 mt-1">{{ filteredTransactions.length }} Orders</div>
        </div>
        <div class="w-9 h-9 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-300 flex items-center justify-center">
          <History class="w-4 h-4" />
        </div>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 flex items-center justify-between">
        <div>
          <span class="text-[10px] font-mono uppercase text-zinc-500">Buy Orders</span>
          <div class="text-xl font-bold font-mono text-emerald-400 mt-1">{{ buyOrdersCount }} Trades</div>
        </div>
        <div class="w-9 h-9 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
          <ArrowDownRight class="w-4 h-4" />
        </div>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 flex items-center justify-between">
        <div>
          <span class="text-[10px] font-mono uppercase text-zinc-500">Sell & Dividends</span>
          <div class="text-xl font-bold font-mono text-zinc-200 mt-1">{{ sellOrDividendCount }} Events</div>
        </div>
        <div class="w-9 h-9 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
          <ArrowUpRight class="w-4 h-4" />
        </div>
      </div>
    </div>

    <!-- Executions Table Section -->
    <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <History class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Transaction History
          </h2>
          <span class="text-[11px] font-mono text-zinc-500 ml-1">({{ filteredTransactions.length }} Records)</span>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <!-- Portfolio Filter -->
          <select
            v-model="selectedPortfolioFilter"
            class="bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1 font-mono outline-none focus:border-zinc-700"
          >
            <option value="ALL">All Portfolios</option>
            <option
              v-for="p in portfolioStore.portfolios"
              :key="p.id"
              :value="p.id"
            >
              {{ p.name }} ({{ p.currency }})
            </option>
          </select>

          <!-- Type Filter Pills -->
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

      <!-- Executions Table -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[11px] font-mono uppercase text-zinc-500">
              <th class="py-3 px-4 font-semibold">Date & Time</th>
              <th class="py-3 px-4 font-semibold">Portfolio</th>
              <th class="py-3 px-4 font-semibold">Asset / Ticker</th>
              <th class="py-3 px-4 font-semibold">Type</th>
              <th class="py-3 px-4 font-semibold text-right">Shares / Qty</th>
              <th class="py-3 px-4 font-semibold text-right">Price</th>
              <th class="py-3 px-4 font-semibold text-right">Fee</th>
              <th class="py-3 px-4 font-semibold text-right">Net Total</th>
              <th class="py-3 px-4 font-semibold">Notes</th>
              <th class="py-3 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="tx in filteredTransactions"
              :key="tx.id"
              class="hover:bg-zinc-900/50 transition-colors"
            >
              <!-- 1. Date & Time -->
              <td class="py-3.5 px-4 font-mono text-zinc-400 whitespace-nowrap">
                {{ formatDateTime(tx.executed_at) }}
              </td>

              <!-- 2. Portfolio -->
              <td class="py-3.5 px-4 font-mono text-zinc-300">
                <div class="flex items-center gap-1.5">
                  <span
                    class="w-2 h-2 rounded-full shrink-0 shadow-sm"
                    :style="{ backgroundColor: getPortfolioColorByTx(tx) }"
                  ></span>
                  <span class="text-xs">{{ tx.portfolio_name || getHoldingPortfolioName(tx.holding) || 'Consolidated' }}</span>
                </div>
              </td>

              <!-- 3. Ticker -->
              <td class="py-3.5 px-4 font-mono">
                <span class="font-bold text-zinc-100 hover:text-zinc-300 cursor-pointer" @click="goToAssetDetail(tx.holding_ticker || tx.ticker || '')">
                  {{ tx.holding_ticker || tx.ticker }}
                </span>
              </td>

              <!-- 4. Action Type Badge -->
              <td class="py-3.5 px-4 font-mono">
                <span
                  class="text-[9px] px-1.5 py-0.5 rounded border font-semibold uppercase"
                  :class="getTransactionBadgeClass(tx.transaction_type)"
                >
                  {{ tx.transaction_type }}
                </span>
              </td>

              <!-- 5. Shares -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-200">
                {{ formatShares(tx.shares) }}
              </td>

              <!-- 6. Price per Share -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-400">
                {{ getTxCurrencySymbol(tx) }}{{ formatPrice(tx.price_per_share) }}
              </td>

              <!-- 7. Fee -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-500">
                {{ Number(tx.fee || 0) > 0 ? `${getTxCurrencySymbol(tx)}${formatNumber(tx.fee, 2)}` : '-' }}
              </td>

              <!-- 8. Net Total -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums font-semibold text-zinc-100">
                {{ getTxCurrencySymbol(tx) }}{{ formatNumber(getTxNetAmount(tx), 2) }}
              </td>

              <!-- 9. Notes -->
              <td class="py-3.5 px-4 text-zinc-400 text-[11px] truncate max-w-[140px]">
                {{ tx.notes || '-' }}
              </td>

              <!-- 10. Actions -->
              <td class="py-3.5 px-4 text-right">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    @click="openEditTransaction(tx)"
                    type="button"
                    class="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                    title="Edit transaction"
                  >
                    <Edit2 class="w-3.5 h-3.5" />
                  </button>
                  <button
                    @click="confirmDeleteTransaction(tx.id)"
                    type="button"
                    class="p-1.5 rounded hover:bg-zinc-800 text-zinc-500 hover:text-rose-400 transition-colors"
                    title="Delete transaction"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </td>
            </tr>

            <!-- Empty State -->
            <tr v-if="portfolioStore.isLoading && portfolioStore.transactions.length === 0">
              <td colspan="10" class="p-4">
                <SkeletonLoader variant="table" :count="5" />
              </td>
            </tr>

            <tr v-else-if="filteredTransactions.length === 0">
              <td colspan="10" class="py-12 text-center text-xs text-zinc-500 font-mono">
                <div class="flex flex-col items-center justify-center gap-2">
                  <History class="w-6 h-6 text-zinc-600" />
                  <p>No executions recorded in this scope</p>
                  <button
                    @click="openAddModal()"
                    type="button"
                    class="mt-2 px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-semibold text-xs"
                  >
                    Record New Execution
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modals -->
    <AddTransactionModal
      :is-open="showAddModal"
      :prefill-ticker="prefillTicker"
      :prefill-holding-id="prefillHoldingId"
      :editing-transaction="selectedEditingTx"
      @close="closeAddModal"
      @saved="handleTradeSaved"
    />

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
import SkeletonLoader from '../../components/common/SkeletonLoader.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import MarketStatusBar from '../../components/portfolio/MarketStatusBar.vue'
import AddTransactionModal from '../../components/portfolio/AddTransactionModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import { getPortfolioColor, type StockTransaction } from '../../types/portfolio'
import {
  History,
  Plus,
  Trash2,
  Edit2,
  ArrowDownRight,
  ArrowUpRight,
  Coins,
  UploadCloud,
  Download
} from 'lucide-vue-next'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const showAddModal = ref(false)
const selectedEditingTx = ref<StockTransaction | null>(null)
const prefillTicker = ref('')
const prefillHoldingId = ref('')

const selectedPortfolioFilter = ref('ALL')
const selectedTypeFilter = ref<'ALL' | 'BUY' | 'SELL' | 'DIVIDEND'>('ALL')

const typeFilters = [
  { value: 'ALL', label: 'All' },
  { value: 'BUY', label: 'Buy' },
  { value: 'SELL', label: 'Sell' },
  { value: 'DIVIDEND', label: 'Dividends' }
] as const

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  action: () => {}
})

function getHoldingPortfolioName(holdingId?: string): string {
  if (!holdingId) return ''
  const h = portfolioStore.holdings.find(item => item.id === holdingId)
  return h?.portfolio_name || ''
}

function getPortfolioColorByTx(tx: StockTransaction): string {
  const portfolioId = tx.portfolio || portfolioStore.holdings.find(h => h.id === tx.holding)?.portfolio
  const p = portfolioStore.portfolios.find(item => item.id === portfolioId)
  return getPortfolioColor(p?.color)
}

const filteredTransactions = computed(() => {
  let list = [...portfolioStore.transactions]
  if (selectedPortfolioFilter.value !== 'ALL') {
    list = list.filter(tx => {
      if (tx.portfolio === selectedPortfolioFilter.value) return true
      const h = portfolioStore.holdings.find(item => item.id === tx.holding)
      return h?.portfolio === selectedPortfolioFilter.value
    })
  }
  if (selectedTypeFilter.value !== 'ALL') {
    list = list.filter(tx => tx.transaction_type === selectedTypeFilter.value)
  }
  return list
})

const buyOrdersCount = computed(() => {
  return portfolioStore.transactions.filter(t => t.transaction_type === 'BUY').length
})

const sellOrDividendCount = computed(() => {
  return portfolioStore.transactions.filter(t => t.transaction_type === 'SELL' || t.transaction_type === 'DIVIDEND').length
})

function formatDateTime(dateStr?: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatNumber(val: any, minFrac = 2, maxFrac = 2): string {
  const num = Number(val || 0)
  return num.toLocaleString('en-US', { minimumFractionDigits: minFrac, maximumFractionDigits: maxFrac })
}

function formatShares(val: any): string {
  const num = Number(val || 0)
  return num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 8 })
}

function formatPrice(val: any): string {
  const num = Number(val || 0)
  if (num === 0) return '0.00'
  if (Math.abs(num) < 1) {
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })
  }
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function getTxCurrencySymbol(tx: StockTransaction): string {
  const curr = (tx.currency || tx.holding_currency || 'THB').toUpperCase()
  return curr === 'USD' ? '$' : '฿'
}

function getTxNetAmount(tx: StockTransaction): number {
  const subtotal = Number(tx.shares || 0) * Number(tx.price_per_share || 0)
  const fee = Number(tx.fee || 0)
  if (tx.transaction_type === 'BUY') {
    return subtotal + fee
  } else {
    return Math.max(0, subtotal - fee)
  }
}

function getTransactionBadgeClass(type: string) {
  switch (type) {
    case 'BUY':
      return 'bg-zinc-900 text-emerald-400 border-zinc-800'
    case 'SELL':
      return 'bg-zinc-900 text-rose-400 border-zinc-800'
    case 'DIVIDEND':
      return 'bg-zinc-900 text-zinc-300 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

function openAddModal() {
  selectedEditingTx.value = null
  prefillTicker.value = ''
  prefillHoldingId.value = ''
  showAddModal.value = true
}

function openEditTransaction(tx: StockTransaction) {
  selectedEditingTx.value = tx
  prefillTicker.value = tx.holding_ticker || tx.ticker || ''
  prefillHoldingId.value = tx.holding || ''
  showAddModal.value = true
}

function closeAddModal() {
  showAddModal.value = false
  selectedEditingTx.value = null
}

function goToAssetDetail(ticker: string) {
  if (!ticker) return
  router.push(`/portfolio/asset/${encodeURIComponent(ticker)}`)
}

async function handleTradeSaved() {
  toast.success('Trade execution recorded')
  await Promise.all([
    portfolioStore.fetchTransactions(),
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchOverview({ currency: portfolioStore.displayCurrency })
  ])
}

function confirmDeleteTransaction(id: string) {
  confirmModal.title = 'Delete Execution'
  confirmModal.message = 'Are you sure you want to delete this trade execution? Portfolio metrics and cost basis will recalculate.'
  confirmModal.confirmText = 'Delete Execution'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await portfolioStore.deleteTransaction(id)
      toast.info('Deleted execution record')
      await portfolioStore.fetchOverview({ currency: portfolioStore.displayCurrency })
    } catch {
      toast.error('Failed to delete transaction')
    }
  }
  confirmModal.isOpen = true
}

function handleConfirmAction() {
  confirmModal.isOpen = false
  confirmModal.action()
}

function exportExecutionsCSV() {
  if (filteredTransactions.value.length === 0) return

  const headers = [
    'Date_Time',
    'Portfolio',
    'Ticker',
    'Type',
    'Shares',
    'Price_Per_Share',
    'Fee',
    'Net_Total',
    'Currency',
    'Notes'
  ]

  const rows = filteredTransactions.value.map(tx => {
    const dateStr = tx.executed_at ? new Date(tx.executed_at).toISOString() : ''
    const pName = tx.portfolio_name || getHoldingPortfolioName(tx.holding) || 'Consolidated'
    const ticker = tx.holding_ticker || tx.ticker || ''
    const type = tx.transaction_type
    const shares = tx.shares || 0
    const price = tx.price_per_share || 0
    const fee = tx.fee || 0
    const net = getTxNetAmount(tx)
    const currency = (tx.currency || tx.holding_currency || 'THB').toUpperCase()
    const notes = (tx.notes || '').replace(/"/g, '""')

    return [
      `"${dateStr}"`,
      `"${pName}"`,
      ticker,
      type,
      shares,
      price,
      fee,
      net.toFixed(2),
      currency,
      `"${notes}"`
    ].join(',')
  })

  const csvContent = [headers.join(','), ...rows].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `trade_executions_${new Date().toISOString().slice(0, 10)}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  toast.success('Trade executions exported to CSV')
}

onMounted(async () => {
  await Promise.all([
    portfolioStore.fetchTransactions(),
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchPortfolios(),
    portfolioStore.fetchMarketStatus()
  ])
})
</script>
