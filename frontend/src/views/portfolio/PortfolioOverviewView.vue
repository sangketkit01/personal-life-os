<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header & Universal Search Bar -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">{{ t('nav.portfolio.overview') }}</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            WEALTH RADAR
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          {{ t('pf.subtitle') }}
        </p>
      </div>

      <!-- Universal Search & Quick Action -->
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 lg:max-w-md w-full">
        <UniversalAssetSearch
          @record-trade="openTradeModalForTicker"
          placeholder="Search any ticker (e.g. NVDA, PTT, BTC)..."
        />
        <button
          @click="openTradeModal()"
          class="px-3.5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 shrink-0 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>{{ t('led.addTransaction') }}</span>
        </button>
      </div>
    </div>

    <!-- Live Market Session & Currency Bar -->
    <MarketStatusBar />

    <!-- Summary KPI Cards -->
    <SkeletonLoader
      v-if="portfolioStore.isLoading && !portfolioStore.overview"
      variant="metrics"
      :count="4"
    />

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- 1. Total Net Worth -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors shadow-sm">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Net Worth</span>
          <Briefcase class="w-3.5 h-3.5 text-zinc-400" />
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-2xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ currSymbol }}{{ formatNumber(activeSummary.total_market_value) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span>Cost Basis:</span>
          <span class="font-mono text-zinc-300">{{ currSymbol }}{{ formatNumber(activeSummary.total_cost_basis) }}</span>
        </div>
      </div>

      <!-- 2. Unrealized P&L -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors shadow-sm">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Unrealized P&L</span>
          <component
            :is="activeSummary.total_unrealized_pnl >= 0 ? TrendingUp : TrendingDown"
            class="w-3.5 h-3.5"
            :class="activeSummary.total_unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          />
        </div>
        <div class="mt-2.5 flex items-baseline gap-2">
          <span
            class="text-2xl font-semibold font-mono tabular-nums"
            :class="activeSummary.total_unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          >
            {{ activeSummary.total_unrealized_pnl >= 0 ? '+' : '' }}{{ currSymbol }}{{ formatNumber(activeSummary.total_unrealized_pnl) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span>Return:</span>
          <span
            class="font-mono font-semibold"
            :class="activeSummary.total_unrealized_pnl_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          >
            {{ activeSummary.total_unrealized_pnl_pct >= 0 ? '+' : '' }}{{ (activeSummary.total_unrealized_pnl_pct || 0).toFixed(2) }}%
          </span>
        </div>
      </div>

      <!-- 3. {{ t('pf.realized') }} / Loss -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors shadow-sm">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Realized Profit</span>
          <CheckCircle2 class="w-3.5 h-3.5 text-zinc-400" />
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span
            class="text-2xl font-semibold font-mono tabular-nums"
            :class="activeSummary.total_realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          >
            {{ activeSummary.total_realized_pnl >= 0 ? '+' : '' }}{{ currSymbol }}{{ formatNumber(activeSummary.total_realized_pnl) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span>Closed trades:</span>
          <span class="font-mono text-zinc-400">Lock-in gains</span>
        </div>
      </div>

      <!-- 4. Passive {{ t('pf.dividends') }} -->
      <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors shadow-sm">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>{{ t('pf.dividends') }}</span>
          <Coins class="w-3.5 h-3.5 text-zinc-400" />
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-2xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ currSymbol }}{{ formatNumber(activeSummary.total_dividends) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span>Passive Income:</span>
          <span class="font-mono text-emerald-400 font-medium">Net Yield</span>
        </div>
      </div>
    </div>

    <!-- Asset Allocation Donut Chart -->
    <AssetAllocationChart
      :allocations="activeSummary.asset_allocation || []"
      :currency-symbol="currSymbol"
    />

    <!-- Multi-Portfolio Account Baskets Grid -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <FolderKanban class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            My Investment Portfolios ({{ portfolioStore.portfolios.length }})
          </h2>
        </div>
        <button
          @click="router.push('/portfolio/accounts/new')"
          class="px-2.5 py-1 rounded-md text-xs font-mono text-zinc-300 hover:text-white bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 transition-colors flex items-center gap-1.5"
        >
          <FolderPlus class="w-3.5 h-3.5 text-zinc-400" />
          <span>{{ t('portfolio.ui.create') }}</span>
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Consolidated All Portfolios Card -->
        <div
          @click="goToPortfolio('ALL')"
          class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700 cursor-pointer transition-all hover:bg-zinc-900/80 group"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-zinc-400"></div>
              <span class="font-semibold text-sm text-zinc-200 group-hover:text-zinc-100 transition-colors">
                All Portfolios (Consolidated)
              </span>
            </div>
            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/60">
              AGGREGATE
            </span>
          </div>

          <div class="mt-3.5 flex items-baseline justify-between">
            <span class="text-lg font-mono font-semibold text-zinc-100">
              {{ currSymbol }}{{ formatNumber(activeSummary.total_market_value) }}
            </span>
            <span
              class="text-xs font-mono font-semibold"
              :class="activeSummary.total_unrealized_pnl_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'"
            >
              {{ activeSummary.total_unrealized_pnl_pct >= 0 ? '+' : '' }}{{ (activeSummary.total_unrealized_pnl_pct || 0).toFixed(2) }}%
            </span>
          </div>

          <div class="mt-3 pt-2.5 border-t border-zinc-800/60 flex items-center justify-between text-xs text-zinc-500">
            <span>{{ portfolioStore.holdings.length }} Assets held</span>
            <span class="text-zinc-400 text-[11px] group-hover:underline flex items-center gap-1">
              <span>Inspect {{ t('pf.holdings') }}</span>
              <ArrowRight class="w-3 h-3 text-zinc-500" />
            </span>
          </div>
        </div>

        <div v-if="portfolioStore.isLoading && portfolioStore.portfolios.length === 0">
          <SkeletonLoader variant="cards" :count="4" />
        </div>

        <!-- Individual Account Cards -->
        <div
          v-for="p in portfolioStore.portfolios"
          :key="p.id"
          @click="goToPortfolio(p.id)"
          class="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800/80 hover:border-zinc-700 cursor-pointer transition-all hover:bg-zinc-900/60 group relative"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span
                class="w-2 h-2 rounded-full shrink-0 shadow-sm"
                :style="{ backgroundColor: getPortfolioColor(p.color) }"
              ></span>
              <span class="font-semibold text-sm text-zinc-200 group-hover:text-zinc-100 transition-colors truncate">
                {{ p.name }}
              </span>
            </div>
            <span
              class="text-[10px] font-mono px-1.5 py-0.2 rounded border font-semibold uppercase bg-zinc-900 text-zinc-400 border-zinc-800"
            >
              {{ p.currency }}
            </span>
          </div>

          <p class="text-xs text-zinc-500 mt-1 line-clamp-1">
            {{ p.description || t('portfolio.ui.emptyDescription') }}
          </p>

          <div class="mt-4 pt-2.5 border-t border-zinc-800/60 flex items-center justify-between text-xs text-zinc-500">
            <span v-if="p.is_default" class="text-[10px] font-mono text-zinc-400 bg-zinc-800 px-1.5 py-0.2 rounded">
              Default
            </span>
            <span v-else class="text-[10px] font-mono text-zinc-500">Custom</span>

            <span class="text-zinc-400 text-[11px] group-hover:underline flex items-center gap-1">
              <span>{{ t('portfolio.ui.view') }}</span>
              <ArrowRight class="w-3 h-3 text-zinc-500" />
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Navigation Hub -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
      <!-- {{ t('pf.watchlist') }} Card -->
      <RouterLink
        to="/portfolio/watchlist"
        class="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800/80 hover:border-zinc-700 transition-all hover:bg-zinc-900/50 group flex items-start gap-3.5"
      >
        <div class="w-9 h-9 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center justify-center shrink-0">
          <Star class="w-4 h-4 text-zinc-400" />
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center justify-between">
            <h3 class="font-medium text-sm text-zinc-200 group-hover:text-zinc-100 transition-colors">
              Market Watchlist
            </h3>
            <span class="text-[11px] font-mono text-zinc-400 bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
              {{ portfolioStore.watchlist.length }}
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-1">Pre/Post market radar and real-time price change alerts</p>
        </div>
      </RouterLink>

      <!-- Executions Card -->
      <RouterLink
        to="/portfolio/executions"
        class="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800/80 hover:border-zinc-700 transition-all hover:bg-zinc-900/50 group flex items-start gap-3.5"
      >
        <div class="w-9 h-9 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center justify-center shrink-0">
          <ArrowLeftRight class="w-4 h-4 text-zinc-400" />
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center justify-between">
            <h3 class="font-medium text-sm text-zinc-200 group-hover:text-zinc-100 transition-colors">
              Trade Executions Log
            </h3>
            <span class="text-[11px] font-mono text-zinc-400 bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
              {{ portfolioStore.transactions.length }}
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-1">Complete audit trail of buy, sell, and dividend cash flows</p>
        </div>
      </RouterLink>

      <!-- {{ t('pf.marketNews') }} Card -->
      <RouterLink
        to="/portfolio/news"
        class="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800/80 hover:border-zinc-700 transition-all hover:bg-zinc-900/50 group flex items-start gap-3.5"
      >
        <div class="w-9 h-9 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 flex items-center justify-center shrink-0">
          <Newspaper class="w-4 h-4 text-zinc-400" />
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center justify-between">
            <h3 class="font-medium text-sm text-zinc-200 group-hover:text-zinc-100 transition-colors">
              Market Intelligence
            </h3>
            <span class="text-[11px] font-mono text-zinc-400 bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
              Signals
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-1">Global market news with AI Thai translation and sentiment</p>
        </div>
      </RouterLink>
    </div>

    <!-- Modals -->
    <AddTransactionModal
      :is-open="showAddModal"
      :prefill-ticker="prefillTicker"
      @close="showAddModal = false"
      @saved="refreshOverview"
    />

  </div>
</template>

<script setup lang="ts">
import SkeletonLoader from '../../components/common/SkeletonLoader.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { t } from '../../i18n'
import UniversalAssetSearch from '../../components/portfolio/UniversalAssetSearch.vue'
import MarketStatusBar from '../../components/portfolio/MarketStatusBar.vue'
import AssetAllocationChart from '../../components/portfolio/AssetAllocationChart.vue'
import AddTransactionModal from '../../components/portfolio/AddTransactionModal.vue'
import { getPortfolioColor } from '../../types/portfolio'
import {
  TrendingUp,
  TrendingDown,
  Briefcase,
  Coins,
  CheckCircle2,
  Plus,
  ArrowRight,
  FolderKanban,
  FolderPlus,
  Star,
  ArrowLeftRight,
  Newspaper
} from 'lucide-vue-next'

const router = useRouter()
const portfolioStore = usePortfolioStore()

const showAddModal = ref(false)
const prefillTicker = ref('')

const currSymbol = computed(() => (portfolioStore.displayCurrency === 'USD' ? '$' : '฿'))

const activeSummary = computed(() => {
  if (portfolioStore.displayCurrency === 'USD') {
    return portfolioStore.overview?.summary_usd || {
      total_market_value: 0,
      total_cost_basis: 0,
      total_unrealized_pnl: 0,
      total_unrealized_pnl_pct: 0,
      total_realized_pnl: 0,
      total_dividends: 0,
      asset_allocation: []
    }
  }
  return portfolioStore.overview?.summary_thb || {
    total_market_value: 0,
    total_cost_basis: 0,
    total_unrealized_pnl: 0,
    total_unrealized_pnl_pct: 0,
    total_realized_pnl: 0,
    total_dividends: 0,
    asset_allocation: []
  }
})

function formatNumber(val: any, minFrac = 2, maxFrac = 2): string {
  const num = Number(val || 0)
  return num.toLocaleString('en-US', { minimumFractionDigits: minFrac, maximumFractionDigits: maxFrac })
}

function openTradeModal() {
  prefillTicker.value = ''
  showAddModal.value = true
}

function openTradeModalForTicker(ticker: string) {
  prefillTicker.value = ticker
  showAddModal.value = true
}

function goToPortfolio(portfolioId: string) {
  portfolioStore.setSelectedPortfolio(portfolioId)
  router.push({
    path: portfolioId === 'ALL' ? '/portfolio/accounts' : `/portfolio/accounts/${portfolioId}`
  })
}

async function refreshOverview() {
  await Promise.all([
    portfolioStore.fetchOverview({ currency: portfolioStore.displayCurrency }),
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchPortfolios()
  ])
}

onMounted(async () => {
  await Promise.all([
    portfolioStore.fetchPortfolios(),
    portfolioStore.fetchOverview({ currency: portfolioStore.displayCurrency }),
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchTransactions(),
    portfolioStore.fetchWatchlist(),
    portfolioStore.fetchMarketStatus()
  ])
})
</script>
