<template>
  <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3 text-xs font-mono px-3.5 py-2.5 rounded-lg bg-zinc-900/30 border border-zinc-800/60">
    <!-- Left: Currency View Toggle & Real-time Rate -->
    <div class="flex flex-wrap items-center gap-3">
      <div class="flex items-center gap-1 bg-zinc-950 border border-zinc-800/80 rounded-md p-0.5">
        <button
          @click="portfolioStore.setDisplayCurrency('THB')"
          type="button"
          class="px-2 py-0.5 rounded text-[11px] font-semibold transition-colors"
          :class="portfolioStore.displayCurrency === 'THB' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
        >
          ฿ THB
        </button>
        <button
          @click="portfolioStore.setDisplayCurrency('USD')"
          type="button"
          class="px-2 py-0.5 rounded text-[11px] font-semibold transition-colors"
          :class="portfolioStore.displayCurrency === 'USD' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'"
        >
          $ USD
        </button>
      </div>

      <div class="text-[11px] text-zinc-400 flex items-center gap-1.5">
        <span class="text-zinc-500 hidden sm:inline">Rate:</span>
        <span class="text-zinc-200 font-semibold">1 USD = ฿{{ Number(portfolioStore.overview?.usd_to_thb_rate || portfolioStore.usdToThbRate).toFixed(2) }}</span>
      </div>

      <div class="h-3.5 w-px bg-zinc-800/80 hidden sm:block"></div>

      <!-- Market Sessions Badges (SET, US, Crypto) - Monochromatic with precise indicator dot -->
      <div class="flex items-center gap-1.5 flex-wrap">
        <!-- SET Badge -->
        <div
          class="flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px]"
          :class="portfolioStore.marketStatus?.markets.SET.is_open
            ? 'bg-zinc-900/70 text-zinc-300 border-zinc-800'
            : 'bg-zinc-950 text-zinc-500 border-zinc-900'"
          :title="(portfolioStore.marketStatus?.markets.SET.hours_description || '') + ' • ' + (portfolioStore.marketStatus?.markets.SET.opens_at || '')"
        >
          <span
            class="w-1.5 h-1.5 rounded-full shrink-0"
            :class="portfolioStore.marketStatus?.markets.SET.is_open ? 'bg-emerald-400' : 'bg-zinc-700'"
          ></span>
          <span>SET: {{ portfolioStore.marketStatus?.markets.SET.session || 'Closed' }}</span>
        </div>

        <!-- US Markets Badge -->
        <div
          class="flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px]"
          :class="portfolioStore.marketStatus?.markets.US.is_open
            ? 'bg-zinc-900/70 text-zinc-300 border-zinc-800'
            : 'bg-zinc-950 text-zinc-500 border-zinc-900'"
          :title="(portfolioStore.marketStatus?.markets.US.hours_description || '') + ' • ' + (portfolioStore.marketStatus?.markets.US.opens_at || '')"
        >
          <span
            class="w-1.5 h-1.5 rounded-full shrink-0"
            :class="portfolioStore.marketStatus?.markets.US.is_open ? 'bg-emerald-400' : 'bg-zinc-700'"
          ></span>
          <span>US: {{ portfolioStore.marketStatus?.markets.US.session || 'Closed' }}</span>
        </div>

        <!-- Crypto Badge -->
        <div
          class="flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] bg-zinc-900/70 text-zinc-300 border-zinc-800"
          title="Crypto trades 24/7 non-stop"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>
          <span>Crypto: 24/7</span>
        </div>
      </div>
    </div>

    <!-- Right: Real-time Polling Status, Last Synced & Refresh Trigger -->
    <div class="flex flex-wrap items-center justify-between sm:justify-end gap-2.5 w-full lg:w-auto lg:self-center">
      <div
        v-if="portfolioStore.overview?.quote_worker?.healthy"
        class="flex items-center gap-1.5 text-[10px] text-zinc-300 bg-zinc-900/60 border border-zinc-800 px-2 py-0.5 rounded"
      >
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>อัปเดตเบื้องหลัง</span>
      </div>
      <div
        v-else
        class="flex items-center gap-1.5 text-[10px] text-zinc-500 bg-zinc-950 border border-zinc-900 px-2 py-0.5 rounded"
      >
        <span class="w-1.5 h-1.5 rounded-full bg-zinc-700"></span>
        <span>รอการอัปเดตราคา</span>
      </div>

      <span v-if="(portfolioStore.overview?.quote_sync?.stale_count || 0) + (portfolioStore.overview?.quote_sync?.missing_count || 0) > 0" class="text-amber-400 text-[10px]">มีราคาที่เก่าหรือยังไม่ทราบเวลาอ้างอิง</span>
      <div v-if="formattedLastSyncTime" class="text-[10px] text-zinc-500 hidden sm:block">
        ราคาอ้างอิง: <span class="text-zinc-400 font-mono">{{ formattedLastSyncTime }}</span>
      </div>

      <button
        @click="handleRefreshPrices"
        :disabled="portfolioStore.isRefreshing"
        type="button"
        class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] font-sans font-medium text-zinc-300 transition-colors flex items-center gap-1.5 disabled:opacity-50"
        title="Refresh market quotes via yfinance"
      >
        <RefreshCw class="w-3 h-3 text-zinc-400" :class="{ 'animate-spin': portfolioStore.isRefreshing }" />
        <span>{{ portfolioStore.isRefreshing ? 'Fetching...' : 'Refresh Quotes' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { usePortfolioStore } from '../../stores/portfolio'
import { useToastStore } from '../../stores/toast'
import { RefreshCw } from 'lucide-vue-next'

const portfolioStore = usePortfolioStore()
const toast = useToastStore()
let stopPolling: (() => void) | undefined
onMounted(() => { stopPolling = portfolioStore.startQuotePolling() })
onUnmounted(() => stopPolling?.())

const formattedLastSyncTime = computed(() => {
  if (!portfolioStore.lastPriceSyncTime) return ''
  return portfolioStore.lastPriceSyncTime.toLocaleString('th-TH')
})

async function handleRefreshPrices() {
  try {
    const result = await portfolioStore.refreshMarketPrices(true)
    await portfolioStore.fetchMarketStatus()
    if (result.sync?.failed.length) toast.error(`ดึงราคาไม่สำเร็จ: ${result.sync.failed.join(', ')} · ใช้ข้อมูลล่าสุดที่มี`)
    else toast.success(`อัปเดตราคาแล้ว ${result.sync?.refreshed.length || 0} สินทรัพย์`)
  } catch {
    toast.error('Failed to refresh market quotes')
  }
}
</script>
