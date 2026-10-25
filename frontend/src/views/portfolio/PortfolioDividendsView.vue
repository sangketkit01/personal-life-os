<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2 mb-2">
          <RouterLink
            to="/portfolio/executions"
            class="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft class="w-3.5 h-3.5" />
            <span>Trade Executions</span>
          </RouterLink>
          <span class="text-zinc-600">/</span>
          <span class="text-xs font-mono text-zinc-300">Dividends</span>
        </div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Dividend & Income Ledger</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-300 border border-zinc-800">
            CASH FLOW AUDIT
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Historical dividend distributions, statutory withholding tax (10% SET, 15% US treaty), and net cash credited
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
        <button
          @click="exportDividendsCSV"
          :disabled="filteredDividends.length === 0"
          type="button"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-40"
        >
          <Download class="w-3.5 h-3.5 text-zinc-400" />
          <span>Export CSV</span>
        </button>
        <button
          @click="openAddDividendModal"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>Record Dividend</span>
        </button>
      </div>
    </div>

    <!-- Live Market Session & Currency Bar -->
    <MarketStatusBar />

    <!-- KPI Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Total Gross Dividends -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">Gross Dividends</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-300 flex items-center justify-center">
            <Coins class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2">
          {{ displayCurrencySymbol }}{{ formatNumber(grossTotalDisplayCurrency) }}
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          THB: ฿{{ formatNumber(grossTotalTHB) }} · USD: ${{ formatNumber(grossTotalUSD) }}
        </p>
      </div>

      <!-- Withholding Tax / Deductions -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">Withholding Tax</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
            <Percent class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-300 mt-2">
          {{ displayCurrencySymbol }}{{ formatNumber(taxTotalDisplayCurrency) }}
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          Settled via statutory withholding
        </p>
      </div>

      <!-- Net Cashflow Received -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">Net Cash Credited</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
            <Wallet class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-emerald-400 mt-2">
          {{ displayCurrencySymbol }}{{ formatNumber(netTotalDisplayCurrency) }}
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          THB: ฿{{ formatNumber(netTotalTHB) }} · USD: ${{ formatNumber(netTotalUSD) }}
        </p>
      </div>

      <!-- Payout Events -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase text-zinc-500">Distribution Events</span>
          <div class="w-7 h-7 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 flex items-center justify-center">
            <CalendarCheck class="w-3.5 h-3.5" />
          </div>
        </div>
        <div class="text-xl font-bold font-mono text-zinc-100 mt-2">
          {{ filteredDividends.length }} Payouts
        </div>
        <p class="text-[11px] text-zinc-500 mt-1 font-mono">
          Across {{ uniqueTickersCount }} unique assets
        </p>
      </div>
    </div>

    <!-- Dividends Ledger Table Section -->
    <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <Coins class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Dividend Distribution History
          </h2>
          <span class="text-[11px] font-mono text-zinc-500 ml-1">({{ filteredDividends.length }} Entries)</span>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          <!-- Search input -->
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Filter ticker / notes..."
              class="bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs rounded-md pl-7 pr-2.5 py-1 font-mono outline-none focus:border-zinc-700 w-36 sm:w-44"
            />
            <Search class="w-3.5 h-3.5 text-zinc-500 absolute left-2 top-1.5" />
          </div>

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

          <!-- Year Filter -->
          <select
            v-model="selectedYearFilter"
            class="bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs rounded-md px-2 py-1 font-mono outline-none focus:border-zinc-700"
          >
            <option value="ALL">All Years</option>
            <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
          </select>
        </div>
      </div>

      <!-- Table Container -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[11px] font-mono uppercase text-zinc-500">
              <th class="py-3 px-4 font-semibold">Payment Date</th>
              <th class="py-3 px-4 font-semibold">Portfolio</th>
              <th class="py-3 px-4 font-semibold">Asset / Ticker</th>
              <th class="py-3 px-4 font-semibold text-right">Shares Held</th>
              <th class="py-3 px-4 font-semibold text-right">DPS (Dividend/Share)</th>
              <th class="py-3 px-4 font-semibold text-right">Gross Dividend</th>
              <th class="py-3 px-4 font-semibold text-right">Withholding Tax</th>
              <th class="py-3 px-4 font-semibold text-right">Net Credited</th>
              <th class="py-3 px-4 font-semibold">Notes</th>
              <th class="py-3 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="tx in filteredDividends"
              :key="tx.id"
              class="hover:bg-zinc-900/50 transition-colors"
            >
              <!-- 1. Payment Date -->
              <td class="py-3.5 px-4 font-mono text-zinc-400 whitespace-nowrap">
                {{ formatDate(tx.executed_at) }}
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
                <span
                  class="font-bold text-zinc-100 hover:text-zinc-300 cursor-pointer"
                  @click="goToAssetDetail(tx.holding_ticker || tx.ticker || '')"
                >
                  {{ tx.holding_ticker || tx.ticker }}
                </span>
              </td>

              <!-- 4. Shares Held -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-300">
                {{ formatShares(tx.shares) }}
              </td>

              <!-- 5. DPS -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-400">
                {{ getTxCurrencySymbol(tx) }}{{ formatPrice(tx.price_per_share) }}
              </td>

              <!-- 6. Gross Dividend -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums font-medium text-zinc-200">
                {{ getTxCurrencySymbol(tx) }}{{ formatNumber(getGrossAmount(tx)) }}
              </td>

              <!-- 7. Withholding Tax -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-500">
                <span v-if="Number(tx.fee || 0) > 0">
                  {{ getTxCurrencySymbol(tx) }}{{ formatNumber(tx.fee) }}
                </span>
                <span v-else class="text-zinc-600">-</span>
              </td>

              <!-- 8. Net Credited -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums font-semibold text-emerald-400">
                {{ getTxCurrencySymbol(tx) }}{{ formatNumber(getNetAmount(tx)) }}
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
                    title="Edit dividend entry"
                  >
                    <Edit2 class="w-3.5 h-3.5" />
                  </button>
                  <button
                    @click="confirmDeleteTransaction(tx.id)"
                    type="button"
                    class="p-1.5 rounded hover:bg-zinc-800 text-zinc-500 hover:text-rose-400 transition-colors"
                    title="Delete dividend entry"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </td>
            </tr>

            <!-- Empty State -->
            <tr v-if="filteredDividends.length === 0">
              <td colspan="10" class="py-12 text-center text-xs text-zinc-500 font-mono">
                <div class="flex flex-col items-center justify-center gap-2">
                  <Coins class="w-6 h-6 text-zinc-600" />
                  <p>No dividend distribution records found in this scope</p>
                  <button
                    @click="openAddDividendModal"
                    type="button"
                    class="mt-2 px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-semibold text-xs"
                  >
                    Record New Dividend
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
      :initial-type="'DIVIDEND'"
      @close="closeAddModal"
      @saved="handleDividendSaved"
    />

    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      :is-loading="confirmModal.isLoading"
      :error-message="confirmModal.errorMessage"
      @confirm="handleConfirmAction"
      @cancel="confirmModal.isOpen = false; confirmModal.errorMessage = ''"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import MarketStatusBar from '../../components/portfolio/MarketStatusBar.vue'
import AddTransactionModal from '../../components/portfolio/AddTransactionModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import { getPortfolioColor, type StockTransaction } from '../../types/portfolio'
import {
  ArrowLeft,
  Plus,
  Download,
  Search,
  Coins,
  Percent,
  Wallet,
  CalendarCheck,
  Edit2,
  Trash2
} from 'lucide-vue-next'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const showAddModal = ref(false)
const selectedEditingTx = ref<StockTransaction | null>(null)
const prefillTicker = ref('')
const prefillHoldingId = ref('')

const searchQuery = ref('')
const selectedPortfolioFilter = ref('ALL')
const selectedYearFilter = ref('ALL')

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

async function handleConfirmAction() {
  confirmModal.isLoading = true
  confirmModal.errorMessage = ''
  try {
    await confirmModal.action()
    confirmModal.isOpen = false
  } catch (err: any) {
    confirmModal.errorMessage = err?.response?.data?.detail || err?.response?.data?.error || err?.message || 'Operation failed'
  } finally {
    confirmModal.isLoading = false
  }
}

const displayCurrencySymbol = computed(() => {
  return portfolioStore.displayCurrency === 'USD' ? '$' : '฿'
})

// Filter only DIVIDEND transactions
const allDividends = computed(() => {
  return portfolioStore.transactions.filter(tx => tx.transaction_type === 'DIVIDEND')
})

const availableYears = computed(() => {
  const years = new Set<string>()
  allDividends.value.forEach(tx => {
    if (tx.executed_at) {
      years.add(new Date(tx.executed_at).getFullYear().toString())
    }
  })
  return Array.from(years).sort().reverse()
})

const filteredDividends = computed(() => {
  let list = [...allDividends.value]

  // Portfolio filter
  if (selectedPortfolioFilter.value !== 'ALL') {
    list = list.filter(tx => {
      if (tx.portfolio === selectedPortfolioFilter.value) return true
      const h = portfolioStore.holdings.find(item => item.id === tx.holding)
      return h?.portfolio === selectedPortfolioFilter.value
    })
  }

  // Year filter
  if (selectedYearFilter.value !== 'ALL') {
    list = list.filter(tx => {
      if (!tx.executed_at) return false
      return new Date(tx.executed_at).getFullYear().toString() === selectedYearFilter.value
    })
  }

  // Search query
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(tx => {
      const ticker = (tx.holding_ticker || tx.ticker || '').toLowerCase()
      const notes = (tx.notes || '').toLowerCase()
      return ticker.includes(q) || notes.includes(q)
    })
  }

  return list
})

const uniqueTickersCount = computed(() => {
  const set = new Set<string>()
  filteredDividends.value.forEach(tx => {
    const t = tx.holding_ticker || tx.ticker
    if (t) set.add(t)
  })
  return set.size
})

function getTxCurrency(tx: StockTransaction): string {
  return (tx.currency || tx.holding_currency || 'THB').toUpperCase()
}

function getTxCurrencySymbol(tx: StockTransaction): string {
  return getTxCurrency(tx) === 'USD' ? '$' : '฿'
}

function getGrossAmount(tx: StockTransaction): number {
  return Number(tx.shares || 0) * Number(tx.price_per_share || 0)
}

function getNetAmount(tx: StockTransaction): number {
  const gross = getGrossAmount(tx)
  const fee = Number(tx.fee || 0)
  return Math.max(0, gross - fee)
}

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

// Totals calculation
const grossTotalTHB = computed(() => {
  return filteredDividends.value
    .filter(tx => getTxCurrency(tx) === 'THB')
    .reduce((sum, tx) => sum + getGrossAmount(tx), 0)
})

const grossTotalUSD = computed(() => {
  return filteredDividends.value
    .filter(tx => getTxCurrency(tx) === 'USD')
    .reduce((sum, tx) => sum + getGrossAmount(tx), 0)
})

const netTotalTHB = computed(() => {
  return filteredDividends.value
    .filter(tx => getTxCurrency(tx) === 'THB')
    .reduce((sum, tx) => sum + getNetAmount(tx), 0)
})

const netTotalUSD = computed(() => {
  return filteredDividends.value
    .filter(tx => getTxCurrency(tx) === 'USD')
    .reduce((sum, tx) => sum + getNetAmount(tx), 0)
})

const grossTotalDisplayCurrency = computed(() => {
  const rate = Number(portfolioStore.overview?.usd_to_thb_rate || 35.5)
  if (portfolioStore.displayCurrency === 'USD') {
    return grossTotalUSD.value + (grossTotalTHB.value / rate)
  }
  return grossTotalTHB.value + (grossTotalUSD.value * rate)
})

const netTotalDisplayCurrency = computed(() => {
  const rate = Number(portfolioStore.overview?.usd_to_thb_rate || 35.5)
  if (portfolioStore.displayCurrency === 'USD') {
    return netTotalUSD.value + (netTotalTHB.value / rate)
  }
  return netTotalTHB.value + (netTotalUSD.value * rate)
})

const taxTotalDisplayCurrency = computed(() => {
  return Math.max(0, grossTotalDisplayCurrency.value - netTotalDisplayCurrency.value)
})

function formatDate(dateStr?: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
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
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function openAddDividendModal() {
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

async function handleDividendSaved() {
  toast.success('Dividend distribution recorded')
  await Promise.all([
    portfolioStore.fetchTransactions(),
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchOverview({ currency: portfolioStore.displayCurrency })
  ])
}

function confirmDeleteTransaction(id: string) {
  confirmModal.title = 'Delete Dividend Entry'
  confirmModal.message = 'Are you sure you want to delete this dividend distribution? Portfolio cash balances and dividend yields will update.'
  confirmModal.confirmText = 'Delete Entry'
  confirmModal.isDanger = true
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    await portfolioStore.deleteTransaction(id)
    toast.info('Deleted dividend record')
    await portfolioStore.fetchOverview({ currency: portfolioStore.displayCurrency })
  }
  confirmModal.isOpen = true
}

function exportDividendsCSV() {
  if (filteredDividends.value.length === 0) return

  const headers = [
    'Date',
    'Portfolio',
    'Ticker',
    'Shares',
    'DPS',
    'Gross_Dividend',
    'Withholding_Tax',
    'Net_Received',
    'Currency',
    'Notes'
  ]

  const rows = filteredDividends.value.map(tx => {
    const dateStr = tx.executed_at ? new Date(tx.executed_at).toISOString().split('T')[0] : ''
    const pName = tx.portfolio_name || getHoldingPortfolioName(tx.holding) || 'Consolidated'
    const ticker = tx.holding_ticker || tx.ticker || ''
    const shares = tx.shares || 0
    const dps = tx.price_per_share || 0
    const gross = getGrossAmount(tx)
    const tax = tx.fee || 0
    const net = getNetAmount(tx)
    const currency = getTxCurrency(tx)
    const notes = (tx.notes || '').replace(/"/g, '""')

    return [
      dateStr,
      `"${pName}"`,
      ticker,
      shares,
      dps,
      gross.toFixed(2),
      tax,
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
  link.setAttribute('download', `dividend_ledger_${new Date().toISOString().slice(0, 10)}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  toast.success('Dividend ledger exported to CSV')
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
