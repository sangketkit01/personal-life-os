<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header & Watchlist Quick Add -->
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

      <!-- Quick Add Ticker Autocomplete Bar -->
      <div ref="searchContainerRef" class="relative w-full lg:max-w-md">
        <div class="flex items-center gap-2">
          <div class="relative flex-1">
            <Search class="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              v-model="searchQuery"
              @input="handleSearchInput"
              @keydown.enter.prevent="handleQuickAdd"
              type="text"
              placeholder="Add ticker to watchlist (e.g. TSLA, DELTA.BK, ETH-USD)..."
              class="w-full pl-9 pr-8 py-2 rounded-lg bg-zinc-900/90 hover:bg-zinc-900 border border-zinc-800 focus:border-zinc-500 focus:bg-zinc-950 text-xs text-zinc-100 placeholder-zinc-500 font-mono transition-all outline-none"
            />
            <Loader2 v-if="isSearching" class="w-3.5 h-3.5 text-zinc-400 animate-spin absolute right-2.5 top-1/2 -translate-y-1/2" />
          </div>
          <button
            @click="handleQuickAdd"
            :disabled="!searchQuery.trim() || isAdding"
            type="button"
            class="px-3.5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shrink-0 disabled:opacity-50"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>Add</span>
          </button>
        </div>

        <!-- Search Autocomplete Dropdown -->
        <div
          v-if="showAutocomplete && searchResults.length > 0"
          class="absolute left-0 right-0 mt-1.5 max-h-[300px] overflow-y-auto rounded-xl bg-zinc-950/95 backdrop-blur-md border border-zinc-800 shadow-2xl z-50 divide-y divide-zinc-800/80"
        >
          <div
            v-for="item in searchResults"
            :key="item.ticker"
            @click="addTickerFromSearch(item.ticker)"
            class="p-2.5 px-3 hover:bg-zinc-900/80 cursor-pointer transition-colors flex items-center justify-between gap-3 text-xs"
          >
            <div>
              <div class="flex items-center gap-2">
                <span class="font-mono font-bold text-zinc-100">{{ item.ticker }}</span>
                <span class="text-[9px] font-mono px-1 py-0.2 rounded border bg-zinc-900 text-zinc-400 border-zinc-800">
                  {{ item.asset_type }}
                </span>
                <span class="text-[9px] font-mono text-zinc-500">{{ item.exchange }}</span>
              </div>
              <div class="text-[11px] text-zinc-400 font-sans truncate mt-0.5 max-w-[260px]">{{ item.name }}</div>
            </div>
            <div class="text-right font-mono">
              <span class="text-xs text-zinc-200">
                {{ (item.currency || '').toUpperCase() === 'USD' ? '$' : '฿' }}{{ formatPrice(item.price) }}
              </span>
              <div
                v-if="item.change_pct !== undefined && item.change_pct !== null"
                class="text-[10px] font-semibold"
                :class="item.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'"
              >
                {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
              </div>
            </div>
          </div>
        </div>
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
                {{ (item.currency || 'USD').toUpperCase() === 'USD' ? '$' : '฿' }}{{ formatPrice(item.current_price) }}
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
            <tr v-if="portfolioStore.watchlist.length === 0">
              <td colspan="7" class="py-12 text-center text-xs text-zinc-500 font-mono">
                <div class="flex flex-col items-center justify-center gap-2">
                  <Star class="w-6 h-6 text-zinc-600" />
                  <p>Your watchlist is currently empty</p>
                  <p class="text-[11px] text-zinc-600">Type any stock or crypto ticker above to start monitoring</p>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import MarketStatusBar from '../../components/portfolio/MarketStatusBar.vue'
import AddTransactionModal from '../../components/portfolio/AddTransactionModal.vue'
import type { MarketAssetSearchResult } from '../../types/portfolio'
import {
  Star,
  Search,
  Plus,
  Loader2,
  Trash2,
  ArrowRight,
  TrendingUp,
  TrendingDown
} from 'lucide-vue-next'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const searchQuery = ref('')
const searchResults = ref<MarketAssetSearchResult[]>([])
const isSearching = ref(false)
const showAutocomplete = ref(false)
const isAdding = ref(false)
const searchContainerRef = ref<HTMLElement | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

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
  const clean = ticker.trim().toUpperCase()
  return portfolioStore.holdings.find(h =>
    h.ticker.toUpperCase() === clean ||
    h.ticker.toUpperCase() === `${clean}.BK` ||
    h.ticker.toUpperCase() === `${clean}-USD`
  )
}

function handleSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  const q = searchQuery.value.trim()
  if (!q) {
    searchResults.value = []
    showAutocomplete.value = false
    return
  }
  isSearching.value = true
  debounceTimer = setTimeout(async () => {
    try {
      searchResults.value = await portfolioStore.searchAssets(q)
      showAutocomplete.value = true
    } catch {
      searchResults.value = []
    } finally {
      isSearching.value = false
    }
  }, 160)
}

async function handleQuickAdd() {
  const t = searchQuery.value.trim().toUpperCase()
  if (!t) return
  if (portfolioStore.isWatchlisted(t)) {
    toast.info(`${t} is already in Watchlist`)
    searchQuery.value = ''
    showAutocomplete.value = false
    return
  }

  isAdding.value = true
  try {
    const isAdded = await portfolioStore.toggleWatchlist(t)
    searchQuery.value = ''
    showAutocomplete.value = false
    if (isAdded) {
      toast.success(`Added ${t} to Watchlist`)
      await portfolioStore.fetchWatchlist()
    }
  } catch (err: any) {
    toast.error(err?.response?.data?.ticker || `Failed to add ${t} to watchlist`)
  } finally {
    isAdding.value = false
  }
}

async function addTickerFromSearch(ticker: string) {
  searchQuery.value = ticker
  await handleQuickAdd()
}

async function handleRemove(ticker: string) {
  try {
    await portfolioStore.toggleWatchlist(ticker)
    toast.info(`Removed ${ticker} from Watchlist`)
    await portfolioStore.fetchWatchlist()
  } catch {
    toast.error(`Failed to remove ${ticker}`)
  }
}

function goToAssetDetail(ticker: string) {
  router.push(`/portfolio/asset/${encodeURIComponent(ticker)}`)
}

function openTradeModal(ticker: string) {
  prefillTicker.value = ticker
  showAddModal.value = true
}

async function handleTradeSaved() {
  toast.success('Trade recorded successfully')
  await portfolioStore.fetchHoldings()
}

function handleClickOutside(e: MouseEvent) {
  if (searchContainerRef.value && !searchContainerRef.value.contains(e.target as Node)) {
    showAutocomplete.value = false
  }
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  await Promise.all([
    portfolioStore.fetchWatchlist(),
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchMarketStatus()
  ])
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
