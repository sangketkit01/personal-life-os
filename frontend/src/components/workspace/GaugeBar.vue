<template>
  <div>
    <div class="flex items-center justify-between text-[10px] font-mono mb-1">
      <span class="text-zinc-400">{{ label }}</span>
      <span class="tabular-nums" :class="pct === null || pct === undefined ? 'text-zinc-600' : pctColor">
        {{ pctText }}
        <span class="text-zinc-600 ml-1.5">{{ detail }}</span>
      </span>
    </div>
    <div class="h-1.5 rounded-full bg-zinc-800/80 overflow-hidden">
      <div
        class="h-full rounded-full transition-all duration-500"
        :class="barColor"
        :style="{ width: `${Math.min(100, Math.max(0, pct ?? 0))}%` }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  pct: number | null | undefined
  detail?: string
  threshold?: number
}>()

const effPct = computed(() => props.pct ?? 0)
const threshold = computed(() => props.threshold ?? 85)

const level = computed(() => {
  if (props.pct === null || props.pct === undefined) return 'none'
  if (effPct.value >= threshold.value) return 'danger'
  if (effPct.value >= threshold.value * 0.7) return 'warn'
  return 'ok'
})

const pctText = computed(() => {
  if (props.pct === null || props.pct === undefined) return '—'
  const val = props.pct % 1 ? props.pct.toFixed(1) : props.pct.toFixed(0)
  return `${val}%`
})

const barColor = computed(() => {
  switch (level.value) {
    case 'danger': return 'bg-rose-500'
    case 'warn': return 'bg-amber-500'
    default: return 'bg-emerald-500'
  }
})

const pctColor = computed(() => {
  switch (level.value) {
    case 'danger': return 'text-rose-400'
    case 'warn': return 'text-amber-400'
    default: return 'text-zinc-200'
  }
})
</script>
