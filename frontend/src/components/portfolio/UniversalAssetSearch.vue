<template>
  <div ref="containerRef" class="relative w-full">
    <div class="relative flex items-center">
      <Search class="w-3.5 h-3.5 text-zinc-500 absolute left-3 pointer-events-none" />
      <input
        ref="inputRef"
        v-model="query"
        @input="handleInput"
        @keydown.down.prevent="navigateResults(1)"
        @keydown.up.prevent="navigateResults(-1)"
        @keydown.enter.prevent="handleEnter"
        @keydown.esc="closeSearch"
        @focus="handleFocus"
        type="text"
        :placeholder="placeholder"
        class="w-full pl-9 pr-14 py-2 rounded-lg bg-zinc-900/50 hover:bg-zinc-900/80 border border-zinc-800/80 focus:border-zinc-700 focus:bg-zinc-950 text-xs text-zinc-100 placeholder-zinc-500 font-mono transition-all outline-none"
      />
      <div class="absolute right-2.5 flex items-center gap-1.5">
        <Loader2 v-if="isSearching" class="w-3 h-3 text-zinc-400 animate-spin" />
        <button
          v-else-if="query"
          @click="clearSearch"
          type="button"
          class="text-zinc-500 hover:text-zinc-300"
        >
          <X class="w-3.5 h-3.5" />
        </button>
        <span
          v-else
          class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-500 border border-zinc-800 pointer-events-none"
          title="Press / anywhere to search"
        >
          /
        </span>
      </div>
    </div>

    <!-- Autocomplete Dropdown Flyout -->
    <div
      v-if="showResults && query.trim()"
      class="absolute left-0 right-0 mt-1.5 max-h-[380px] overflow-y-auto rounded-xl bg-zinc-950/98 backdrop-blur-md border border-zinc-800/90 shadow-2xl z-50 divide-y divide-zinc-900"
    >
      <!-- Results Header -->
      <div class="px-3.5 py-2 bg-zinc-900/40 text-[10px] font-mono text-zinc-500 flex items-center justify-between border-b border-zinc-900">
        <span v-if="results.length > 0">
          {{ results.length }} result{{ results.length > 1 ? 's' : '' }} for "{{ query }}"
        </span>
        <span v-else>
          Market Search
        </span>
        <span class="text-zinc-600">Enter ↵ to inspect</span>
      </div>

      <!-- Result Items -->
      <div v-if="results.length > 0" class="divide-y divide-zinc-900">
        <div
          v-for="(item, idx) in results"
          :key="item.ticker"
          @click="selectAsset(item.ticker)"
          class="p-2.5 px-3.5 hover:bg-zinc-900/60 cursor-pointer transition-colors flex items-center justify-between gap-3 group"
          :class="{ 'bg-zinc-900/80 border-l-2 border-zinc-400': selectedIndex === idx }"
        >
          <!-- Left: Ticker, Name, Badges -->
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono font-semibold text-xs text-zinc-100 group-hover:text-white transition-colors">
                {{ item.ticker }}
              </span>
              <span class="text-[9px] font-mono px-1.5 py-0.2 rounded border border-zinc-800 bg-zinc-900 text-zinc-400">
                {{ item.asset_type }}
              </span>
              <span class="text-[9px] font-mono text-zinc-600 uppercase">
                {{ item.exchange || (item.ticker.endsWith('.BK') ? 'SET' : 'US') }}
              </span>

              <!-- Status Badges: Held or Watchlist -->
              <span
                v-if="isTickerHeld(item.ticker)"
                class="text-[9px] font-mono px-1.5 py-0.2 rounded border border-zinc-800 bg-zinc-900 text-zinc-300 flex items-center gap-1"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>Held</span>
              </span>
              <span
                v-if="portfolioStore.isWatchlisted(item.ticker)"
                class="text-[9px] font-mono px-1.5 py-0.2 rounded border border-zinc-800 bg-zinc-900 text-zinc-400 flex items-center gap-1"
              >
                <Star class="w-2.5 h-2.5 text-zinc-400" />
                <span>Watchlist</span>
              </span>
            </div>
            <div class="text-[11px] text-zinc-400 font-sans truncate mt-0.5">
              {{ item.name }}
            </div>
          </div>

          <!-- Right: Price and Quick Actions -->
          <div class="flex items-center gap-3 shrink-0">
            <div v-if="item.price" class="text-right font-mono">
              <div class="text-xs font-semibold text-zinc-200">
                {{ (item.currency || '').toUpperCase() === 'USD' ? '$' : '฿' }}{{ formatPrice(item.price) }}
              </div>
              <div
                v-if="item.change_pct !== undefined && item.change_pct !== null"
                class="text-[10px] font-mono font-medium"
                :class="item.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'"
              >
                {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
              </div>
            </div>

            <!-- Quick Action Buttons -->
            <div class="flex items-center gap-1" @click.stop>
              <!-- Watchlist Toggle -->
              <button
                @click="portfolioStore.toggleWatchlist(item.ticker)"
                type="button"
                class="p-1 rounded hover:bg-zinc-800 text-zinc-500 hover:text-zinc-200 transition-colors"
                :title="portfolioStore.isWatchlisted(item.ticker) ? 'Remove from Watchlist' : 'Add to Watchlist'"
              >
                <Star
                  class="w-3.5 h-3.5"
                  :class="portfolioStore.isWatchlisted(item.ticker) ? 'text-zinc-200 fill-zinc-200' : 'text-zinc-600'"
                />
              </button>

              <!-- Quick Trade -->
              <button
                @click="handleQuickTrade(item.ticker)"
                type="button"
                class="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] font-mono text-zinc-300 hover:text-zinc-100 transition-colors"
                title="Record Trade for this ticker"
              >
                + Buy
              </button>

              <!-- View Details -->
              <button
                @click="selectAsset(item.ticker)"
                type="button"
                class="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] font-mono text-zinc-300 hover:text-white transition-colors flex items-center gap-1"
              >
                <span>View</span>
                <ArrowRight class="w-2.5 h-2.5 text-zinc-500" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Fallback direct inspect card if no catalog match -->
      <div
        v-else-if="!isSearching"
        @click="selectAsset(query.trim())"
        class="p-3.5 px-4 hover:bg-zinc-900/60 cursor-pointer transition-colors flex items-center justify-between text-xs font-mono group"
      >
        <div>
          <div class="text-zinc-200 font-semibold flex items-center gap-2">
            <span>Inspect "{{ query.toUpperCase() }}"</span>
            <span class="text-[10px] px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">Direct Lookup</span>
          </div>
          <div class="text-[11px] text-zinc-500 font-sans mt-0.5">
            Query market quotes, price history, and news for this symbol
          </div>
        </div>
        <ArrowRight class="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import type { MarketAssetSearchResult } from '../../types/portfolio'
import { Search, Loader2, X, Star, ArrowRight } from 'lucide-vue-next'

withDefaults(defineProps<{
  placeholder?: string
}>(), {
  placeholder: 'Search any ticker (e.g. NVDA, PTT.BK, BTC-USD)...'
})

const emit = defineEmits<{
  (e: 'record-trade', ticker: string): void
}>()

const router = useRouter()
const portfolioStore = usePortfolioStore()

const query = ref('')
const results = ref<MarketAssetSearchResult[]>([])
const isSearching = ref(false)
const showResults = ref(false)
const selectedIndex = ref(-1)
const containerRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

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

function handleInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  const q = query.value.trim()
  if (!q) {
    results.value = []
    isSearching.value = false
    selectedIndex.value = -1
    return
  }

  isSearching.value = true
  debounceTimer = setTimeout(async () => {
    try {
      results.value = await portfolioStore.searchAssets(q)
      showResults.value = true
      selectedIndex.value = -1
    } catch {
      results.value = []
    } finally {
      isSearching.value = false
    }
  }, 160)
}

function handleFocus() {
  showResults.value = true
  if (query.value.trim() && results.value.length === 0) {
    handleInput()
  }
}

function navigateResults(direction: number) {
  if (!results.value.length) return
  const max = results.value.length - 1
  selectedIndex.value = Math.max(-1, Math.min(max, selectedIndex.value + direction))
}

function handleEnter() {
  if (selectedIndex.value >= 0 && results.value[selectedIndex.value]) {
    selectAsset(results.value[selectedIndex.value].ticker)
  } else if (query.value.trim()) {
    selectAsset(query.value.trim())
  }
}

function selectAsset(ticker: string) {
  if (!ticker) return
  showResults.value = false
  query.value = ''
  router.push(`/portfolio/asset/${encodeURIComponent(ticker)}`)
}

function handleQuickTrade(ticker: string) {
  showResults.value = false
  emit('record-trade', ticker)
}

function closeSearch() {
  showResults.value = false
  selectedIndex.value = -1
}

function clearSearch() {
  query.value = ''
  results.value = []
  closeSearch()
}

function handleGlobalKeydown(e: KeyboardEvent) {
  if ((e.key === '/' || (e.ctrlKey && e.key.toLowerCase() === 'k')) && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) {
    e.preventDefault()
    inputRef.value?.focus()
    showResults.value = true
  }
}

function handleClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    closeSearch()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
  document.removeEventListener('click', handleClickOutside)
})
</script>
