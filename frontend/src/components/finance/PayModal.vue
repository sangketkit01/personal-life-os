<template>
  <div v-if="isOpen && obligation" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl relative">
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="mb-4">
        <div class="text-[10px] font-mono uppercase tracking-wider text-zinc-400 mb-0.5">
          {{ obligation.type === 'INSTALLMENT' ? 'Term Settlement' : (obligation.type === 'DEBT' ? 'Debt Settlement' : 'Record Payment') }}
        </div>
        <h3 class="text-sm font-semibold text-zinc-100">{{ obligation.title }}</h3>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handlePay" class="space-y-3.5">
        <!-- Installment Context -->
        <div v-if="obligation.type === 'INSTALLMENT'" class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono space-y-1">
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>Current Term:</span>
            <span class="text-zinc-200">{{ obligation.summary?.current_term }} / {{ obligation.summary?.total_terms }}</span>
          </div>
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>Advancing to:</span>
            <span class="text-zinc-100 font-semibold">Term {{ Number(obligation.summary?.current_term || 0) + 1 }}</span>
          </div>
        </div>

        <!-- Debt Context -->
        <div v-if="obligation.type === 'DEBT'" class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono space-y-1">
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>Outstanding Balance:</span>
            <span class="text-zinc-100 font-semibold">฿{{ Number(obligation.summary?.remaining_balance || obligation.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}</span>
          </div>
        </div>

        <!-- Amount to pay -->
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
            {{ obligation.type === 'DEBT' ? 'Settlement Amount (Partial Allowed)' : 'Payment Amount (฿)' }}
          </label>
          <input
            v-model="paidAmount"
            type="number"
            step="0.01"
            required
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <!-- Note -->
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Payment Reference / Note</label>
          <input
            v-model="note"
            type="text"
            placeholder="e.g. Bank transfer ref, Slip #"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {{ isSubmitting ? 'Recording...' : 'Confirm Settlement' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useFinanceStore } from '../../stores/finance'
import type { FinancialObligation } from '../../types/finance'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  obligation: FinancialObligation | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'paid'): void
}>()

const financeStore = useFinanceStore()

const paidAmount = ref('')
const note = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

watch(() => props.obligation, (ob) => {
  errorMessage.value = ''
  note.value = ''
  if (!ob) return

  if (ob.type === 'DEBT') {
    paidAmount.value = String(ob.summary?.remaining_balance || ob.amount)
  } else {
    paidAmount.value = String(ob.amount)
  }
}, { immediate: true })

async function handlePay() {
  if (!props.obligation) return
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    await financeStore.payObligation(props.obligation.id, {
      paid_amount: parseFloat(paidAmount.value),
      note: note.value
    })
    emit('paid')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || 'Failed to record settlement'
  } finally {
    isSubmitting.value = false
  }
}
</script>
