<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header & Universal Asset Search -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Market Watchlist</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            PRE/POST MARKET RADAR
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Monitor potential trade setups, real-time pre/post market quotes, and 24h price action alerts
        </p>
      </div>

      <!-- Universal Search Bar -->
      <div class="relative w-full lg:max-w-md">
        <UniversalAssetSearch
          @record-trade="openTradeModal"
          :placeholder="t('portfolio.search.placeholder')"
        />
      </div>
    </div>

    <!-- Live Market Session & Currency Bar -->
    <MarketStatusBar />

    <!-- Watchlist Overview Stat Strip -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 flex items-center justify-between">
        <div>
          <span class="text-[10px] font-mono uppercase text-zinc-500">Tracked Tickers</span>
          <div class="text-lg font-bold font-mono text-zinc-100 mt-1">{{ portfolioStore.watchlist.length }} Assets</div>
        </div>
        <div class="w-8 h-8 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-300 flex items-center justify-center">
          <Star class="w-4 h-4 text-zinc-400" />
        </div>
      </div>

      <div class="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 flex items-center justify-between">
        <div>
          <span class="text-[10px] font-mono uppercase text-zinc-500">Daily Gainers</span>
          <div class="text-lg font-bold font-mono text-emerald-400 mt-1">{{ gainersCount }} Assets</div>
        </div>
        <div class="w-8 h-8 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-emerald-400 flex items-center justify-center">
          <TrendingUp class="w-4 h-4" />
        </div>
      </div>

      <div class="p-3.5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 flex items-center justify-between">
        <div>
          <span class="text-[10px] font-mono uppercase text-zinc-500">Daily Decliners</span>
          <div class="text-lg font-bold font-mono text-rose-400 mt-1">{{ losersCount }} Assets</div>
        </div>
        <div class="w-8 h-8 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-rose-400 flex items-center justify-center">
          <TrendingDown class="w-4 h-4" />
        </div>
      </div>
    </div>

    <!-- Watchlist Table -->
    <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Star class="w-4 h-4 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Radar Assets
          </h2>
        </div>
        <span class="text-[11px] font-mono text-zinc-500">{{ portfolioStore.watchlist.length }} items</span>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-zinc-800/80 bg-zinc-950/40 text-[11px] font-mono uppercase text-zinc-500">
              <th class="py-3 px-4 font-semibold">Ticker / Company</th>
              <th class="py-3 px-4 font-semibold">Asset Class</th>
              <th class="py-3 px-4 font-semibold text-right">Price</th>
              <th class="py-3 px-4 font-semibold text-right">24h Change</th>
              <th class="py-3 px-4 font-semibold text-right">24h Change (Amt)</th>
              <th class="py-3 px-4 font-semibold">Portfolio Status</th>
              <th class="py-3 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="item in portfolioStore.watchlist"
              :key="item.id || item.ticker"
              class="hover:bg-zinc-900/50 transition-colors group cursor-pointer"
              @click="goToAssetDetail(item.ticker)"
            >
              <!-- 1. Ticker / Name -->
              <td class="py-3.5 px-4 font-mono">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-zinc-100 group-hover:text-zinc-300 transition-colors">
                    {{ item.ticker }}
                  </span>
                  <span class="text-[9px] font-mono text-zinc-500 uppercase">
                    {{ item.ticker.endsWith('.BK') ? 'SET' : (item.asset_type === 'CRYPTO' ? 'CRYPTO' : 'US') }}
                  </span>
                </div>
                <div class="text-[11px] text-zinc-400 font-sans truncate max-w-[220px] mt-0.5">
                  {{ item.name || item.ticker }}
                </div>
              </td>

              <!-- 2. Asset Class -->
              <td class="py-3.5 px-4 font-mono">
                <span class="text-[9px] px-1.5 py-0.5 rounded border border-zinc-800 bg-zinc-900 text-zinc-400 font-medium font-mono">
                  {{ item.asset_type || 'STOCK' }}
                </span>
              </td>

              <!-- 3. Current Price -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums font-semibold text-zinc-100">
                <template v-if="item.current_price !== undefined && item.current_price !== null">{{ (item.currency || 'USD').toUpperCase() === 'USD' ? '$' : '฿' }}{{ formatPrice(item.current_price) }}</template>
                <span v-else class="text-zinc-500">—</span>
                <QuoteFreshness :quote="item.quote" />
              </td>

              <!-- 4. 24h Change -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums">
                <div
                  v-if="item.change_pct !== undefined && item.change_pct !== null"
                  class="text-[11px] font-semibold"
                  :class="item.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'"
                >
                  <span>{{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%</span>
                </div>
                <span v-else class="text-zinc-600">-</span>
              </td>

              <!-- 5. 24h Change Amount -->
              <td class="py-3.5 px-4 text-right font-mono tabular-nums text-zinc-400 text-[11px]">
                <span v-if="item.change_amount !== undefined && item.change_amount !== null">
                  {{ item.change_amount >= 0 ? '+' : '' }}{{ formatPrice(item.change_amount) }}
                </span>
                <span v-else class="text-zinc-600">-</span>
              </td>

              <!-- 6. Portfolio Status (Held / Not held) -->
              <td class="py-3.5 px-4">
                <span
                  v-if="isTickerHeld(item.ticker)"
                  class="text-[9px] font-mono px-2 py-0.5 rounded border border-zinc-800 bg-zinc-900 text-zinc-300 font-medium inline-flex items-center gap-1.5"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span>Held in Portfolio</span>
                </span>
                <span v-else class="text-[9px] font-mono text-zinc-500">
                  Watching only
                </span>
              </td>

              <!-- 7. Actions -->
              <td class="py-3.5 px-4 text-right" @click.stop>
                <div class="flex items-center justify-end gap-1.5">
                  <!-- Quick Buy -->
                  <button
                    @click="openTradeModal(item.ticker)"
                    type="button"
                    class="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] font-mono text-zinc-300 hover:text-white transition-colors"
                    title="Record Trade Execution"
                  >
                    + Buy
                  </button>

                  <!-- View Asset -->
                  <button
                    @click="goToAssetDetail(item.ticker)"
                    type="button"
                    class="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                    title="Inspect Asset Chart & Analytics"
                  >
                    <ArrowRight class="w-3.5 h-3.5" />
                  </button>

                  <!-- Remove from Watchlist -->
                  <button
                    @click="handleRemove(item.ticker)"
                    type="button"
                    class="p-1.5 rounded hover:bg-zinc-800 text-zinc-500 hover:text-rose-400 transition-colors"
                    title="Remove from Watchlist"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </td>
            </tr>

            <!-- Empty State -->
            <tr v-if="portfolioStore.isLoadingWatchlist && portfolioStore.watchlist.length === 0">
              <td colspan="7" class="p-4">
                <SkeletonLoader variant="table" :count="5" />
              </td>
            </tr>

            <tr v-else-if="portfolioStore.watchlist.length === 0">
              <td colspan="7" class="py-12 text-center text-xs text-zinc-500 font-mono">
                <div class="flex flex-col items-center justify-center gap-2">
                  <Star class="w-6 h-6 text-zinc-600" />
                  <p>Your watchlist is currently empty</p>
                  <p class="text-[11px] text-zinc-600">Search any stock or crypto ticker above to inspect and monitor</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Trade Modal -->
    <AddTransactionModal
      :is-open="showAddModal"
      :prefill-ticker="prefillTicker"
      @close="showAddModal = false"
      @saved="handleTradeSaved"
    />
    <PriceAlertsPanel />
  </div>
</template>

<script setup lang="ts">
import QuoteFreshness from '../../components/portfolio/QuoteFreshness.vue'
import PriceAlertsPanel from '../../components/portfolio/PriceAlertsPanel.vue'
import SkeletonLoader from '../../components/common/SkeletonLoader.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore, isTickerMatch } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import { t } from '../../i18n'
import MarketStatusBar from '../../components/portfolio/MarketStatusBar.vue'
import UniversalAssetSearch from '../../components/portfolio/UniversalAssetSearch.vue'
import AddTransactionModal from '../../components/portfolio/AddTransactionModal.vue'
import {
  Star,
  Trash2,
  ArrowRight,
  TrendingUp,
  TrendingDown
} from 'lucide-vue-next'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const showAddModal = ref(false)
const prefillTicker = ref('')

const gainersCount = computed(() => {
  return portfolioStore.watchlist.filter(w => (w.change_pct || 0) > 0).length
})

const losersCount = computed(() => {
  return portfolioStore.watchlist.filter(w => (w.change_pct || 0) < 0).length
})

function formatPrice(val: any): string {
  const num = Number(val || 0)
  if (num === 0) return '0.00'
  if (Math.abs(num) < 1) {
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })
  }
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function isTickerHeld(ticker: string) {
  return portfolioStore.holdings.some(h => isTickerMatch(h.ticker, ticker))
}

async function handleRemove(ticker: string) {
  try {
    await portfolioStore.toggleWatchlist(ticker)
    toast.info(t('portfolio.watchlist.removeSuccess', { ticker }))
  } catch {
    toast.error(t('portfolio.watchlist.toggleFailed', { ticker }))
  }
}

function goToAssetDetail(ticker: string) {
  router.push(`/portfolio/asset/${encodeURIComponent(ticker)}`)
}

function openTradeModal(ticker?: string) {
  prefillTicker.value = ticker || ''
  showAddModal.value = true
}

async function handleTradeSaved() {
  toast.success('Trade recorded successfully')
  await portfolioStore.fetchHoldings()
}

onMounted(async () => {
  await Promise.all([
    portfolioStore.fetchWatchlist(),
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchMarketStatus()
  ])
})
</script>
