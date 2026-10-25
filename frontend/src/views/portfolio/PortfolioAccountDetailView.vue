<template>
  <div class="max-w-7xl mx-auto space-y-6 font-sans">
    <!-- Top Bar: Back Link, Account Identity & Master Actions -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          @click="router.push('/portfolio/accounts')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Brokerage Accounts"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>

        <div>
          <div class="flex items-center gap-2">
            <span
              v-if="currentPortfolio"
              class="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
              :style="{ backgroundColor: getPortfolioColor(currentPortfolio.color) }"
            ></span>
            <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 font-semibold">
              {{ currentPortfolio?.currency || 'THB' }} ACCOUNT
            </span>
            <h1 class="text-lg font-semibold text-zinc-100 tracking-tight font-sans">
              {{ currentPortfolio?.name || 'Brokerage Account Dossier' }}
            </h1>
            <span
              v-if="currentPortfolio?.is_default"
              class="text-[9px] font-mono px-2 py-0.2 rounded border uppercase font-medium bg-zinc-900 text-zinc-300 border-zinc-700"
            >
              DEFAULT
            </span>
          </div>
          <div class="flex items-center gap-3 text-xs text-zinc-500 font-mono mt-0.5">
            <span>{{ accountOverview?.holdings?.length || 0 }} asset positions</span>
            <span>Created: {{ currentPortfolio?.created_at ? new Date(currentPortfolio.created_at).toLocaleDateString('en-GB') : '-' }}</span>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center gap-2 self-start sm:self-auto">
        <button
          @click="openEditModal"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Edit Account Details"
        >
          <Edit2 class="w-4 h-4" />
        </button>

        <button
          v-if="!currentPortfolio?.is_default"
          @click="confirmDeletePortfolio"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-500 hover:text-rose-400 transition-colors"
          title="Delete Account"
        >
          <Trash2 class="w-4 h-4" />
        </button>

        <button
          @click="openAddTradeModal"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>Record Trade</span>
        </button>
      </div>
    </div>

    <!-- Live Market Session & Currency Bar -->
    <MarketStatusBar />

    <div v-if="isLoading" class="p-16 text-center text-xs font-mono text-zinc-500">
      Loading account dossier and positions...
    </div>

    <div v-else-if="currentPortfolio" class="space-y-6">
      <!-- 4 Key High-Contrast Metrics Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <!-- Card 1: Total Portfolio Market Value -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Total Market Value</span>
          <div class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ curSymbol }}{{ Number(accountOverview?.total_market_value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">Current liquidated value</span>
        </div>

        <!-- Card 2: Total Invested Cost -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Total Invested Cost</span>
          <div class="text-xl font-semibold font-mono text-zinc-300 tabular-nums">
            {{ curSymbol }}{{ Number(accountOverview?.total_cost_basis || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">Weighted DCA capital invested</span>
        </div>

        <!-- Card 3: Unrealized Profit / Loss -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono uppercase text-zinc-500 block">Unrealized PnL</span>
            <span
              class="text-[10px] font-mono font-semibold"
              :class="(accountOverview?.total_unrealized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
            >
              {{ (accountOverview?.total_unrealized_pnl || 0) >= 0 ? '+' : '' }}{{ (accountOverview?.total_unrealized_pnl_pct || 0).toFixed(2) }}%
            </span>
          </div>
          <div
            class="text-xl font-semibold font-mono tabular-nums"
            :class="(accountOverview?.total_unrealized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          >
            {{ (accountOverview?.total_unrealized_pnl || 0) >= 0 ? '+' : '' }}{{ curSymbol }}{{ Number(accountOverview?.total_unrealized_pnl || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">Unrealized open return</span>
        </div>

        <!-- Card 4: Realized Return & Dividends -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono uppercase text-zinc-500 block">Realized & Dividends</span>
            <span class="text-[10px] font-mono text-zinc-500">
              Closed
            </span>
          </div>
          <div class="text-xl font-semibold font-mono text-zinc-200 tabular-nums">
            +{{ curSymbol }}{{ Number((accountOverview?.total_realized_pnl || 0) + (accountOverview?.total_dividends || 0)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">
            Dividends: {{ curSymbol }}{{ Number(accountOverview?.total_dividends || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </span>
        </div>
      </div>

      <!-- Segmented Workspace Tabs -->
      <div class="border-b border-zinc-800/80">
        <div class="flex items-center gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="px-4 py-2 text-xs font-mono transition-colors border-b-2 flex items-center gap-2"
            :class="[
              activeTab === tab.id
                ? 'border-zinc-200 text-zinc-100 font-semibold bg-zinc-900/30'
                : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/20'
            ]"
          >
            <component :is="tab.icon" class="w-3.5 h-3.5" />
            <span>{{ tab.label }}</span>
            <span
              v-if="tab.badge"
              class="px-1.5 py-0.2 rounded text-[10px] font-mono bg-zinc-900 border border-zinc-800 text-zinc-400"
            >
              {{ tab.badge }}
            </span>
          </button>
        </div>
      </div>

      <!-- TAB 1: HOLDINGS POSITION LEDGER -->
      <div v-if="activeTab === 'HOLDINGS'" class="space-y-4">
        <!-- Filter Bar -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/80">
          <div class="flex items-center gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-lg">
            <button
              v-for="aType in ['ALL', 'STOCK', 'CRYPTO', 'FUND']"
              :key="aType"
              @click="selectedAssetFilter = aType"
              class="px-2.5 py-1 rounded text-xs font-mono transition-colors"
              :class="selectedAssetFilter === aType ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
            >
              {{ aType }}
            </button>
          </div>

          <button
            @click="openAddTradeModal"
            class="px-3 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm self-start sm:self-auto"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>Add Position</span>
          </button>
        </div>

        <!-- Holdings Table -->
        <div v-if="filteredHoldings.length === 0" class="p-12 text-center text-xs font-mono text-zinc-500 bg-zinc-900/20 rounded-xl border border-zinc-800 space-y-2">
          <p>No active asset holdings recorded in this brokerage account.</p>
          <button
            @click="openAddTradeModal"
            class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-sans text-xs transition-colors"
          >
            + Record First Buy Trade
          </button>
        </div>

        <div v-else class="rounded-xl border border-zinc-800/80 overflow-hidden bg-zinc-900/30 shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs font-mono">
              <thead>
                <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-950/40">
                  <th class="py-2.5 pl-4">Asset / Ticker</th>
                  <th class="py-2.5">Type</th>
                  <th class="py-2.5 text-right">Shares / Units</th>
                  <th class="py-2.5 text-right">Avg Cost</th>
                  <th class="py-2.5 text-right">Market Price</th>
                  <th class="py-2.5 text-right">Current Value</th>
                  <th class="py-2.5 text-right">Unrealized PnL</th>
                  <th class="py-2.5 text-right pr-4">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/50">
                <tr
                  v-for="h in filteredHoldings"
                  :key="h.id"
                  class="hover:bg-zinc-900/40 transition-colors"
                >
                  <td class="py-3 pl-4">
                    <RouterLink
                      :to="`/portfolio/asset/${h.ticker}`"
                      class="font-semibold text-zinc-100 hover:underline flex items-center gap-1.5"
                    >
                      <span>{{ h.ticker }}</span>
                      <ExternalLink class="w-3 h-3 text-zinc-500" />
                    </RouterLink>
                    <div class="text-[10px] text-zinc-500 truncate max-w-xs">{{ h.name || h.ticker }}</div>
                  </td>
                  <td class="py-3">
                    <span class="text-[9px] uppercase px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
                      {{ h.asset_type }}
                    </span>
                  </td>
                  <td class="py-3 text-right font-medium text-zinc-200 tabular-nums">
                    {{ Number(h.position?.shares || 0).toLocaleString('en-US', { maximumFractionDigits: 6 }) }}
                  </td>
                  <td class="py-3 text-right text-zinc-400 tabular-nums">
                    {{ curSymbol }}{{ Number(h.position?.avg_cost || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) }}
                  </td>
                  <td class="py-3 text-right font-medium text-zinc-200 tabular-nums">
                    {{ curSymbol }}{{ Number(h.position?.current_price || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) }}
                  </td>
                  <td class="py-3 text-right font-semibold text-zinc-100 tabular-nums">
                    {{ curSymbol }}{{ Number(h.position?.market_value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-3 text-right tabular-nums">
                    <div
                      class="font-semibold"
                      :class="(h.position?.unrealized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
                    >
                      {{ (h.position?.unrealized_pnl || 0) >= 0 ? '+' : '' }}{{ curSymbol }}{{ Number(h.position?.unrealized_pnl || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                    </div>
                    <div class="text-[10px] text-zinc-500">
                      {{ (h.position?.unrealized_pnl_pct || 0) >= 0 ? '+' : '' }}{{ (h.position?.unrealized_pnl_pct || 0).toFixed(2) }}%
                    </div>
                  </td>
                  <td class="py-3 text-right pr-4">
                    <div class="flex items-center justify-end gap-1.5">
                      <button
                        @click="openAddTradeModalForHolding(h)"
                        class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-[10px] transition-colors"
                        title="Trade this ticker"
                      >
                        Trade
                      </button>
                      <button
                        @click="openMoveModal(h)"
                        class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
                        title="Move to another brokerage"
                      >
                        <ArrowRightLeft class="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 2: TRADE EXECUTIONS HISTORY -->
      <div v-if="activeTab === 'EXECUTIONS'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/60">
            <div>
              <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Executed Transactions Audit Log
              </h3>
              <p class="text-xs text-zinc-500 mt-0.5">
                All order fills, sales, and dividend credits booked into {{ currentPortfolio.name }}.
              </p>
            </div>

            <button
              @click="openAddTradeModal"
              class="px-3.5 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Plus class="w-3.5 h-3.5 text-zinc-950" />
              <span>Record Trade</span>
            </button>
          </div>

          <div v-if="portfolioTransactions.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500 bg-zinc-950/40 rounded-lg border border-zinc-800">
            No transaction records executed in this portfolio yet.
          </div>

          <div v-else class="rounded-lg border border-zinc-800 overflow-hidden bg-zinc-950/60">
            <div class="overflow-x-auto">
            <table class="w-full text-left text-xs font-mono">
              <thead>
                <tr class="border-b border-zinc-800 text-[10px] text-zinc-500 uppercase tracking-wider bg-zinc-950">
                  <th class="py-2.5 pl-4">Executed Date</th>
                  <th class="py-2.5">Action</th>
                  <th class="py-2.5">Asset</th>
                  <th class="py-2.5 text-right">Shares</th>
                  <th class="py-2.5 text-right">Price</th>
                  <th class="py-2.5 text-right">Fee</th>
                  <th class="py-2.5 text-right">Net Value</th>
                  <th class="py-2.5 text-right pr-4">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/60">
                <tr
                  v-for="tx in portfolioTransactions"
                  :key="tx.id"
                  class="hover:bg-zinc-900/30 transition-colors"
                >
                  <td class="py-2.5 pl-4 text-zinc-400">
                    {{ new Date(tx.executed_at).toLocaleString('en-GB') }}
                  </td>
                  <td class="py-2.5">
                    <span
                      class="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border font-semibold"
                      :class="tx.transaction_type === 'BUY'
                        ? 'bg-zinc-900 text-emerald-400 border-emerald-500/30'
                        : (tx.transaction_type === 'SELL' ? 'bg-zinc-900 text-rose-400 border-rose-500/30' : 'bg-zinc-900 text-zinc-300 border-zinc-700')"
                    >
                      {{ tx.transaction_type }}
                    </span>
                  </td>
                  <td class="py-2.5 font-semibold text-zinc-200">
                    {{ tx.holding_ticker || tx.ticker }}
                  </td>
                  <td class="py-2.5 text-right text-zinc-300 tabular-nums">
                    {{ Number(tx.shares).toLocaleString('en-US', { maximumFractionDigits: 6 }) }}
                  </td>
                  <td class="py-2.5 text-right text-zinc-400 tabular-nums">
                    {{ curSymbol }}{{ Number(tx.price_per_share).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) }}
                  </td>
                  <td class="py-2.5 text-right text-zinc-500 tabular-nums">
                    {{ curSymbol }}{{ Number(tx.fee || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-2.5 text-right font-semibold text-zinc-100 tabular-nums">
                    {{ curSymbol }}{{ Number((Number(tx.shares) * Number(tx.price_per_share)) + Number(tx.fee || 0)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-2.5 text-right pr-4">
                    <button
                      @click="handleDeleteTransaction(tx.id)"
                      class="p-1 rounded text-zinc-500 hover:text-rose-400 transition-colors"
                      title="Delete Trade"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 3: STRATEGY & ACCOUNT THESIS -->
      <div v-if="activeTab === 'STRATEGY'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="pb-3 border-b border-zinc-800/60">
            <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Brokerage Strategy & Parameters
            </h3>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Account Name</span>
              <span class="text-zinc-200 font-semibold">{{ currentPortfolio.name }}</span>
            </div>
            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Base Currency</span>
              <span class="text-zinc-200 font-semibold">{{ currentPortfolio.currency }}</span>
            </div>
            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Account Type</span>
              <span class="text-zinc-200">{{ currentPortfolio.is_default ? 'Primary Main Portfolio' : 'Sub-Account Basket' }}</span>
            </div>
          </div>

          <div class="p-4 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1 font-mono text-xs">
            <span class="text-[10px] text-zinc-500 uppercase block">Investment Strategy Thesis</span>
            <p class="text-zinc-300 font-sans leading-relaxed">
              {{ currentPortfolio.description || 'No strategic mandate defined yet for this account basket. Click edit to document DCA goals and risk parameters.' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <AddTransactionModal
      :is-open="showAddModal"
      :prefill-portfolio-id="accountId"
      :prefill-ticker="selectedHoldingForTrade?.ticker"
      :prefill-holding-id="selectedHoldingForTrade?.id"
      @close="closeAddModal"
      @saved="refreshAll"
    />

    <CreatePortfolioModal
      :is-open="showEditPortfolioModal"
      :edit-portfolio="currentPortfolio"
      @close="showEditPortfolioModal = false"
      @saved="refreshAll"
    />

    <MoveHoldingModal
      v-if="selectedHoldingForMove"
      :is-open="showMoveModal"
      :holding="selectedHoldingForMove"
      @close="showMoveModal = false"
      @moved="refreshAll"
    />

    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      :is-loading="confirmModal.isLoading"
      :error-message="confirmModal.errorMessage"
      @confirm="executeConfirmModal"
      @cancel="confirmModal.isOpen = false; confirmModal.errorMessage = ''"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import { getPortfolioColor, type StockHolding, type PortfolioOverview } from '../../types/portfolio'
import apiClient from '../../api/client'
import MarketStatusBar from '../../components/portfolio/MarketStatusBar.vue'
import AddTransactionModal from '../../components/portfolio/AddTransactionModal.vue'
import CreatePortfolioModal from '../../components/portfolio/CreatePortfolioModal.vue'
import MoveHoldingModal from '../../components/portfolio/MoveHoldingModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import {
  ArrowLeft,
  Layers,
  History,
  FileText,
  Plus,
  Edit2,
  Trash2,
  ExternalLink,
  ArrowRightLeft
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const portfolioStore = usePortfolioStore()
const toast = useToastStore()

const accountId = computed(() => route.params.id as string)
const activeTab = ref<'HOLDINGS' | 'EXECUTIONS' | 'STRATEGY'>('HOLDINGS')
const selectedAssetFilter = ref('ALL')
const isLoading = ref(true)
const accountOverview = ref<PortfolioOverview | null>(null)

const showAddModal = ref(false)
const showEditPortfolioModal = ref(false)
const showMoveModal = ref(false)
const selectedHoldingForTrade = ref<StockHolding | null>(null)
const selectedHoldingForMove = ref<StockHolding | null>(null)

const currentPortfolio = computed(() => {
  return portfolioStore.portfolios.find(p => p.id === accountId.value) || null
})

const curSymbol = computed(() => {
  return currentPortfolio.value?.currency === 'USD' ? '$' : '฿'
})

const portfolioTransactions = computed(() => {
  return portfolioStore.transactions.filter(t => t.portfolio === accountId.value)
})

const filteredHoldings = computed(() => {
  const list = accountOverview.value?.holdings || []
  if (selectedAssetFilter.value === 'ALL') return list
  return list.filter(h => h.asset_type === selectedAssetFilter.value)
})

const tabs = computed<Array<{ id: 'HOLDINGS' | 'EXECUTIONS' | 'STRATEGY'; label: string; icon: any; badge?: string }>>(() => [
  { id: 'HOLDINGS', label: 'Holdings Position Ledger', icon: Layers, badge: `${accountOverview.value?.holdings?.length || 0}` },
  { id: 'EXECUTIONS', label: 'Trade Executions History', icon: History, badge: `${portfolioTransactions.value.length}` },
  { id: 'STRATEGY', label: 'Strategy & Thesis', icon: FileText }
])

onMounted(async () => {
  await refreshAll()
})

async function refreshAll() {
  isLoading.value = true
  try {
    await portfolioStore.fetchPortfolios()
    if (!currentPortfolio.value) {
      toast.error('Brokerage account not found')
      router.push('/portfolio/accounts')
      return
    }

    // Fetch overview specifically for this portfolio
    const cur = currentPortfolio.value.currency || 'THB'
    const res = await apiClient.get<PortfolioOverview>('/portfolio/overview/', {
      params: {
        portfolio_id: accountId.value,
        currency: cur
      }
    })
    accountOverview.value = res.data

    // Fetch executions
    await portfolioStore.fetchTransactions({ portfolioId: accountId.value })
  } catch (err: any) {
    toast.error('Failed to load portfolio account dossier')
  } finally {
    isLoading.value = false
  }
}

function openAddTradeModal() {
  selectedHoldingForTrade.value = null
  showAddModal.value = true
}

function openAddTradeModalForHolding(h: StockHolding) {
  selectedHoldingForTrade.value = h
  showAddModal.value = true
}

function closeAddModal() {
  showAddModal.value = false
  selectedHoldingForTrade.value = null
}

function openEditModal() {
  showEditPortfolioModal.value = true
}

function openMoveModal(h: StockHolding) {
  selectedHoldingForMove.value = h
  showMoveModal.value = true
}

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

async function executeConfirmModal() {
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

function handleDeleteTransaction(txId: string) {
  confirmModal.title = 'Delete Executed Transaction'
  confirmModal.message = 'Are you sure you want to delete this executed transaction? Cost basis and portfolio metrics will recompute.'
  confirmModal.confirmText = 'Delete Transaction'
  confirmModal.isDanger = true
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    await portfolioStore.deleteTransaction(txId)
    toast.success('Transaction deleted')
    await refreshAll()
  }
  confirmModal.isOpen = true
}

function confirmDeletePortfolio() {
  if (!currentPortfolio.value) return
  if (accountOverview.value?.holdings && accountOverview.value.holdings.length > 0) {
    toast.error('Cannot delete account with active holdings. Move or close all positions first.')
    return
  }
  confirmModal.title = 'Delete Brokerage Account'
  confirmModal.message = `Are you sure you want to delete brokerage account "${currentPortfolio.value.name}"?`
  confirmModal.confirmText = 'Delete Account'
  confirmModal.isDanger = true
  confirmModal.errorMessage = ''
  confirmModal.action = async () => {
    await portfolioStore.deletePortfolio(accountId.value)
    toast.success('Brokerage account removed')
    router.push('/portfolio/accounts')
  }
  confirmModal.isOpen = true
}
</script>
