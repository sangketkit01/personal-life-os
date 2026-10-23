<template>
  <div class="space-y-6 font-sans">
    <!-- Summary Header Cards for Installments -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm">
        <span class="text-[10px] font-mono uppercase text-zinc-400 block">Total Remaining Debt</span>
        <div class="mt-2 text-xl font-bold font-mono text-zinc-100 tabular-nums">
          ฿{{ totalRemainingInstallmentDebt.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">Total remaining principal across contracts</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm">
        <span class="text-[10px] font-mono uppercase text-zinc-400 block">Monthly Installment Outflow</span>
        <div class="mt-2 text-xl font-bold font-mono text-zinc-100 tabular-nums">
          ฿{{ totalMonthlyInstallmentOutflow.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">Monthly installment cash outflow</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm">
        <span class="text-[10px] font-mono uppercase text-zinc-400 block">Active Contracts</span>
        <div class="mt-2 text-xl font-bold font-mono text-zinc-100 tabular-nums">
          {{ installmentList.length }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">
          {{ hirePurchaseList.length }} Hire-Purchase • {{ generalList.length }} 0% Term Plans
        </span>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="installmentList.length === 0"
      class="p-12 rounded-xl bg-zinc-900/20 border border-zinc-800/80 text-center space-y-3 font-mono text-xs text-zinc-500"
    >
      <p>No active vehicle hire purchase or installment contracts found.</p>
      <button
        @click="emit('openCreate')"
        class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-medium text-xs transition-colors inline-block shadow-sm"
      >
        + Add New Contract
      </button>
    </div>

    <!-- 1. VEHICLE HIRE PURCHASE CONTRACTS SECTION -->
    <div v-if="hirePurchaseList.length > 0" class="space-y-4">
      <div class="flex items-center gap-2 pb-1.5 border-b border-zinc-800/80">
        <Car class="w-4 h-4 text-zinc-400" />
        <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
          Vehicle Hire Purchase (Thai OCPB 2023 Regulated)
        </h2>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div
          v-for="hp in hirePurchaseList"
          :key="hp.id"
          class="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 space-y-4 hover:border-zinc-700/80 hover:bg-zinc-900/70 transition-all duration-200 shadow-sm hover:shadow-md"
        >
          <!-- Top Row: Vehicle title & Leasing -->
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-semibold">
                  Hire Purchase
                </span>
                <span class="text-xs text-zinc-400 font-mono">{{ hp.metadata?.lender || 'Auto Leasing' }}</span>
              </div>
              <h3
                @click="emit('select', hp.id)"
                class="text-sm font-semibold text-zinc-100 mt-1 cursor-pointer hover:text-white transition-colors"
              >
                {{ hp.metadata?.vehicle_model || hp.title }}
              </h3>
            </div>

            <!-- Action buttons -->
            <div class="flex items-center gap-1.5">
              <button
                @click="emit('select', hp.id)"
                class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 active:scale-95 border border-zinc-800 text-zinc-300 text-xs font-mono transition-all"
                title="View Full Contract Dossier & Amortization"
              >
                Dossier &rarr;
              </button>
              <button
                v-if="hp.status === 'ACTIVE'"
                @click="emit('openPay', hp)"
                class="px-2.5 py-1 rounded bg-zinc-100 hover:bg-white active:scale-95 text-zinc-950 text-xs font-semibold transition-all shadow-sm"
              >
                Pay Term
              </button>
            </div>
          </div>

          <!-- Financed Parameters Grid -->
          <div class="grid grid-cols-3 gap-2 p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80 font-mono text-xs">
            <div>
              <span class="text-[9px] text-zinc-500 block uppercase">Financed Principal</span>
              <span class="text-zinc-200 font-semibold">฿{{ Number(hp.metadata?.financed_amount || hp.metadata?.total_principal || 0).toLocaleString('en-US') }}</span>
            </div>
            <div>
              <span class="text-[9px] text-zinc-500 block uppercase">Flat Rate P.A.</span>
              <span class="text-zinc-200 font-semibold">{{ hp.metadata?.flat_rate_pa || 0 }}% / yr</span>
            </div>
            <div class="text-right">
              <span class="text-[9px] text-zinc-500 block uppercase">Monthly Installment</span>
              <span class="text-zinc-100 font-semibold">฿{{ Number(hp.amount).toLocaleString('en-US') }}</span>
            </div>
          </div>

          <!-- Progress Bar -->
          <div class="space-y-1 font-mono text-xs">
            <div class="flex justify-between text-[11px] text-zinc-400">
              <span>Term {{ hp.summary?.current_term || 0 }} / {{ hp.summary?.total_terms || 1 }} ({{ hp.summary?.progress_percentage ?? 0 }}%)</span>
              <span>{{ (hp.summary?.total_terms || 1) - (hp.summary?.current_term || 0) }} terms remaining</span>
            </div>
            <div class="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
              <div
                class="bg-zinc-200 h-full rounded-full transition-all duration-300"
                :style="{ width: `${hp.summary?.progress_percentage ?? 0}%` }"
              />
            </div>
          </div>

          <!-- Expandable Inline OCPB Early Payoff Simulator Button -->
          <div class="pt-1">
            <button
              @click="toggleSimulator(hp.id)"
              class="w-full py-1.5 px-3 rounded-lg bg-zinc-900/60 hover:bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-300 flex items-center justify-between transition-colors"
            >
              <div class="flex items-center gap-2">
                <Calculator class="w-3.5 h-3.5 text-zinc-400" />
                <span>Statutory Early Payoff Simulator</span>
              </div>
              <span class="text-[10px] text-zinc-500 font-sans">
                {{ expandedSimulators[hp.id] ? 'Hide Calculator' : 'Simulate Payoff' }}
              </span>
            </button>

            <!-- Inline Simulator Panel -->
            <div
              v-if="expandedSimulators[hp.id]"
              class="mt-2.5 p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-3 font-mono text-xs"
            >
              <div class="flex items-center justify-between">
                <span class="text-[11px] text-zinc-300 font-semibold">Simulate Payoff at Term: {{ getSimTerm(hp) }} / {{ hp.summary?.total_terms }}</span>
                <span class="text-[10px] px-1.5 py-0.2 rounded font-mono bg-zinc-900 text-zinc-300 border border-zinc-800">
                  Unearned Interest Discount: {{ getDiscountPct(hp) }}%
                </span>
              </div>

              <!-- Slider -->
              <input
                v-model.number="simulatorTerms[hp.id]"
                type="range"
                :min="hp.summary?.current_term || 0"
                :max="hp.summary?.total_terms || 36"
                step="1"
                class="w-full accent-zinc-200 cursor-pointer"
              />

              <!-- Calculation Result -->
              <div class="p-2.5 rounded bg-zinc-900/40 border border-zinc-800/80 text-zinc-300 space-y-1.5 text-[11px]">
                <div class="flex justify-between text-zinc-400">
                  <span>Outstanding Principal:</span>
                  <span>฿{{ getSimBreakdown(hp).remainingPrincipal.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
                </div>
                <div class="flex justify-between text-emerald-400">
                  <span>OCPB Interest Saved ({{ getDiscountPct(hp) }}%):</span>
                  <span>-฿{{ getSimBreakdown(hp).interestSaved.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
                </div>
                <div class="flex justify-between text-zinc-400">
                  <span>Value-Added Tax (VAT 7%):</span>
                  <span>฿{{ getSimBreakdown(hp).vat.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
                </div>
                <div class="pt-1.5 border-t border-zinc-800 flex justify-between font-semibold">
                  <span class="text-zinc-100">Net Payoff Settlement:</span>
                  <span class="text-zinc-100 text-xs">฿{{ getSimBreakdown(hp).payoffTotal.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
                </div>
              </div>

              <!-- Net Savings Highlight -->
              <div class="p-2 rounded bg-zinc-900 border border-zinc-800 text-[11px] flex justify-between items-center">
                <span class="text-zinc-400">Net Cash Savings:</span>
                <span class="font-bold tabular-nums text-emerald-400">+฿{{ getSimBreakdown(hp).netSavings.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. GENERAL 0% INSTALLMENTS TABLE -->
    <div v-if="generalList.length > 0" class="space-y-3 pt-2">
      <div class="flex items-center gap-2 pb-1.5 border-b border-zinc-800/80">
        <CreditCard class="w-4 h-4 text-zinc-400" />
        <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
          Fixed & 0% Card Installment Plans
        </h2>
      </div>

      <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead>
              <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-950/40">
                <th class="py-2.5 pl-4">Product / Item</th>
                <th class="py-2.5">Lender / Institution</th>
                <th class="py-2.5">Terms Progress</th>
                <th class="py-2.5 text-right">Monthly (฿)</th>
                <th class="py-2.5 text-right">Remaining Balance</th>
                <th class="py-2.5">Due Date</th>
                <th class="py-2.5 text-right pr-4">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr
                v-for="item in generalList"
                :key="item.id"
                class="hover:bg-zinc-800/40 transition-colors cursor-pointer"
                @click="emit('select', item.id)"
              >
                <td class="py-2.5 pl-4 font-sans font-medium text-zinc-100 hover:text-white">{{ item.title }}</td>
                <td class="py-2.5 text-zinc-400">{{ item.metadata?.lender || '-' }}</td>
                <td class="py-2.5 text-zinc-300">
                  <span>Term {{ item.summary?.current_term || 0 }} / {{ item.summary?.total_terms || 1 }}</span>
                  <div class="w-20 bg-zinc-800 h-1.5 rounded-full mt-1 overflow-hidden">
                    <div
                      class="bg-zinc-200 h-full rounded-full"
                      :style="{ width: `${item.summary?.progress_percentage ?? 0}%` }"
                    />
                  </div>
                </td>
                <td class="py-2.5 text-right font-semibold text-zinc-100 tabular-nums">
                  ฿{{ Number(item.amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </td>
                <td class="py-2.5 text-right text-zinc-300 tabular-nums">
                  ฿{{ Number(item.summary?.remaining_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                </td>
                <td class="py-2.5 text-zinc-400">
                  {{ item.due_date ? new Date(item.due_date).toLocaleDateString('en-GB') : `Day ${item.billing_day || '-'}` }}
                </td>
                <td class="py-2.5 text-right pr-4" @click.stop>
                  <div class="flex items-center justify-end gap-1.5">
                    <button
                      @click="emit('select', item.id)"
                      class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 active:scale-95 border border-zinc-800 text-[10px] text-zinc-300 transition-all"
                      title="View Contract Dossier"
                    >
                      Dossier
                    </button>
                    <button
                      @click="emit('openHistory', item)"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 active:scale-95 transition-all"
                      title="History"
                    >
                      <History class="w-3.5 h-3.5" />
                    </button>
                    <button
                      @click="emit('openEdit', item)"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 active:scale-95 transition-all"
                      title="Edit"
                    >
                      <Edit2 class="w-3.5 h-3.5" />
                    </button>
                    <button
                      v-if="item.status === 'ACTIVE'"
                      @click="emit('openPay', item)"
                      class="px-2.5 py-0.5 rounded bg-zinc-100 hover:bg-white active:scale-95 text-zinc-950 font-semibold text-[10px] transition-all shadow-sm"
                    >
                      Pay
                    </button>
                    <button
                      @click="emit('delete', item.id)"
                      class="p-1 rounded text-zinc-600 hover:text-rose-400 active:scale-95 transition-all"
                      title="Delete"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { FinancialObligation } from '../../../types/finance'
import {
  Car,
  CreditCard,
  Calculator,
  History,
  Edit2,
  Trash2
} from 'lucide-vue-next'

const props = defineProps<{
  obligations: FinancialObligation[]
}>()

const emit = defineEmits<{
  (e: 'openCreate'): void
  (e: 'select', id: string): void
  (e: 'openPay', ob: FinancialObligation): void
  (e: 'openHistory', ob: FinancialObligation): void
  (e: 'openEdit', ob: FinancialObligation): void
  (e: 'delete', id: string): void
}>()

const expandedSimulators = ref<Record<string, boolean>>({})
const simulatorTerms = ref<Record<string, number>>({})

const installmentList = computed(() => {
  return props.obligations.filter(o => o.type === 'INSTALLMENT' && o.subtype !== 'BNPL_ACCOUNT' && !o.parent)
})

const hirePurchaseList = computed(() => {
  return installmentList.value.filter(o => o.subtype === 'HIRE_PURCHASE')
})

const generalList = computed(() => {
  return installmentList.value.filter(o => o.subtype !== 'HIRE_PURCHASE')
})

const totalRemainingInstallmentDebt = computed(() => {
  return installmentList.value.reduce((sum, o) => sum + Number(o.summary?.remaining_balance || 0), 0)
})

const totalMonthlyInstallmentOutflow = computed(() => {
  return installmentList.value.filter(o => o.status === 'ACTIVE').reduce((sum, o) => sum + Number(o.amount || 0), 0)
})

function toggleSimulator(id: string) {
  expandedSimulators.value[id] = !expandedSimulators.value[id]
  const match = hirePurchaseList.value.find(o => o.id === id)
  if (match && simulatorTerms.value[id] === undefined) {
    simulatorTerms.value[id] = match.summary?.current_term || 0
  }
}

function getSimTerm(hp: FinancialObligation) {
  if (simulatorTerms.value[hp.id] !== undefined) {
    return simulatorTerms.value[hp.id]
  }
  return hp.summary?.current_term || 0
}

function getDiscountPct(hp: FinancialObligation) {
  const totalTerms = Number(hp.summary?.total_terms || 1)
  const simTerm = getSimTerm(hp)
  const ratio = totalTerms > 0 ? simTerm / totalTerms : 0
  if (ratio <= 0.3334) return 60
  if (ratio <= 0.6667) return 70
  return 100
}

function getSimBreakdown(hp: FinancialObligation) {
  const totalTerms = Number(hp.summary?.total_terms || 1)
  const financed = Number(hp.metadata?.financed_amount || hp.metadata?.total_principal || 0)
  const flatRate = Number(hp.metadata?.flat_rate_pa || 0)
  const simTerm = getSimTerm(hp)
  const remTerms = Math.max(0, totalTerms - simTerm)

  const years = totalTerms / 12
  const totalInterest = financed * (flatRate / 100) * years
  const monthlyPrincipal = totalTerms > 0 ? financed / totalTerms : 0
  const monthlyInterest = totalTerms > 0 ? totalInterest / totalTerms : 0

  const remainingPrincipal = monthlyPrincipal * remTerms
  const remainingInterestBefore = monthlyInterest * remTerms
  const discountPct = getDiscountPct(hp)
  const discountedInterest = remainingInterestBefore * (1 - discountPct / 100)
  const interestSaved = remainingInterestBefore - discountedInterest

  const vat = (remainingPrincipal + discountedInterest) * 0.07
  const payoffTotal = remainingPrincipal + discountedInterest + vat
  const normalRemainingTotal = remTerms * Number(hp.amount || 0)
  const netSavings = Math.max(0, normalRemainingTotal - payoffTotal)

  return {
    remainingPrincipal,
    discountedInterest,
    interestSaved,
    vat,
    payoffTotal,
    netSavings
  }
}
</script>
