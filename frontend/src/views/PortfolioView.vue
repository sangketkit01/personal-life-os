<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header & Universal Search Bar -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3.5 pb-4 border-b border-zinc-800/80">
      <div class="flex-shrink-0">
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Portfolio Snapshot</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            MARKET DATA
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-0.5">Multi-asset bookkeeping (SET, US, Crypto) with weighted DCA cost basis and dual THB/USD conversion</p>
      </div>

      <!-- Universal Ticker & Asset Search Bar (Always visible & accessible from ANY tab) -->
      <div ref="universalSearchContainerRef" class="relative w-full lg:max-w-md">
        <div class="relative flex items-center">
          <Search class="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
          <input
            ref="universalSearchInputRef"
            v-model="universalSearchQuery"
            @input="handleUniversalSearchInput"
            @keydown.down.prevent="navigateSearchResults(1)"
            @keydown.up.prevent="navigateSearchResults(-1)"
            @keydown.enter.prevent="handleUniversalSearchEnter"
            @keydown.esc="closeUniversalSearch"
            @focus="handleUniversalSearchFocus"
            type="text"
            placeholder="Search any ticker (e.g. NVDA, PTT, BTC, TSLA)..."
            class="w-full pl-9 pr-14 py-2 rounded-lg bg-zinc-900/90 hover:bg-zinc-900 border border-zinc-800 focus:border-blue-500/60 focus:bg-zinc-950 text-xs text-zinc-100 placeholder-zinc-500 font-mono transition-all shadow-inner outline-none"
          />
          <div class="absolute right-2.5 flex items-center gap-1.5">
            <Loader2 v-if="isUniversalSearching" class="w-3.5 h-3.5 text-blue-400 animate-spin" />
            <button
              v-else-if="universalSearchQuery"
              @click="universalSearchQuery = ''; universalSearchResults = []; closeUniversalSearch()"
              type="button"
              class="text-zinc-500 hover:text-zinc-300"
            >
              <X class="w-3.5 h-3.5" />
            </button>
            <span v-else class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/60 shadow-sm pointer-events-none" title="Press / anywhere to search">
              /
            </span>
          </div>
        </div>

        <!-- Autocomplete Dropdown Flyout -->
        <div
          v-if="showUniversalSearchResults && universalSearchQuery.trim()"
          class="absolute left-0 right-0 mt-1.5 max-h-[380px] overflow-y-auto rounded-xl bg-zinc-950/95 backdrop-blur-md border border-zinc-800 shadow-2xl z-50 divide-y divide-zinc-800/80"
        >
          <!-- Results Header -->
          <div class="px-3 py-2 bg-zinc-900/60 text-[10px] font-mono text-zinc-400 flex items-center justify-between">
            <span v-if="universalSearchResults.length > 0">
              Found {{ universalSearchResults.length }} asset{{ universalSearchResults.length > 1 ? 's' : '' }} for "{{ universalSearchQuery }}"
            </span>
            <span v-else>
              Market Asset Search
            </span>
            <span class="text-zinc-500">Press Enter ↵ to inspect</span>
          </div>

          <!-- Result Items -->
          <div v-if="universalSearchResults.length > 0" class="divide-y divide-zinc-800/50">
            <div
              v-for="(item, idx) in universalSearchResults"
              :key="item.ticker"
              @click="selectSearchAsset(item.ticker)"
              class="p-2.5 px-3 hover:bg-zinc-900/80 cursor-pointer transition-colors flex items-center justify-between gap-3 group"
              :class="{ 'bg-zinc-900/90 border-l-2 border-blue-500': selectedResultIndex === idx }"
            >
              <!-- Left: Ticker, Name, Badges -->
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-mono font-bold text-xs text-zinc-100 group-hover:text-blue-400 transition-colors">
                    {{ item.ticker }}
                  </span>
                  <span
                    class="text-[9px] font-mono px-1.5 py-0.2 rounded border font-semibold"
                    :class="item.asset_type === 'CRYPTO' ? 'bg-purple-950/40 text-purple-400 border-purple-500/30' : (item.ticker.endsWith('.BK') ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30' : 'bg-blue-950/40 text-blue-400 border-blue-500/30')"
                  >
                    {{ item.asset_type }}
                  </span>
                  <span class="text-[9px] font-mono text-zinc-500 uppercase">
                    {{ item.exchange || (item.ticker.endsWith('.BK') ? 'SET' : 'US') }}
                  </span>

                  <!-- Status Badges: Held or Watchlist -->
                  <span
                    v-if="isTickerHeld(item.ticker)"
                    class="text-[9px] font-sans px-1.5 py-0.2 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium flex items-center gap-1"
                  >
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    <span>Held</span>
                  </span>
                  <span
                    v-if="portfolioStore.isWatchlisted(item.ticker)"
                    class="text-[9px] font-sans px-1.5 py-0.2 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium flex items-center gap-0.5"
                  >
                    <Star class="w-2.5 h-2.5 fill-amber-400" />
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
                    {{ item.currency === 'USD' ? '$' : '฿' }}{{ formatPrice(item.price) }}
                  </div>
                  <div
                    v-if="item.change_pct !== undefined && item.change_pct !== null"
                    class="text-[10px] font-semibold"
                    :class="item.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'"
                  >
                    {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
                  </div>
                </div>

                <!-- Quick Action Buttons -->
                <div class="flex items-center gap-1" @click.stop>
                  <!-- Quick Watchlist Toggle -->
                  <button
                    @click="portfolioStore.toggleWatchlist(item.ticker)"
                    type="button"
                    class="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-amber-400 transition-colors"
                    :title="portfolioStore.isWatchlisted(item.ticker) ? 'Remove from Watchlist' : 'Add to Watchlist'"
                  >
                    <Star
                      class="w-3.5 h-3.5"
                      :class="portfolioStore.isWatchlisted(item.ticker) ? 'text-amber-400 fill-amber-400' : 'text-zinc-500'"
                    />
                  </button>

                  <!-- Quick Buy Button -->
                  <button
                    @click="openBuyModalForTicker(item.ticker); closeUniversalSearch()"
                    type="button"
                    class="px-2 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] font-mono text-zinc-300 hover:text-zinc-100 transition-colors"
                    title="Record Trade for this ticker"
                  >
                    + Buy
                  </button>

                  <!-- View Asset Details -->
                  <button
                    @click="selectSearchAsset(item.ticker)"
                    type="button"
                    class="px-2 py-1 rounded bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-[10px] font-mono text-blue-400 hover:text-blue-300 font-semibold transition-colors flex items-center gap-1"
                  >
                    <span>View</span>
                    <ArrowRight class="w-2.5 h-2.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Fallback direct inspect card if no catalog match -->
          <div
            v-else-if="!isUniversalSearching"
            @click="selectSearchAsset(universalSearchQuery.trim())"
            class="p-4 hover:bg-zinc-900/80 cursor-pointer transition-colors flex items-center justify-between text-xs font-mono group"
          >
            <div>
              <div class="text-zinc-300 font-semibold flex items-center gap-2">
                <span>Inspect "{{ universalSearchQuery.toUpperCase() }}" in Universal Mode</span>
                <span class="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">Live Market</span>
              </div>
              <div class="text-[11px] text-zinc-500 font-sans mt-0.5">
                Query live stock quotes, charts and AI translated news for this ticker directly
              </div>
            </div>
            <ArrowRight class="w-4 h-4 text-zinc-500 group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all" />
          </div>
        </div>
      </div>

      <!-- Right: Action Buttons -->
      <div class="flex flex-wrap items-center gap-2.5 flex-shrink-0">
        <button
          @click="handleRefreshPrices"
          :disabled="portfolioStore.isRefreshing"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-xs font-medium text-zinc-300 transition-colors flex items-center gap-1.5 disabled:opacity-50"
          title="Refresh market quotes via yfinance"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': portfolioStore.isRefreshing }" />
          <span>{{ portfolioStore.isRefreshing ? 'Fetching Quotes...' : 'Refresh Quotes' }}</span>
        </button>

        <button
          @click="openAddModal()"
          class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>Record Trade</span>
        </button>
      </div>
    </div>

    <!-- Dime-Style Multi-Portfolio Switcher Bar -->
    <div class="flex items-center justify-between gap-3 overflow-x-auto pb-1">
      <div class="flex items-center gap-1.5 flex-nowrap">
        <!-- All Portfolios Aggregate Tab -->
        <button
          @click="portfolioStore.setSelectedPortfolio('ALL')"
          class="px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-2 border whitespace-nowrap"
          :class="portfolioStore.selectedPortfolioId === 'ALL'
            ? 'bg-zinc-800 text-zinc-100 font-bold border-zinc-700 shadow-sm'
            : 'bg-zinc-900/60 text-zinc-400 border-zinc-800/80 hover:text-zinc-200 hover:bg-zinc-900'"
        >
          <Globe class="w-3.5 h-3.5 text-zinc-400" />
          <span>All Portfolios</span>
          <span class="text-[10px] px-1 py-0.2 rounded bg-zinc-950 text-zinc-500 border border-zinc-800">
            Consolidated
          </span>
        </button>

        <!-- User Named Sub-Portfolios -->
        <div
          v-for="p in portfolioStore.portfolios"
          :key="p.id"
          class="flex items-center group relative"
        >
          <button
            @click="portfolioStore.setSelectedPortfolio(p.id)"
            class="px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-2 border whitespace-nowrap"
            :class="portfolioStore.selectedPortfolioId === p.id
              ? 'bg-zinc-800 text-zinc-100 font-bold border-zinc-700 shadow-sm'
              : 'bg-zinc-900/60 text-zinc-400 border-zinc-800/80 hover:text-zinc-200 hover:bg-zinc-900'"
          >
            <span
              class="w-2 h-2 rounded-full flex-shrink-0"
              :style="{ backgroundColor: p.color || '#3B82F6' }"
            ></span>
            <span>{{ p.name }}</span>
            <span
              class="text-[10px] px-1 py-0.2 rounded border font-semibold"
              :class="p.currency === 'USD' ? 'bg-blue-950/40 text-blue-400 border-blue-500/30' : 'bg-zinc-950 text-zinc-400 border-zinc-800'"
            >
              {{ p.currency }}
            </span>
          </button>

          <!-- Edit & Delete buttons on hover -->
          <div class="hidden group-hover:flex items-center gap-1 absolute -top-2 -right-2 z-10">
            <button
              @click.stop="openEditPortfolio(p)"
              class="w-4 h-4 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-blue-400 hover:border-blue-500/50 flex items-center justify-center transition-colors shadow"
              title="Edit portfolio"
            >
              <Edit2 class="w-2.5 h-2.5" />
            </button>
            <button
              v-if="!p.is_default"
              @click.stop="confirmDeletePortfolio(p)"
              class="w-4 h-4 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-rose-400 hover:border-rose-500/50 flex items-center justify-center transition-colors shadow"
              title="Delete portfolio"
            >
              <X class="w-2.5 h-2.5" />
            </button>
          </div>
        </div>
      </div>

      <!-- Add New Portfolio Button -->
      <button
        @click="showCreatePortfolioModal = true"
        class="px-2.5 py-1.5 rounded-lg text-xs font-mono text-zinc-400 hover:text-zinc-200 bg-zinc-900/40 hover:bg-zinc-900 border border-dashed border-zinc-800 hover:border-zinc-700 transition-colors flex items-center gap-1.5 whitespace-nowrap flex-shrink-0"
      >
        <FolderPlus class="w-3.5 h-3.5 text-zinc-400" />
        <span>New Portfolio</span>
      </button>
    </div>

    <!-- Unified High-Density Terminal Command Strip (Currency Toggle, Market Sessions, 1m Live Sync) -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3 text-xs font-mono px-3.5 py-2.5 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
      <!-- Left: Currency View Toggle & Real-time Rate -->
      <div class="flex flex-wrap items-center gap-3">
        <div class="flex items-center gap-1 bg-zinc-950/80 border border-zinc-800/80 rounded-md p-0.5">
          <button
            @click="portfolioStore.setDisplayCurrency('THB')"
            class="px-2 py-0.5 rounded text-[11px] font-semibold transition-colors"
            :class="portfolioStore.displayCurrency === 'THB' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
          >
            ฿ THB
          </button>
          <button
            @click="portfolioStore.setDisplayCurrency('USD')"
            class="px-2 py-0.5 rounded text-[11px] font-semibold transition-colors"
            :class="portfolioStore.displayCurrency === 'USD' ? 'bg-blue-950/60 text-blue-400 border border-blue-500/30 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
          >
            $ USD
          </button>
        </div>

        <div class="text-[11px] text-zinc-400 flex items-center gap-1.5">
          <span class="text-zinc-500 hidden sm:inline">Rate:</span>
          <span class="text-zinc-200 font-bold">1 USD = ฿{{ Number(portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate).toFixed(2) }}</span>
        </div>

        <div class="h-3.5 w-px bg-zinc-800 hidden sm:block"></div>

        <!-- Market Sessions Badges (SET, US, Crypto) -->
        <div class="flex items-center gap-1.5 flex-wrap">
          <!-- SET Badge -->
          <div
            class="flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px]"
            :class="portfolioStore.marketStatus?.markets.SET.is_open
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-zinc-950 text-zinc-500 border-zinc-800'"
            :title="(portfolioStore.marketStatus?.markets.SET.hours_description || '') + ' • ' + (portfolioStore.marketStatus?.markets.SET.opens_at || '')"
          >
            <span
              class="w-1.5 h-1.5 rounded-full"
              :class="portfolioStore.marketStatus?.markets.SET.is_open ? 'bg-emerald-400' : 'bg-zinc-600'"
            ></span>
            <span>SET: {{ portfolioStore.marketStatus?.markets.SET.session || 'Closed' }}</span>
          </div>

          <!-- US Markets Badge -->
          <div
            class="flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px]"
            :class="portfolioStore.marketStatus?.markets.US.is_open
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-zinc-950 text-zinc-500 border-zinc-800'"
            :title="(portfolioStore.marketStatus?.markets.US.hours_description || '') + ' • ' + (portfolioStore.marketStatus?.markets.US.opens_at || '')"
          >
            <span
              class="w-1.5 h-1.5 rounded-full"
              :class="portfolioStore.marketStatus?.markets.US.is_open ? 'bg-emerald-400' : 'bg-zinc-600'"
            ></span>
            <span>US: {{ portfolioStore.marketStatus?.markets.US.session || 'Closed' }}</span>
          </div>

          <!-- Crypto Badge -->
          <div
            class="flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
            title="Crypto trades 24/7 non-stop"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Crypto: 24/7</span>
          </div>
        </div>
      </div>

      <!-- Right: Real-time Polling Status, Last Synced & Refresh Trigger -->
      <div class="flex items-center gap-2.5 self-end lg:self-center">
        <div
          v-if="portfolioStore.marketStatus?.should_poll_realtime"
          class="flex items-center gap-1.5 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>1m Live Sync</span>
        </div>
        <div
          v-else
          class="flex items-center gap-1.5 text-[10px] text-zinc-500 bg-zinc-950 border border-zinc-800 px-2 py-0.5 rounded"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-zinc-600"></span>
          <span>Sync Paused</span>
        </div>

        <div v-if="formattedLastSyncTime" class="text-[10px] text-zinc-500 hidden sm:block">
          Synced: <span class="text-zinc-300 font-medium">{{ formattedLastSyncTime }}</span>
        </div>

        <button
          @click="handleRefreshPrices"
          :disabled="portfolioStore.isRefreshing"
          class="p-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
          title="Force refresh market quotes"
        >
          <RefreshCw class="w-3 h-3" :class="portfolioStore.isRefreshing ? 'animate-spin text-blue-400' : ''" />
        </button>
      </div>
    </div>

    <!-- 4 Yahoo Finance Key Metrics Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      <!-- 1. Total Portfolio Value -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Portfolio Value</span>
          <span
            class="font-mono text-[10px] tabular-nums"
            :class="Number(activeSummary.total_unrealized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          >
            {{ Number(activeSummary.total_unrealized_pnl || 0) >= 0 ? '+' : '' }}{{ Number(activeSummary.total_unrealized_pnl_pct || 0).toFixed(2) }}%
          </span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ currSymbol }}{{ formatNumber(activeSummary.total_market_value) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span
            class="w-1.5 h-1.5 rounded-full"
            :class="Number(activeSummary.total_unrealized_pnl || 0) >= 0 ? 'bg-emerald-400' : 'bg-rose-400'"
          />
          <span class="font-mono tabular-nums">
            Unrealized: {{ Number(activeSummary.total_unrealized_pnl || 0) >= 0 ? '+' : '' }}{{ currSymbol }}{{ formatNumber(activeSummary.total_unrealized_pnl) }}
          </span>
        </div>
      </div>

      <!-- 2. Cost Basis -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Cost Basis</span>
          <span>Invested</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ currSymbol }}{{ formatNumber(activeSummary.total_cost_basis) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
          <span>{{ portfolioStore.overview?.active_assets_count || 0 }} open positions</span>
        </div>
      </div>

      <!-- 3. Realized PnL -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Realized PnL</span>
          <span>Closed</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span
            class="text-xl font-semibold font-mono tabular-nums"
            :class="Number(activeSummary.total_realized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          >
            {{ Number(activeSummary.total_realized_pnl || 0) >= 0 ? '+' : '' }}{{ currSymbol }}{{ formatNumber(activeSummary.total_realized_pnl) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
          <span>Cumulative closed profit/loss</span>
        </div>
      </div>

      <!-- 4. Dividends -->
      <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80">
        <div class="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          <span>Dividends</span>
          <span>Passive</span>
        </div>
        <div class="mt-2.5 flex items-baseline gap-1.5">
          <span class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            {{ currSymbol }}{{ formatNumber(activeSummary.total_dividends) }}
          </span>
        </div>
        <div class="mt-3 text-[11px] text-zinc-500 flex items-center gap-1.5 border-t border-zinc-800/50 pt-2.5">
          <span class="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
          <span>Net passive income</span>
        </div>
      </div>
    </div>

    <!-- Asset Allocation Donut Chart -->
    <AssetAllocationChart
      :allocations="activeSummary.asset_allocation || []"
      :currency-symbol="currSymbol"
    />

    <!-- Navigation Tabs (Holdings | Market News | Executions) -->
    <div class="flex items-center gap-2 border-b border-zinc-800/80 pb-2">
      <button
        @click="activeTab = 'holdings'"
        class="px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-colors flex items-center gap-2"
        :class="activeTab === 'holdings' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <TrendingUp class="w-3.5 h-3.5" />
        <span>Holdings Position</span>
        <span class="text-[10px] px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-700/60 text-zinc-400">
          {{ portfolioStore.holdings.length }}
        </span>
      </button>

      <button
        @click="switchTab('watchlist')"
        class="px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-colors flex items-center gap-2"
        :class="activeTab === 'watchlist' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <Star class="w-3.5 h-3.5 text-amber-400" />
        <span>Watchlist</span>
        <span class="text-[10px] px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-700/60 text-zinc-400">
          {{ portfolioStore.watchlist.length }}
        </span>
      </button>

      <button
        @click="switchTab('news')"
        class="px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-colors flex items-center gap-2"
        :class="activeTab === 'news' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <Newspaper class="w-3.5 h-3.5" />
        <span>Market Intelligence</span>
        <span
          v-if="portfolioStore.newsTotalCount > 0"
          class="text-[10px] px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-700/60 text-zinc-400"
        >
          {{ portfolioStore.newsTotalCount }}
        </span>
      </button>

      <button
        @click="activeTab = 'transactions'"
        class="px-3 py-1.5 rounded-md text-xs font-mono uppercase tracking-wider transition-colors flex items-center gap-2"
        :class="activeTab === 'transactions' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <History class="w-3.5 h-3.5" />
        <span>Executions</span>
        <span class="text-[10px] px-1.5 py-0.2 rounded bg-zinc-900 border border-zinc-700/60 text-zinc-400">
          {{ portfolioStore.transactions.length }}
        </span>
      </button>
    </div>

    <!-- TAB 1: Holdings Position -->
    <div v-if="activeTab === 'holdings'" class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <TrendingUp class="w-3.5 h-3.5 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
            Holdings Position (in {{ portfolioStore.displayCurrency }})
          </h2>
        </div>
        <span class="text-[11px] font-mono text-zinc-500">{{ portfolioStore.holdings.length }} Assets</span>
      </div>

      <!-- Asset Class Filter Pills (Stocks / Crypto / Funds / Other) -->
      <div class="px-5 py-2.5 border-b border-zinc-800/60 bg-zinc-950/20 flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-1.5 flex-wrap">
          <span class="text-[11px] font-mono uppercase tracking-wider text-zinc-500 mr-1">Asset Class:</span>
          <button
            v-for="cat in assetClassFilters"
            :key="cat.value"
            @click="portfolioStore.setSelectedAssetType(cat.value)"
            class="px-2.5 py-1 rounded text-xs font-mono transition-colors border"
            :class="portfolioStore.selectedAssetType === cat.value
              ? 'bg-zinc-100 text-zinc-950 font-bold border-zinc-100'
              : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'"
          >
            {{ cat.label }}
          </button>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="hideClosedPositions = !hideClosedPositions"
            class="px-2.5 py-1 rounded text-xs font-mono transition-colors flex items-center gap-1.5 border"
            :class="hideClosedPositions
              ? 'bg-zinc-800 text-zinc-200 border-zinc-700'
              : 'bg-zinc-900/60 text-zinc-500 border-zinc-800 hover:text-zinc-300'"
            :title="hideClosedPositions ? 'Click to show closed positions' : 'Click to hide 0-share positions'"
          >
            <span>Hide Closed (0 Shares)</span>
            <span v-if="closedHoldingsCount > 0" class="text-[10px] px-1 py-0.2 rounded bg-zinc-950 text-zinc-400 border border-zinc-800">
              {{ closedHoldingsCount }}
            </span>
          </button>
          <div class="text-[11px] font-mono text-zinc-500">
            Showing {{ displayedHoldings.length }} position{{ displayedHoldings.length !== 1 ? 's' : '' }}
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-if="displayedHoldings.length === 0 && !portfolioStore.isLoading"
        class="p-12 text-center space-y-3 font-mono text-xs text-zinc-500"
      >
        <p>No holdings recorded for this category.</p>
        <button
          @click="openAddModal()"
          class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-sans transition-colors inline-block"
        >
          + Record first trade
        </button>
      </div>

      <!-- Table -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-xs font-mono">
          <thead>
            <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-950/40 select-none">
              <th @click="toggleSort('ticker')" class="py-2.5 pl-4 sticky left-0 bg-zinc-950 z-10 cursor-pointer hover:text-zinc-300 transition-colors">
                <div class="flex items-center gap-1">
                  <span>Symbol / Name</span>
                  <span v-if="sortKey === 'ticker'" class="text-blue-400">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('currency')" class="py-2.5 text-center cursor-pointer hover:text-zinc-300 transition-colors">
                <div class="flex items-center justify-center gap-1">
                  <span>Denom</span>
                  <span v-if="sortKey === 'currency'" class="text-blue-400">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('shares')" class="py-2.5 text-right cursor-pointer hover:text-zinc-300 transition-colors">
                <div class="flex items-center justify-end gap-1">
                  <span>Shares</span>
                  <span v-if="sortKey === 'shares'" class="text-blue-400">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('avg_cost')" class="py-2.5 text-right cursor-pointer hover:text-zinc-300 transition-colors">
                <div class="flex items-center justify-end gap-1">
                  <span>Avg Cost</span>
                  <span v-if="sortKey === 'avg_cost'" class="text-blue-400">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('current_price')" class="py-2.5 text-right cursor-pointer hover:text-zinc-300 transition-colors">
                <div class="flex items-center justify-end gap-1">
                  <span>Market Price</span>
                  <span v-if="sortKey === 'current_price'" class="text-blue-400">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('market_value')" class="py-2.5 text-right cursor-pointer hover:text-zinc-300 transition-colors">
                <div class="flex items-center justify-end gap-1">
                  <span>Market Value</span>
                  <span v-if="sortKey === 'market_value'" class="text-blue-400">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('unrealized_pnl')" class="py-2.5 text-right cursor-pointer hover:text-zinc-300 transition-colors">
                <div class="flex items-center justify-end gap-1">
                  <span>Unrealized PnL</span>
                  <span v-if="sortKey === 'unrealized_pnl'" class="text-blue-400">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th @click="toggleSort('total_realized_pnl')" class="py-2.5 text-right cursor-pointer hover:text-zinc-300 transition-colors">
                <div class="flex items-center justify-end gap-1">
                  <span>Realized PnL</span>
                  <span v-if="sortKey === 'total_realized_pnl'" class="text-blue-400">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
                </div>
              </th>
              <th class="py-2.5 text-right pr-4">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr
              v-for="holding in displayedHoldings"
              :key="holding.id"
              class="hover:bg-zinc-900/40 transition-colors"
            >
              <!-- Symbol / Name (Sticky Column) -->
              <td class="py-2.5 pl-4 sticky left-0 bg-zinc-950/90 backdrop-blur z-10">
                <div class="flex items-center gap-2">
                  <button
                    @click="goToAssetDetail(holding.ticker, holding.portfolio, holding.id)"
                    class="font-bold text-zinc-100 tracking-wide hover:underline hover:text-blue-400 text-left transition-colors font-mono"
                    title="View asset details, performance & news"
                  >
                    {{ holding.ticker }}
                  </button>
                  <span class="text-[9px] px-1 py-0.2 rounded bg-zinc-800 text-zinc-400 border border-zinc-700/50">
                    {{ holding.asset_type }}
                  </span>
                  <!-- Sub-portfolio badge when viewing All Portfolios -->
                  <span
                    v-if="portfolioStore.selectedPortfolioId === 'ALL' && holding.portfolio_name"
                    class="text-[9px] px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 font-sans"
                    title="Target Portfolio"
                  >
                    {{ holding.portfolio_name }}
                  </span>
                </div>
                <div v-if="holding.name && holding.name !== holding.ticker" class="text-[10px] text-zinc-500 font-sans mt-0.5 truncate max-w-[160px]">
                  {{ holding.name }}
                </div>
              </td>

              <!-- Native Denomination Badge -->
              <td class="py-2.5 text-center">
                <span
                  class="text-[10px] font-mono px-1.5 py-0.5 rounded border font-semibold"
                  :class="holding.currency === 'USD' ? 'bg-blue-950/30 text-blue-400 border-blue-500/30' : 'bg-zinc-900 text-zinc-300 border-zinc-700/60'"
                >
                  {{ holding.currency || 'THB' }}
                </span>
              </td>

              <!-- Shares (8-decimal precision) -->
              <td class="py-2.5 text-right text-zinc-300 tabular-nums">
                {{ formatShares(holding.position.shares) }}
              </td>

              <!-- Avg Cost (Converted to active view currency + native preview) -->
              <td class="py-2.5 text-right text-zinc-400 tabular-nums">
                <div>
                  {{ currSymbol }}{{ formatHoldingPrice(holding, 'avg_cost') }}
                </div>
                <div
                  v-if="holding.currency !== portfolioStore.displayCurrency"
                  class="text-[9px] text-zinc-600"
                >
                  ({{ getHoldingNativeSymbol(holding) }}{{ formatPrice(holding.position.avg_cost) }})
                </div>
              </td>

              <!-- Market Price (Converted to active view currency + native preview) -->
              <td class="py-2.5 text-right text-zinc-200 font-semibold tabular-nums">
                <div class="flex items-center justify-end gap-1.5">
                  <span
                    v-if="holding.position.market_session === 'PRE'"
                    class="text-[9px] font-mono px-1 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 font-bold"
                    title="Pre-Market Live Price"
                  >
                    PRE
                  </span>
                  <span
                    v-else-if="holding.position.market_session === 'POST'"
                    class="text-[9px] font-mono px-1 py-0.2 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30 font-bold"
                    title="Post-Market / Extended Hours Price"
                  >
                    POST
                  </span>
                  <span>{{ currSymbol }}{{ formatHoldingPrice(holding, 'current_price') }}</span>
                </div>
                <div
                  v-if="holding.currency !== portfolioStore.displayCurrency"
                  class="text-[9px] text-zinc-500 font-normal"
                >
                  ({{ getHoldingNativeSymbol(holding) }}{{ formatPrice(holding.position.current_price) }})
                </div>
              </td>

              <!-- Market Value (in active view currency) -->
              <td class="py-2.5 text-right text-zinc-100 font-semibold tabular-nums">
                {{ currSymbol }}{{ formatHoldingValue(holding, 'market_value') }}
              </td>

              <!-- Unrealized PnL -->
              <td class="py-2.5 text-right tabular-nums">
                <span
                  class="font-medium"
                  :class="getHoldingPnL(holding) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
                >
                  {{ getHoldingPnL(holding) >= 0 ? '+' : '' }}{{ currSymbol }}{{ formatNumber(getHoldingPnL(holding)) }}
                </span>
                <span
                  class="text-[10px] ml-1"
                  :class="holding.position.unrealized_pnl_pct >= 0 ? 'text-emerald-500' : 'text-rose-500'"
                >
                  ({{ holding.position.unrealized_pnl_pct >= 0 ? '+' : '' }}{{ Number(holding.position.unrealized_pnl_pct).toFixed(2) }}%)
                </span>
              </td>

              <!-- Realized PnL -->
              <td class="py-2.5 text-right text-zinc-400 tabular-nums">
                <span :class="getHoldingRealizedPnL(holding) > 0 ? 'text-emerald-400' : ''">
                  {{ getHoldingRealizedPnL(holding) > 0 ? '+' : '' }}{{ currSymbol }}{{ formatNumber(getHoldingRealizedPnL(holding)) }}
                </span>
              </td>

              <!-- Action -->
              <td class="py-2.5 text-right pr-4">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    @click="goToAssetDetail(holding.ticker, holding.portfolio, holding.id)"
                    class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] text-blue-400 hover:text-blue-300 font-semibold transition-colors"
                    title="View asset details, executions & news"
                  >
                    Details →
                  </button>
                  <button
                    @click="openAddModal(holding)"
                    class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[10px] text-zinc-300 transition-colors"
                  >
                    Trade
                  </button>
                  <button
                    @click="openEditHolding(holding)"
                    class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
                    title="Edit asset settings (currency, name, notes)"
                  >
                    <Edit2 class="w-3 h-3" />
                  </button>
                  <button
                    @click="openMoveHolding(holding)"
                    class="p-1 rounded text-zinc-500 hover:text-blue-400 transition-colors"
                    title="Move asset to another portfolio"
                  >
                    <FolderInput class="w-3 h-3" />
                  </button>
                  <button
                    @click="confirmDeleteHolding(holding)"
                    class="p-1 rounded text-zinc-600 hover:text-rose-400 transition-colors"
                    title="Delete asset"
                  >
                    <Trash2 class="w-3 h-3" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB: Watchlist (Pre-investment & Targeted Assets) -->
    <div v-else-if="activeTab === 'watchlist'" class="space-y-4">
      <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 p-5 space-y-4">
        <!-- Header & Quick Add Input -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-800/60">
          <div>
            <div class="flex items-center gap-2">
              <Star class="w-4 h-4 text-amber-400 fill-amber-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Watchlist & Pre-Investment Assets</h2>
            </div>
            <p class="text-xs text-zinc-500 mt-0.5">
              ติดตามความเคลื่อนไหว กราฟราคา และข่าวกรอง AI ของสินทรัพย์ที่กำลังเล็งไว้ก่อนตัดสินใจเข้าซื้อ
            </p>
          </div>

          <!-- Quick Add to Watchlist with Autocomplete -->
          <div ref="watchlistSearchContainerRef" class="relative">
            <div class="flex items-center gap-2">
              <div class="relative">
                <Search class="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  v-model="watchlistSearchQuery"
                  @input="handleWatchlistSearchInput"
                  @keyup.enter="handleQuickAddWatchlist"
                  @focus="showWatchlistAutocomplete = true"
                  placeholder="ค้นหาหรือเพิ่ม Ticker (NVDA, PTT)..."
                  class="pl-8 pr-3 py-1.5 rounded-md bg-zinc-950 border border-zinc-800 focus:border-zinc-600 text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none w-72 font-mono"
                />
              </div>
              <button
                @click="handleQuickAddWatchlist"
                :disabled="isAddingToWatchlist || !watchlistSearchQuery.trim()"
                class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50 shadow"
              >
                <Plus class="w-3.5 h-3.5" />
                <span>เพิ่ม Watchlist</span>
              </button>
            </div>

            <!-- Autocomplete Dropdown for Watchlist Quick Add -->
            <div
              v-if="showWatchlistAutocomplete && watchlistSearchResults.length > 0 && watchlistSearchQuery.trim()"
              class="absolute right-0 left-0 mt-1.5 max-h-56 overflow-y-auto rounded-lg bg-zinc-950/95 border border-zinc-800 shadow-xl z-50 divide-y divide-zinc-800/60"
            >
              <div
                v-for="res in watchlistSearchResults"
                :key="res.ticker"
                @click="addTickerToWatchlistFromSearch(res.ticker)"
                class="p-2 px-3 hover:bg-zinc-900 cursor-pointer transition-colors flex items-center justify-between text-xs font-mono"
              >
                <div>
                  <span class="font-bold text-zinc-200">{{ res.ticker }}</span>
                  <span class="text-[10px] text-zinc-400 font-sans ml-1.5 truncate max-w-[140px]">{{ res.name }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <span v-if="res.price" class="text-zinc-400 text-[11px]">
                    {{ res.currency === 'USD' ? '$' : '฿' }}{{ formatPrice(res.price) }}
                  </span>
                  <span
                    class="text-[9px] px-1.5 py-0.5 rounded border"
                    :class="portfolioStore.isWatchlisted(res.ticker) ? 'bg-amber-950/40 text-amber-400 border-amber-500/30' : 'bg-zinc-900 text-zinc-300 border-zinc-700'"
                  >
                    {{ portfolioStore.isWatchlisted(res.ticker) ? 'Added' : '+ Add' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Watchlist Empty State -->
        <div
          v-if="portfolioStore.watchlist.length === 0"
          class="p-12 text-center rounded-lg bg-zinc-950/40 border border-zinc-800/60 space-y-3"
        >
          <div class="w-10 h-10 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto text-amber-400">
            <Star class="w-5 h-5" />
          </div>
          <div class="text-xs font-mono text-zinc-300 font-semibold">ยังไม่มีสินทรัพย์ใน Watchlist</div>
          <p class="text-xs text-zinc-500 font-sans max-w-md mx-auto leading-relaxed">
            เพิ่มหุ้นที่คุณกำลังสนใจเพื่อติดตามราคาก่อนเข้าซื้อ ระบบจะทำการกวาดข่าวและสรุปผลกระทบด้วย AI ให้ทันที
          </p>
        </div>

        <!-- Watchlist Grid -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <div
            v-for="item in portfolioStore.watchlist"
            :key="item.id"
            class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 hover:border-zinc-700/80 transition-all shadow-sm space-y-3"
          >
            <!-- Card Top: Ticker & Actions -->
            <div class="flex items-start justify-between gap-2">
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-mono font-bold text-sm text-zinc-100">{{ item.ticker }}</span>
                  <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
                    {{ item.asset_type }}
                  </span>
                </div>
                <div class="text-xs text-zinc-400 font-sans truncate max-w-[200px] mt-0.5">
                  {{ item.name || item.ticker }}
                </div>
              </div>

              <button
                @click="handleRemoveWatchlist(item.ticker)"
                class="text-zinc-600 hover:text-rose-400 p-1 transition-colors"
                title="นำออกจาก Watchlist"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>

            <!-- Price & Daily Change -->
            <div class="flex items-baseline justify-between pt-1 border-t border-zinc-800/60">
              <div>
                <div class="text-[10px] font-mono uppercase text-zinc-500">Market Price</div>
                <div class="text-base font-bold font-mono text-zinc-100 tabular-nums">
                  {{ item.currency === 'USD' ? '$' : '฿' }}{{ formatNumber(item.current_price || 0) }}
                </div>
              </div>

              <div class="text-right">
                <div class="text-[10px] font-mono uppercase text-zinc-500">24h Return</div>
                <div
                  class="text-xs font-mono font-bold tabular-nums"
                  :class="Number(item.change_pct || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
                >
                  {{ Number(item.change_pct || 0) >= 0 ? '+' : '' }}{{ Number(item.change_pct || 0).toFixed(2) }}%
                </div>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="flex items-center gap-2 pt-2 border-t border-zinc-800/60">
              <button
                @click="goToAssetDetail(item.ticker)"
                class="flex-1 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-300 hover:text-white transition-colors flex items-center justify-center gap-1.5"
              >
                <span>ดูกราฟ & ข่าว AI</span>
                <span>→</span>
              </button>

              <button
                @click="openBuyModalForTicker(item.ticker)"
                class="px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-colors flex items-center justify-center gap-1 shadow"
              >
                <Plus class="w-3.5 h-3.5" />
                <span>ซื้อ</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: Market Intelligence News -->
    <div v-else-if="activeTab === 'news'" class="space-y-4">
      <div class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 p-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-800/60">
          <div>
            <div class="flex items-center gap-2">
              <Newspaper class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Market Intelligence</h2>
            </div>
            <p class="text-xs text-zinc-500 mt-0.5">
              Multi-source financial news (Yahoo Finance & Google News) enriched with Gemini Thai translation
            </p>
          </div>

          <div class="flex items-center gap-2">
            <!-- Search Any Ticker News Bar -->
            <div class="relative">
              <input
                v-model="searchTickerNewsQuery"
                @keyup.enter="handleSearchNewsTicker"
                placeholder="ค้นหาข่าวหุ้นใดๆ (เช่น NVDA)..."
                class="px-3 py-1.5 rounded-md bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 w-56"
              />
            </div>
            <button
              @click="handleSearchNewsTicker"
              class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-300"
              title="ค้นหาข่าวหุ้น"
            >
              <Search class="w-3.5 h-3.5" />
            </button>

            <button
              @click="handleSyncNews"
              :disabled="portfolioStore.isSyncingNews"
              class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-300 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': portfolioStore.isSyncingNews }" />
              <span>{{ portfolioStore.isSyncingNews ? 'Syncing...' : 'Sync News' }}</span>
            </button>
          </div>
        </div>

        <!-- Filter Pills & Options -->
        <div class="pt-3 flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-1.5">
            <!-- Scope Pills -->
            <button
              @click="selectNewsScope('ALL')"
              class="px-2.5 py-1 rounded text-xs font-mono transition-colors border"
              :class="newsScope === 'ALL' && !selectedTicker ? 'bg-zinc-100 text-zinc-950 font-semibold border-zinc-100' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'"
            >
              All Assets
            </button>

            <button
              @click="selectNewsScope('HELD')"
              class="px-2.5 py-1 rounded text-xs font-mono transition-colors border"
              :class="newsScope === 'HELD' && !selectedTicker ? 'bg-zinc-100 text-zinc-950 font-semibold border-zinc-100' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'"
            >
              Holdings Only
            </button>

            <button
              @click="selectNewsScope('WATCHLIST')"
              class="px-2.5 py-1 rounded text-xs font-mono transition-colors border flex items-center gap-1"
              :class="newsScope === 'WATCHLIST' && !selectedTicker ? 'bg-amber-400 text-zinc-950 font-semibold border-amber-400' : 'bg-zinc-900 text-amber-400/80 border-zinc-800 hover:text-amber-300'"
            >
              <Star class="w-3 h-3 fill-current" />
              <span>Watchlist</span>
            </button>

            <span class="text-zinc-700 mx-1">|</span>

            <!-- Ticker Pills -->
            <button
              v-for="h in portfolioStore.holdings"
              :key="h.id"
              @click="selectFilterTicker(h.ticker)"
              class="px-2.5 py-1 rounded text-xs font-mono transition-colors border"
              :class="selectedTicker === h.ticker ? 'bg-zinc-100 text-zinc-950 font-semibold border-zinc-100' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'"
            >
              {{ h.ticker }}
            </button>

            <button
              v-for="w in portfolioStore.watchlist"
              :key="w.id"
              @click="selectFilterTicker(w.ticker)"
              class="px-2.5 py-1 rounded text-xs font-mono transition-colors border flex items-center gap-1"
              :class="selectedTicker === w.ticker ? 'bg-amber-400 text-zinc-950 font-semibold border-amber-400' : 'bg-zinc-900 text-amber-400/70 border-zinc-800 hover:text-amber-300'"
            >
              <Star class="w-2.5 h-2.5 fill-current" />
              <span>{{ w.ticker }}</span>
            </button>
          </div>

          <div class="flex items-center gap-2">
            <label class="flex items-center gap-1.5 text-xs font-mono text-zinc-400 cursor-pointer">
              <input
                type="checkbox"
                v-model="isTodayOnly"
                @change="handleNewsFilterChange"
                class="rounded bg-zinc-900 border-zinc-700 text-zinc-100 focus:ring-0 w-3.5 h-3.5"
              />
              <span>Today Only</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="portfolioStore.isLoadingNews" class="p-12 text-center text-xs text-zinc-500 font-mono">
        <RefreshCw class="w-4 h-4 animate-spin mx-auto mb-2 text-zinc-400" />
        Loading intelligence feed...
      </div>

      <!-- Empty State -->
      <div
        v-else-if="portfolioStore.news.length === 0"
        class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 p-12 text-center space-y-3 font-mono text-xs text-zinc-500"
      >
        <p>No news articles found for {{ selectedTicker ? selectedTicker : 'your portfolio' }}.</p>
        <button
          @click="handleSyncNews"
          class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-sans transition-colors inline-block"
        >
          Sync Latest News Now
        </button>
      </div>

      <!-- News Articles Cards -->
      <div v-else class="space-y-3">
        <div
          v-for="article in portfolioStore.news"
          :key="article.id"
          class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700/80 transition-all font-sans"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-zinc-800/50">
            <div class="flex flex-wrap items-center gap-2">
              <button
                @click="goToAssetDetail(article.ticker)"
                class="px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-zinc-800 text-zinc-100 hover:text-blue-400 border border-zinc-700/60 transition-colors"
                title="View asset details & executions"
              >
                {{ article.ticker }}
              </button>

              <span class="text-[10px] font-mono text-zinc-400 uppercase">
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

            <!-- Per-card Language Switcher [EN / TH] -->
            <div class="flex items-center gap-1.5 self-end sm:self-auto">
              <span class="text-[10px] font-mono text-zinc-500 uppercase">Lang:</span>
              <div class="inline-flex rounded-md bg-zinc-900 border border-zinc-800 p-0.5 text-[10px] font-mono">
                <button
                  @click="setArticleLang(article.id, 'EN')"
                  class="px-2 py-0.5 rounded transition-colors"
                  :class="getArticleLang(article.id) === 'EN' ? 'bg-zinc-800 text-zinc-100 font-bold' : 'text-zinc-500 hover:text-zinc-300'"
                >
                  EN
                </button>
                <button
                  @click="toggleThaiLang(article)"
                  :disabled="translatingIds.has(article.id)"
                  class="px-2 py-0.5 rounded transition-colors flex items-center gap-1"
                  :class="getArticleLang(article.id) === 'TH' ? 'bg-zinc-800 text-zinc-100 font-bold' : 'text-zinc-500 hover:text-zinc-300'"
                >
                  <span>TH</span>
                  <RefreshCw v-if="translatingIds.has(article.id)" class="w-2.5 h-2.5 animate-spin" />
                </button>
              </div>
            </div>
          </div>

          <!-- Article Content -->
          <div class="mt-3 space-y-1.5">
            <h3
              @click="goToNewsDetail(article.id)"
              class="text-sm font-semibold text-zinc-100 leading-snug cursor-pointer hover:text-blue-400 transition-colors"
            >
              {{ getArticleTitle(article) }}
            </h3>

            <p
              @click="goToNewsDetail(article.id)"
              v-if="getArticleSummary(article)"
              class="text-xs text-zinc-400 leading-relaxed font-sans cursor-pointer line-clamp-2 hover:text-zinc-300 transition-colors"
            >
              {{ getArticleSummary(article) }}
            </p>
          </div>

          <!-- Bottom Footer -->
          <div class="mt-3.5 pt-2 border-t border-zinc-800/40 flex items-center justify-between text-xs">
            <div class="flex items-center gap-2">
              <span
                v-if="article.title_th"
                class="text-[10px] font-mono text-emerald-400 flex items-center gap-1"
                title="Translation cached in DB"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Gemini translation ready
              </span>
            </div>

            <div class="flex items-center gap-3">
              <button
                @click="goToNewsDetail(article.id)"
                class="inline-flex items-center gap-1 text-[11px] font-mono text-blue-400 hover:text-blue-300 font-semibold transition-colors"
              >
                <span>Read Full Article Page →</span>
              </button>

              <a
                :href="article.url"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1 text-[11px] font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <span>Original</span>
                <ExternalLink class="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>

        <!-- Pagination Controls -->
        <div v-if="portfolioStore.newsTotalCount > 50" class="flex items-center justify-between p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80 font-mono text-xs text-zinc-400">
          <div>
            Showing {{ portfolioStore.news.length }} of {{ portfolioStore.newsTotalCount }} articles
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="changeNewsPage(currentNewsPage - 1)"
              :disabled="currentNewsPage <= 1"
              class="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-zinc-300 disabled:opacity-40"
            >
              Prev
            </button>
            <span class="text-zinc-200">Page {{ currentNewsPage }} of {{ totalNewsPages }}</span>
            <button
              @click="changeNewsPage(currentNewsPage + 1)"
              :disabled="currentNewsPage >= totalNewsPages"
              class="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-zinc-300 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: Recent Transactions Feed -->
    <div v-else-if="activeTab === 'transactions'" class="rounded-lg bg-zinc-900/30 border border-zinc-800/80">
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <History class="w-3.5 h-3.5 text-zinc-400" />
          <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Recent Executions</h2>
        </div>
        <span class="text-[11px] font-mono text-zinc-500">{{ portfolioStore.transactions.length }} Trades</span>
      </div>

      <div v-if="portfolioStore.transactions.length === 0" class="p-8 text-center text-xs text-zinc-500 font-mono">
        No execution history.
      </div>

      <div v-else class="divide-y divide-zinc-800/50 font-mono text-xs">
        <div
          v-for="tx in portfolioStore.transactions"
          :key="tx.id"
          class="px-5 py-2.5 flex items-center justify-between hover:bg-zinc-900/40 transition-colors"
        >
          <div class="flex items-center gap-3">
            <span
              class="px-1.5 py-0.2 rounded text-[9px] font-mono border"
              :class="getTransactionBadgeClass(tx.transaction_type)"
            >
              {{ tx.transaction_type }}
            </span>
            <div>
              <div class="flex items-center gap-1.5">
                <span class="font-bold text-zinc-100">{{ tx.holding_ticker }}</span>
                <span class="text-[9px] px-1 py-0.1 rounded border font-semibold bg-zinc-900 text-zinc-400 border-zinc-800">
                  {{ tx.currency || tx.holding_currency || 'THB' }}
                </span>
              </div>
              <div class="text-[10px] text-zinc-500 mt-0.5">
                {{ new Date(tx.executed_at).toLocaleDateString('en-GB') }} {{ tx.notes ? '• ' + tx.notes : '' }}
              </div>
            </div>
          </div>

          <div class="flex items-center gap-4 tabular-nums">
            <span class="text-zinc-300">
              {{ formatShares(tx.shares) }} @ {{ getTxCurrencySymbol(tx) }}{{ formatPrice(tx.price_per_share) }}
            </span>
            <div class="text-right min-w-[90px]">
              <div class="text-zinc-100 font-medium">
                {{ getTxCurrencySymbol(tx) }}{{ getTxNetAmount(tx).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </div>
            </div>
            <div class="flex items-center gap-1">
              <button
                @click="openEditTransaction(tx)"
                class="text-zinc-500 hover:text-zinc-200 transition-colors p-1"
                title="Edit trade execution"
              >
                <Edit2 class="w-3 h-3" />
              </button>
              <button
                @click="confirmDeleteTransaction(tx.id)"
                class="text-zinc-600 hover:text-rose-400 transition-colors p-1"
                title="Delete execution"
              >
                <X class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Transaction Modal -->
    <AddTransactionModal
      :is-open="showAddModal"
      :prefill-ticker="prefillTicker"
      :prefill-holding-id="prefillHoldingId"
      :editing-transaction="selectedEditingTx"
      @close="closeAddModal"
      @saved="handleModalSaved"
    />

    <!-- Edit Holding Modal -->
    <EditHoldingModal
      :is-open="showEditHoldingModal"
      :holding="selectedHoldingToEdit"
      @close="showEditHoldingModal = false"
      @saved="handleHoldingSaved"
    />

    <!-- Create Portfolio Modal (Dime-style) -->
    <CreatePortfolioModal
      :is-open="showCreatePortfolioModal"
      @close="showCreatePortfolioModal = false"
      @created="handlePortfolioCreated"
    />

    <!-- Edit Portfolio Modal -->
    <EditPortfolioModal
      :is-open="showEditPortfolioModal"
      :portfolio="selectedPortfolioForEdit"
      @close="showEditPortfolioModal = false"
      @saved="handlePortfolioUpdated"
    />

    <!-- Move Holding Modal -->
    <MoveHoldingModal
      :is-open="showMoveModal"
      :holding="selectedHoldingToMove"
      @close="showMoveModal = false"
      @moved="handleHoldingMoved"
    />

    <!-- Custom Dark Confirmation Modal -->
    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      @confirm="handleConfirmAction"
      @cancel="confirmModal.isOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '../stores/portfolio'
import { useToastStore } from '../stores/toast'
import AddTransactionModal from '../components/portfolio/AddTransactionModal.vue'
import EditHoldingModal from '../components/portfolio/EditHoldingModal.vue'
import CreatePortfolioModal from '../components/portfolio/CreatePortfolioModal.vue'
import EditPortfolioModal from '../components/portfolio/EditPortfolioModal.vue'
import MoveHoldingModal from '../components/portfolio/MoveHoldingModal.vue'
import ConfirmModal from '../components/common/ConfirmModal.vue'
import AssetAllocationChart from '../components/portfolio/AssetAllocationChart.vue'
import type { StockHolding, StockTransaction, StockNewsArticle, InvestmentPortfolio, MarketAssetSearchResult } from '../types/portfolio'
import {
  TrendingUp,
  RefreshCw,
  Plus,
  Trash2,
  History,
  X,
  Newspaper,
  ExternalLink,
  Edit2,
  Globe,
  FolderPlus,
  FolderInput,
  Star,
  Search,
  Loader2,
  ArrowRight
} from 'lucide-vue-next'

const portfolioStore = usePortfolioStore()
const toast = useToastStore()
const router = useRouter()

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

function getTxNetAmount(tx: StockTransaction): number {
  const subtotal = Number(tx.shares || 0) * Number(tx.price_per_share || 0)
  const fee = Number(tx.fee || 0)
  if (tx.transaction_type === 'BUY') {
    return subtotal + fee
  } else {
    return Math.max(0, subtotal - fee)
  }
}

function goToNewsDetail(articleId: string) {
  if (!articleId) return
  router.push(`/portfolio/news/${articleId}`)
}

// Universal Market Asset Search Bar State (ค้นหา Ticker ได้จากทุก Tab ทุกเวลา)
const universalSearchQuery = ref('')
const universalSearchResults = ref<MarketAssetSearchResult[]>([])
const isUniversalSearching = ref(false)
const showUniversalSearchResults = ref(false)
const selectedResultIndex = ref(-1)
const universalSearchContainerRef = ref<HTMLElement | null>(null)
const universalSearchInputRef = ref<HTMLInputElement | null>(null)
let universalSearchDebounceTimer: ReturnType<typeof setTimeout> | null = null

// Watchlist Quick Add Autocomplete State
const watchlistSearchResults = ref<MarketAssetSearchResult[]>([])
const showWatchlistAutocomplete = ref(false)
const watchlistSearchContainerRef = ref<HTMLElement | null>(null)
let watchlistSearchDebounceTimer: ReturnType<typeof setTimeout> | null = null

function handleUniversalSearchInput() {
  if (universalSearchDebounceTimer) clearTimeout(universalSearchDebounceTimer)
  const q = universalSearchQuery.value.trim()
  if (!q) {
    universalSearchResults.value = []
    isUniversalSearching.value = false
    selectedResultIndex.value = -1
    return
  }

  isUniversalSearching.value = true
  universalSearchDebounceTimer = setTimeout(async () => {
    try {
      const results = await portfolioStore.searchAssets(q)
      universalSearchResults.value = results
      showUniversalSearchResults.value = true
      selectedResultIndex.value = -1
    } catch {
      universalSearchResults.value = []
    } finally {
      isUniversalSearching.value = false
    }
  }, 160)
}

function handleUniversalSearchFocus() {
  showUniversalSearchResults.value = true
  if (universalSearchQuery.value.trim() && universalSearchResults.value.length === 0) {
    handleUniversalSearchInput()
  }
}

function navigateSearchResults(direction: number) {
  if (!universalSearchResults.value.length) return
  const max = universalSearchResults.value.length - 1
  selectedResultIndex.value = Math.max(-1, Math.min(max, selectedResultIndex.value + direction))
}

function handleUniversalSearchEnter() {
  if (selectedResultIndex.value >= 0 && universalSearchResults.value[selectedResultIndex.value]) {
    const item = universalSearchResults.value[selectedResultIndex.value]
    selectSearchAsset(item.ticker)
  } else if (universalSearchQuery.value.trim()) {
    selectSearchAsset(universalSearchQuery.value.trim())
  }
}

function selectSearchAsset(ticker: string) {
  if (!ticker) return
  showUniversalSearchResults.value = false
  universalSearchQuery.value = ''
  goToAssetDetail(ticker)
}

function closeUniversalSearch() {
  showUniversalSearchResults.value = false
  selectedResultIndex.value = -1
}

function handleWatchlistSearchInput() {
  if (watchlistSearchDebounceTimer) clearTimeout(watchlistSearchDebounceTimer)
  const q = watchlistSearchQuery.value.trim()
  if (!q) {
    watchlistSearchResults.value = []
    showWatchlistAutocomplete.value = false
    return
  }
  watchlistSearchDebounceTimer = setTimeout(async () => {
    try {
      const results = await portfolioStore.searchAssets(q)
      watchlistSearchResults.value = results
      showWatchlistAutocomplete.value = true
    } catch {
      watchlistSearchResults.value = []
    }
  }, 180)
}

async function addTickerToWatchlistFromSearch(ticker: string) {
  watchlistSearchQuery.value = ''
  showWatchlistAutocomplete.value = false
  if (portfolioStore.isWatchlisted(ticker)) {
    toast.info(`${ticker} อยู่ใน Watchlist แล้ว`)
    return
  }
  try {
    const added = await portfolioStore.toggleWatchlist(ticker)
    if (added) {
      toast.success(`เพิ่ม ${ticker} เข้าสู่ Watchlist เรียบร้อยแล้ว`)
    }
  } catch (err: any) {
    toast.error(err?.response?.data?.ticker || `ไม่สามารถเพิ่ม ${ticker} ได้`)
  }
}

function isTickerHeld(ticker: string): StockHolding | undefined {
  const clean = ticker.trim().toUpperCase()
  return portfolioStore.holdings.find(h =>
    h.ticker.toUpperCase() === clean ||
    h.ticker.toUpperCase() === `${clean}.BK` ||
    h.ticker.toUpperCase() === `${clean}-USD`
  )
}

function handleGlobalKeydown(e: KeyboardEvent) {
  // '/' or 'Ctrl+K' focuses universal search
  if ((e.key === '/' || (e.ctrlKey && e.key.toLowerCase() === 'k')) && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) {
    e.preventDefault()
    universalSearchInputRef.value?.focus()
    showUniversalSearchResults.value = true
  }
}

function handleClickOutside(e: MouseEvent) {
  if (universalSearchContainerRef.value && !universalSearchContainerRef.value.contains(e.target as Node)) {
    closeUniversalSearch()
  }
  if (watchlistSearchContainerRef.value && !watchlistSearchContainerRef.value.contains(e.target as Node)) {
    showWatchlistAutocomplete.value = false
  }
}

const activeTab = ref<'holdings' | 'watchlist' | 'news' | 'transactions'>('holdings')
const watchlistSearchQuery = ref('')
const isAddingToWatchlist = ref(false)
const newsScope = ref<'ALL' | 'HELD' | 'WATCHLIST'>('ALL')
const searchTickerNewsQuery = ref('')
const showAddModal = ref(false)
const showEditHoldingModal = ref(false)
const showCreatePortfolioModal = ref(false)
const showEditPortfolioModal = ref(false)
const showMoveModal = ref(false)
const selectedPortfolioForEdit = ref<InvestmentPortfolio | null>(null)
const selectedHoldingToMove = ref<StockHolding | null>(null)
const prefillTicker = ref('')
const prefillHoldingId = ref('')
const selectedEditingTx = ref<StockTransaction | null>(null)
const selectedHoldingToEdit = ref<StockHolding | null>(null)
let realtimeSyncTimer: ReturnType<typeof setInterval> | null = null

// Holdings Table Sorting & Active Toggle
const hideClosedPositions = ref(true)
const sortKey = ref<'ticker' | 'currency' | 'shares' | 'avg_cost' | 'current_price' | 'market_value' | 'unrealized_pnl' | 'total_realized_pnl'>('market_value')
const sortOrder = ref<'asc' | 'desc'>('desc')

// Confirm Modal state
const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  action: () => {}
})

function handleConfirmAction() {
  confirmModal.isOpen = false
  confirmModal.action()
}

const assetClassFilters = [
  { value: 'ALL', label: 'All' },
  { value: 'STOCK', label: 'Stocks' },
  { value: 'CRYPTO', label: 'Crypto' },
  { value: 'FUND', label: 'Funds' },
  { value: 'OTHER', label: 'Other' }
] as const

// News filter and per-card language state
const selectedTicker = ref<string | null>(null)
const isTodayOnly = ref(false)
const currentNewsPage = ref(1)
const articleLangMap = reactive<Record<string, 'EN' | 'TH'>>({})
const translatingIds = reactive(new Set<string>())

const currSymbol = computed(() => (portfolioStore.displayCurrency === 'USD' ? '$' : '฿'))

const closedHoldingsCount = computed(() => {
  return portfolioStore.holdings.filter(h => Number(h.position?.shares || 0) <= 0).length
})

const displayedHoldings = computed(() => {
  let list = [...portfolioStore.holdings]
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

const totalNewsPages = computed(() => {
  return Math.ceil(portfolioStore.newsTotalCount / 50) || 1
})

const formattedLastSyncTime = computed(() => {
  if (!portfolioStore.lastPriceSyncTime) return ''
  return portfolioStore.lastPriceSyncTime.toLocaleTimeString('en-GB')
})

const activeSummary = computed(() => {
  if (portfolioStore.displayCurrency === 'USD' && portfolioStore.overview?.summary_usd) {
    return portfolioStore.overview.summary_usd
  }
  if (portfolioStore.overview?.summary_thb) {
    return portfolioStore.overview.summary_thb
  }
  return portfolioStore.overview || {
    total_market_value: 0,
    total_cost_basis: 0,
    total_unrealized_pnl: 0,
    total_unrealized_pnl_pct: 0,
    total_realized_pnl: 0,
    total_dividends: 0,
    asset_allocation: []
  }
})

onMounted(async () => {
  await Promise.all([
    portfolioStore.fetchPortfolios(),
    portfolioStore.fetchOverview({ currency: portfolioStore.displayCurrency }),
    portfolioStore.fetchHoldings(),
    portfolioStore.fetchTransactions(),
    portfolioStore.fetchNews({ page: 1 }),
    portfolioStore.fetchWatchlist(),
    portfolioStore.fetchMarketStatus()
  ])

  // Real-time quotes sync every 1 minute (respecting market trading hours)
  realtimeSyncTimer = setInterval(async () => {
    if (document.visibilityState !== 'visible') return
    try {
      const status = await portfolioStore.fetchMarketStatus()
      if (status.should_poll_realtime || status.is_any_market_open) {
        await portfolioStore.refreshMarketPrices(false) // force=false respects market hours
      }
    } catch {
      // Graceful catch for background polling
    }
  }, 60000)

  // Universal Search Global Keyboard & Click Outside listeners
  window.addEventListener('keydown', handleGlobalKeydown)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  if (realtimeSyncTimer) clearInterval(realtimeSyncTimer)
  window.removeEventListener('keydown', handleGlobalKeydown)
  document.removeEventListener('click', handleClickOutside)
})

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

function getHoldingNativeSymbol(holding: StockHolding): string {
  return (holding.currency || 'THB').toUpperCase() === 'USD' ? '$' : '฿'
}

function getTxCurrencySymbol(tx: StockTransaction): string {
  const curr = (tx.currency || tx.holding_currency || 'THB').toUpperCase()
  return curr === 'USD' ? '$' : '฿'
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

function switchTab(tab: 'holdings' | 'watchlist' | 'news' | 'transactions') {
  activeTab.value = tab
  if (tab === 'watchlist') {
    portfolioStore.fetchWatchlist()
  } else if (tab === 'news' && portfolioStore.news.length === 0) {
    loadNews()
  }
}

async function handleQuickAddWatchlist() {
  const t = watchlistSearchQuery.value.trim().toUpperCase()
  if (!t) return
  // F10: ตรวจสอบก่อนว่ามีใน Watchlist แล้วหรือไม่ เพื่อไม่ให้กดซ้ำแล้วกลายเป็นการลบ
  if (portfolioStore.isWatchlisted(t)) {
    toast.info(`${t} อยู่ใน Watchlist แล้ว`)
    watchlistSearchQuery.value = ''
    return
  }
  isAddingToWatchlist.value = true
  try {
    const isAdded = await portfolioStore.toggleWatchlist(t)
    watchlistSearchQuery.value = ''
    if (isAdded) {
      toast.success(`เพิ่ม ${t} เข้าสู่ Watchlist เรียบร้อยแล้ว`)
    } else {
      toast.info(`นำ ${t} ออกจาก Watchlist เรียบร้อยแล้ว`)
    }
  } catch (err: any) {
    toast.error(err?.response?.data?.ticker || `ไม่สามารถเพิ่ม ${t} ใน Watchlist ได้`)
  } finally {
    isAddingToWatchlist.value = false
  }
}

async function handleRemoveWatchlist(ticker: string) {
  try {
    const isAdded = await portfolioStore.toggleWatchlist(ticker)
    if (!isAdded) {
      toast.success(`นำ ${ticker} ออกจาก Watchlist เรียบร้อยแล้ว`)
    } else {
      toast.info(`เพิ่ม ${ticker} ใน Watchlist แล้ว`)
    }
  } catch (err) {
    toast.error(`ไม่สามารถนำ ${ticker} ออกจาก Watchlist ได้`)
  }
}

function openBuyModalForTicker(ticker: string) {
  prefillTicker.value = ticker
  prefillHoldingId.value = ''
  selectedEditingTx.value = null
  showAddModal.value = true
}

async function selectNewsScope(scope: 'ALL' | 'HELD' | 'WATCHLIST') {
  newsScope.value = scope
  selectedTicker.value = null
  searchTickerNewsQuery.value = ''
  currentNewsPage.value = 1
  await loadNews()
}

async function handleSearchNewsTicker() {
  const t = searchTickerNewsQuery.value.trim().toUpperCase()
  if (!t) {
    selectedTicker.value = null
  } else {
    selectedTicker.value = t
  }
  currentNewsPage.value = 1
  await loadNews()
}

function selectFilterTicker(ticker: string | null) {
  selectedTicker.value = ticker
  searchTickerNewsQuery.value = ''
  currentNewsPage.value = 1
  loadNews()
}

function handleNewsFilterChange() {
  currentNewsPage.value = 1
  loadNews()
}

function changeNewsPage(page: number) {
  currentNewsPage.value = page
  loadNews()
}

async function loadNews() {
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
}

async function handleSyncNews() {
  try {
    await portfolioStore.syncNews()
    toast.success('Market news synced and translated')
    await loadNews()
  } catch (err) {
    toast.error('Failed to sync market news')
  }
}

function getArticleLang(id: string): 'EN' | 'TH' {
  return articleLangMap[id] || 'EN'
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
  } catch (err) {
    toast.error('Failed to translate article')
  } finally {
    translatingIds.delete(article.id)
  }
}

function getArticleTitle(article: StockNewsArticle): string {
  if (getArticleLang(article.id) === 'TH' && article.title_th) {
    return article.title_th
  }
  return article.title
}

function getArticleSummary(article: StockNewsArticle): string {
  if (getArticleLang(article.id) === 'TH' && article.summary_th) {
    return article.summary_th
  }
  return article.summary || ''
}

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
  return d.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getTransactionBadgeClass = (type: string) => {
  switch (type) {
    case 'BUY':
      return 'bg-zinc-900 text-emerald-400 border-zinc-800'
    case 'SELL':
      return 'bg-zinc-900 text-rose-400 border-zinc-800'
    case 'DIVIDEND':
      return 'bg-zinc-900 text-amber-400 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

const openAddModal = (holding?: StockHolding) => {
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

const openEditTransaction = (tx: StockTransaction) => {
  selectedEditingTx.value = tx
  prefillTicker.value = tx.holding_ticker || tx.ticker || ''
  prefillHoldingId.value = tx.holding || ''
  showAddModal.value = true
}

const openEditHolding = (holding: StockHolding) => {
  selectedHoldingToEdit.value = holding
  showEditHoldingModal.value = true
}

const openMoveHolding = (holding: StockHolding) => {
  selectedHoldingToMove.value = holding
  showMoveModal.value = true
}

const handleHoldingMoved = async () => {
  // Store has already refreshed
}

const closeAddModal = () => {
  showAddModal.value = false
  selectedEditingTx.value = null
}

const handleRefreshPrices = async () => {
  try {
    await portfolioStore.refreshMarketPrices(true)
    await portfolioStore.fetchMarketStatus()
    toast.success('Market quotes and USD/THB exchange rate refreshed')
  } catch (err) {
    toast.error('Failed to refresh market prices')
  }
}

const handleModalSaved = async () => {
  toast.success('Trade execution recorded and updated')
}

const handleHoldingSaved = async () => {
  // Handled
}

function openEditPortfolio(p: InvestmentPortfolio) {
  selectedPortfolioForEdit.value = p
  showEditPortfolioModal.value = true
}

function handlePortfolioUpdated(updated: InvestmentPortfolio) {
  toast.success(`Updated portfolio "${updated.name}"`)
}

const confirmDeleteHolding = (holding: StockHolding) => {
  confirmModal.title = 'Delete Holding'
  confirmModal.message = `Are you sure you want to delete holding ${holding.ticker} and all its transaction history?`
  confirmModal.confirmText = 'Delete Holding'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await portfolioStore.deleteHolding(holding.id)
      toast.info(`Deleted holding ${holding.ticker}`)
    } catch (err) {
      toast.error('Failed to delete holding')
    }
  }
  confirmModal.isOpen = true
}

const confirmDeleteTransaction = (id: string) => {
  confirmModal.title = 'Delete Execution'
  confirmModal.message = 'Are you sure you want to delete this trade execution? Portfolio metrics will recalculate.'
  confirmModal.confirmText = 'Delete Execution'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await portfolioStore.deleteTransaction(id)
      toast.info('Deleted transaction record')
    } catch (err) {
      toast.error('Failed to delete transaction')
    }
  }
  confirmModal.isOpen = true
}

const handlePortfolioCreated = async (created: InvestmentPortfolio) => {
  toast.success(`Created portfolio "${created.name}"`)
  await portfolioStore.setSelectedPortfolio(created.id)
}

const confirmDeletePortfolio = (p: InvestmentPortfolio) => {
  if (p.is_default) {
    toast.error('Default portfolio cannot be deleted')
    return
  }
  confirmModal.title = 'Delete Portfolio'
  confirmModal.message = `Are you sure you want to delete portfolio "${p.name}"? Holdings under this portfolio will be removed.`
  confirmModal.confirmText = 'Delete Portfolio'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await portfolioStore.deletePortfolio(p.id)
      toast.info(`Deleted portfolio "${p.name}"`)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to delete portfolio')
    }
  }
  confirmModal.isOpen = true
}
</script>