<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- View Header & Universal Search -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">{{ t('nav.portfolio.accounts') }}</h1>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          {{ t('portfolio.ui.manageHelp') }}
        </p>
      </div>

      <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 lg:max-w-md w-full">
        <UniversalAssetSearch
          @record-trade="openAddModalForTicker"
          placeholder="Search any ticker (e.g. NVDA, PTT.BK, BTC-USD)..."
        />
        <div class="flex items-center gap-2 shrink-0">
          <button
            @click="router.push('/portfolio/accounts/new')"
            class="px-3 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-white text-xs font-mono transition-colors flex items-center gap-1.5"
            :title="t('portfolio.ui.create')"
          >
            <FolderPlus class="w-3.5 h-3.5 text-zinc-400" />
            <span>{{ t('portfolio.ui.create') }}</span>
          </button>
          <button
            @click="openAddModal()"
            class="px-3.5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <Plus class="w-3.5 h-3.5 text-zinc-950" />
            <span>{{ t('portfolio.ui.recordTrade') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Live Market Session & Currency Bar -->
    <MarketStatusBar />

    <!-- Multi-Portfolio Switcher Bar (Dime Style) -->
    <div class="flex items-center justify-between gap-3 overflow-x-auto pb-1">
      <div class="flex items-center gap-1.5 flex-nowrap">
        <!-- All Portfolios Aggregate Tab -->
        <button
          @click="selectPortfolio('ALL')"
          type="button"
          class="px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-2 border whitespace-nowrap"
          :class="portfolioStore.selectedPortfolioId === 'ALL'
            ? 'bg-zinc-800 text-zinc-100 font-bold border-zinc-700 shadow-sm'
            : 'bg-zinc-900/60 text-zinc-400 border-zinc-800/80 hover:text-zinc-200 hover:bg-zinc-900'"
        >
          <Globe class="w-3.5 h-3.5 text-zinc-400" />
          <span>{{ t('portfolio.ui.all') }}</span>
        </button>

        <!-- User Named Sub-Portfolios -->
        <div
          v-for="p in portfolioStore.portfolios"
          :key="p.id"
          class="flex items-center group relative"
        >
          <button
            @click="selectPortfolio(p.id)"
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-2 border whitespace-nowrap"
            :class="portfolioStore.selectedPortfolioId === p.id
              ? 'bg-zinc-800 text-zinc-100 font-bold border-zinc-700 shadow-sm'
              : 'bg-zinc-900/60 text-zinc-400 border-zinc-800/80 hover:text-zinc-200 hover:bg-zinc-900'"
          >
            <span
              class="w-2 h-2 rounded-full flex-shrink-0 shadow-sm"
              :style="{ backgroundColor: getPortfolioColor(p.color) }"
            ></span>
            <span>{{ p.name }}</span>
            <span
              class="text-[10px] px-1 py-0.2 rounded border bg-zinc-950 text-zinc-400 border-zinc-800"
            >
              {{ p.currency }}
            </span>
          </button>

        </div>
      </div>

    </div>

    <!-- Active Portfolio Card Info (if single portfolio selected) -->
    <div
      v-if="currentPortfolio"
      class="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
    >
      <div class="flex items-center gap-3">
        <span
          class="w-3 h-3 rounded-full shrink-0 shadow-sm"
          :style="{ backgroundColor: getPortfolioColor(currentPortfolio.color) }"
        ></span>
        <div>
          <div class="flex items-center gap-2">
            <span class="font-bold text-zinc-100 text-sm">{{ currentPortfolio.name }}</span>
            <span
              class="text-[10px] font-mono px-1.5 py-0.2 rounded border uppercase bg-zinc-950 text-zinc-400 border-zinc-800"
            >
              {{ currentPortfolio.currency }}
            </span>
            <span v-if="currentPortfolio.is_default" class="text-[10px] font-mono text-zinc-500 bg-zinc-800 px-1.5 py-0.2 rounded">
              {{ t('portfolio.ui.default') }}
            </span>
          </div>
          <p class="text-zinc-500 mt-0.5 text-[11px]">{{ currentPortfolio.description || t('portfolio.ui.emptyDescription') }}</p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <RouterLink
          :to="`/portfolio/accounts/${currentPortfolio.id}`"
          class="px-3 py-1 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans flex items-center gap-1.5 shadow-sm transition-colors"
        >
          <span>{{ t('portfolio.ui.view') }}</span>
          <ArrowRight class="w-3.5 h-3.5 text-zinc-950" />
        </RouterLink>
      </div>
    </div>

    <!-- Holdings Table Section -->
    <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <TrendingUp class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Holdings Position (in {{ portfolioStore.displayCurrency }})
          </h2>
          <span class="text-[11px] font-mono text-zinc-500 ml-1">({{ displayedHoldings.length }} Assets)</span>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <!-- Asset Class Filter Pills -->
          <div class="flex items-center bg-zinc-950/80 border border-zinc-800/80 rounded-md p-0.5">
            <button
              v-for="filter in assetClassFilters"
              :key="filter.value"
              @click="selectedAssetClass = filter.value"
              type="button"
              class="px-2 py-0.5 rounded text-[11px] font-mono transition-colors"
              :class="selectedAssetClass === filter.value ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
            >
              {{ filter.label }}
            </button>
          </div>

          <!-- Hide Closed Positions Toggle -->
          <label class="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer select-none">
            <input
              type="checkbox"
              v-model="hideClosedPositions"
              class="rounded bg-zinc-900 border-zinc-700 text-zinc-100 accent-zinc-600 focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5"
            />
            <span class="text-[11px]">Hide 0 units ({{ closedHoldingsCount }})</span>
          </label>
        </div>
      </div>

      <!-- Holdings Table -->
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[11px] font-mono uppercase text-zinc-500">
              <th @click="toggleSort('ticker')" class="py-3 px-4 font-semibold cursor-pointer hover:text-zinc-300 select-none">
                <div class="flex items-center gap-1">
                  <span>Ticker / Asset</span>
                  <span v-if="sortKey === 'ticker'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('shares')" class="py-3 px-4 font-semibold text-right cursor-pointer hover:text-zinc-300 select-none">
                <div class="flex items-center justify-end gap-1">
                  <span>Shares / Units</span>
                  <span v-if="sortKey === 'shares'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('avg_cost')" class="py-3 px-4 font-semibold text-right cursor-pointer hover:text-zinc-300 select-none">
                <div class="flex items-center justify-end gap-1">
                  <span>Avg Cost</span>
                  <span v-if="sortKey === 'avg_cost'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('current_price')" class="py-3 px-4 font-semibold text-right cursor-pointer hover:text-zinc-300 select-none">
                <div class="flex items-center justify-end gap-1">
                  <span>Price</span>
                  <span v-if="sortKey === 'current_price'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('market_value')" class="py-3 px-4 font-semibold text-right cursor-pointer hover:text-zinc-300 select-none">
                <div class="flex items-center justify-end gap-1">
                  <span>Market Value</span>
                  <span v-if="sortKey === 'market_value'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('unrealized_pnl')" class="py-3 px-4 font-semibold text-right cursor-pointer hover:text-zinc-300 select-none">
                <div class="flex items-center justify-end gap-1">
                  <span>Unrealized P&L</span>
                  <span v-if="sortKey === 'unrealized_pnl'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('total_realized_pnl')" class="py-3 px-4 font-semibold text-right cursor-pointer hover:text-zinc-300 select-none">
                <div class="flex items-center justify-end gap-1">
                  <span>Realized Gain</span>
                  <span v-if="sortKey === 'total_realized_pnl'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th class="py-3 px-4 font-semibold text-right select-none">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="holding in displayedHoldings"
              :key="holding.id"
              class="hover:bg-zinc-900/50 transition-colors group cursor-pointer"
              @click="goToAssetDetail(holding.ticker, holding.portfolio, holding.id)"
            >
              <!-- 1. Ticker / Asset -->
              <td class="py-3.5 px-4 font-mono">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-bold text-zinc-100 group-hover:text-zinc-300 transition-colors">
                    {{ holding.ticker }}
                  </span>
                  <span class="text-[9px] px-1.5 py-0.5 rounded border border-zinc-800 bg-zinc-900 text-zinc-400 font-medium font-mono">
                    {{ holding.asset_type }}
                  </span>
                  <span class="text-[9px] text-zinc-500 uppercase">
                    {{ holding.currency || 'THB' }}
                  </span>
                </div>
                <div class="text-[11px] text-zinc-400 font-sans truncate max-w-[200px] mt-0.5">
                  {{ holding.name }}
                </div>
              </td>

              <!-- 2. Shares -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-200">
                {{ formatShares(holding.position.shares) }}
              </td>

              <!-- 3. Avg Cost -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-400">
                {{ currSymbol }}{{ formatHoldingPrice(holding, 'avg_cost') }}
              </td>

              <!-- 4. Price -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-200">
                {{ currSymbol }}{{ formatHoldingPrice(holding, 'current_price') }}
                <QuoteFreshness :quote="holding.position?.quote" />
              </td>

              <!-- 5. Market Value -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums font-semibold text-zinc-100">
                {{ currSymbol }}{{ formatHoldingValue(holding, 'market_value') }}
              </td>

              <!-- 6. Unrealized P&L -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums">
                <div
                  class="font-semibold text-xs"
                  :class="getHoldingPnL(holding) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
                >
                  {{ getHoldingPnL(holding) >= 0 ? '+' : '' }}{{ currSymbol }}{{ formatNumber(getHoldingPnL(holding)) }}
                </div>
                <div
                  class="text-[10px]"
                  :class="holding.position.unrealized_pnl_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'"
                >
                  {{ holding.position.unrealized_pnl_pct >= 0 ? '+' : '' }}{{ (holding.position.unrealized_pnl_pct || 0).toFixed(2) }}%
                </div>
              </td>

              <!-- 7. Realized Gain -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums">
                <span
                  class="text-xs"
                  :class="getHoldingRealizedPnL(holding) >= 0 ? 'text-zinc-400' : 'text-rose-400'"
                >
                  {{ currSymbol }}{{ formatNumber(getHoldingRealizedPnL(holding)) }}
                </span>
              </td>

              <!-- 8. Actions -->
              <td class="py-3.5 px-4 text-right" @click.stop>
                <div class="flex items-center justify-end gap-1">
                  <!-- Buy / Trade -->
                  <button
                    @click="openAddModal(holding)"
                    type="button"
                    class="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
                    title="Record Trade (Buy / Sell / Dividend)"
                  >
                    <Plus class="w-3.5 h-3.5" />
                  </button>

                  <!-- Move Holding to another portfolio -->
                  <button
                    @click="openMoveHolding(holding)"
                    type="button"
                    class="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                    :title="t('portfolio.ui.moveHolding')"
                  >
                    <FolderInput class="w-3.5 h-3.5" />
                  </button>

                  <!-- Edit holding -->
                  <button
                    @click="openEditHolding(holding)"
                    type="button"
                    class="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                    title="Edit holding details"
                  >
                    <Edit2 class="w-3.5 h-3.5" />
                  </button>

                  <!-- Delete holding -->
                  <button
                    @click="confirmDeleteHolding(holding)"
                    type="button"
                    class="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors"
                    title="Delete holding position"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </td>
            </tr>

            <!-- Empty State -->
            <tr v-if="displayedHoldings.length === 0">
              <td colspan="8" class="py-12 text-center text-xs text-zinc-500 font-mono">
                <div class="flex flex-col items-center justify-center gap-2">
                  <TrendingUp class="w-6 h-6 text-zinc-600" />
                  <p>No holdings found in this portfolio</p>
                  <button
                    @click="openAddModal()"
                    type="button"
                    class="mt-2 px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-semibold text-xs"
                  >
                    Record First Trade Execution
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

    <EditHoldingModal
      :is-open="showEditHoldingModal"
      :holding="selectedHoldingToEdit"
      @close="showEditHoldingModal = false"
      @saved="refreshHoldings"
    />



    <MoveHoldingModal
      :is-open="showMoveModal"
      :holding="selectedHoldingToMove"
      @close="showMoveModal = false"
      @moved="refreshHoldings"
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
import { t } from '../../i18n'
import QuoteFreshness from '../../components/portfolio/QuoteFreshness.vue'
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import UniversalAssetSearch from '../../components/portfolio/UniversalAssetSearch.vue'
import MarketStatusBar from '../../components/portfolio/MarketStatusBar.vue'
import AddTransactionModal from '../../components/portfolio/AddTransactionModal.vue'
import EditHoldingModal from '../../components/portfolio/EditHoldingModal.vue'
import MoveHoldingModal from '../../components/portfolio/MoveHoldingModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import { getPortfolioColor, type StockHolding, type StockTransaction } from '../../types/portfolio'
import {
  TrendingUp,
  Plus,
  Trash2,
  Edit2,
  Globe,
  FolderPlus,
  FolderInput,
  ArrowRight
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const showAddModal = ref(false)
const showEditHoldingModal = ref(false)
const showMoveModal = ref(false)

const selectedHoldingToMove = ref<StockHolding | null>(null)
const selectedHoldingToEdit = ref<StockHolding | null>(null)
const selectedEditingTx = ref<StockTransaction | null>(null)
const prefillTicker = ref('')
const prefillHoldingId = ref('')

const selectedAssetClass = ref<'ALL' | 'STOCK' | 'CRYPTO' | 'FUND' | 'OTHER'>('ALL')
const hideClosedPositions = ref(true)
const sortKey = ref<'ticker' | 'currency' | 'shares' | 'avg_cost' | 'current_price' | 'market_value' | 'unrealized_pnl' | 'total_realized_pnl'>('market_value')
const sortOrder = ref<'asc' | 'desc'>('desc')

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

const assetClassFilters = [
  { value: 'ALL', label: 'All' },
  { value: 'STOCK', label: 'Stocks' },
  { value: 'CRYPTO', label: 'Crypto' },
  { value: 'FUND', label: 'Funds' },
  { value: 'OTHER', label: 'Other' }
] as const

const currSymbol = computed(() => (portfolioStore.displayCurrency === 'USD' ? '$' : '฿'))

const currentPortfolio = computed(() => {
  if (portfolioStore.selectedPortfolioId === 'ALL') return null
  return portfolioStore.portfolios.find(p => p.id === portfolioStore.selectedPortfolioId) || null
})

const closedHoldingsCount = computed(() => {
  return portfolioStore.holdings.filter(h => Number(h.position?.shares || 0) <= 0).length
})

const displayedHoldings = computed(() => {
  let list = [...portfolioStore.holdings]
  if (selectedAssetClass.value !== 'ALL') {
    list = list.filter(h => h.asset_type === selectedAssetClass.value)
  }
  if (hideClosedPositions.value) {
    list = list.filter(h => Number(h.position?.shares || 0) > 0)
  }

  const isUSD = portfolioStore.displayCurrency === 'USD'
  list.sort((a, b) => {
    let valA: any
    let valB: any

    switch (sortKey.value) {
      case 'ticker':
        valA = a.ticker.toLowerCase()
        valB = b.ticker.toLowerCase()
        break
      case 'currency':
        valA = (a.currency || 'THB').toLowerCase()
        valB = (b.currency || 'THB').toLowerCase()
        break
      case 'shares':
        valA = Number(a.position?.shares || 0)
        valB = Number(b.position?.shares || 0)
        break
      case 'avg_cost':
        valA = Number(isUSD ? a.position?.avg_cost_usd : a.position?.avg_cost_thb) || Number(a.position?.avg_cost || 0)
        valB = Number(isUSD ? b.position?.avg_cost_usd : b.position?.avg_cost_thb) || Number(b.position?.avg_cost || 0)
        break
      case 'current_price':
        valA = Number(isUSD ? a.position?.current_price_usd : a.position?.current_price_thb) || Number(a.position?.current_price || 0)
        valB = Number(isUSD ? b.position?.current_price_usd : b.position?.current_price_thb) || Number(b.position?.current_price || 0)
        break
      case 'market_value':
        valA = Number(isUSD ? a.position?.market_value_usd : a.position?.market_value_thb) || Number(a.position?.market_value || 0)
        valB = Number(isUSD ? b.position?.market_value_usd : b.position?.market_value_thb) || Number(b.position?.market_value || 0)
        break
      case 'unrealized_pnl':
        valA = Number(isUSD ? a.position?.unrealized_pnl_usd : a.position?.unrealized_pnl_thb) || Number(a.position?.unrealized_pnl || 0)
        valB = Number(isUSD ? b.position?.unrealized_pnl_usd : b.position?.unrealized_pnl_thb) || Number(b.position?.unrealized_pnl || 0)
        break
      case 'total_realized_pnl':
        valA = Number(isUSD ? a.position?.total_realized_pnl_usd : a.position?.total_realized_pnl_thb) || Number(a.position?.total_realized_pnl || 0)
        valB = Number(isUSD ? b.position?.total_realized_pnl_usd : b.position?.total_realized_pnl_thb) || Number(b.position?.total_realized_pnl || 0)
        break
      default:
        valA = 0
        valB = 0
    }

    if (valA < valB) return sortOrder.value === 'asc' ? -1 : 1
    if (valA > valB) return sortOrder.value === 'asc' ? 1 : -1
    return 0
  })

  return list
})

function toggleSort(key: typeof sortKey.value) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = (key === 'ticker' || key === 'currency') ? 'asc' : 'desc'
  }
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

function formatHoldingPrice(holding: StockHolding, field: 'avg_cost' | 'current_price'): string {
  if (portfolioStore.displayCurrency === 'USD') {
    const val = field === 'avg_cost' ? holding.position.avg_cost_usd : holding.position.current_price_usd
    return formatPrice(val !== undefined ? val : holding.position[field])
  } else {
    const val = field === 'avg_cost' ? holding.position.avg_cost_thb : holding.position.current_price_thb
    return formatPrice(val !== undefined ? val : holding.position[field])
  }
}

function formatHoldingValue(holding: StockHolding, field: 'market_value' | 'total_invested'): string {
  if (portfolioStore.displayCurrency === 'USD') {
    const val = field === 'market_value' ? holding.position.market_value_usd : holding.position.total_invested_usd
    return formatNumber(val !== undefined ? val : holding.position[field], 2)
  } else {
    const val = field === 'market_value' ? holding.position.market_value_thb : holding.position.total_invested_thb
    return formatNumber(val !== undefined ? val : holding.position[field], 2)
  }
}

function getHoldingPnL(holding: StockHolding): number {
  if (portfolioStore.displayCurrency === 'USD') {
    return Number(holding.position.unrealized_pnl_usd !== undefined ? holding.position.unrealized_pnl_usd : holding.position.unrealized_pnl)
  }
  return Number(holding.position.unrealized_pnl_thb !== undefined ? holding.position.unrealized_pnl_thb : holding.position.unrealized_pnl)
}

function getHoldingRealizedPnL(holding: StockHolding): number {
  if (portfolioStore.displayCurrency === 'USD') {
    return Number(holding.position.total_realized_pnl_usd !== undefined ? holding.position.total_realized_pnl_usd : holding.position.total_realized_pnl)
  }
  return Number(holding.position.total_realized_pnl_thb !== undefined ? holding.position.total_realized_pnl_thb : holding.position.total_realized_pnl)
}

function goToAssetDetail(ticker: string, portfolioId?: string, holdingId?: string) {
  if (!ticker) return
  const query: Record<string, string> = {}
  if (holdingId) query.holding_id = holdingId
  if (portfolioId && portfolioId !== 'ALL') query.portfolio_id = portfolioId
  router.push({
    path: `/portfolio/asset/${encodeURIComponent(ticker)}`,
    query
  })
}

function selectPortfolio(id: string) {
  portfolioStore.setSelectedPortfolio(id)
  router.replace({
    query: id !== 'ALL' ? { portfolio: id } : {}
  }).catch(() => {})
}

function openAddModal(holding?: StockHolding) {
  selectedEditingTx.value = null
  if (holding) {
    prefillTicker.value = holding.ticker
    prefillHoldingId.value = holding.id
  } else {
    prefillTicker.value = ''
    prefillHoldingId.value = ''
  }
  showAddModal.value = true
}

function openAddModalForTicker(ticker: string) {
  selectedEditingTx.value = null
  prefillTicker.value = ticker
  prefillHoldingId.value = ''
  showAddModal.value = true
}

function closeAddModal() {
  showAddModal.value = false
  selectedEditingTx.value = null
}

function openEditHolding(holding: StockHolding) {
  selectedHoldingToEdit.value = holding
  showEditHoldingModal.value = true
}

function openMoveHolding(holding: StockHolding) {
  selectedHoldingToMove.value = holding
  showMoveModal.value = true
}

async function handleTradeSaved() {
  toast.success('Trade execution recorded and updated')
  await refreshHoldings()
}

async function refreshHoldings() {
  await Promise.all([
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchOverview({ currency: portfolioStore.displayCurrency })
  ])
}

function confirmDeleteHolding(holding: StockHolding) {
  confirmModal.title = 'Delete Holding'
  confirmModal.message = `Are you sure you want to delete holding ${holding.ticker} and all its transaction history?`
  confirmModal.confirmText = 'Delete Holding'
  confirmModal.isDanger = true
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    await portfolioStore.deleteHolding(holding.id)
    toast.info(`Deleted holding ${holding.ticker}`)
  }
  confirmModal.isOpen = true
}

onMounted(async () => {
  if (route.query.portfolio && typeof route.query.portfolio === 'string') {
    portfolioStore.setSelectedPortfolio(route.query.portfolio)
  }
  await Promise.all([
    portfolioStore.fetchPortfolios(),
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchOverview({ currency: portfolioStore.displayCurrency }),
    portfolioStore.fetchMarketStatus()
  ])
})

watch(() => route.query.portfolio, (newPortfolio) => {
  if (newPortfolio && typeof newPortfolio === 'string') {
    if (portfolioStore.selectedPortfolioId !== newPortfolio) {
      portfolioStore.setSelectedPortfolio(newPortfolio)
    }
  }
})
</script>
