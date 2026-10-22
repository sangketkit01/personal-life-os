<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">System Overview</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            Operational
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">Logged in as {{ authStore.user?.username }} • Central command for obligations, assets, and tasks</p>
      </div>

      <div class="flex items-center gap-2.5">
        <RouterLink
          to="/finance"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <CreditCard class="w-3.5 h-3.5 text-zinc-400" />
          <span>Financial Radar</span>
        </RouterLink>
        <RouterLink
          to="/portfolio"
          class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5"
        >
          <TrendingUp class="w-3.5 h-3.5 text-zinc-950" />
          <span>Portfolio</span>
        </RouterLink>
      </div>
    </div>

    <!-- 4 Cloudflare Console Metric Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      <!-- 1. Monthly Burn Rate -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 relative">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Monthly Burn Rate</span>
          <span>Fixed</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            ฿{{ Number(financeStore.overview?.confirmed_burn_rate || 0).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
          <span class="text-[11px] text-zinc-500 font-mono">/ mo</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
          <span>Total committed fixed obligations</span>
        </div>
      </div>

      <!-- 2. Due in Next 7 Days -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 relative">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Due In 7 Days</span>
          <span>Upcoming</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ financeStore.overview?.upcoming_7_days_count || 0 }}
          </span>
          <span class="text-[11px] text-zinc-500 font-mono">items</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span
            class="w-1.5 h-1.5 rounded-full"
            :class="(financeStore.overview?.upcoming_7_days_count || 0) > 0 ? 'bg-amber-400' : 'bg-emerald-400'"
          />
          <span>{{ (financeStore.overview?.upcoming_7_days_count || 0) > 0 ? 'Pending settlements this week' : 'No upcoming payments' }}</span>
        </div>
      </div>

      <!-- 3. Free Trial Liability -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 relative">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Trial Liability</span>
          <span>Risk</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ financeStore.overview?.active_trials_count || 0 }}
          </span>
          <span class="text-[11px] text-zinc-500 font-mono">active trials</span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span
            class="w-1.5 h-1.5 rounded-full"
            :class="(financeStore.overview?.critical_trials_count || 0) > 0 ? 'bg-rose-400' : 'bg-zinc-500'"
          />
          <span>Potential risk: ฿{{ Number(financeStore.overview?.potential_risk_amount || 0).toLocaleString('th-TH') }}</span>
        </div>
      </div>

      <!-- 4. Portfolio Snapshot -->
      <RouterLink
        to="/portfolio"
        class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors block group relative"
      >
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Portfolio Value</span>
          <span
            class="font-mono text-[10px] tabular-nums"
            :class="Number(activePortfolioSummary.total_unrealized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          >
            {{ Number(activePortfolioSummary.total_unrealized_pnl || 0) >= 0 ? '+' : '' }}{{ Number(activePortfolioSummary.total_unrealized_pnl_pct || 0).toFixed(2) }}%
          </span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ portfolioStore.displayCurrency === 'USD' ? '$' : '฿' }}{{ Number(activePortfolioSummary.total_market_value || 0).toLocaleString(portfolioStore.displayCurrency === 'USD' ? 'en-US' : 'th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center justify-between border-t border-zinc-800/50 pt-2.5">
          <span class="flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
            <span>{{ portfolioStore.overview?.active_assets_count || 0 }} assets tracked</span>
          </span>
          <span class="text-[10px] font-mono text-zinc-400 group-hover:text-zinc-200 transition-colors">Details →</span>
        </div>
      </RouterLink>
    </div>

    <!-- Upcoming Settlements in 7 Days Table -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Calendar class="w-3.5 h-3.5 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Upcoming In 7 Days</h2>
        </div>
        <RouterLink to="/finance" class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors">
          View all in Radar →
        </RouterLink>
      </div>

      <div v-if="(financeStore.overview?.upcoming_7_days?.length || 0) === 0" class="p-8 text-center text-xs text-zinc-500 font-mono">
        No upcoming bills or trials requiring settlement within the next 7 days.
      </div>

      <div v-else class="divide-y divide-zinc-800/60 font-mono text-xs">
        <div
          v-for="bill in financeStore.overview?.upcoming_7_days"
          :key="bill.id"
          class="px-5 py-3 flex items-center justify-between hover:bg-zinc-900/40 transition-colors"
        >
          <div class="flex items-center gap-3">
            <span
              class="w-1.5 h-1.5 rounded-full shrink-0"
              :class="bill.days_left <= 1 ? 'bg-rose-400' : 'bg-amber-400'"
            />
            <div>
              <div class="text-xs font-medium text-zinc-200 font-sans">{{ bill.title }}</div>
              <div class="text-[10px] text-zinc-500">
                {{ bill.days_left === 0 ? 'Due today' : `Due in ${bill.days_left} day${bill.days_left > 1 ? 's' : ''}` }}
              </div>
            </div>
          </div>

          <div class="flex items-center gap-4">
            <span class="text-xs font-semibold text-zinc-100 tabular-nums">
              ฿{{ Number(bill.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
            </span>
            <RouterLink
              to="/finance"
              class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] font-sans text-zinc-300 transition-colors"
            >
              Manage
            </RouterLink>
          </div>
        </div>
      </div>
    </div>

    <!-- Today's Market Intelligence -->
    <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Newspaper class="w-3.5 h-3.5 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Today's Market Intelligence</h2>
        </div>
        <RouterLink to="/portfolio" class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors">
          View all in Portfolio →
        </RouterLink>
      </div>

      <div v-if="portfolioStore.isLoadingNews" class="p-8 text-center text-xs text-zinc-500 font-mono">
        <RefreshCw class="w-4 h-4 animate-spin mx-auto mb-2 text-zinc-400" />
        Loading today's headlines...
      </div>

      <div v-else-if="todayNews.length === 0" class="p-8 text-center text-xs text-zinc-500 font-mono">
        No market news recorded for today yet.
        <RouterLink to="/portfolio" class="text-zinc-300 underline ml-1 hover:text-white">
          Go to Portfolio to sync
        </RouterLink>
      </div>

      <div v-else class="divide-y divide-zinc-800/60 font-sans">
        <div
          v-for="article in todayNews.slice(0, 4)"
          :key="article.id"
          class="p-4 hover:bg-zinc-900/40 transition-colors"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-1.5">
            <div class="flex flex-wrap items-center gap-2">
              <button
                @click="goToAssetDetail(article.ticker)"
                class="px-1.5 py-0.5 rounded text-[10px] font-bold font-mono bg-zinc-800 hover:bg-zinc-700 text-blue-400 hover:text-blue-300 border border-zinc-700/60 transition-colors"
                title="คลิกเพื่อดูหน้าสินทรัพย์"
              >
                ${{ article.ticker }}
              </button>
              <span class="text-[10px] font-mono text-zinc-500 uppercase">
                {{ article.source }}
              </span>
              <span
                class="px-1.5 py-0.2 rounded text-[9px] font-mono font-medium uppercase border"
                :class="getSentimentClass(article.sentiment)"
              >
                {{ article.sentiment }}
              </span>
              <span class="text-[10px] text-zinc-500 font-mono">
                {{ formatDateTime(article.published_at) }}
              </span>
            </div>

            <div class="flex items-center gap-2">
              <!-- Per-card EN / TH toggle -->
              <div class="inline-flex rounded bg-zinc-900 border border-zinc-800 p-0.5 text-[9px] font-mono">
                <button
                  @click="articleLangMap[article.id] = 'EN'"
                  class="px-1.5 py-0.2 rounded transition-colors"
                  :class="(articleLangMap[article.id] || 'EN') === 'EN' ? 'bg-zinc-800 text-zinc-100 font-bold' : 'text-zinc-500 hover:text-zinc-300'"
                >
                  EN
                </button>
                <button
                  @click="toggleThaiLang(article)"
                  :disabled="translatingIds.has(article.id)"
                  class="px-1.5 py-0.2 rounded transition-colors flex items-center gap-1"
                  :class="(articleLangMap[article.id] || 'EN') === 'TH' ? 'bg-zinc-800 text-zinc-100 font-bold' : 'text-zinc-500 hover:text-zinc-300'"
                >
                  <span>TH</span>
                  <RefreshCw v-if="translatingIds.has(article.id)" class="w-2 h-2 animate-spin" />
                </button>
              </div>

              <a
                :href="article.url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-zinc-500 hover:text-zinc-200 p-1"
                title="เว็บข่าวต้นฉบับภายนอก"
              >
                <ExternalLink class="w-3 h-3" />
              </a>
            </div>
          </div>

          <div class="mt-1 space-y-1">
            <h4
              @click="goToNewsDetail(article.id)"
              class="text-xs font-semibold text-zinc-200 leading-snug cursor-pointer hover:text-blue-400 transition-colors"
            >
              {{ (articleLangMap[article.id] === 'TH' && article.title_th) ? article.title_th : article.title }}
            </h4>
            <p
              v-if="getSummary(article)"
              @click="goToNewsDetail(article.id)"
              class="text-[11px] text-zinc-400 mt-1 line-clamp-2 cursor-pointer hover:text-zinc-300 transition-colors"
            >
              {{ getSummary(article) }}
            </p>
          </div>

          <!-- Read Full Article Action Link -->
          <div class="mt-2.5 flex items-center justify-between">
            <button
              @click="goToNewsDetail(article.id)"
              class="inline-flex items-center gap-1 text-[11px] font-mono text-blue-400 hover:text-blue-300 font-semibold transition-colors group"
            >
              <span>อ่านข่าวฉบับเต็ม & สรุป AI</span>
              <span class="group-hover:translate-x-0.5 transition-transform">→</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Navigation Panels -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Left: Financial Radar Highlights -->
      <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
        <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <CreditCard class="w-3.5 h-3.5 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Obligations Breakdown</h2>
          </div>
          <RouterLink to="/finance" class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors">
            Open Radar →
          </RouterLink>
        </div>

        <div class="p-4 space-y-2 text-xs">
          <div class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-between">
            <span class="text-zinc-400 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-zinc-500"></span>
              Installment Schedules
            </span>
            <span class="font-mono text-zinc-200 font-medium">
              {{ financeStore.overview?.items_by_type?.INSTALLMENT?.length || 0 }} items
            </span>
          </div>

          <div class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-between">
            <span class="text-zinc-400 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-zinc-500"></span>
              Free Trial Alerts
            </span>
            <span class="font-mono text-zinc-200 font-medium">
              {{ financeStore.overview?.items_by_type?.FREE_TRIAL?.length || 0 }} items
            </span>
          </div>

          <div class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-between">
            <span class="text-zinc-400 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-zinc-500"></span>
              Subscriptions
            </span>
            <span class="font-mono text-zinc-200 font-medium">
              {{ financeStore.overview?.items_by_type?.SUBSCRIPTION?.length || 0 }} items
            </span>
          </div>

          <div class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-between">
            <span class="text-zinc-400 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-zinc-500"></span>
              Debt Settlements
            </span>
            <span class="font-mono text-zinc-200 font-medium">
              {{ financeStore.overview?.items_by_type?.DEBT?.length || 0 }} items
            </span>
          </div>
        </div>
      </div>

      <!-- Right: Workspace Pipeline Highlights -->
      <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
        <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <FolderKanban class="w-3.5 h-3.5 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Document Pipeline</h2>
          </div>
          <RouterLink to="/workspace" class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors">
            Open Board →
          </RouterLink>
        </div>

        <div class="p-4 space-y-2 text-xs">
          <div class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-between">
            <span class="text-zinc-400 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
              Drafting Deliverables
            </span>
            <span class="font-mono text-zinc-200 font-medium">
              {{ workspaceStore.overview?.pipeline_counts?.drafting || 0 }} tasks
            </span>
          </div>

          <div class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-between">
            <span class="text-zinc-400 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
              Waiting / Client Review
            </span>
            <span class="font-mono text-zinc-200 font-medium">
              {{ workspaceStore.overview?.pipeline_counts?.waiting || 0 }} tasks
            </span>
          </div>

          <div class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-between">
            <span class="text-zinc-400 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Completed Documents
            </span>
            <span class="font-mono text-zinc-200 font-medium">
              {{ workspaceStore.overview?.pipeline_counts?.completed || 0 }} tasks
            </span>
          </div>

          <div class="p-2.5 rounded bg-zinc-900/60 border border-zinc-800/60 flex items-center justify-between">
            <span class="text-zinc-400 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
              Upcoming Deadlines (7 Days)
            </span>
            <span class="font-mono text-zinc-200 font-medium">
              {{ workspaceStore.overview?.upcoming_deadlines_count || 0 }} deadlines
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useFinanceStore } from '../stores/finance'
import { useWorkspaceStore } from '../stores/workspace'
import { usePortfolioStore } from '../stores/portfolio'
import { useToastStore } from '../stores/toast'
import type { StockNewsArticle } from '../types/portfolio'
import {
  CreditCard,
  TrendingUp,
  FolderKanban,
  Calendar,
  Newspaper,
  ExternalLink,
  RefreshCw
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()
const financeStore = useFinanceStore()
const workspaceStore = useWorkspaceStore()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const todayNews = ref<StockNewsArticle[]>([])
const articleLangMap = reactive<Record<string, 'EN' | 'TH'>>({})
const translatingIds = reactive(new Set<string>())

const activePortfolioSummary = computed(() => {
  if (portfolioStore.displayCurrency === 'USD') {
    return portfolioStore.overview?.summary_usd || {
      total_market_value: 0,
      total_unrealized_pnl: 0,
      total_unrealized_pnl_pct: 0
    }
  }
  return portfolioStore.overview?.summary_thb || {
    total_market_value: 0,
    total_unrealized_pnl: 0,
    total_unrealized_pnl_pct: 0
  }
})

function getSentimentClass(sentiment: string) {
  switch (sentiment) {
    case 'BULLISH':
      return 'bg-emerald-950/30 text-emerald-400 border-emerald-500/30'
    case 'BEARISH':
      return 'bg-rose-950/30 text-rose-400 border-rose-500/30'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

function formatDateTime(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getSummary(article: StockNewsArticle): string {
  if (articleLangMap[article.id] === 'TH' && article.summary_th) {
    return article.summary_th
  }
  return article.summary || ''
}

async function toggleThaiLang(article: StockNewsArticle) {
  if (articleLangMap[article.id] === 'TH') return
  if (article.title_th) {
    articleLangMap[article.id] = 'TH'
    return
  }
  translatingIds.add(article.id)
  try {
    const updated = await portfolioStore.translateArticle(article.id)
    const idx = todayNews.value.findIndex(a => a.id === article.id)
    if (idx !== -1) {
      todayNews.value[idx] = updated
    }
    articleLangMap[article.id] = 'TH'
  } catch (err) {
    toast.error('Failed to translate headline')
  } finally {
    translatingIds.delete(article.id)
  }
}

function goToNewsDetail(articleId: string) {
  if (!articleId) return
  router.push(`/portfolio/news/${articleId}`)
}

function goToAssetDetail(ticker: string) {
  if (!ticker) return
  router.push(`/portfolio/asset/${encodeURIComponent(ticker)}`)
}

onMounted(async () => {
  await Promise.allSettled([
    financeStore.fetchOverview(),
    workspaceStore.fetchOverview(),
    portfolioStore.fetchOverview(),
    (async () => {
      try {
        let res = await portfolioStore.fetchNews({ today_only: true, held_only: true })
        if (!res || res.length === 0) {
          res = await portfolioStore.fetchNews({ held_only: true })
        }
        todayNews.value = res || []
      } catch (err) {
        console.error('Failed to load today news', err)
      }
    })()
  ])
})
</script>
