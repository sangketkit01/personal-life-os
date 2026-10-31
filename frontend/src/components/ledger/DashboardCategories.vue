<template>
  <section class="rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 space-y-4 min-w-0">
    <h2 class="font-semibold text-sm text-zinc-100">{{ title }}</h2>
    <p v-if="!groups.length" class="text-xs text-zinc-500 py-6">ไม่มีรายการในช่วงนี้</p>
    <div v-for="group in groups" :key="group.id || 'uncategorized'">
      <button type="button" @click="$emit('select',group.id)" class="w-full text-left rounded hover:bg-zinc-800/40 focus-visible:outline focus-visible:outline-emerald-400">
        <span class="flex flex-wrap justify-between gap-2 text-xs"><span class="text-zinc-200">{{ group.name }} <span class="text-zinc-500">({{ group.count }})</span></span><span class="text-zinc-200 tabular-nums">{{ currency }} {{ Number(group.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}</span></span>
        <span class="mt-2 flex items-center gap-2"><span class="h-1.5 bg-zinc-800 rounded-full flex-1 overflow-hidden"><span class="block h-full rounded-full" :class="income ? 'bg-emerald-400/70' : 'bg-amber-400/70'" :style="{ width: `${group.share}%` }"></span></span><span class="text-[10px] text-zinc-500 w-10 text-right">{{ group.share.toFixed(1) }}%</span></span>
      </button>
      <details v-if="group.children.length" class="mt-2 ml-3 text-xs text-zinc-400"><summary class="cursor-pointer">หมวดย่อย</summary><button v-for="child in group.children" :key="child.id" type="button" @click="$emit('select',child.id)" class="w-full flex justify-between gap-2 py-2 text-left hover:text-zinc-100"><span>{{ child.name }} ({{ child.count }})</span><span>{{ currency }} {{ Number(child.amount).toLocaleString('th-TH') }}</span></button></details>
    </div>
  </section>
</template>
<script setup lang="ts">
import type { DashboardCategory } from '../../types/ledger'
defineProps<{ title: string; groups: DashboardCategory[]; currency: string; income?: boolean }>()
defineEmits<{ select: [id: string | null] }>()
</script>
