<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-lg p-6 shadow-2xl relative my-8">
      <!-- Close button -->
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- Modal Title -->
      <div class="mb-5">
        <h2 class="text-base font-semibold text-zinc-100 tracking-tight">
          {{ editingTransaction ? 'Edit Trade' : 'Record Trade' }}
        </h2>
        <p class="text-xs text-zinc-500 mt-0.5">
          {{ editingTransaction ? 'Update trade execution details' : 'Log trade execution into your portfolio' }}
        </p>
      </div>

      <!-- Transaction Type Switcher Tabs -->
      <div class="grid grid-cols-3 gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-lg mb-4">
        <button
          type="button"
          @click="form.transaction_type = 'BUY'"
          class="py-1.5 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5"
          :class="[
            form.transaction_type === 'BUY'
              ? 'bg-zinc-800 text-zinc-100 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          ]"
        >
          <ArrowDownLeft class="w-3.5 h-3.5 text-zinc-400" />
          <span>Buy</span>
        </button>

        <button
          type="button"
          @click="form.transaction_type = 'SELL'"
          class="py-1.5 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5"
          :class="[
            form.transaction_type === 'SELL'
              ? 'bg-zinc-800 text-zinc-100 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          ]"
        >
          <ArrowUpRight class="w-3.5 h-3.5 text-zinc-400" />
          <span>Sell</span>
        </button>

        <button
          type="button"
          @click="form.transaction_type = 'DIVIDEND'"
          class="py-1.5 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5"
          :class="[
            form.transaction_type === 'DIVIDEND'
              ? 'bg-zinc-800 text-zinc-100 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          ]"
        >
          <Coins class="w-3.5 h-3.5 text-zinc-400" />
          <span>Dividend</span>
        </button>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-3.5">
        <!-- Target Portfolio Selector (Dime-style) (F05) -->
        <div v-if="!editingTransaction && portfolioStore.portfolios.length > 0">
          <div class="flex items-center justify-between mb-1">
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400">
              Target Portfolio
            </label>
            <span v-if="prefillHoldingId" class="text-[10px] text-zinc-500 font-sans">
              (Locked to Holding)
            </span>
          </div>
          <div class="relative flex items-center">
            <span
              v-if="currentSelectedPortfolio"
              class="w-2.5 h-2.5 rounded-full absolute left-3 pointer-events-none z-10 shadow-sm"
              :style="{ backgroundColor: getPortfolioColor(currentSelectedPortfolio.color) }"
            ></span>
            <select
              v-model="form.portfolio"
              :disabled="!!prefillHoldingId"
              class="w-full pl-8 pr-8 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-sans focus:outline-none focus:border-zinc-600 transition-colors appearance-none cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <option
                v-for="p in portfolioStore.portfolios"
                :key="p.id"
                :value="p.id"
              >
                {{ p.name }} ({{ p.currency }}) {{ p.is_default ? '• Default' : '' }}
              </option>
            </select>
            <ChevronDown v-if="!prefillHoldingId" class="w-3.5 h-3.5 text-zinc-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>

        <!-- Asset Search & Strict Autocomplete Selection (For new trades without prefilled asset) (F09) -->
        <div v-if="!prefillHoldingId && !editingTransaction && !prefillTicker">
          <!-- Asset Class Filter Pills -->
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-[11px] font-mono uppercase tracking-wider text-zinc-400">
              Select Asset <span class="text-rose-400">*</span>
            </label>
            <div class="flex items-center gap-1">
              <button
                v-for="type in assetTypes"
                :key="type.value"
                type="button"
                @click="setSearchAssetType(type.value)"
                class="px-2 py-0.5 rounded text-[10px] font-mono transition-colors"
                :class="searchAssetType === type.value ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700' : 'text-zinc-500 hover:text-zinc-300'"
              >
                {{ type.label }}
              </button>
            </div>
          </div>

          <!-- If Asset is Selected & Verified -->
          <div
            v-if="selectedAsset"
            class="p-2.5 rounded-lg bg-zinc-900/90 border border-emerald-500/30 flex items-center justify-between"
          >
            <div class="flex items-center gap-2.5">
              <div class="w-7 h-7 rounded-md bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300">
                <CheckCircle2 class="w-4 h-4 text-zinc-300" />
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-mono font-bold text-zinc-100 text-xs">{{ selectedAsset.ticker }}</span>
                  <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/50">
                    {{ selectedAsset.asset_type }}
                  </span>
                  <span class="text-[9px] font-mono text-zinc-500">
                    {{ selectedAsset.exchange }}
                  </span>
                </div>
                <div class="text-[11px] text-zinc-400 truncate max-w-[260px]">
                  {{ selectedAsset.name }}
                </div>
              </div>
            </div>

            <button
              type="button"
              @click="clearSelectedAsset"
              class="px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-[11px] font-sans transition-colors"
            >
              Change
            </button>
          </div>

          <!-- Search Input Box with Live Autocomplete -->
          <div v-else ref="searchContainerRef" class="relative">
            <div class="relative">
              <input
                v-model="searchQuery"
                type="text"
                @input="handleSearchInput"
                @focus="showSearchResults = true"
                @keydown.escape="showSearchResults = false"
                placeholder="Search symbol or name (e.g. AAPL, PTT, BTC, NVDA, SCB)"
                class="w-full pl-8 pr-8 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
              />
              <Search class="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <Loader2 v-if="isSearching" class="w-3.5 h-3.5 text-zinc-400 animate-spin absolute right-2.5 top-1/2 -translate-y-1/2" />
              <button
                v-else-if="searchQuery"
                type="button"
                @click="searchQuery = ''; searchResults = []"
                class="text-zinc-500 hover:text-zinc-300 absolute right-2.5 top-1/2 -translate-y-1/2"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>

            <!-- Autocomplete Results Dropdown -->
            <div
              v-if="showSearchResults && (searchResults.length > 0 || isSearching || (searchQuery.trim().length >= 2 && !isSearching))"
              class="absolute left-0 right-0 mt-1 z-30 rounded-lg bg-zinc-950 border border-zinc-800 shadow-2xl max-h-56 overflow-y-auto divide-y divide-zinc-900 font-sans"
            >
              <div v-if="isSearching" class="p-3 text-center text-xs text-zinc-500 font-mono">
                Searching verified assets...
              </div>

              <div
                v-else-if="searchResults.length === 0"
                class="p-4 text-center text-xs text-zinc-500"
              >
                No verified market asset found for "{{ searchQuery }}".
                <p class="text-[10px] text-zinc-600 mt-0.5">Please check ticker spelling or select another category.</p>
              </div>

              <button
                v-for="item in searchResults"
                :key="item.ticker"
                type="button"
                @click="selectAsset(item)"
                class="w-full text-left px-3.5 py-2.5 hover:bg-zinc-900 flex items-center justify-between transition-colors group"
              >
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-mono font-bold text-zinc-200 group-hover:text-zinc-100 text-xs">{{ item.ticker }}</span>
                    <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
                      {{ item.asset_type }}
                    </span>
                    <span class="text-[10px] font-mono text-zinc-500">
                      {{ item.exchange }}
                    </span>
                  </div>
                  <div class="text-[11px] text-zinc-400 truncate max-w-[280px]">
                    {{ item.name }}
                  </div>
                </div>

                <div class="flex items-center gap-2">
                  <span class="text-[10px] font-mono px-1.5 py-0.5 rounded border uppercase bg-zinc-900 text-zinc-400 border-zinc-800">
                    {{ item.currency }}
                  </span>
                  <span class="text-xs text-zinc-600 group-hover:text-zinc-300">Select →</span>
                </div>
              </button>
            </div>

            <!-- Hint if no asset selected -->
            <p v-if="!selectedAsset" class="text-[10px] text-zinc-400 mt-1 flex items-center gap-1">
              <span>* You must select a verified asset from the search list to record a trade.</span>
            </p>
          </div>
        </div>

        <!-- Prefilled / Locked Ticker Display (If editing or prefilled from holding) -->
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Asset Symbol</label>
            <div class="px-3 py-2 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono font-bold text-zinc-200">
              {{ form.ticker }}
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Denomination</label>
            <div class="px-3 py-2 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono font-bold text-zinc-200">
              {{ form.currency }}
            </div>
          </div>
        </div>

        <!-- Currency Selector (Dual THB vs USD) - Only editable if creating new holding without existing denomination (F03) -->
        <div v-if="!prefillHoldingId && !editingTransaction && !currentHolding">
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
            Trade Currency
          </label>
          <div class="grid grid-cols-2 gap-1 p-0.5 bg-zinc-900 border border-zinc-800 rounded-md">
            <button
              type="button"
              @click="setCurrency('THB')"
              class="py-1.5 rounded text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1"
              :class="form.currency === 'THB' ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700/60 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
            >
              <span>฿ THB</span>
            </button>
            <button
              type="button"
              @click="setCurrency('USD')"
              class="py-1.5 rounded text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1"
              :class="form.currency === 'USD' ? 'bg-zinc-800 text-zinc-100 font-bold border border-zinc-700/60 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
            >
              <span>$ USD</span>
            </button>
          </div>
        </div>

        <!-- Position Context Warning on SELL (F08) -->
        <div
          v-if="form.transaction_type === 'SELL'"
          class="p-2.5 rounded bg-zinc-900/80 border border-zinc-800 flex items-center justify-between text-xs font-mono"
        >
          <span class="text-zinc-400 text-[11px]">Holding Position:</span>
          <div v-if="currentHolding" class="flex items-center gap-2">
            <span class="text-zinc-200 font-semibold">{{ formatShares(currentHolding.position.shares) }} shares available</span>
            <button
              type="button"
              @click="setMaxSell"
              class="px-1.5 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-[10px]"
            >
              Max
            </button>
          </div>
          <div v-else class="text-rose-400 text-[11px]">
            No shares held in selected portfolio
          </div>
        </div>

        <!-- Shares (8-decimal precision) and Price Per Share -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              {{ form.transaction_type === 'DIVIDEND' ? 'Eligible Shares' : 'Units / Shares (Max 8 Decimals)' }}
            </label>
            <input
              v-model.number="form.shares"
              type="number"
              step="any"
              min="0.00000001"
              required
              :placeholder="sharesPlaceholder"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>

          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              {{ form.transaction_type === 'DIVIDEND' ? `DPS (${currencySymbol})` : `Price / Unit (${currencySymbol})` }}
            </label>
            <input
              v-model.number="form.price_per_share"
              type="number"
              step="any"
              min="0.00000001"
              required
              :placeholder="pricePlaceholder"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>
        </div>

        <!-- Fee & Execution Date -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              {{ form.transaction_type === 'DIVIDEND' ? `Withholding Tax (${currencySymbol})` : `Broker Fee (${currencySymbol})` }}
            </label>
            <input
              v-model.number="form.fee"
              type="number"
              step="any"
              min="0"
              placeholder="0.00"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400">Execution Date & Time</label>
              <span class="text-[10px] text-zinc-500 font-sans">{{ localTzLabel }}</span>
            </div>
            <input
              v-model="form.executed_at"
              type="datetime-local"
              required
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>
        </div>

        <!-- Live Estimate Box -->
        <div class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 flex items-center justify-between text-xs font-mono">
          <span class="text-zinc-500 text-[11px]">
            {{ form.transaction_type === 'BUY' ? 'Gross Settlement:' : 'Net Proceeds:' }}
          </span>
          <span class="font-semibold text-zinc-100">
            {{ currencySymbol }}{{ formattedEstimatedTotal }}
          </span>
        </div>

        <!-- Notes -->
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Notes (Optional)</label>
          <input
            v-model="form.notes"
            type="text"
            placeholder="Optional notes"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <!-- Submit Buttons -->
        <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="portfolioStore.isSubmitting || isSubmitDisabled"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {{ portfolioStore.isSubmitting ? 'Posting...' : (editingTransaction ? 'Save Changes' : 'Save Trade') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { usePortfolioStore } from '../../stores/portfolio'
import {
  getPortfolioColor,
  type AssetType,
  type TransactionType,
  type StockTransaction,
  type MarketAssetSearchResult
} from '../../types/portfolio'
import {
  X,
  ArrowDownLeft,
  ArrowUpRight,
  Coins,
  Search,
  CheckCircle2,
  ChevronDown,
  Loader2
} from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  prefillTicker?: string
  prefillHoldingId?: string
  editingTransaction?: StockTransaction | null
  initialType?: TransactionType
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

const portfolioStore = usePortfolioStore()
const errorMessage = ref<string | null>(null)
const manualCurrency = ref(false)

// Autocomplete State
const searchContainerRef = ref<HTMLElement | null>(null)
const searchQuery = ref('')
const searchResults = ref<MarketAssetSearchResult[]>([])
const isSearching = ref(false)
const showSearchResults = ref(false)
const selectedAsset = ref<MarketAssetSearchResult | null>(null)
const searchAssetType = ref<'ALL' | 'STOCK' | 'CRYPTO' | 'FUND' | 'OTHER'>('ALL')
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function handleClickOutside(e: MouseEvent) {
  if (searchContainerRef.value && !searchContainerRef.value.contains(e.target as Node)) {
    showSearchResults.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside)
  if (debounceTimer) clearTimeout(debounceTimer)
})

const assetTypes = [
  { value: 'ALL', label: 'All' },
  { value: 'STOCK', label: 'Stocks' },
  { value: 'CRYPTO', label: 'Crypto' },
  { value: 'FUND', label: 'Funds' }
] as const

const getNowLocalDateTime = () => {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

// F07: Convert UTC database timestamp to local datetime-local input safely
function toLocalInputDateTime(dateInput?: string | Date): string {
  if (!dateInput) return getNowLocalDateTime()
  const d = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
  const tzOffset = d.getTimezoneOffset() * 60000
  const localTime = new Date(d.getTime() - tzOffset)
  return localTime.toISOString().slice(0, 16)
}

const localTzLabel = computed(() => {
  try {
    const offsetMin = new Date().getTimezoneOffset()
    const sign = offsetMin <= 0 ? '+' : '-'
    const hours = Math.floor(Math.abs(offsetMin) / 60)
    const mins = Math.abs(offsetMin) % 60
    const offsetStr = `GMT${sign}${hours}${mins > 0 ? `:${mins}` : ''}`
    const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone
    return `${tzName} (${offsetStr})`
  } catch {
    return 'Local Time'
  }
})

const form = ref({
  portfolio: '',
  ticker: '',
  currency: 'THB' as 'THB' | 'USD',
  transaction_type: 'BUY' as TransactionType,
  shares: null as number | null,
  price_per_share: null as number | null,
  fee: 0,
  executed_at: getNowLocalDateTime(),
  notes: ''
})

const currencySymbol = computed(() => ((form.value.currency || '').toUpperCase() === 'USD' ? '$' : '฿'))

const currentSelectedPortfolio = computed(() =>
  portfolioStore.portfolios.find(p => p.id === form.value.portfolio)
)

const isSubmitDisabled = computed(() => {
  if (portfolioStore.isSubmitting) return true
  // F09: If not editing and not prefilled, must have selected a verified asset or prefilled ticker
  if (!props.editingTransaction && !props.prefillHoldingId && !props.prefillTicker) {
    if (!selectedAsset.value || !form.value.ticker) return true
  }
  // Validate shares and price
  if (!form.value.shares || form.value.shares <= 0) return true
  if (form.value.price_per_share === null || form.value.price_per_share < 0) return true

  // F08: Validate oversell on UI
  if (form.value.transaction_type === 'SELL') {
    const available = Number(currentHolding.value?.position?.shares || 0) + (props.editingTransaction?.transaction_type === 'SELL' ? Number(props.editingTransaction.shares) : 0)
    if (!currentHolding.value || Number(form.value.shares || 0) > available || available <= 0) {
      return true
    }
  }
  return false
})

const sharesPlaceholder = computed(() => {
  if (selectedAsset.value?.asset_type === 'CRYPTO') return 'e.g. 0.00250000'
  return 'e.g. 100'
})

const pricePlaceholder = computed(() => {
  if (selectedAsset.value?.asset_type === 'CRYPTO') return 'e.g. 64250.00'
  return form.value.currency === 'USD' ? 'e.g. 182.50' : 'e.g. 35.50'
})

// F05 & F08: Find holding matching ticker and selected portfolio
const currentHolding = computed(() => {
  if (props.prefillHoldingId) {
    return portfolioStore.holdings.find(h => h.id === props.prefillHoldingId)
  }
  const t = form.value.ticker.trim().toUpperCase()
  if (!t) return null
  return portfolioStore.holdings.find(h =>
    (!form.value.portfolio || h.portfolio === form.value.portfolio) &&
    (h.ticker.toUpperCase() === t ||
     h.ticker.toUpperCase() === `${t}.BK` ||
     h.ticker.toUpperCase() === `${t}-USD`)
  )
})

function formatShares(shares: number | string): string {
  const n = Number(shares || 0)
  return n.toLocaleString('en-US', { maximumFractionDigits: 8 })
}

function setCurrency(curr: 'THB' | 'USD') {
  form.value.currency = curr
  manualCurrency.value = true
}

function setSearchAssetType(type: 'ALL' | 'STOCK' | 'CRYPTO' | 'FUND' | 'OTHER') {
  searchAssetType.value = type
  if (searchQuery.value.trim().length >= 1) {
    triggerSearch(searchQuery.value)
  }
}

function handleSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  const q = searchQuery.value.trim()
  if (!q) {
    searchResults.value = []
    isSearching.value = false
    return
  }

  isSearching.value = true
  debounceTimer = setTimeout(() => {
    triggerSearch(q)
  }, 250)
}

async function triggerSearch(q: string) {
  isSearching.value = true
  try {
    const results = await portfolioStore.searchAssets(q, searchAssetType.value)
    searchResults.value = results
    showSearchResults.value = true
  } catch (err) {
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

function selectAsset(item: MarketAssetSearchResult) {
  selectedAsset.value = item
  form.value.ticker = item.ticker
  form.value.currency = item.currency
  manualCurrency.value = false
  showSearchResults.value = false
  searchQuery.value = ''
  errorMessage.value = null

  // Pre-fill price from existing holding snapshot if available
  const existing = portfolioStore.holdings.find(h =>
    h.ticker.toUpperCase() === item.ticker.toUpperCase() ||
    h.ticker.toUpperCase() === `${item.ticker.toUpperCase()}.BK`
  )
  if (existing?.position?.current_price) {
    form.value.price_per_share = Number(existing.position.current_price)
  }
}

function clearSelectedAsset() {
  selectedAsset.value = null
  form.value.ticker = ''
  showSearchResults.value = false
}

const setMaxSell = () => {
  if (currentHolding.value) {
    form.value.shares = currentHolding.value.position.shares
  }
}

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      errorMessage.value = null
      manualCurrency.value = false
      searchQuery.value = ''
      searchResults.value = []
      showSearchResults.value = false
      selectedAsset.value = null

      // Set target portfolio default
      const defaultPortfolio = portfolioStore.portfolios.find(p => p.is_default) || portfolioStore.portfolios[0]
      const activePortfolioId = portfolioStore.selectedPortfolioId !== 'ALL'
        ? portfolioStore.selectedPortfolioId
        : (defaultPortfolio?.id || '')
      form.value.portfolio = activePortfolioId

      if (props.editingTransaction) {
        const tx = props.editingTransaction
        form.value.ticker = tx.holding_ticker || tx.ticker || ''
        form.value.currency = (tx.currency || tx.holding_currency || 'THB').toUpperCase() as 'THB' | 'USD'
        form.value.transaction_type = tx.transaction_type
        form.value.shares = Number(tx.shares)
        form.value.price_per_share = Number(tx.price_per_share)
        form.value.fee = Number(tx.fee || 0)
        // F07: Use toLocalInputDateTime to preserve local timezone offset
        form.value.executed_at = toLocalInputDateTime(tx.executed_at)
        form.value.notes = tx.notes || ''
        manualCurrency.value = true
      } else {
        form.value.ticker = props.prefillTicker || ''
        form.value.transaction_type = props.initialType || 'BUY'
        form.value.shares = null
        form.value.price_per_share = null
        form.value.fee = 0
        form.value.executed_at = getNowLocalDateTime()
        form.value.notes = ''

        // F05 & F09: Handle initial defaults when opened from Holding or Watchlist
        if (props.prefillHoldingId && currentHolding.value) {
          form.value.currency = (currentHolding.value.currency || 'THB').toUpperCase() as 'THB' | 'USD'
          if (currentHolding.value.portfolio) {
            form.value.portfolio = currentHolding.value.portfolio
          }
          if (currentHolding.value.position?.current_price) {
            form.value.price_per_share = Number(currentHolding.value.position.current_price)
          }
          selectedAsset.value = {
            ticker: currentHolding.value.ticker,
            name: currentHolding.value.name || currentHolding.value.ticker,
            currency: (currentHolding.value.currency === 'USD' ? 'USD' : 'THB'),
            asset_type: (currentHolding.value.asset_type || 'STOCK') as AssetType,
            exchange: currentHolding.value.ticker.endsWith('.BK') ? 'SET' : 'US'
          }
        } else if (props.prefillTicker) {
          const t = props.prefillTicker.trim().toUpperCase()
          form.value.ticker = t

          // Check if already held in this portfolio
          const held = currentHolding.value
          if (held) {
            form.value.currency = (held.currency || 'THB').toUpperCase() as 'THB' | 'USD'
            if (held.position?.current_price) {
              form.value.price_per_share = Number(held.position.current_price)
            }
            selectedAsset.value = {
              ticker: held.ticker,
              name: held.name || held.ticker,
              currency: (held.currency === 'USD' ? 'USD' : 'THB'),
              asset_type: (held.asset_type || 'STOCK') as AssetType,
              exchange: held.ticker.endsWith('.BK') ? 'SET' : 'US'
            }
          } else {
            // Check from watchlist
            const watch = portfolioStore.watchlist.find(w => w.ticker.toUpperCase() === t)
            if (watch) {
              selectedAsset.value = {
                ticker: watch.ticker,
                name: watch.name || watch.ticker,
                currency: (watch.currency === 'USD' ? 'USD' : 'THB'),
                asset_type: (watch.asset_type || 'STOCK') as AssetType,
                exchange: watch.ticker.endsWith('.BK') ? 'SET' : 'US'
              }
              form.value.currency = (watch.currency === 'USD' ? 'USD' : 'THB')
              if (watch.current_price) {
                form.value.price_per_share = Number(watch.current_price)
              }
            } else {
              selectedAsset.value = {
                ticker: t,
                name: t,
                currency: t.endsWith('.BK') ? 'THB' : 'USD',
                asset_type: t.includes('-USD') ? 'CRYPTO' : 'STOCK',
                exchange: t.endsWith('.BK') ? 'SET' : (t.includes('-USD') ? 'CRYPTO' : 'US')
              }
              form.value.currency = t.endsWith('.BK') ? 'THB' : 'USD'
            }
          }
        } else {
          form.value.currency = portfolioStore.displayCurrency
        }
      }
    }
  }
)

const estimatedTotal = computed(() => {
  const shares = Number(form.value.shares || 0)
  const price = Number(form.value.price_per_share || 0)
  const fee = Number(form.value.fee || 0)
  const subtotal = shares * price

  if (form.value.transaction_type === 'BUY') {
    return subtotal + fee
  } else {
    return Math.max(0, subtotal - fee)
  }
})

const formattedEstimatedTotal = computed(() => {
  const total = estimatedTotal.value
  if (total === 0) return '0.00'
  if (total < 1) {
    return total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 6 })
  }
  return total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const handleSubmit = async () => {
  errorMessage.value = null

  if (!props.editingTransaction && !props.prefillHoldingId && !form.value.ticker) {
    errorMessage.value = 'Please search and select a verified asset from the list'
    return
  }

  if (!form.value.shares || form.value.shares <= 0) {
    errorMessage.value = 'Units must be greater than 0'
    return
  }
  if (!form.value.price_per_share || form.value.price_per_share <= 0) {
    errorMessage.value = 'Price must be greater than 0'
    return
  }

  // Safety check on Sell: warn if exceeding holding
  if (form.value.transaction_type === 'SELL' && currentHolding.value && !props.editingTransaction) {
    if (form.value.shares > currentHolding.value.position.shares) {
      errorMessage.value = `Cannot sell ${form.value.shares} shares; you only hold ${currentHolding.value.position.shares} shares`
      return
    }
  }

  try {
    const payload: any = {
      transaction_type: form.value.transaction_type,
      shares: form.value.shares,
      price_per_share: form.value.price_per_share,
      fee: form.value.fee || 0,
      currency: form.value.currency,
      executed_at: new Date(form.value.executed_at).toISOString(),
      notes: form.value.notes
    }

    if (form.value.portfolio) {
      payload.portfolio = form.value.portfolio
    }

    if (props.editingTransaction) {
      await portfolioStore.updateTransaction(props.editingTransaction.id, payload)
    } else {
      if (props.prefillHoldingId) {
        payload.holding = props.prefillHoldingId
      } else {
        payload.ticker = form.value.ticker
      }
      await portfolioStore.addTransaction(payload)
    }

    emit('saved')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.ticker?.[0] ||
      err?.response?.data?.holding?.[0] ||
      err?.response?.data?.shares?.[0] ||
      err?.response?.data?.detail ||
      'Failed to record trade. Please check inputs.'
  }
}
</script>
