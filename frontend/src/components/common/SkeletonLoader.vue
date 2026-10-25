<template>
  <!-- Metric cards (KPI strips) -->
  <div v-if="variant === 'metrics'" :class="metricsGridClass">
    <div v-for="i in resolvedCount" :key="i" class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 space-y-3">
      <div class="flex items-center justify-between">
        <div class="h-3 w-24 bg-zinc-800/70 animate-pulse rounded"></div>
        <div class="h-3 w-12 bg-zinc-800/50 animate-pulse rounded"></div>
      </div>
      <div class="h-7 w-32 bg-zinc-800/80 animate-pulse rounded"></div>
      <div class="pt-2.5 border-t border-zinc-800/50">
        <div class="h-2.5 w-36 bg-zinc-800/50 animate-pulse rounded"></div>
      </div>
    </div>
  </div>

  <!-- Content cards (project/note grids) -->
  <div v-else-if="variant === 'cards'" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
    <div v-for="i in resolvedCount" :key="i" class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 space-y-3.5">
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="w-8 h-8 rounded-md bg-zinc-800/70 animate-pulse shrink-0"></div>
          <div class="h-4 w-36 bg-zinc-800/80 animate-pulse rounded"></div>
        </div>
        <div class="h-3 w-16 bg-zinc-800/50 animate-pulse rounded shrink-0"></div>
      </div>
      <div class="space-y-2">
        <div class="h-3 w-full bg-zinc-800/50 animate-pulse rounded"></div>
        <div class="h-3 w-2/3 bg-zinc-800/50 animate-pulse rounded"></div>
      </div>
      <div class="h-1.5 w-full bg-zinc-800/60 animate-pulse rounded-full"></div>
    </div>
  </div>

  <!-- Table / ledger lists -->
  <div v-else-if="variant === 'table'" class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 divide-y divide-zinc-800/50 overflow-hidden">
    <div class="px-4 py-2.5 bg-zinc-900/50 flex items-center justify-between gap-4">
      <div v-for="i in 4" :key="i" class="h-2.5 w-20 bg-zinc-800/60 animate-pulse rounded"></div>
    </div>
    <div v-for="i in resolvedCount" :key="i" class="px-4 py-3 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3 min-w-0">
        <div class="h-7 w-7 rounded-md bg-zinc-800/60 animate-pulse shrink-0"></div>
        <div class="space-y-1.5 min-w-0">
          <div class="h-3.5 w-44 bg-zinc-800/70 animate-pulse rounded"></div>
          <div class="h-3 w-24 bg-zinc-800/50 animate-pulse rounded hidden sm:block"></div>
        </div>
      </div>
      <div class="h-4 w-20 bg-zinc-800/70 animate-pulse rounded shrink-0"></div>
    </div>
  </div>

  <!-- Compact rows -->
  <div v-else-if="variant === 'list'" class="space-y-2">
    <div
      v-for="i in resolvedCount"
      :key="i"
      class="p-3 rounded-lg bg-zinc-900/40 border border-zinc-800/70 flex items-center justify-between gap-3"
    >
      <div class="space-y-1.5 min-w-0">
        <div class="h-3.5 w-40 bg-zinc-800/70 animate-pulse rounded"></div>
        <div class="h-3 w-24 bg-zinc-800/50 animate-pulse rounded"></div>
      </div>
      <div class="h-5 w-14 bg-zinc-800/60 animate-pulse rounded shrink-0"></div>
    </div>
  </div>

  <!-- Kanban board -->
  <div v-else-if="variant === 'kanban'" class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <div v-for="col in 3" :key="col" class="p-3 rounded-xl bg-zinc-900/30 border border-zinc-800/80 space-y-3">
      <div class="h-4 w-24 bg-zinc-800/70 animate-pulse rounded"></div>
      <div v-for="i in 3" :key="i" class="p-3 rounded-lg bg-zinc-950/70 border border-zinc-800/70 space-y-2">
        <div class="h-3.5 w-3/4 bg-zinc-800/60 animate-pulse rounded"></div>
        <div class="h-3 w-1/2 bg-zinc-800/50 animate-pulse rounded"></div>
      </div>
    </div>
  </div>

  <!-- Detail page header + body lines -->
  <div v-else class="space-y-4">
    <div class="p-5 rounded-lg bg-zinc-900/40 border border-zinc-800/80 space-y-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-zinc-800/70 animate-pulse shrink-0"></div>
        <div class="space-y-2 flex-1">
          <div class="h-5 w-52 bg-zinc-800/80 animate-pulse rounded"></div>
          <div class="h-3 w-32 bg-zinc-800/50 animate-pulse rounded"></div>
        </div>
      </div>
      <div class="pt-4 border-t border-zinc-800/60 space-y-2.5">
        <div
          v-for="i in resolvedCount"
          :key="i"
          class="h-3 bg-zinc-800/50 animate-pulse rounded"
          :style="{ width: i % 3 === 0 ? '60%' : i % 3 === 1 ? '100%' : '80%' }"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    variant?: 'metrics' | 'cards' | 'table' | 'list' | 'kanban' | 'detail'
    count?: number
    columns?: number
  }>(),
  { variant: 'cards' }
)

const resolvedCount = computed(() => {
  if (props.count !== undefined) return props.count
  switch (props.variant) {
    case 'metrics':
      return 4
    case 'table':
    case 'list':
      return 5
    case 'kanban':
      return 3
    default:
      return 6
  }
})

// 4 columns collapse straight to a 2x2 phone grid; other column counts
// get the sm/lg stepping.
const metricsGridClass = computed(() =>
  props.columns === undefined || props.columns === 4
    ? 'grid grid-cols-2 lg:grid-cols-4 gap-3.5'
    : 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5'
)
</script>
