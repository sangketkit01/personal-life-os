<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Market Intelligence & News</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            AI SENTIMENT & TRANSLATION
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">
          Global financial news filtered by your held assets and watchlist, with LLM Thai summary and sentiment analysis
        </p>
      </div>

      <div class="flex items-center gap-2.5 self-start sm:self-auto">
        <button
          @click="handleSyncNews"
          :disabled="isSyncing"
          class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-xs font-medium text-zinc-200 transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': isSyncing }" />
          <span>{{ isSyncing ? 'Crawling & Analyzing...' : 'Sync Market News' }}</span>
        </button>
      </div>
    </div>

    <!-- Live Market Session & Currency Bar -->
    <MarketStatusBar />

    <!-- Filter & Scope Strip -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-3.5">
      <!-- Left: Scope Pills -->
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex items-center bg-zinc-950/80 border border-zinc-800/80 rounded-md p-0.5">
          <button
            @click="selectScope('ALL')"
            type="button"
            class="px-2.5 py-1 rounded text-[11px] font-mono transition-colors"
            :class="newsScope === 'ALL' ? 'bg-zinc-800 text-zinc-100 font-semibold shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
          >
            All Market
          </button>
          <button
            @click="selectScope('HELD')"
            type="button"
            class="px-2.5 py-1 rounded text-[11px] font-mono transition-colors"
            :class="newsScope === 'HELD' ? 'bg-zinc-800 text-zinc-100 font-semibold shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
          >
            My Holdings
          </button>
          <button
            @click="selectScope('WATCHLIST')"
            type="button"
            class="px-2.5 py-1 rounded text-[11px] font-mono transition-colors"
            :class="newsScope === 'WATCHLIST' ? 'bg-zinc-800 text-zinc-100 font-semibold shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
          >
            Watchlist
          </button>
        </div>

        <!-- Today Only Toggle -->
        <label class="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer select-none ml-2">
          <input
            type="checkbox"
            v-model="isTodayOnly"
            @change="handleFilterChange"
            class="rounded bg-zinc-900 border-zinc-700 text-zinc-100 accent-zinc-600 focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5"
          />
          <span class="text-[11px] font-mono">Today Only</span>
        </label>
      </div>

      <!-- Right: Search by Ticker -->
      <div class="flex items-center gap-2">
        <div class="relative w-full md:w-56">
          <Search class="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            v-model="searchTickerQuery"
            @keydown.enter.prevent="handleSearchTicker"
            type="text"
            placeholder="Filter ticker (e.g. NVDA)..."
            class="w-full pl-8 pr-7 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 font-mono outline-none focus:border-zinc-700"
          />
          <button
            v-if="searchTickerQuery"
            @click="clearTickerSearch"
            type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
        <button
          @click="handleSearchTicker"
          type="button"
          class="px-2.5 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-mono"
        >
          Filter
        </button>
      </div>
    </div>

    <!-- Active Filter Tag (if ticker selected) -->
    <div v-if="selectedTicker" class="flex items-center gap-2 text-xs font-mono">
      <span class="text-zinc-500">Filtered by asset:</span>
      <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-900 text-zinc-200 border border-zinc-800">
        <span>{{ selectedTicker }}</span>
        <button @click="clearTickerSearch" class="hover:text-white">
          <X class="w-3 h-3" />
        </button>
      </span>
    </div>

    <!-- News Feed List -->
    <div v-if="isLoading && portfolioStore.news.length === 0" class="p-2">
      <SkeletonLoader variant="list" :count="5" />
    </div>

    <div v-else-if="portfolioStore.news.length > 0" class="space-y-3">
      <div
        v-for="article in portfolioStore.news"
        :key="article.id"
        class="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800/80 hover:border-zinc-700 transition-all hover:bg-zinc-900/50 group"
      >
        <!-- Top Meta: Source, Time, Sentiment, Language Switcher -->
        <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
          <div class="flex items-center gap-2 flex-wrap">
            <!-- Source Tag -->
            <span class="font-mono text-[10px] text-zinc-400 bg-zinc-900 border border-zinc-800 px-2 py-0.5 rounded">
              {{ article.source || 'MarketWire' }}
            </span>

            <!-- Published Date -->
            <span class="text-zinc-500 text-[11px] font-mono">
              {{ formatDateTime(article.published_at) }}
            </span>

            <!-- Sentiment Badge -->
            <span
              v-if="article.sentiment"
              class="text-[9px] font-mono px-2 py-0.5 rounded border uppercase font-semibold flex items-center gap-1"
              :class="getSentimentClass(article.sentiment)"
            >
              <span>{{ getSentimentEmoji(article.sentiment) }}</span>
              <span>{{ article.sentiment }}</span>
            </span>
          </div>

          <!-- Language Selector (EN / TH) -->
          <div class="flex items-center gap-1 bg-zinc-950 border border-zinc-800 rounded p-0.5 text-[10px] font-mono">
            <button
              @click="setArticleLang(article.id, 'EN')"
              type="button"
              class="px-1.5 py-0.5 rounded transition-colors"
              :class="getArticleLang(article) === 'EN' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
            >
              EN
            </button>
            <button
              @click="toggleThaiLang(article)"
              :disabled="translatingIds.has(article.id)"
              type="button"
              class="px-1.5 py-0.5 rounded transition-colors flex items-center gap-1"
              :class="getArticleLang(article) === 'TH' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
            >
              <Loader2 v-if="translatingIds.has(article.id)" class="w-2.5 h-2.5 animate-spin" />
              <span>TH</span>
            </button>
          </div>
        </div>

        <!-- Headline -->
        <h3
          @click="goToNewsDetail(article.id)"
          class="font-semibold text-sm text-zinc-100 hover:text-zinc-300 cursor-pointer transition-colors mt-2 leading-snug"
        >
          {{ getArticleTitle(article) }}
        </h3>

        <!-- Summary -->
        <p class="text-xs text-zinc-400 mt-1.5 leading-relaxed line-clamp-3 font-sans">
          {{ getArticleSummary(article) }}
        </p>

        <!-- Bottom Bar: Tickers & Detail Link -->
        <div class="mt-3.5 pt-2.5 border-t border-zinc-800/60 flex items-center justify-between gap-3 text-xs">
          <!-- Ticker tag -->
          <div class="flex items-center gap-1.5 flex-wrap">
            <button
              v-if="article.ticker"
              @click="selectFilterTicker(article.ticker)"
              type="button"
              class="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-zinc-800 transition-colors"
            >
              ${{ article.ticker }}
            </button>
          </div>

          <div class="flex items-center gap-3 shrink-0">
            <a
              v-if="article.url"
              :href="article.url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-zinc-500 hover:text-zinc-300 text-[11px] flex items-center gap-1"
            >
              <span>Source</span>
              <ExternalLink class="w-3 h-3" />
            </a>

            <button
              @click="goToNewsDetail(article.id)"
              class="text-zinc-300 hover:text-white text-xs font-medium flex items-center gap-1 group-hover:underline"
            >
              <span>Full Analysis</span>
              <ArrowRight class="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="p-12 text-center text-xs font-mono text-zinc-500 bg-zinc-900/20 border border-zinc-800/80 rounded-xl">
      <div class="flex flex-col items-center justify-center gap-2">
        <Newspaper class="w-6 h-6 text-zinc-600" />
        <p>No news articles found for this filter criteria</p>
        <button
          @click="handleSyncNews"
          type="button"
          class="mt-2 px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-semibold text-xs"
        >
          Sync Latest Market News
        </button>
      </div>
    </div>

    <!-- Pagination Controls -->
    <div v-if="portfolioStore.newsTotalCount > 50" class="flex items-center justify-between text-xs font-mono pt-2">
      <span class="text-zinc-500">
        Page {{ currentNewsPage }} of {{ totalNewsPages }} ({{ portfolioStore.newsTotalCount }} articles)
      </span>
      <div class="flex items-center gap-2">
        <button
          @click="changeNewsPage(currentNewsPage - 1)"
          :disabled="currentNewsPage <= 1"
          class="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white disabled:opacity-50"
        >
          Previous
        </button>
        <button
          @click="changeNewsPage(currentNewsPage + 1)"
          :disabled="currentNewsPage >= totalNewsPages"
          class="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import SkeletonLoader from '../../components/common/SkeletonLoader.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { locale } from '../../i18n'
import { useToastStore } from '../../stores/toast'
import MarketStatusBar from '../../components/portfolio/MarketStatusBar.vue'
import type { StockNewsArticle } from '../../types/portfolio'
import {
  Newspaper,
  RefreshCw,
  Search,
  X,
  ExternalLink,
  ArrowRight,
  Loader2
} from 'lucide-vue-next'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const newsScope = ref<'ALL' | 'HELD' | 'WATCHLIST'>('ALL')
const searchTickerQuery = ref('')
const selectedTicker = ref<string | null>(null)
const isTodayOnly = ref(false)
const currentNewsPage = ref(1)
const isSyncing = ref(false)
const isLoading = ref(false)

const articleLangMap = reactive<Record<string, 'EN' | 'TH'>>({})
const translatingIds = reactive(new Set<string>())

const totalNewsPages = computed(() => {
  return Math.ceil(portfolioStore.newsTotalCount / 50) || 1
})

function formatDateTime(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getSentimentClass(sentiment: string) {
  switch (sentiment) {
    case 'BULLISH':
      return 'bg-zinc-900 text-emerald-400 border-zinc-800'
    case 'BEARISH':
      return 'bg-zinc-900 text-rose-400 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

function getSentimentEmoji(sentiment: string) {
  switch (sentiment) {
    case 'BULLISH':
      return '▲'
    case 'BEARISH':
      return '▼'
    default:
      return '•'
  }
}

function getArticleLang(article: StockNewsArticle): 'EN' | 'TH' {
  if (articleLangMap[article.id]) return articleLangMap[article.id]
  // Default to the active app locale - TH only when a Thai translation exists
  if (locale.value === 'th' && (article.title_th || article.summary_th)) return 'TH'
  return 'EN'
}

function setArticleLang(id: string, lang: 'EN' | 'TH') {
  articleLangMap[id] = lang
}

async function toggleThaiLang(article: StockNewsArticle) {
  if (articleLangMap[article.id] === 'TH') return
  if (article.title_th) {
    articleLangMap[article.id] = 'TH'
    return
  }
  translatingIds.add(article.id)
  try {
    await portfolioStore.translateArticle(article.id)
    articleLangMap[article.id] = 'TH'
  } catch {
    toast.error('Failed to translate article to Thai')
  } finally {
    translatingIds.delete(article.id)
  }
}

function getArticleTitle(article: StockNewsArticle): string {
  if (getArticleLang(article) === 'TH' && article.title_th) {
    return article.title_th
  }
  return article.title
}

function getArticleSummary(article: StockNewsArticle): string {
  if (getArticleLang(article) === 'TH' && article.summary_th) {
    return article.summary_th
  }
  return article.summary || ''
}

async function loadNews() {
  isLoading.value = true
  try {
    const params: any = {
      today_only: isTodayOnly.value,
      page: currentNewsPage.value
    }
    if (selectedTicker.value) {
      params.ticker = selectedTicker.value
    } else if (newsScope.value === 'WATCHLIST') {
      params.watchlist_only = true
    } else if (newsScope.value === 'HELD') {
      params.held_only = true
    }
    await portfolioStore.fetchNews(params)
  } finally {
    isLoading.value = false
  }
}

async function selectScope(scope: 'ALL' | 'HELD' | 'WATCHLIST') {
  newsScope.value = scope
  selectedTicker.value = null
  searchTickerQuery.value = ''
  currentNewsPage.value = 1
  await loadNews()
}

async function handleSearchTicker() {
  const t = searchTickerQuery.value.trim().toUpperCase()
  if (!t) {
    selectedTicker.value = null
  } else {
    selectedTicker.value = t
  }
  currentNewsPage.value = 1
  await loadNews()
}

function selectFilterTicker(ticker: string) {
  selectedTicker.value = ticker
  searchTickerQuery.value = ticker
  currentNewsPage.value = 1
  loadNews()
}

function clearTickerSearch() {
  selectedTicker.value = null
  searchTickerQuery.value = ''
  currentNewsPage.value = 1
  loadNews()
}

function handleFilterChange() {
  currentNewsPage.value = 1
  loadNews()
}

function changeNewsPage(page: number) {
  currentNewsPage.value = page
  loadNews()
}

async function handleSyncNews() {
  isSyncing.value = true
  try {
    await portfolioStore.syncNews()
    toast.success('Market news synchronized with AI sentiment')
    await loadNews()
  } catch {
    toast.error('Failed to sync market news')
  } finally {
    isSyncing.value = false
  }
}

function goToNewsDetail(articleId: string) {
  router.push(`/portfolio/news/${articleId}`)
}

onMounted(async () => {
  await Promise.all([
    loadNews(),
    portfolioStore.fetchMarketStatus()
  ])
})
</script>
