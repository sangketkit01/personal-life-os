<template>
  <div>
    <div class="flex flex-wrap justify-between gap-2 text-xs text-zinc-400"><span><span class="text-emerald-400">● รายรับ</span> <span class="ml-3 text-amber-400">● ค่าใช้จ่ายส่วนตัว</span></span><span>สูงสุด {{ money(peak) }}</span></div>
    <p v-if="!points.length" class="py-16 text-center text-sm text-zinc-500">ยังไม่มีวันที่เกิดขึ้นในช่วงนี้</p>
    <div v-else class="overflow-x-auto mt-4 pb-2">
      <div class="flex gap-1 items-end" :style="{ minWidth: points.length > 15 ? '620px' : '360px' }">
        <button v-for="(point, index) in points" :key="point.label" type="button" @click="$emit('select', index)" :aria-label="`${point.label} รายรับ ${money(point.income)} รายจ่าย ${money(point.expense)} กดดูรายการ`" :title="`${point.label}\nรายรับ ${money(point.income)}\nรายจ่าย ${money(point.expense)}`" class="flex-1 min-w-0 rounded px-0.5 hover:bg-zinc-800/60 focus-visible:outline focus-visible:outline-emerald-400">
          <span class="h-40 flex items-end justify-center gap-0.5"><span class="w-2/5 rounded-t bg-emerald-400/80" :style="{ height: `${Number(point.income) / maximum * 100}%` }"></span><span class="w-2/5 rounded-t bg-amber-400/80" :style="{ height: `${Number(point.expense) / maximum * 100}%` }"></span></span>
          <span class="block mt-2 text-[9px] text-zinc-500 truncate">{{ point.label }}</span>
        </button>
      </div>
    </div>
    <details v-if="points.length" class="text-xs text-zinc-400 mt-3"><summary class="cursor-pointer">ดูตัวเลขในตาราง</summary><div class="overflow-x-auto"><table class="w-full mt-2 text-right"><thead><tr><th class="text-left py-2">ช่วงเวลา</th><th>รายรับ</th><th>รายจ่าย</th></tr></thead><tbody><tr v-for="(point,index) in points" :key="point.label"><td class="text-left py-1"><button type="button" @click="$emit('select',index)" class="underline">{{ point.label }}</button></td><td>{{ money(point.income) }}</td><td>{{ money(point.expense) }}</td></tr></tbody></table></div></details>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ points: Array<{ label: string; income: string; expense: string }>; currency: string }>()
defineEmits<{ select: [index: number] }>()
const peak = computed(() => Math.max(0, ...props.points.flatMap(p => [Number(p.income),Number(p.expense)])))
const maximum = computed(() => Math.max(1,peak.value))
const money = (value: string | number) => `${props.currency} ${Number(value).toLocaleString('th-TH', { maximumFractionDigits: 2 })}`
</script>
