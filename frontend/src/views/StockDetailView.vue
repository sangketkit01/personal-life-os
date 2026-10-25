<template>
  <div class="space-y-6 max-w-6xl mx-auto font-sans pb-16">
    <!-- Top Navigation Breadcrumbs & Controls -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div class="flex items-center gap-2 text-xs font-mono text-zinc-400">
        <RouterLink to="/portfolio" class="hover:text-zinc-200 transition-colors flex items-center gap-1">
          <ArrowLeft class="w-3.5 h-3.5" />
          <span>Portfolio</span>
        </RouterLink>
        <span class="text-zinc-600">/</span>
        <span class="text-zinc-500">Holdings</span>
        <span class="text-zinc-600">/</span>
        <span class="text-zinc-100 font-bold font-mono">{{ tickerParam }}</span>
      </div>

      <!-- Quick Actions -->
      <div class="flex flex-wrap items-center gap-2">
        <!-- Currency View Toggle (F01) -->
        <div class="flex items-center gap-1 bg-zinc-900 border border-zinc-800 rounded-md p-0.5">
          <button
            @click="portfolioStore.setDisplayCurrency('THB')"
            class="px-2 py-1 rounded text-[11px] font-semibold transition-colors"
            :class="portfolioStore.displayCurrency === 'THB' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
          >
            ฿ THB
          </button>
          <button
            @click="portfolioStore.setDisplayCurrency('USD')"
            class="px-2 py-1 rounded text-[11px] font-semibold transition-colors"
            :class="portfolioStore.displayCurrency === 'USD' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
          >
            $ USD
          </button>
        </div>

        <button
          @click="handleToggleWatchlist"
          :disabled="isTogglingWatchlist"
          class="px-2.5 py-1.5 rounded-md border text-xs font-mono transition-colors flex items-center gap-1.5 disabled:opacity-50"
          :class="isWatchlisted ? 'bg-zinc-800 text-zinc-200 border-zinc-700' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'"
          :title="isWatchlisted ? 'In Watchlist' : 'Add to Watchlist'"
        >
          <Star class="w-3.5 h-3.5" :class="{ 'fill-zinc-300 text-zinc-200': isWatchlisted }" />
          <span>{{ isWatchlisted ? 'In Watchlist' : 'Watchlist' }}</span>
        </button>

        <button
          @click="handleSyncThisAsset"
          :disabled="isRefreshingThisAsset"
          class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-300 hover:text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
          title="Refresh quote & news for this asset"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': isRefreshingThisAsset }" />
          <span>{{ isRefreshingThisAsset ? 'Syncing...' : 'Sync Market Data' }}</span>
        </button>

        <button
          v-if="holding?.is_held"
          @click="openMoveModal"
          class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-300 hover:text-white transition-colors flex items-center gap-1.5"
          title="Move holding to another portfolio"
        >
          <ArrowRightLeft class="w-3.5 h-3.5 text-zinc-400" />
          <span>Move Port</span>
        </button>

        <button
          @click="openTradeModal"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>{{ holding?.is_held ? 'Record Trade' : '+ Record Buy' }}</span>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="p-16 text-center text-xs text-zinc-500 font-mono space-y-2">
      <div class="w-5 h-5 border-2 border-zinc-600 border-t-zinc-200 rounded-full animate-spin mx-auto"></div>
      <div>Loading {{ tickerParam }} position & financial data...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="errorMessage && !holding" class="p-12 text-center rounded-xl bg-zinc-900/30 border border-zinc-800 space-y-3">
      <p class="text-xs text-rose-400 font-mono">{{ errorMessage }}</p>
      <RouterLink
        to="/portfolio"
        class="inline-block px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200 transition-colors"
      >
        Return to Portfolio
      </RouterLink>
    </div>

    <!-- Main Content -->
    <div v-else class="space-y-6">
      <!-- Asset Header Card -->
      <div class="p-6 rounded-xl bg-zinc-950 border border-zinc-800 shadow-xl space-y-5">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div class="space-y-1.5">
            <div class="flex items-center gap-2.5 flex-wrap">
              <h1 class="text-2xl font-bold font-mono text-zinc-100 tracking-tight">
                {{ holding?.ticker || tickerParam }}
              </h1>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-800">
                {{ holding?.asset_type || 'STOCK' }}
              </span>
              <span
                class="text-[10px] font-mono px-2 py-0.5 rounded border uppercase bg-zinc-900 text-zinc-400 border-zinc-800"
              >
                {{ holding?.currency || 'THB' }}
              </span>
              <!-- Holding's Portfolio Badge with Multi-portfolio Switcher (F04) -->
              <div v-if="holding?.all_holdings && holding.all_holdings.length > 1" class="flex items-center gap-1.5 flex-wrap">
                <span class="text-[10px] text-zinc-500 font-sans">Portfolios:</span>
                <button
                  v-for="h in holding.all_holdings"
                  :key="h.id"
                  @click="switchHolding(h.id, h.portfolio_id)"
                  type="button"
                  class="text-[11px] font-sans px-2.5 py-0.5 rounded-full border transition-colors flex items-center gap-1.5"
                  :class="h.id === holding.id ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-semibold shadow-sm' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200 hover:bg-zinc-800/60'"
                >
                  <FolderKanban class="w-3 h-3 text-zinc-400" />
                  <span>{{ h.portfolio_name }}</span>
                </button>
              </div>
              <span
                v-else-if="holding?.portfolio_name && holding?.is_held"
                class="text-[11px] font-sans px-2.5 py-0.5 rounded-full bg-zinc-900 text-zinc-400 border border-zinc-800 flex items-center gap-1.5"
              >
                <FolderKanban class="w-3 h-3 text-zinc-500" />
                <span>{{ holding.portfolio_name }}</span>
              </span>

              <!-- Market Session Badge (Pre/Post-Market) -->
              <span
                v-if="holding?.position?.market_session === 'PRE'"
                class="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-800 font-medium flex items-center gap-1.5"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-pulse"></span>
                <span>Pre-Market Live</span>
              </span>
              <span
                v-else-if="holding?.position?.market_session === 'POST' || holding?.position?.market_session === 'POSTPOST'"
                class="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-800 font-medium flex items-center gap-1.5"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-pulse"></span>
                <span>Post-Market (Extended)</span>
              </span>

              <!-- Non-held Pre-investment Badge -->
              <span
                v-if="holding && !holding.is_held"
                class="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 font-medium flex items-center gap-1.5"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
                <span>Pre-investment Research Mode</span>
              </span>
            </div>

            <div class="text-xs text-zinc-400 font-sans">
              {{ holding?.name && holding.name !== holding.ticker ? holding.name : 'Verified Financial Market Asset' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Interactive Dime-Style Stock Price Chart -->
      <StockPriceChart
        :ticker="holding?.ticker || tickerParam"
        :currency="holding?.currency"
        :current-price="holding?.position?.current_price"
        :extended-price="holding?.position?.extended_price"
        :extended-change="holding?.position?.extended_change"
        :extended-change-pct="holding?.position?.extended_change_pct"
        :market-session="holding?.position?.market_session"
      />

      <!-- Position & Performance Metrics Grid (When Held) -->
      <div v-if="holding?.is_held" class="p-6 rounded-xl bg-zinc-950 border border-zinc-800 shadow-xl space-y-4">
        <div class="text-xs font-semibold uppercase tracking-wider font-mono text-zinc-400 flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <TrendingUp class="w-4 h-4 text-zinc-400" />
            <span>Your Position & Financial Performance</span>
          </div>
          <span class="text-[11px] font-mono text-zinc-500 font-normal">Values in {{ portfolioStore.displayCurrency }}</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 font-mono">
          <!-- Shares Held -->
          <div class="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/60">
            <div class="text-[10px] uppercase text-zinc-500">Units Held</div>
            <div class="text-sm font-semibold text-zinc-200 mt-1 tabular-nums">
              {{ formatShares(holding?.position?.shares || 0) }}
            </div>
            <div class="text-[10px] text-zinc-500 font-sans mt-0.5">8-decimal shares</div>
          </div>

          <!-- Avg Cost Basis (F01: Dual-currency consistency) -->
          <div class="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/60">
            <div class="text-[10px] uppercase text-zinc-500">Average Cost</div>
            <div class="text-sm font-semibold text-zinc-200 mt-1 tabular-nums">
              {{ currSymbol }}{{ formatPrice(displayAvgCost) }}
            </div>
            <div v-if="holding?.currency !== portfolioStore.displayCurrency" class="text-[9px] text-zinc-500 font-sans mt-0.5">
              ({{ nativeSymbol }}{{ formatPrice(holding?.position?.avg_cost || 0) }})
            </div>
            <div v-else class="text-[10px] text-zinc-500 font-sans mt-0.5">per unit</div>
          </div>

          <!-- Total Cost Basis (Invested) (F01: Dual-currency consistency) -->
          <div class="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/60">
            <div class="text-[10px] uppercase text-zinc-500">Total Invested</div>
            <div class="text-sm font-semibold text-zinc-300 mt-1 tabular-nums">
              {{ currSymbol }}{{ formatPrice(displayInvested) }}
            </div>
            <div v-if="holding?.currency !== portfolioStore.displayCurrency" class="text-[9px] text-zinc-500 font-sans mt-0.5">
              ({{ nativeSymbol }}{{ formatPrice(holding?.position?.total_invested || 0) }})
            </div>
            <div v-else class="text-[10px] text-zinc-500 font-sans mt-0.5">Cost Basis</div>
          </div>

          <!-- Market Value (F01: Dual-currency consistency) -->
          <div class="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/60">
            <div class="text-[10px] uppercase text-zinc-500">Market Value</div>
            <div class="text-sm font-bold text-zinc-100 mt-1 tabular-nums">
              {{ currSymbol }}{{ formatPrice(displayMarketValue) }}
            </div>
            <div v-if="holding?.currency !== portfolioStore.displayCurrency" class="text-[9px] text-zinc-500 font-sans mt-0.5">
              ({{ nativeSymbol }}{{ formatPrice(holding?.position?.market_value || 0) }})
            </div>
            <div v-else class="text-[10px] text-zinc-500 font-sans mt-0.5">Current Value</div>
          </div>

          <!-- Unrealized PnL (F01: Dual-currency consistency) -->
          <div class="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/60">
            <div class="text-[10px] uppercase text-zinc-500">Unrealized PnL</div>
            <div
              class="text-sm font-bold mt-1 tabular-nums"
              :class="getPnlClass(displayUnrealizedPnl)"
            >
              {{ displayUnrealizedPnl >= 0 ? '+' : '' }}{{ currSymbol }}{{ formatPrice(displayUnrealizedPnl) }}
            </div>
            <div
              class="text-[10px] font-semibold mt-0.5"
              :class="getPnlClass(displayUnrealizedPnl)"
            >
              {{ (holding?.position?.unrealized_pnl_pct || 0) >= 0 ? '+' : '' }}{{ Number(holding?.position?.unrealized_pnl_pct || 0).toFixed(2) }}%
            </div>
          </div>

          <!-- Realized PnL & Dividends (F01: Dual-currency consistency) -->
          <div class="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/60">
            <div class="text-[10px] uppercase text-zinc-500">Realized / Divs</div>
            <div
              class="text-sm font-semibold mt-1 tabular-nums"
              :class="getPnlClass(displayRealizedPnl)"
            >
              {{ currSymbol }}{{ formatPrice(displayRealizedPnl) }}
            </div>
            <div class="text-[10px] text-amber-400 font-sans mt-0.5">
              +{{ currSymbol }}{{ formatPrice(displayDividends) }} Divs
            </div>
          </div>
        </div>

        <!-- Notes (if any) -->
        <div v-if="holding?.notes" class="p-3 rounded-lg bg-zinc-900/20 border border-zinc-800/50 text-xs text-zinc-400 flex items-start gap-2">
          <FileText class="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />
          <div class="font-sans leading-relaxed">{{ holding.notes }}</div>
        </div>
      </div>

      <!-- Pre-investment Research Banner (When Not Held) -->
      <div v-else class="p-6 rounded-xl bg-zinc-950 border border-zinc-800 shadow-xl space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg bg-zinc-900/60 border border-zinc-800">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-zinc-400"></span>
              <span class="text-xs font-mono uppercase tracking-wider text-zinc-300 font-semibold">Pre-investment Research Mode</span>
            </div>
            <p class="text-xs text-zinc-400 font-sans leading-relaxed">
              Researching market quote and price action for <strong class="text-zinc-200">{{ holding?.name || tickerParam }}</strong> ({{ holding?.ticker || tickerParam }}). No active position held in this portfolio.
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2 shrink-0">
            <button
              @click="handleToggleWatchlist"
              :disabled="isTogglingWatchlist"
              class="px-3 py-1.5 rounded-md border text-xs font-mono transition-colors flex items-center gap-1.5"
              :class="isWatchlisted ? 'bg-zinc-800 text-zinc-200 border-zinc-700' : 'bg-zinc-900 text-zinc-300 border-zinc-800 hover:bg-zinc-800 hover:text-white'"
            >
              <Star class="w-3.5 h-3.5" :class="{ 'fill-zinc-300 text-zinc-200': isWatchlisted }" />
              <span>{{ isWatchlisted ? 'In Watchlist' : 'Add to Watchlist' }}</span>
            </button>

            <button
              @click="openTradeModal"
              class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow"
            >
              <Plus class="w-3.5 h-3.5" />
              <span>Record Execution (Buy {{ holding?.ticker || tickerParam }})</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Navigation Tabs: Executions vs Targeted News -->
      <div class="flex items-center gap-1 p-1 bg-zinc-950 border border-zinc-800 rounded-lg w-fit">
        <button
          type="button"
          @click="activeTab = 'trades'"
          class="px-3.5 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-colors flex items-center gap-2"
          :class="activeTab === 'trades' ? 'bg-zinc-800 text-zinc-100 font-semibold shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
        >
          <History class="w-3.5 h-3.5" />
          <span>Execution History</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
            {{ assetTransactions.length }}
          </span>
        </button>

        <button
          type="button"
          @click="activeTab = 'news'"
          class="px-3.5 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-colors flex items-center gap-2"
          :class="activeTab === 'news' ? 'bg-zinc-800 text-zinc-100 font-semibold shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
        >
          <Newspaper class="w-3.5 h-3.5" />
          <span>Targeted News</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
            {{ assetNews.length }}
          </span>
        </button>
      </div>

      <!-- TAB 1: Execution History Table -->
      <div v-if="activeTab === 'trades'" class="rounded-xl bg-zinc-950 border border-zinc-800 shadow-xl overflow-hidden">
        <div class="px-5 py-3.5 border-b border-zinc-800/80 flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <History class="w-3.5 h-3.5 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Trade History for {{ holding?.ticker || tickerParam }}
            </h2>
          </div>

          <button
            @click="openTradeModal"
            class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-300 hover:text-white transition-colors flex items-center gap-1"
          >
            <Plus class="w-3 h-3" />
            <span>Record Execution</span>
          </button>
        </div>

        <!-- Empty State -->
        <div v-if="assetTransactions.length === 0" class="p-12 text-center text-xs text-zinc-500 font-mono space-y-3">
          <p>No trade executions recorded for this asset yet.</p>
          <button
            @click="openTradeModal"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-200 text-xs font-sans transition-colors inline-block"
          >
            + Record first execution
          </button>
        </div>

        <!-- Transactions Table -->
        <div v-else class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-900/30">
                <th class="py-2.5 pl-4">Executed Date</th>
                <th class="py-2.5 text-center">Type</th>
                <th class="py-2.5 text-right">Shares</th>
                <th class="py-2.5 text-right">Price</th>
                <th class="py-2.5 text-right">Fee</th>
                <th class="py-2.5 text-right">Net Value</th>
                <th class="py-2.5 pl-4">Notes</th>
                <th class="py-2.5 text-right pr-4">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr
                v-for="tx in assetTransactions"
                :key="tx.id"
                class="hover:bg-zinc-900/40 transition-colors"
              >
                <td class="py-2.5 pl-4 text-zinc-400 whitespace-nowrap">
                  {{ formatDate(tx.executed_at) }}
                </td>

                <td class="py-2.5 text-center whitespace-nowrap">
                  <span
                    class="px-2 py-0.5 rounded text-[10px] font-mono border font-semibold"
                    :class="getTransactionBadgeClass(tx.transaction_type)"
                  >
                    {{ tx.transaction_type }}
                  </span>
                </td>

                <td class="py-2.5 text-right text-zinc-200 tabular-nums">
                  {{ formatShares(tx.shares) }}
                </td>

                <td class="py-2.5 text-right text-zinc-300 tabular-nums">
                  {{ getTxSymbol(tx) }}{{ formatPrice(tx.price_per_share) }}
                </td>

                <td class="py-2.5 text-right text-zinc-500 tabular-nums">
                  {{ tx.fee ? `${getTxSymbol(tx)}${formatPrice(tx.fee)}` : '-' }}
                </td>

                <td class="py-2.5 text-right font-semibold text-zinc-100 tabular-nums">
                  {{ getTxSymbol(tx) }}{{ formatPrice(Number(tx.shares) * Number(tx.price_per_share) + (tx.transaction_type === 'BUY' ? Number(tx.fee || 0) : -Number(tx.fee || 0))) }}
                </td>

                <td class="py-2.5 pl-4 text-zinc-500 font-sans truncate max-w-[160px]">
                  {{ tx.notes || '-' }}
                </td>

                <td class="py-2.5 text-right pr-4 whitespace-nowrap">
                  <div class="flex items-center justify-end gap-1.5">
                    <button
                      @click="editTransaction(tx)"
                      class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] text-zinc-400 hover:text-zinc-200 transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      @click="confirmDeleteTx(tx)"
                      class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-rose-950/40 border border-zinc-800 hover:border-rose-800/50 text-[10px] text-zinc-400 hover:text-rose-400 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- TAB 2: Targeted News Feed for this Asset -->
      <div v-else-if="activeTab === 'news'" class="space-y-4">
        <div class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
          <div>
            <div class="flex items-center gap-2">
              <Newspaper class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Market Intelligence for {{ holding?.ticker || tickerParam }}
              </h2>
            </div>
            <p class="text-xs text-zinc-500 mt-0.5">
              Verified news streams from Yahoo Finance & Google News, with Gemini AI Thai translation
            </p>
          </div>

          <button
            @click="handleSyncThisAsset"
            :disabled="isRefreshingThisAsset"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-300 hover:text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': isRefreshingThisAsset }" />
            <span>Sync News</span>
          </button>
        </div>

        <!-- Empty News -->
        <div v-if="assetNews.length === 0" class="p-12 text-center text-xs text-zinc-500 font-mono rounded-xl bg-zinc-950 border border-zinc-800 space-y-2">
          <Newspaper class="w-6 h-6 text-zinc-600 mx-auto" />
          <div>No news articles collected yet for {{ holding?.ticker || tickerParam }}.</div>
          <p class="text-[11px] text-zinc-600">Click "Sync News" above to query recent market headlines.</p>
        </div>

        <!-- News Cards Grid -->
        <div v-else class="grid grid-cols-1 gap-3.5">
          <div
            v-for="item in assetNews"
            :key="item.id"
            @click="goToNewsDetail(item.id)"
            class="p-5 rounded-xl bg-zinc-950 border border-zinc-800 hover:border-zinc-700 transition-all cursor-pointer group shadow-sm hover:shadow-md"
          >
            <!-- Meta Bar -->
            <div class="flex items-center justify-between text-xs pb-2 border-b border-zinc-800/60">
              <div class="flex items-center gap-2">
                <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-800">
                  {{ item.source || 'Market Intelligence' }}
                </span>
                <span
                  class="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full border flex items-center gap-1"
                  :class="getSentimentClass(item.sentiment)"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="getSentimentDot(item.sentiment)"></span>
                  <span>{{ item.sentiment }}</span>
                </span>
              </div>

              <span class="text-[11px] font-mono text-zinc-500">
                {{ formatDateTime(item.published_at) }}
              </span>
            </div>

            <!-- Title & Summary -->
            <div class="mt-3 space-y-1.5">
              <h3 class="text-sm font-semibold text-zinc-100 group-hover:text-white transition-colors leading-snug">
                {{ item.title }}
              </h3>
              <p v-if="item.summary_th || item.summary" class="text-xs text-zinc-400 font-sans leading-relaxed line-clamp-2">
                {{ item.summary_th || item.summary }}
              </p>
            </div>

            <!-- Footer -->
            <div class="mt-3.5 pt-2 border-t border-zinc-800/40 flex items-center justify-between text-xs">
              <span v-if="item.title_th" class="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Thai Translation Ready
              </span>
              <span v-else class="text-[10px] font-mono text-zinc-600">English Original</span>

              <span class="text-xs font-mono text-zinc-400 group-hover:text-zinc-200 transition-colors flex items-center gap-1">
                <span>Read Full Article Page</span>
                <ArrowRight class="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add / Edit Execution Modal -->
    <AddTransactionModal
      :is-open="showTradeModal"
      :prefill-ticker="holding?.ticker || tickerParam"
      :prefill-holding-id="holding?.id || undefined"
      :editing-transaction="selectedTxToEdit"
      @close="showTradeModal = false"
      @saved="handleTradeSaved"
    />

    <!-- Move Holding Modal -->
    <MoveHoldingModal
      v-if="holding"
      :is-open="showMoveModal"
      :holding="holding"
      @close="showMoveModal = false"
      @moved="handleHoldingMoved"
    />

    <!-- Confirmation Modal for Delete -->
    <div
      v-if="showDeleteModal && txToDelete"
      class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 font-sans"
    >
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl max-w-sm w-full p-5 space-y-4 shadow-2xl">
        <div class="text-sm font-semibold text-zinc-100">Delete Trade Execution?</div>
        <p class="text-xs text-zinc-400 font-sans">
          Are you sure you want to delete this {{ txToDelete.transaction_type }} trade of {{ txToDelete.shares }} units? This action cannot be undone.
        </p>
        <div class="flex items-center justify-end gap-2 pt-2">
          <button
            @click="showDeleteModal = false"
            class="px-3 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-400 hover:text-zinc-200"
          >
            Cancel
          </button>
          <button
            @click="executeDeleteTx"
            class="px-3 py-1.5 rounded-md bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white"
          >
            Delete Execution
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePortfolioStore } from '../stores/portfolio'
import type { StockHolding, StockTransaction, StockNewsArticle } from '../types/portfolio'
import AddTransactionModal from '../components/portfolio/AddTransactionModal.vue'
import MoveHoldingModal from '../components/portfolio/MoveHoldingModal.vue'
import StockPriceChart from '../components/portfolio/StockPriceChart.vue'
import {
  ArrowLeft,
  ArrowRight,
  ArrowRightLeft,
  Plus,
  RefreshCw,
  FolderKanban,
  FileText,
  History,
  Newspaper,
  Star,
  TrendingUp
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const portfolioStore = usePortfolioStore()

const tickerParam = computed(() => {
  return decodeURIComponent((route.params.ticker as string) || '').trim().toUpperCase()
})

const holding = ref<StockHolding | null>(null)
const assetTransactions = ref<StockTransaction[]>([])
const assetNews = ref<StockNewsArticle[]>([])
const isLoading = ref(true)
const isRefreshingThisAsset = ref(false)
const isTogglingWatchlist = ref(false)
const errorMessage = ref('')
const activeTab = ref<'trades' | 'news'>('trades')

const isWatchlisted = computed(() => {
  return holding.value?.is_watchlisted ?? portfolioStore.isWatchlisted(tickerParam.value)
})

async function handleToggleWatchlist() {
  if (!tickerParam.value) return
  isTogglingWatchlist.value = true
  try {
    const status = await portfolioStore.toggleWatchlist(tickerParam.value)
    if (holding.value) {
      holding.value.is_watchlisted = status
    }
  } catch (err) {
    console.error('Failed to toggle watchlist', err)
  } finally {
    isTogglingWatchlist.value = false
  }
}

// Modals
const showTradeModal = ref(false)
const selectedTxToEdit = ref<StockTransaction | null>(null)
const showMoveModal = ref(false)
const showDeleteModal = ref(false)
const txToDelete = ref<StockTransaction | null>(null)

const nativeSymbol = computed(() => {
  return (holding.value?.currency || 'THB').toUpperCase() === 'USD' ? '$' : '฿'
})

const currSymbol = computed(() => {
  return portfolioStore.displayCurrency === 'USD' ? '$' : '฿'
})

function getTxSymbol(tx: StockTransaction): string {
  const c = (tx.currency || holding.value?.currency || 'THB').toUpperCase()
  return c === 'USD' ? '$' : '฿'
}

// Compute market value in selected display currency (THB / USD)
const displayMarketValue = computed(() => {
  const p = holding.value?.position
  if (!p) return 0
  if (portfolioStore.displayCurrency === 'USD') {
    if (p.market_value_usd !== undefined && p.market_value_usd !== null) return Number(p.market_value_usd)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'USD' ? Number(p.market_value || 0) : Number(p.market_value || 0) / rate
  } else {
    if (p.market_value_thb !== undefined && p.market_value_thb !== null) return Number(p.market_value_thb)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'THB' ? Number(p.market_value || 0) : Number(p.market_value || 0) * rate
  }
})

const displayInvested = computed(() => {
  const p = holding.value?.position
  if (!p) return 0
  if (portfolioStore.displayCurrency === 'USD') {
    if (p.total_invested_usd !== undefined && p.total_invested_usd !== null) return Number(p.total_invested_usd)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'USD' ? Number(p.total_invested || 0) : Number(p.total_invested || 0) / rate
  } else {
    if (p.total_invested_thb !== undefined && p.total_invested_thb !== null) return Number(p.total_invested_thb)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'THB' ? Number(p.total_invested || 0) : Number(p.total_invested || 0) * rate
  }
})

const displayUnrealizedPnl = computed(() => {
  const p = holding.value?.position
  if (!p) return 0
  if (portfolioStore.displayCurrency === 'USD') {
    if (p.unrealized_pnl_usd !== undefined && p.unrealized_pnl_usd !== null) return Number(p.unrealized_pnl_usd)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'USD' ? Number(p.unrealized_pnl || 0) : Number(p.unrealized_pnl || 0) / rate
  } else {
    if (p.unrealized_pnl_thb !== undefined && p.unrealized_pnl_thb !== null) return Number(p.unrealized_pnl_thb)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'THB' ? Number(p.unrealized_pnl || 0) : Number(p.unrealized_pnl || 0) * rate
  }
})

const displayRealizedPnl = computed(() => {
  const p = holding.value?.position
  if (!p) return 0
  if (portfolioStore.displayCurrency === 'USD') {
    if (p.total_realized_pnl_usd !== undefined && p.total_realized_pnl_usd !== null) return Number(p.total_realized_pnl_usd)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'USD' ? Number(p.total_realized_pnl || 0) : Number(p.total_realized_pnl || 0) / rate
  } else {
    if (p.total_realized_pnl_thb !== undefined && p.total_realized_pnl_thb !== null) return Number(p.total_realized_pnl_thb)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'THB' ? Number(p.total_realized_pnl || 0) : Number(p.total_realized_pnl || 0) * rate
  }
})

const displayDividends = computed(() => {
  const p = holding.value?.position
  if (!p) return 0
  if (portfolioStore.displayCurrency === 'USD') {
    if (p.total_dividends_usd !== undefined && p.total_dividends_usd !== null) return Number(p.total_dividends_usd)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'USD' ? Number(p.total_dividends || 0) : Number(p.total_dividends || 0) / rate
  } else {
    if (p.total_dividends_thb !== undefined && p.total_dividends_thb !== null) return Number(p.total_dividends_thb)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'THB' ? Number(p.total_dividends || 0) : Number(p.total_dividends || 0) * rate
  }
})

const displayAvgCost = computed(() => {
  const p = holding.value?.position
  if (!p) return 0
  if (portfolioStore.displayCurrency === 'USD') {
    if (p.avg_cost_usd !== undefined && p.avg_cost_usd !== null) return Number(p.avg_cost_usd)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'USD' ? Number(p.avg_cost || 0) : Number(p.avg_cost || 0) / rate
  } else {
    if (p.avg_cost_thb !== undefined && p.avg_cost_thb !== null) return Number(p.avg_cost_thb)
    const rate = portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate || 34
    return (holding.value?.currency || '').toUpperCase() === 'THB' ? Number(p.avg_cost || 0) : Number(p.avg_cost || 0) * rate
  }
})

function switchHolding(holdingId: string, portfolioId: string) {
  router.replace({
    path: route.path,
    query: { ...route.query, holding_id: holdingId, portfolio_id: portfolioId }
  })
}

function formatPrice(val: number | string): string {
  const n = Number(val || 0)
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatShares(shares: number | string): string {
  const n = Number(shares || 0)
  return n.toLocaleString('en-US', { maximumFractionDigits: 8 })
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('th-TH', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  })
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('th-TH', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getPnlClass(val: number) {
  if (val > 0) return 'text-emerald-400'
  if (val < 0) return 'text-rose-400'
  return 'text-zinc-400'
}

function getTransactionBadgeClass(type: string) {
  switch (type) {
    case 'BUY':
      return 'bg-zinc-900 text-emerald-400 border-zinc-800'
    case 'SELL':
      return 'bg-zinc-900 text-rose-400 border-zinc-800'
    case 'DIVIDEND':
      return 'bg-zinc-900 text-zinc-300 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
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

function getSentimentDot(sentiment: string) {
  switch (sentiment) {
    case 'BULLISH':
      return 'bg-emerald-400'
    case 'BEARISH':
      return 'bg-rose-400'
    default:
      return 'bg-zinc-500'
  }
}

function goToNewsDetail(articleId: string) {
  router.push(`/portfolio/news/${articleId}`)
}

function openTradeModal() {
  selectedTxToEdit.value = null
  showTradeModal.value = true
}

function editTransaction(tx: StockTransaction) {
  selectedTxToEdit.value = tx
  showTradeModal.value = true
}

function confirmDeleteTx(tx: StockTransaction) {
  txToDelete.value = tx
  showDeleteModal.value = true
}

async function executeDeleteTx() {
  if (!txToDelete.value) return
  try {
    await portfolioStore.deleteTransaction(txToDelete.value.id)
    showDeleteModal.value = false
    txToDelete.value = null
    await loadAssetData()
  } catch (err: any) {
    console.error('Delete transaction failed', err)
  }
}

function openMoveModal() {
  showMoveModal.value = true
}

async function handleHoldingMoved() {
  showMoveModal.value = false
  await loadAssetData()
}

async function handleTradeSaved() {
  showTradeModal.value = false
  selectedTxToEdit.value = null
  await loadAssetData()
}

async function handleSyncThisAsset() {
  isRefreshingThisAsset.value = true
  try {
    await Promise.all([
      portfolioStore.refreshMarketPrices(true),
      portfolioStore.syncNews()
    ])
    await loadAssetData()
  } finally {
    isRefreshingThisAsset.value = false
  }
}

async function loadAssetData() {
  const ticker = tickerParam.value
  if (!ticker) return

  const portfolioId = (route.query.portfolio_id as string) || (portfolioStore.selectedPortfolioId !== 'ALL' ? portfolioStore.selectedPortfolioId : undefined)
  const holdingId = (route.query.holding_id as string) || undefined

  try {
    // 1. Fetch holding info with holdingId/portfolioId filter
    const fetchedHolding = await portfolioStore.fetchHoldingByTicker(ticker, { holdingId, portfolioId })
    holding.value = fetchedHolding

    // If not held yet and no transactions, default tab to news
    if (!fetchedHolding.is_held && assetTransactions.value.length === 0) {
      activeTab.value = 'news'
    }

    // 2. Fetch transactions for this specific holding and portfolio
    if (fetchedHolding.is_held && fetchedHolding.id) {
      const txList = await portfolioStore.fetchTransactions({
        ticker,
        holdingId: fetchedHolding.id,
        portfolioId: fetchedHolding.portfolio
      })
      assetTransactions.value = txList
    } else {
      assetTransactions.value = []
    }

    // 3. Fetch news for this ticker (with On-demand ingestion)
    const newsList = await portfolioStore.fetchNews({ ticker })
    assetNews.value = newsList
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.detail || `Asset quote unavailable for ${ticker} in market feed`
  }
}

watch(
  () => [route.query.holding_id, route.query.portfolio_id],
  () => {
    loadAssetData()
  }
)

onMounted(async () => {
  isLoading.value = true
  try {
    await loadAssetData()
  } finally {
    isLoading.value = false
  }
})
</script>
