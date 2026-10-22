<template>
  <div class="rounded-xl bg-zinc-950 border border-zinc-800 p-5 sm:p-6 shadow-xl space-y-4 font-sans select-none relative overflow-hidden">
    <!-- Header: Dynamic Price & Daily / Period Change Rate -->
    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div>
        <div class="text-[11px] font-mono uppercase tracking-wider text-zinc-500 flex items-center gap-2">
          <span>{{ displaySubtitle }}</span>
          <span v-if="hoveredPoint" class="text-zinc-400 font-semibold">• {{ hoveredTimeFormatted }}</span>
        </div>

        <div class="flex items-baseline gap-3 mt-1">
          <!-- Main Price Callout -->
          <span class="text-3xl sm:text-4xl font-bold font-mono tracking-tight text-zinc-100 tabular-nums">
            {{ currencySymbol }}{{ formatPrice(displayPrice) }}
          </span>

          <!-- Change Amount & Percentage Badge -->
          <div
            class="flex items-center gap-1 font-mono text-xs sm:text-sm font-semibold tabular-nums px-2 py-0.5 rounded"
            :class="isPositive ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/30' : 'bg-rose-950/40 text-rose-400 border border-rose-500/30'"
          >
            <span>{{ isPositive ? '+' : '' }}{{ currencySymbol }}{{ formatPrice(displayChangeAmount) }}</span>
            <span>({{ isPositive ? '+' : '' }}{{ displayChangePct.toFixed(2) }}%)</span>
          </div>
        </div>

        <!-- Pre-Market / Post-Market (Extended Hours / Night Market) Secondary Callout (Dime / Webull style) -->
        <div
          v-if="!hoveredPoint && isExtendedSession && activeExtendedPrice"
          class="flex items-center gap-2 mt-2 text-xs font-mono"
        >
          <span
            class="px-1.5 py-0.5 rounded font-semibold text-[10px] flex items-center gap-1"
            :class="activeMarketSession === 'PRE'
              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
              : 'bg-purple-500/10 text-purple-400 border border-purple-500/30'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="activeMarketSession === 'PRE' ? 'bg-amber-400 animate-pulse' : 'bg-purple-400 animate-pulse'"></span>
            <span>{{ activeMarketSession === 'PRE' ? 'Pre-Market' : 'Post-Market' }}</span>
          </span>
          <span class="font-bold text-zinc-100 tabular-nums">
            {{ currencySymbol }}{{ formatPrice(activeExtendedPrice) }}
          </span>
          <span
            v-if="activeExtendedChangePct !== null"
            class="font-semibold tabular-nums text-[11px]"
            :class="(activeExtendedChangePct || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'"
          >
            {{ (activeExtendedChangePct || 0) >= 0 ? '+' : '' }}{{ activeExtendedChange !== null ? currencySymbol + formatPrice(activeExtendedChange) + ' ' : '' }}({{ (activeExtendedChangePct || 0) >= 0 ? '+' : '' }}{{ Number(activeExtendedChangePct || 0).toFixed(2) }}%)
          </span>
        </div>
      </div>

      <!-- Timeframe Selector Pills (Dime style) -->
      <div class="flex items-center gap-1 p-1 bg-zinc-900 border border-zinc-800 rounded-lg self-start sm:self-auto overflow-x-auto max-w-full">
        <button
          v-for="tf in timeframes"
          :key="tf"
          type="button"
          @click="changePeriod(tf)"
          class="px-2.5 py-1 rounded text-xs font-mono transition-colors font-medium cursor-pointer"
          :class="selectedPeriod === tf
            ? 'bg-zinc-800 text-zinc-100 font-bold shadow-sm border border-zinc-700/60'
            : 'text-zinc-400 hover:text-zinc-200'"
        >
          {{ tf }}
        </button>
      </div>
    </div>

    <!-- Chart Canvas Area (Interactive SVG) -->
    <div
      ref="chartContainerRef"
      class="relative w-full h-56 sm:h-72 mt-2 cursor-crosshair touch-none"
      @mousemove="handleMouseMove"
      @mouseleave="handleMouseLeave"
      @touchstart="handleTouchStart"
      @touchmove="handleTouchMove"
      @touchend="handleMouseLeave"
    >
      <!-- Loading Overlay -->
      <div v-if="isLoading" class="absolute inset-0 z-20 bg-zinc-950/60 backdrop-blur-[1px] flex items-center justify-center">
        <div class="flex items-center gap-2 text-xs font-mono text-zinc-400">
          <div class="w-4 h-4 border-2 border-zinc-600 border-t-zinc-200 rounded-full animate-spin"></div>
          <span>Loading {{ selectedPeriod }} candle series...</span>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="!chartData || points.length === 0" class="absolute inset-0 flex flex-col items-center justify-center text-xs text-zinc-500 font-mono space-y-1">
        <span>No historical quotes recorded for {{ selectedPeriod }}.</span>
        <span class="text-[10px] text-zinc-600">Sync is operating normally in the background.</span>
      </div>

      <!-- Main SVG Rendering -->
      <svg
        v-if="points.length > 0"
        class="w-full h-full overflow-visible"
        :viewBox="`0 0 ${viewWidth} ${viewHeight}`"
        preserveAspectRatio="none"
      >
        <defs>
          <!-- Gradient Fill for Area Under Curve -->
          <linearGradient :id="`chartGrad-${uid}`" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="isPositive ? '#10b981' : '#f43f5e'" stop-opacity="0.28" />
            <stop offset="65%" :stop-color="isPositive ? '#10b981' : '#f43f5e'" stop-opacity="0.06" />
            <stop offset="100%" :stop-color="isPositive ? '#10b981' : '#f43f5e'" stop-opacity="0.0" />
          </linearGradient>

          <!-- Glow Filter for Stroke -->
          <filter :id="`glow-${uid}`" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        <!-- Previous Close Baseline (Horizontal Dashed Line) -->
        <line
          v-if="baselineY !== null"
          x1="0"
          :y1="baselineY"
          :x2="viewWidth"
          :y2="baselineY"
          stroke="#3f3f46"
          stroke-dasharray="4 4"
          stroke-width="1"
          opacity="0.8"
        />

        <!-- Area Fill Under Curve -->
        <path
          :d="areaPath"
          :fill="`url(#chartGrad-${uid})`"
        />

        <!-- Line Curve -->
        <path
          :d="linePath"
          fill="none"
          :stroke="isPositive ? '#10b981' : '#f43f5e'"
          stroke-width="2.2"
          stroke-linecap="round"
          stroke-linejoin="round"
          :filter="`url(#glow-${uid})`"
        />

        <!-- Interactive Crosshair (Active on hover/scrub) -->
        <g v-if="hoverX !== null && hoverY !== null">
          <!-- Vertical Tracking Line -->
          <line
            :x1="hoverX"
            y1="0"
            :x2="hoverX"
            :y2="viewHeight"
            stroke="#71717a"
            stroke-dasharray="3 3"
            stroke-width="1.2"
          />

          <!-- Outer Glow Ring on Point -->
          <circle
            :cx="hoverX"
            :cy="hoverY"
            r="6"
            :fill="isPositive ? '#10b981' : '#f43f5e'"
            opacity="0.25"
          />

          <!-- Inner Dot on Curve -->
          <circle
            :cx="hoverX"
            :cy="hoverY"
            r="3.5"
            :fill="isPositive ? '#10b981' : '#f43f5e'"
            stroke="#090a0f"
            stroke-width="1.5"
          />
        </g>
      </svg>

      <!-- Baseline Label Indicator (Right Edge) -->
      <div
        v-if="baselineY !== null && points.length > 0"
        class="absolute right-1 text-[9px] font-mono text-zinc-500 pointer-events-none -translate-y-1/2 bg-zinc-950/80 px-1 rounded border border-zinc-800/60"
        :style="{ top: `${(baselineY / viewHeight) * 100}%` }"
      >
        Prev {{ currencySymbol }}{{ formatPrice(basePrice) }}
      </div>
    </div>

    <!-- Chart Footer: High/Low summary for this timeframe -->
    <div v-if="points.length > 0" class="flex items-center justify-between pt-2 border-t border-zinc-800/60 text-[11px] font-mono text-zinc-500">
      <div class="flex items-center gap-4">
        <div>
          <span>Low: </span>
          <span class="text-zinc-300 font-semibold">{{ currencySymbol }}{{ formatPrice(minPrice) }}</span>
        </div>
        <div>
          <span>High: </span>
          <span class="text-zinc-300 font-semibold">{{ currencySymbol }}{{ formatPrice(maxPrice) }}</span>
        </div>
      </div>

      <div class="flex items-center gap-1.5 text-[10px]">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
        <span>1-min market sync active</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { usePortfolioStore } from '../../stores/portfolio'
import type { StockChartData, StockChartPoint } from '../../types/portfolio'

const props = defineProps<{
  ticker: string
  currency?: string
  currentPrice?: number
  extendedPrice?: number
  extendedChange?: number
  extendedChangePct?: number
  marketSession?: 'REGULAR' | 'PRE' | 'POST' | 'POSTPOST' | 'NIGHT'
}>()

const activeExtendedPrice = computed(() => {
  return chartData.value?.extended_price ?? props.extendedPrice ?? null
})

const activeExtendedChange = computed(() => {
  return chartData.value?.extended_change ?? props.extendedChange ?? null
})

const activeExtendedChangePct = computed(() => {
  return chartData.value?.extended_change_pct ?? props.extendedChangePct ?? null
})

const activeMarketSession = computed(() => {
  return chartData.value?.market_session ?? props.marketSession ?? 'REGULAR'
})

const isExtendedSession = computed(() => {
  return (
    activeExtendedPrice.value !== null &&
    activeExtendedPrice.value !== undefined &&
    activeMarketSession.value !== 'REGULAR'
  )
})

const portfolioStore = usePortfolioStore()
const uid = Math.random().toString(36).substring(2, 9)

const timeframes = ['1D', '5D', '1M', '6M', '1Y', 'ALL'] as const
type Timeframe = typeof timeframes[number]

const selectedPeriod = ref<Timeframe>('1D')
const chartData = ref<StockChartData | null>(null)
const isLoading = ref(false)

const chartContainerRef = ref<HTMLDivElement | null>(null)
const hoveredIndex = ref<number | null>(null)
const hoverX = ref<number | null>(null)
const hoverY = ref<number | null>(null)

const viewWidth = 1000
const viewHeight = 320
const paddingY = 24

const points = computed<StockChartPoint[]>(() => {
  return chartData.value?.points || []
})

const currencySymbol = computed(() => {
  const c = (chartData.value?.currency || props.currency || 'USD').toUpperCase()
  return c === 'THB' ? '฿' : '$'
})

const basePrice = computed(() => {
  if (chartData.value) {
    return chartData.value.base_price || chartData.value.previous_close || 0
  }
  return 0
})

const minPrice = computed(() => {
  if (points.value.length === 0) return 0
  const prices = points.value.map(p => p.price)
  if (basePrice.value > 0) prices.push(basePrice.value)
  return Math.min(...prices)
})

const maxPrice = computed(() => {
  if (points.value.length === 0) return 1
  const prices = points.value.map(p => p.price)
  if (basePrice.value > 0) prices.push(basePrice.value)
  return Math.max(...prices)
})

// Mapped SVG Coordinates
const svgCoords = computed(() => {
  const pts = points.value
  if (pts.length === 0) return []
  const min = minPrice.value
  const max = maxPrice.value
  const range = max - min || 1

  return pts.map((pt, index) => {
    const x = pts.length > 1 ? (index / (pts.length - 1)) * viewWidth : viewWidth / 2
    // Invert Y because SVG 0 is top
    const y = viewHeight - paddingY - ((pt.price - min) / range) * (viewHeight - paddingY * 2)
    return { x, y, pt }
  })
})

const baselineY = computed(() => {
  if (basePrice.value <= 0 || points.value.length === 0) return null
  const min = minPrice.value
  const max = maxPrice.value
  const range = max - min || 1
  return viewHeight - paddingY - ((basePrice.value - min) / range) * (viewHeight - paddingY * 2)
})

// Catmull-Rom to Cubic Bezier Curve Path
const linePath = computed(() => {
  const coords = svgCoords.value
  if (coords.length === 0) return ''
  if (coords.length === 1) return `M ${coords[0].x} ${coords[0].y}`

  let d = `M ${coords[0].x.toFixed(1)} ${coords[0].y.toFixed(1)}`
  for (let i = 0; i < coords.length - 1; i++) {
    const p0 = coords[i === 0 ? i : i - 1]
    const p1 = coords[i]
    const p2 = coords[i + 1]
    const p3 = coords[i + 2] || p2
    const cp1x = p1.x + (p2.x - p0.x) / 6
    const cp1y = p1.y + (p2.y - p0.y) / 6
    const cp2x = p2.x - (p3.x - p1.x) / 6
    const cp2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`
  }
  return d
})

// Area Path closed to bottom of SVG
const areaPath = computed(() => {
  const coords = svgCoords.value
  if (coords.length === 0) return ''
  const lp = linePath.value
  const lastX = coords[coords.length - 1].x.toFixed(1)
  const firstX = coords[0].x.toFixed(1)
  return `${lp} L ${lastX} ${viewHeight} L ${firstX} ${viewHeight} Z`
})

// Hovered state
const hoveredPoint = computed<StockChartPoint | null>(() => {
  if (hoveredIndex.value === null || !points.value[hoveredIndex.value]) return null
  return points.value[hoveredIndex.value]
})

const hoveredTimeFormatted = computed(() => {
  if (!hoveredPoint.value) return ''
  const d = new Date(hoveredPoint.value.time)
  if (selectedPeriod.value === '1D') {
    return d.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }) + ' น.'
  }
  return d.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
})

// Active Price Calculation (Hover vs Latest)
const displayPrice = computed(() => {
  if (hoveredPoint.value) {
    return hoveredPoint.value.price
  }
  return chartData.value?.current_price || props.currentPrice || (points.value.length > 0 ? points.value[points.value.length - 1].price : 0)
})

const displayChangeAmount = computed(() => {
  if (hoveredPoint.value) {
    return hoveredPoint.value.price - basePrice.value
  }
  return chartData.value?.change_amount || 0
})

const displayChangePct = computed(() => {
  if (hoveredPoint.value) {
    if (basePrice.value > 0) {
      return ((hoveredPoint.value.price - basePrice.value) / basePrice.value) * 100
    }
    return 0
  }
  return chartData.value?.change_pct || 0
})

const isPositive = computed(() => {
  return displayChangeAmount.value >= 0
})

const displaySubtitle = computed(() => {
  if (hoveredPoint.value) {
    return 'Scrubbing Historical Point'
  }
  if (selectedPeriod.value === '1D') {
    return 'วันนี้ เทียบกับราคาปิดวันก่อน'
  }
  return `ผลตอบแทนรอบ ${selectedPeriod.value}`
})

function formatPrice(val: number): string {
  const n = Number(val || 0)
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function updateHoverPosition(clientX: number) {
  if (!chartContainerRef.value || svgCoords.value.length === 0) return
  const rect = chartContainerRef.value.getBoundingClientRect()
  const mouseX = Math.max(0, Math.min(rect.width, clientX - rect.left))
  const ratio = mouseX / rect.width
  const svgX = ratio * viewWidth

  // Find nearest coordinate
  const coords = svgCoords.value
  let closestIndex = 0
  let minDiff = Infinity
  for (let i = 0; i < coords.length; i++) {
    const diff = Math.abs(coords[i].x - svgX)
    if (diff < minDiff) {
      minDiff = diff
      closestIndex = i
    }
  }

  hoveredIndex.value = closestIndex
  hoverX.value = coords[closestIndex].x
  hoverY.value = coords[closestIndex].y
}

function handleMouseMove(e: MouseEvent) {
  updateHoverPosition(e.clientX)
}

function handleMouseLeave() {
  hoveredIndex.value = null
  hoverX.value = null
  hoverY.value = null
}

function handleTouchStart(e: TouchEvent) {
  if (e.touches.length > 0) {
    updateHoverPosition(e.touches[0].clientX)
  }
}

function handleTouchMove(e: TouchEvent) {
  if (e.touches.length > 0) {
    updateHoverPosition(e.touches[0].clientX)
  }
}

async function changePeriod(p: Timeframe) {
  selectedPeriod.value = p
  await loadChart()
}

async function loadChart() {
  if (!props.ticker) return
  isLoading.value = true
  try {
    const data = await portfolioStore.fetchStockChart(props.ticker, selectedPeriod.value)
    chartData.value = data
  } catch (err) {
    console.warn(`Failed to fetch chart for ${props.ticker}`, err)
  } finally {
    isLoading.value = false
  }
}

watch(
  () => props.ticker,
  async (newTicker) => {
    if (newTicker) {
      await loadChart()
    }
  }
)

onMounted(async () => {
  await loadChart()
})
</script>
