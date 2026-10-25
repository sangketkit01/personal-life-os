<template>
  <div class="space-y-6 font-sans">
    <!-- Summary Header Cards for BNPL -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm">
        <span class="text-[10px] font-mono uppercase text-zinc-400 block">Total Credit Limit</span>
        <div class="mt-2 text-xl font-bold font-mono text-zinc-100 tabular-nums">
          ฿{{ totalCreditLimit.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">Aggregated approved credit limit</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm">
        <span class="text-[10px] font-mono uppercase text-zinc-400 block">Current Cycle Bill Sum</span>
        <div class="mt-2 text-xl font-bold font-mono text-zinc-100 tabular-nums">
          ฿{{ totalCurrentCycleBills.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">Due this statement cycle</span>
      </div>

      <div class="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/70 hover:-translate-y-0.5 transition-all duration-200 shadow-sm">
        <span class="text-[10px] font-mono uppercase text-zinc-400 block">Total Outstanding Debt</span>
        <div class="mt-2 text-xl font-bold font-mono text-zinc-100 tabular-nums">
          ฿{{ totalRemainingBNPLDebt.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <span class="text-[10px] text-zinc-500 mt-1 block">Total remaining installment balance</span>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="bnplAccounts.length === 0"
      class="p-12 rounded-xl bg-zinc-900/20 border border-zinc-800 text-center space-y-3 font-mono text-xs text-zinc-500"
    >
      <p>No active BNPL credit accounts found (Shopee SPayLater, LazPayLater, TikTok Shop).</p>
      <button
        @click="emit('openCreate')"
        class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-medium text-xs transition-colors inline-block shadow-sm"
      >
        + Add BNPL Account
      </button>
    </div>

    <!-- MASTER-DETAIL WORKBENCH -->
    <div v-else class="space-y-5">
      <!-- 1. Account Selector Strip -->
      <div>
        <div class="flex items-center justify-between pb-2 border-b border-zinc-800/80 mb-3">
          <div class="flex items-center gap-2">
            <ShoppingBag class="w-4 h-4 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Revolving BNPL Credit Accounts (Select line to manage)
            </h2>
          </div>
          <button
            @click="emit('openCreate')"
            class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            + New Line
          </button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
          <div
            v-for="acc in bnplAccounts"
            :key="acc.id"
            @click="selectedAccountId = acc.id"
            class="p-4 rounded-xl border cursor-pointer transition-all space-y-3 shadow-sm hover:shadow-md"
            :class="[
              selectedAccountId === acc.id
                ? 'bg-zinc-900 border-zinc-500'
                : 'bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700/80 hover:bg-zinc-900/60'
            ]"
          >
            <div class="flex items-start justify-between">
              <div>
                <span class="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">
                  {{ acc.metadata?.provider || 'BNPL' }}
                </span>
                <h3 class="text-sm font-semibold text-zinc-100 mt-1 font-sans">{{ acc.title }}</h3>
              </div>
              <span class="text-[10px] font-mono text-zinc-500">
                Cutoff: {{ acc.metadata?.cutoff_day || 25 }}th
              </span>
            </div>

            <!-- Gauge -->
            <div class="space-y-1 font-mono text-xs">
              <div class="flex justify-between text-[11px]">
                <span class="text-zinc-400">Available: {{ currencySymbol(acc.currency) }}{{ Number(acc.summary?.available_credit || 0).toLocaleString('th-TH') }}</span>
                <span class="text-zinc-500">Limit: {{ currencySymbol(acc.currency) }}{{ Number(acc.metadata?.credit_limit || 0).toLocaleString('th-TH') }}</span>
              </div>
              <div class="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-300"
                  :class="(acc.summary?.utilization_pct || 0) > 80 ? 'bg-rose-500/80' : 'bg-zinc-200'"
                  :style="{ width: `${Math.min(100, Number(acc.summary?.utilization_pct || 0))}%` }"
                />
              </div>
            </div>

            <!-- Actions Bar inside card -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1.5 border-t border-zinc-800/60 text-[11px] font-mono">
              <span class="text-zinc-400">
                Cycle Due: <strong class="text-zinc-100">{{ currencySymbol(acc.currency) }}{{ Number(acc.summary?.current_bill_amount || 0).toLocaleString('en-US') }}</strong>
              </span>

              <div class="flex flex-wrap items-center gap-1.5 self-end sm:self-auto" @click.stop>
                <RouterLink
                  :to="`/finance/bnpl/${acc.id}`"
                  class="px-2 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 active:scale-95 border border-zinc-800 text-zinc-300 font-sans text-[10px] flex items-center gap-1 transition-all"
                  title="Open Dedicated Account Dossier"
                >
                  <span>Dossier</span>
                  <ArrowRight class="w-3 h-3 text-zinc-500" />
                </RouterLink>
                <button
                  @click="emit('openHistory', acc)"
                  class="p-1 rounded text-zinc-400 hover:text-white active:scale-95 transition-all"
                  title="Payment History"
                >
                  <History class="w-3.5 h-3.5" />
                </button>
                <button
                  @click="emit('openEdit', acc)"
                  class="p-1 rounded text-zinc-400 hover:text-white active:scale-95 transition-all"
                  title="Edit Account"
                >
                  <Edit2 class="w-3.5 h-3.5" />
                </button>
                <button
                  v-if="acc.status === 'ACTIVE'"
                  @click="emit('openPay', acc)"
                  class="px-2.5 py-0.5 rounded bg-zinc-100 hover:bg-white active:scale-95 text-zinc-950 font-sans font-semibold text-[10px] transition-all shadow-sm"
                >
                  Pay Bill
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Selected Account Detail & Sub-Orders Table -->
      <div v-if="activeAccount" class="space-y-4 pt-2">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-zinc-800/80">
          <div>
            <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono flex items-center gap-2">
              <span>Orders in {{ activeAccount.title }}</span>
              <span class="text-[10px] text-zinc-500 font-normal">({{ activeSubOrders.length }} active orders)</span>
            </h3>
          </div>

          <div class="flex items-center gap-2">
            <button
              @click="showAddOrderForm = !showAddOrderForm"
              class="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-200 text-xs font-mono transition-colors flex items-center gap-1.5"
            >
              <Plus class="w-3 h-3 text-zinc-400" />
              <span>{{ showAddOrderForm ? 'Cancel' : '+ New Sub-Order' }}</span>
            </button>
          </div>
        </div>

        <!-- Inline Quick Add Sub-Order Form -->
        <div
          v-if="showAddOrderForm"
          class="p-4 rounded-xl bg-zinc-950 border border-zinc-800 space-y-3 font-mono text-xs"
        >
          <div class="flex items-center justify-between">
            <span class="text-zinc-200 font-semibold text-xs">Add Item Order to {{ activeAccount.title }}</span>
            <button @click="showAddOrderForm = false" class="text-zinc-500 hover:text-zinc-300">
              <X class="w-3.5 h-3.5" />
            </button>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div>
              <label class="text-[10px] text-zinc-500 uppercase block mb-1">Item Title / Order</label>
              <input
                v-model="newOrderForm.title"
                type="text"
                placeholder="e.g. Wireless Keyboard"
                class="w-full px-2.5 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-100 text-xs outline-none focus:border-zinc-700 font-mono"
              />
            </div>
            <div>
              <label class="text-[10px] text-zinc-500 uppercase block mb-1">Monthly Amount</label>
              <input
                v-model.number="newOrderForm.monthly_amount"
                type="number"
                step="0.01"
                placeholder="0.00"
                class="w-full px-2.5 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-100 text-xs outline-none focus:border-zinc-700 font-mono"
              />
            </div>
            <div>
              <label class="text-[10px] text-zinc-500 uppercase block mb-1">Total Terms</label>
              <input
                v-model.number="newOrderForm.total_terms"
                type="number"
                min="1"
                placeholder="3"
                class="w-full px-2.5 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-100 text-xs outline-none focus:border-zinc-700 font-mono"
              />
            </div>
            <div>
              <label class="text-[10px] text-zinc-500 uppercase block mb-1">Current Term Paid</label>
              <input
                v-model.number="newOrderForm.current_term"
                type="number"
                min="0"
                placeholder="0"
                class="w-full px-2.5 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-100 text-xs outline-none focus:border-zinc-700 font-mono"
              />
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-1">
            <button
              @click="submitNewOrder"
              :disabled="isSubmittingOrder || !newOrderForm.title || !newOrderForm.monthly_amount"
              class="px-3.5 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 font-sans font-semibold text-xs transition-colors disabled:opacity-50"
            >
              {{ isSubmittingOrder ? 'Saving...' : 'Add Sub-Order' }}
            </button>
          </div>
        </div>

        <!-- Orders Table -->
        <div class="rounded-xl bg-zinc-900/30 border border-zinc-800/80 overflow-hidden shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs font-mono">
              <thead>
                <tr class="border-b border-zinc-800/80 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold bg-zinc-950/40">
                  <th class="py-2.5 pl-4">Sub-Order / Purchase</th>
                  <th class="py-2.5">Progress</th>
                  <th class="py-2.5 text-right">Monthly </th>
                  <th class="py-2.5 text-right">Remaining Balance</th>
                  <th class="py-2.5 text-right pr-4">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/50">
                <tr
                  v-for="order in activeSubOrders"
                  :key="order.id"
                  class="hover:bg-zinc-800/40 transition-colors"
                >
                  <td class="py-2.5 pl-4 font-sans font-medium text-zinc-100">{{ order.title }}</td>
                  <td class="py-2.5 text-zinc-300">
                    <span>Term {{ order.metadata?.current_term || 0 }} / {{ order.metadata?.total_terms || 1 }}</span>
                    <div class="w-20 bg-zinc-800 h-1.5 rounded-full mt-1 overflow-hidden">
                      <div
                        class="bg-zinc-200 h-full rounded-full"
                        :style="{ width: `${Math.min(100, Math.round(((order.metadata?.current_term || 0) / (order.metadata?.total_terms || 1)) * 100))}%` }"
                      />
                    </div>
                  </td>
                  <td class="py-2.5 text-right font-semibold text-zinc-100 tabular-nums">
                    {{ currencySymbol(order.currency) }}{{ Number(order.amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-2.5 text-right text-zinc-300 tabular-nums">
                    {{ currencySymbol(order.currency) }}{{ getRemainingOrderBalance(order).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-2.5 text-right pr-4">
                    <button
                      @click="emit('deleteOrder', order.id)"
                      class="p-1 rounded text-zinc-600 hover:text-rose-400 active:scale-95 transition-all"
                      title="Delete Order"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>

                <tr v-if="activeSubOrders.length === 0">
                  <td colspan="5" class="py-8 text-center text-zinc-500 font-mono text-xs">
                    No active item orders in this BNPL line. Click "+ New Sub-Order" to track your purchases.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { currencySymbol } from '../../../utils/currency'
import { ref, reactive, computed, watch } from 'vue'
import type { FinancialObligation } from '../../../types/finance'
import apiClient from '../../../api/client'
import { useToastStore } from '../../../stores/toast'
import {
  ShoppingBag,
  History,
  Edit2,
  Plus,
  X,
  Trash2,
  ArrowRight
} from 'lucide-vue-next'

const props = defineProps<{
  obligations: FinancialObligation[]
}>()

const emit = defineEmits<{
  (e: 'openCreate'): void
  (e: 'openPay', ob: FinancialObligation): void
  (e: 'openHistory', ob: FinancialObligation): void
  (e: 'openEdit', ob: FinancialObligation): void
  (e: 'deleteOrder', id: string): void
  (e: 'orderCreated'): void
}>()

const toast = useToastStore()
const selectedAccountId = ref<string>('')
const showAddOrderForm = ref(false)
const isSubmittingOrder = ref(false)

const newOrderForm = reactive({
  title: '',
  monthly_amount: null as number | null,
  total_terms: 3,
  current_term: 0
})

const bnplAccounts = computed(() => {
  return props.obligations.filter(o => o.subtype === 'BNPL_ACCOUNT')
})

// Auto select first account if none selected
watch(
  bnplAccounts,
  (accounts) => {
    if (accounts.length > 0 && (!selectedAccountId.value || !accounts.some(a => a.id === selectedAccountId.value))) {
      selectedAccountId.value = accounts[0].id
    }
  },
  { immediate: true }
)

const activeAccount = computed(() => {
  return bnplAccounts.value.find(a => a.id === selectedAccountId.value) || null
})

const activeSubOrders = computed(() => {
  if (!activeAccount.value) return []
  return (activeAccount.value.sub_orders || []).filter(o => o.status === 'ACTIVE')
})

const totalCreditLimit = computed(() => {
  return bnplAccounts.value.reduce((sum, a) => sum + Number(a.metadata?.credit_limit || 0), 0)
})

const totalCurrentCycleBills = computed(() => {
  return bnplAccounts.value.reduce((sum, a) => sum + Number(a.summary?.current_bill_amount || 0), 0)
})

const totalRemainingBNPLDebt = computed(() => {
  return bnplAccounts.value.reduce((sum, a) => sum + Number(a.summary?.total_remaining_debt || 0), 0)
})

function getRemainingOrderBalance(order: FinancialObligation): number {
  const total = Number(order.metadata?.total_terms || 1)
  const current = Number(order.metadata?.current_term || 0)
  const remainingTerms = Math.max(0, total - current)
  return remainingTerms * Number(order.amount || 0)
}

async function submitNewOrder() {
  if (!activeAccount.value || !newOrderForm.title || !newOrderForm.monthly_amount) return
  isSubmittingOrder.value = true
  try {
    await apiClient.post('/finance/obligations/', {
      parent: activeAccount.value.id,
      title: newOrderForm.title,
      type: 'INSTALLMENT',
      subtype: 'BNPL_ORDER',
      amount: newOrderForm.monthly_amount,
      metadata: {
        total_terms: Number(newOrderForm.total_terms || 1),
        current_term: Number(newOrderForm.current_term || 0)
      }
    })

    toast.success(`Added sub-order "${newOrderForm.title}" to ${activeAccount.value.title}`)
    newOrderForm.title = ''
    newOrderForm.monthly_amount = null
    newOrderForm.total_terms = 3
    newOrderForm.current_term = 0
    showAddOrderForm.value = false
    emit('orderCreated')
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || 'Failed to add sub-order')
  } finally {
    isSubmittingOrder.value = false
  }
}
</script>
