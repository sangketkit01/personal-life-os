<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[70] flex items-center justify-center p-2 sm:p-4 font-sans overflow-hidden"
    >
      <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" @click="emit('close')" />

      <div class="relative w-full max-w-3xl max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden">
        <!-- Header -->
        <div class="px-4 sm:px-5 py-3 sm:py-4 border-b border-zinc-800 bg-zinc-900/60 flex items-center justify-between shrink-0">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="p-1.5 sm:p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0">
              <ArrowDownLeft class="w-4 h-4" />
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                <h3 class="text-xs sm:text-sm font-semibold text-zinc-100 truncate">
                  {{ t('fin.inflowBreakdownTitle') }}
                </h3>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border border-emerald-800/60 text-emerald-400 bg-emerald-950/40">
                  {{ targetMonth || 'Current Month' }}
                </span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border border-zinc-700 text-zinc-400 bg-zinc-900">
                  THB
                </span>
              </div>
              <p class="text-[11px] sm:text-xs text-zinc-400 mt-0.5 font-mono truncate">
                {{ t('fin.inflowBreakdownSubtitle') }}
              </p>
            </div>
          </div>
          <button
            type="button"
            @click="emit('close')"
            class="p-1.5 rounded-md text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60 transition-colors shrink-0"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- Category Summary Grid -->
        <div class="p-3 sm:p-5 border-b border-zinc-800/70 bg-zinc-950 grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-3 shrink-0 max-h-[35vh] sm:max-h-none overflow-y-auto">
          <!-- Total Expected Inflow Card -->
          <div class="p-3.5 rounded-lg bg-emerald-950/20 border border-emerald-800/40">
            <div class="flex items-center justify-between text-[10px] font-mono text-emerald-400/90 uppercase">
              <span>{{ t('fin.totalExpectedInflow') }}</span>
              <Coins class="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div class="text-lg font-bold font-mono text-emerald-400 mt-1 tabular-nums">
              +฿{{ fmt(totalAmount) }}
            </div>
            <p class="text-[10px] font-mono text-zinc-500 mt-0.5">
              {{ items.length }} {{ t('fin.inflowItemsCount', { n: String(items.length) }) }}
            </p>
          </div>

          <!-- MA Revenue Card -->
          <div
            @click="activeCategory = activeCategory === 'MA' ? 'ALL' : 'MA'"
            class="p-3.5 rounded-lg bg-zinc-900/50 border border-zinc-800 hover:border-sky-700/60 transition-all cursor-pointer group"
            :class="{ 'border-sky-500 bg-sky-950/20': activeCategory === 'MA' }"
          >
            <div class="flex items-center justify-between text-[10px] font-mono text-zinc-400 uppercase">
              <span class="group-hover:text-sky-300 transition-colors">{{ t('fin.inflowCatMa') }}</span>
              <FileSignature class="w-3.5 h-3.5 text-sky-400" />
            </div>
            <div class="text-lg font-bold font-mono text-zinc-100 mt-1 tabular-nums">
              ฿{{ fmt(maAmount) }}
            </div>
            <p class="text-[10px] font-mono text-zinc-500 mt-0.5">
              {{ maItems.length }} {{ t('fin.itemsLabel') }}
            </p>
          </div>

          <!-- Debt Repayments Card -->
          <div
            @click="activeCategory = activeCategory === 'DEBT' ? 'ALL' : 'DEBT'"
            class="p-3.5 rounded-lg bg-zinc-900/50 border border-zinc-800 hover:border-amber-700/60 transition-all cursor-pointer group"
            :class="{ 'border-amber-500 bg-amber-950/20': activeCategory === 'DEBT' }"
          >
            <div class="flex items-center justify-between text-[10px] font-mono text-zinc-400 uppercase">
              <span class="group-hover:text-amber-300 transition-colors">{{ t('fin.inflowCatDebt') }}</span>
              <HandCoins class="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div class="text-lg font-bold font-mono text-zinc-100 mt-1 tabular-nums">
              ฿{{ fmt(debtAmount) }}
            </div>
            <p class="text-[10px] font-mono text-zinc-500 mt-0.5">
              {{ debtItems.length }} {{ t('fin.itemsLabel') }}
            </p>
          </div>
        </div>

        <!-- Filter Pills & Search -->
        <div class="px-5 py-2.5 border-b border-zinc-800/60 bg-zinc-900/30 flex items-center justify-between gap-3 shrink-0">
          <div class="flex items-center gap-1.5 overflow-x-auto text-[11px] font-mono">
            <button
              type="button"
              @click="activeCategory = 'ALL'"
              class="px-2.5 py-1 rounded transition-colors"
              :class="activeCategory === 'ALL' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
            >
              {{ t('fin.filterAll') }} ({{ items.length }})
            </button>
            <button
              type="button"
              @click="activeCategory = 'MA'"
              class="px-2.5 py-1 rounded transition-colors"
              :class="activeCategory === 'MA' ? 'bg-sky-950/60 text-sky-400 border border-sky-800/60 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
            >
              {{ t('fin.inflowCatMa') }} ({{ maItems.length }})
            </button>
            <button
              type="button"
              @click="activeCategory = 'DEBT'"
              class="px-2.5 py-1 rounded transition-colors"
              :class="activeCategory === 'DEBT' ? 'bg-amber-950/60 text-amber-400 border border-amber-800/60 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
            >
              {{ t('fin.inflowCatDebt') }} ({{ debtItems.length }})
            </button>
            <button
              v-if="recurringItems.length > 0"
              type="button"
              @click="activeCategory = 'RECURRING'"
              class="px-2.5 py-1 rounded transition-colors"
              :class="activeCategory === 'RECURRING' ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
            >
              {{ t('fin.inflowCatRecurring') }} ({{ recurringItems.length }})
            </button>
          </div>

          <span class="text-[10px] font-mono text-zinc-500 hidden sm:inline">
            {{ filteredItems.length }} / {{ items.length }} {{ t('fin.itemsShown') }}
          </span>
        </div>

        <!-- Item List Body -->
        <div class="flex-1 overflow-y-auto overscroll-contain min-h-0 p-3 sm:p-5 space-y-2">
          <div
            v-if="filteredItems.length === 0"
            class="p-12 text-center rounded-lg bg-zinc-900/30 border border-zinc-800/80 space-y-2"
          >
            <Coins class="w-7 h-7 text-zinc-600 mx-auto" />
            <p class="text-xs text-zinc-400 font-mono">
              {{ t('fin.noInflowItems') }}
            </p>
            <p class="text-[11px] text-zinc-600 font-mono">
              {{ t('fin.noInflowItemsHint') }}
            </p>
          </div>

          <div
            v-for="item in filteredItems"
            :key="item.id"
            class="p-3.5 rounded-lg bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div class="flex items-start sm:items-center gap-3 min-w-0 flex-1">
              <div
                class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border"
                :class="categoryIconClass(item.category)"
              >
                <component :is="categoryIcon(item.category)" class="w-4 h-4" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-xs font-semibold text-zinc-100 truncate">{{ item.title }}</span>
                  <span
                    class="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border"
                    :class="categoryBadgeClass(item.category)"
                  >
                    {{ categoryLabel(item.category) }}
                  </span>
                  <span v-if="item.counterparty" class="text-[11px] text-zinc-400 font-mono">
                    · {{ item.counterparty }}
                  </span>
                </div>
                <div class="flex items-center gap-2 mt-1 text-[10px] font-mono text-zinc-500">
                  <span v-if="item.due_date">
                    {{ t('fin.expectedDate') }}: {{ formatLocaleDate(item.due_date, 'short') }}
                  </span>
                  <span v-else>
                    {{ t('fin.monthlyRecurring') }}
                  </span>
                  <span v-if="item.currency && item.currency !== 'THB'" class="text-zinc-400">
                    · {{ item.currency }} {{ fmt(item.amount) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Amount & Navigation Button -->
            <div class="flex items-center justify-between sm:justify-end gap-3 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-zinc-800/60">
              <div class="text-left sm:text-right">
                <div class="text-sm font-semibold font-mono text-emerald-400 tabular-nums">
                  +฿{{ fmt(item.amount_thb) }}
                </div>
                <div v-if="item.currency && item.currency !== 'THB'" class="text-[10px] font-mono text-zinc-500">
                  ≈ {{ item.currency }} {{ fmt(item.amount) }}
                </div>
              </div>

              <button
                type="button"
                @click="navigateItem(item)"
                class="px-2.5 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-zinc-300 hover:text-zinc-100 text-[11px] font-mono transition-colors flex items-center gap-1 shadow-sm"
              >
                <span>{{ actionLabel(item) }}</span>
                <ArrowUpRight class="w-3 h-3 text-zinc-400" />
              </button>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-5 py-3 border-t border-zinc-800 bg-zinc-900/60 flex items-center justify-between text-[11px] font-mono text-zinc-500 shrink-0">
          <span>{{ t('fin.sumMatchesOverview') }}</span>
          <button
            type="button"
            @click="emit('close')"
            class="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors"
          >
            {{ t('common.close') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowDownLeft, X, Coins, FileSignature, HandCoins, Repeat, ArrowUpRight
} from 'lucide-vue-next'
import { t, formatLocaleDate } from '../../../i18n'
import { useBodyScrollLock } from '../../../composables/useBodyScrollLock'
import type { ExpectedInflowItem, ExpectedInflowBreakdown } from '../../../types/finance'

const props = defineProps<{
  isOpen: boolean
  targetMonth?: string
  breakdown?: ExpectedInflowBreakdown
  totalAmount?: string | number
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

useBodyScrollLock(() => props.isOpen)

const router = useRouter()
const activeCategory = ref<'ALL' | 'MA' | 'DEBT' | 'RECURRING'>('ALL')

const items = computed<ExpectedInflowItem[]>(() => props.breakdown?.items || [])

const maItems = computed(() => items.value.filter(i => i.category === 'MA'))
const debtItems = computed(() => items.value.filter(i => i.category === 'DEBT'))
const recurringItems = computed(() => items.value.filter(i => i.category === 'RECURRING'))

const maAmount = computed(() => props.breakdown?.ma_amount || maItems.value.reduce((s, i) => s + Number(i.amount_thb || 0), 0))
const debtAmount = computed(() => props.breakdown?.debt_amount || debtItems.value.reduce((s, i) => s + Number(i.amount_thb || 0), 0))

const filteredItems = computed(() => {
  if (activeCategory.value === 'ALL') return items.value
  return items.value.filter(i => i.category === activeCategory.value)
})

function fmt(val: string | number | undefined): string {
  const num = Number(val || 0)
  return num.toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function categoryIcon(cat: string) {
  if (cat === 'MA') return FileSignature
  if (cat === 'DEBT') return HandCoins
  return Repeat
}

function categoryIconClass(cat: string) {
  if (cat === 'MA') return 'bg-sky-950/40 border-sky-800/60 text-sky-400'
  if (cat === 'DEBT') return 'bg-amber-950/40 border-amber-800/60 text-amber-400'
  return 'bg-emerald-950/40 border-emerald-800/60 text-emerald-400'
}

function categoryBadgeClass(cat: string) {
  if (cat === 'MA') return 'border-sky-800/60 text-sky-400 bg-sky-950/40'
  if (cat === 'DEBT') return 'border-amber-800/60 text-amber-400 bg-amber-950/40'
  return 'border-emerald-800/60 text-emerald-400 bg-emerald-950/40'
}

function categoryLabel(cat: string): string {
  if (cat === 'MA') return t('fin.inflowCatMa')
  if (cat === 'DEBT') return t('fin.inflowCatDebt')
  return t('fin.inflowCatRecurring')
}

function actionLabel(item: ExpectedInflowItem): string {
  if (item.category === 'MA' && item.project_id) return t('fin.openProject')
  if (item.type === 'DEBT') return t('fin.openDebtDossier')
  if (item.type === 'INSTALLMENT') return t('fin.openInstallment')
  if (item.type === 'SUBSCRIPTION') return t('fin.openSubscription')
  return t('fin.openDetails')
}

function navigateItem(item: ExpectedInflowItem) {
  emit('close')
  if (item.category === 'MA' && item.project_id) {
    router.push(`/workspace/projects/${item.project_id}?tab=infrastructure`)
  } else if (item.type === 'DEBT') {
    router.push(`/finance/debts/${item.id}`)
  } else if (item.type === 'INSTALLMENT') {
    router.push(`/finance/installments/${item.id}`)
  } else if (item.type === 'SUBSCRIPTION') {
    router.push(`/finance/subscriptions/${item.id}`)
  } else {
    router.push(`/finance/subscriptions/${item.id}`)
  }
}
</script>
