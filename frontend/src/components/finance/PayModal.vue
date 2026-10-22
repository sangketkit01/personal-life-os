<template>
  <div v-if="isOpen && obligation" @click.self="emit('close')" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl relative">
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="mb-4">
        <div class="text-[10px] font-mono uppercase tracking-wider text-zinc-400 mb-0.5">
          {{ obligation.direction === 'INFLOW' ? 'Record Repayment' : (obligation.subtype === 'BNPL_ACCOUNT' ? 'BNPL Statement Settlement' : (obligation.type === 'INSTALLMENT' ? 'Term Settlement' : (obligation.type === 'DEBT' ? 'Debt Settlement' : 'Record Payment'))) }}
        </div>
        <h3 class="text-sm font-semibold text-zinc-100">{{ obligation.title }}</h3>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handlePay" class="space-y-3.5">
        <!-- Installment Context -->
        <div v-if="obligation.type === 'INSTALLMENT' && obligation.subtype !== 'BNPL_ACCOUNT'" class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono space-y-1">
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>Current Term:</span>
            <span class="text-zinc-200">{{ obligation.summary?.current_term }} / {{ obligation.summary?.total_terms }}</span>
          </div>
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>Advancing to:</span>
            <span class="text-zinc-100 font-semibold">Term {{ Number(obligation.summary?.current_term || 0) + 1 }}</span>
          </div>
        </div>

        <!-- BNPL Statement Context -->
        <div v-if="obligation.subtype === 'BNPL_ACCOUNT'" class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono space-y-1">
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>Active Sub-Orders:</span>
            <span class="text-zinc-200">{{ (obligation.sub_orders || obligation.summary?.sub_orders || []).length }} items</span>
          </div>
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>Current Cycle Bill:</span>
            <span class="text-zinc-100 font-semibold">฿{{ Number(obligation.summary?.current_bill_amount || obligation.amount).toLocaleString('en-US') }}</span>
          </div>
        </div>

        <!-- Debt Context -->
        <div v-if="obligation.type === 'DEBT'" class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono space-y-1">
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>{{ obligation.direction === 'INFLOW' ? 'Remaining to collect:' : 'Outstanding Balance:' }}</span>
            <span class="font-semibold" :class="obligation.direction === 'INFLOW' ? 'text-emerald-400' : 'text-zinc-100'">
              ฿{{ Number(obligation.summary?.remaining_balance || obligation.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
            </span>
          </div>
        </div>

        <!-- Amount to pay -->
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
            {{ obligation.direction === 'INFLOW' ? 'Repayment Amount Received (฿)' : (obligation.subtype === 'BNPL_ACCOUNT' ? 'Bill Amount to Settle (฿)' : (obligation.type === 'DEBT' ? 'Settlement Amount (Partial Allowed)' : 'Payment Amount (฿)')) }}
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

        <!-- Slip File Upload -->
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Transfer Slip / Proof (Optional)</label>
          <div class="flex items-center gap-2">
            <label class="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-zinc-900 border border-dashed border-zinc-700 hover:border-zinc-500 cursor-pointer text-xs text-zinc-400 hover:text-zinc-200 transition-colors">
              <Upload class="w-3.5 h-3.5 text-zinc-400" />
              <span class="truncate">{{ selectedFile ? selectedFile.name : 'Attach payment slip (JPG, PNG, PDF)' }}</span>
              <input
                type="file"
                accept="image/*,application/pdf"
                class="hidden"
                @change="handleFileChange"
              />
            </label>
            <button
              v-if="selectedFile"
              type="button"
              @click="selectedFile = null"
              class="p-2 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors"
              title="Remove slip"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
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
            {{ isSubmitting ? 'Recording...' : (obligation.direction === 'INFLOW' ? 'Confirm Repayment' : 'Confirm Settlement') }}
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
import { X, Upload, Trash2 } from 'lucide-vue-next'

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
const selectedFile = ref<File | null>(null)
const isSubmitting = ref(false)
const errorMessage = ref('')

watch(() => props.obligation, (ob) => {
  errorMessage.value = ''
  note.value = ''
  selectedFile.value = null
  if (!ob) return

  if (ob.direction === 'INFLOW' || ob.type === 'DEBT') {
    paidAmount.value = String(ob.summary?.remaining_balance || ob.amount)
  } else if (ob.subtype === 'BNPL_ACCOUNT') {
    paidAmount.value = String(ob.summary?.current_bill_amount || ob.amount)
  } else {
    paidAmount.value = String(ob.amount)
  }
}, { immediate: true })

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    selectedFile.value = target.files[0]
  }
}

async function handlePay() {
  if (!props.obligation) return
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    await financeStore.payObligation(props.obligation.id, {
      paid_amount: parseFloat(paidAmount.value),
      note: note.value,
      slip_file: selectedFile.value || undefined
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
