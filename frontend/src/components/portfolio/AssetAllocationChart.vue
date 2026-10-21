<template>
  <div class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 font-sans">
    <div class="flex items-center justify-between pb-3 border-b border-zinc-800/60 mb-3">
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-zinc-400"></span>
        <h3 class="text-xs font-semibold uppercase tracking-wider text-zinc-300 font-mono">Asset Allocation</h3>
      </div>
      <span class="text-[10px] font-mono text-zinc-500 uppercase">{{ allocations.length }} Categories</span>
    </div>

    <!-- Empty state -->
    <div v-if="allocations.length === 0" class="py-6 text-center text-xs text-zinc-500 font-mono">
      No active asset allocation data.
    </div>

    <div v-else class="flex flex-col sm:flex-row items-center gap-6">
      <!-- SVG Donut Chart -->
      <div class="relative w-36 h-36 flex-shrink-0">
        <svg class="w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
          <!-- Background track -->
          <circle
            cx="50"
            cy="50"
            r="38"
            class="text-zinc-800/50 stroke-current"
            stroke-width="12"
            fill="none"
          />

          <!-- Slices -->
          <circle
            v-for="slice in chartSlices"
            :key="slice.type"
            cx="50"
            cy="50"
            r="38"
            :stroke="slice.color"
            stroke-width="12"
            fill="none"
            :stroke-dasharray="slice.dasharray"
            :stroke-dashoffset="slice.dashoffset"
            class="transition-all duration-500 hover:opacity-80"
          />
        </svg>

        <!-- Center Label -->
        <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span class="text-[10px] font-mono text-zinc-500 uppercase">Total</span>
          <span class="text-xs font-bold font-mono text-zinc-200">100%</span>
        </div>
      </div>

      <!-- Legend -->
      <div class="flex-1 w-full space-y-2">
        <div
          v-for="item in allocations"
          :key="item.type"
          class="flex items-center justify-between text-xs py-1 border-b border-zinc-800/30 last:border-none"
        >
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full flex-shrink-0" :style="{ backgroundColor: getColor(item.type) }"></span>
            <span class="font-medium text-zinc-300 font-sans">{{ item.label }}</span>
            <span class="text-[10px] text-zinc-500 font-mono">({{ item.count }})</span>
          </div>
          <div class="text-right font-mono">
            <span class="font-bold text-zinc-200">{{ Number(item.percentage).toFixed(1) }}%</span>
            <span class="text-[10px] text-zinc-500 ml-2">{{ currencySymbol }}{{ Number(item.value).toLocaleString('en-US', { maximumFractionDigits: 0 }) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface AllocationItem {
  type: string
  label: string
  value: number
  percentage: number
  count: number
}

const props = withDefaults(
  defineProps<{
    allocations: AllocationItem[]
    currencySymbol?: string
  }>(),
  {
    currencySymbol: '฿'
  }
)

const COLOR_MAP: Record<string, string> = {
  STOCK: '#3B82F6',   // Blue
  CRYPTO: '#10B981',  // Emerald
  FUND: '#F59E0B',    // Amber
  OTHER: '#8B5CF6'    // Purple
}

function getColor(type: string): string {
  return COLOR_MAP[type.toUpperCase()] || '#71717A'
}

// Compute SVG Stroke Dasharray / Offset
const circumference = 2 * Math.PI * 38 // ~238.76

const chartSlices = computed(() => {
  let accumulatedPercent = 0

  return props.allocations.map(item => {
    const percent = item.percentage / 100
    const strokeLength = circumference * percent
    const offset = -(circumference * accumulatedPercent)
    accumulatedPercent += percent

    return {
      type: item.type,
      color: getColor(item.type),
      dasharray: `${strokeLength} ${circumference - strokeLength}`,
      dashoffset: offset
    }
  })
})
</script>
