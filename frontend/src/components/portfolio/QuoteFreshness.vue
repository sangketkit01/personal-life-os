<template>
  <span class="block text-[10px] font-normal mt-0.5" :class="warning ? 'text-amber-400' : 'text-zinc-500'" :title="quote?.error || quote?.as_of || ''">
    {{ label }}<template v-if="quote?.as_of"> · {{ new Date(quote.as_of).toLocaleString('th-TH', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) }}</template>
  </span>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import type { QuoteMetadata } from '../../types/portfolio'
const props = defineProps<{ quote?: QuoteMetadata | null }>()
const warning = computed(() => !props.quote || ['STALE', 'UNKNOWN', 'MISSING'].includes(props.quote.state))
const label = computed(() => ({ CURRENT: 'ราคาอ้างอิง', CLOSED: 'ราคาปิด', STALE: 'ข้อมูลราคาเก่า', UNKNOWN: 'ยังไม่ทราบเวลาอ้างอิง', MISSING: 'ยังไม่มีราคาตลาด' })[props.quote?.state || 'UNKNOWN'])
</script>
