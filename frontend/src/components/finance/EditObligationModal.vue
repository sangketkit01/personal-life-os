<template>
  <div v-if="isOpen && obligation" @click.self="emit('close')" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-lg p-6 shadow-2xl relative my-8">
      <!-- Close button -->
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- Modal Title -->
      <div class="mb-4">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border bg-zinc-900 text-zinc-400 border-zinc-800">
            {{ obligation.type }}
          </span>
          <span v-if="obligation.subtype" class="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border bg-zinc-900 text-zinc-300 border-zinc-800">
            {{ obligation.subtype }}
          </span>
          <span class="text-xs text-zinc-500 font-mono">ID: {{ obligation.id.slice(0, 8) }}</span>
        </div>
        <h2 class="text-base font-semibold text-zinc-100 tracking-tight flex items-center gap-2">
          <span>Edit Obligation</span>
          <span class="text-xs font-normal text-zinc-500 font-mono">Edit Obligation</span>
        </h2>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="space-y-3.5">
        <!-- Common Title & Amount -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div class="sm:col-span-2">
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Title</label>
            <input
              v-model="form.title"
              type="text"
              required
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              Amount ({{ form.currency || 'THB' }})
            </label>
            <input
              v-model="form.amount"
              type="number"
              step="0.01"
              required
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Currency</label>
            <select
              v-model="form.currency"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600 transition-colors"
            >
              <option value="THB">THB (฿)</option>
              <option value="USD">USD ($)</option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Flow Direction</label>
            <select
              v-model="form.direction"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600 transition-colors"
            >
              <option value="OUTFLOW">OUTFLOW (Expense / Liability)</option>
              <option value="INFLOW">INFLOW (Income / Receivable)</option>
            </select>
          </div>
        </div>

        <!-- 1. HIRE PURCHASE -->
        <div v-if="obligation.type === 'INSTALLMENT' && (obligation.subtype === 'HIRE_PURCHASE' || form.metadata.subtype === 'HIRE_PURCHASE')" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-200 uppercase tracking-wider">Hire Purchase Parameters</div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Total Terms (Months)</label>
              <input
                v-model.number="form.metadata.total_terms"
                type="number"
                min="1"
                required
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Current Term</label>
              <input
                v-model.number="form.metadata.current_term"
                type="number"
                min="0"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Financed Principal (฿)</label>
              <input
                v-model.number="form.metadata.financed_amount"
                type="number"
                step="0.01"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Flat Rate Interest (% p.a.)</label>
              <input
                v-model.number="form.metadata.flat_rate_pa"
                type="number"
                step="0.01"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Vehicle Model / Plate</label>
              <input
                v-model="form.metadata.vehicle_model"
                type="text"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Lender / Leasing</label>
              <input
                v-model="form.metadata.lender"
                type="text"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
        </div>

        <!-- 2. BNPL ACCOUNT -->
        <div v-else-if="obligation.type === 'INSTALLMENT' && (obligation.subtype === 'BNPL_ACCOUNT' || form.metadata.subtype === 'BNPL_ACCOUNT')" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-200 uppercase tracking-wider">BNPL Account Parameters</div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Credit Limit (฿)</label>
              <input
                v-model.number="form.metadata.credit_limit"
                type="number"
                step="0.01"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Provider</label>
              <input
                v-model="form.metadata.provider"
                type="text"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Cutoff Day (1-31)</label>
              <input
                v-model.number="form.metadata.cutoff_day"
                type="number"
                min="1"
                max="31"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Due Day (1-31)</label>
              <input
                v-model.number="form.metadata.due_day"
                type="number"
                min="1"
                max="31"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
        </div>

        <!-- 3. STANDARD INSTALLMENT -->
        <div v-else-if="obligation.type === 'INSTALLMENT'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Installment Parameters</div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Total Terms</label>
              <input
                v-model.number="form.metadata.total_terms"
                type="number"
                min="1"
                required
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Terms Already Paid</label>
              <input
                v-model.number="form.metadata.current_term"
                type="number"
                min="0"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Billing Day of Month (1-31)</label>
              <input
                v-model.number="form.billing_day"
                type="number"
                min="1"
                max="31"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Lender / Institution</label>
              <input
                v-model="form.metadata.lender"
                type="text"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
        </div>

        <!-- 4. SUBSCRIPTION -->
        <div v-else-if="obligation.type === 'SUBSCRIPTION'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Subscription Schedule</div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Billing Cycle</label>
              <select
                v-model="form.metadata.billing_cycle"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              >
                <option value="MONTHLY">Monthly</option>
                <option value="YEARLY">Yearly</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Billing Day (1-31)</label>
              <input
                v-model.number="form.billing_day"
                type="number"
                min="1"
                max="31"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
        </div>

        <!-- 5. DEBT -->
        <div v-else-if="obligation.type === 'DEBT'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Debt Settlement Details</div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Counterparty / Name</label>
              <input
                v-model="form.metadata.counterparty"
                type="text"
                required
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">PromptPay (for Recall)</label>
              <input
                v-model="form.metadata.promptpay"
                type="text"
                placeholder="PromptPay number"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Contact Phone</label>
              <input
                v-model="form.metadata.contact"
                type="text"
                placeholder="081-xxx-xxxx"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Remaining Balance (฿)</label>
              <input
                v-model.number="form.metadata.remaining_balance"
                type="number"
                step="0.01"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono"
              />
            </div>
          </div>
        </div>

        <!-- Common Next Due Date -->
        <div>
          <label class="block text-[10px] text-zinc-500 mb-1 font-mono">Next Due / Settlement Date</label>
          <input
            v-model="form.due_date"
            type="date"
            class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono"
          />
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="emit('close')"
            class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-all active:scale-[0.98]"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-all active:scale-[0.98] disabled:opacity-50 shadow-sm"
          >
            {{ isSubmitting ? 'Saving...' : 'Save Changes' }}
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
  (e: 'updated'): void
}>()

const financeStore = useFinanceStore()
const isSubmitting = ref(false)
const errorMessage = ref('')

const form = ref({
  title: '',
  amount: '',
  currency: 'THB',
  direction: 'OUTFLOW' as 'OUTFLOW' | 'INFLOW',
  due_date: '',
  billing_day: '' as string | number,
  metadata: {} as Record<string, any>,
})

watch(() => props.obligation, (ob) => {
  errorMessage.value = ''
  if (!ob) return

  form.value = {
    title: ob.title,
    amount: String(ob.amount),
    currency: ob.currency,
    direction: ob.direction || 'OUTFLOW',
    due_date: ob.due_date ? ob.due_date.split('T')[0] : '',
    billing_day: ob.billing_day || '',
    metadata: { ...(ob.metadata || {}) }
  }
}, { immediate: true })

async function handleSubmit() {
  if (!props.obligation) return
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    const payload: Record<string, any> = {
      title: form.value.title.trim(),
      amount: parseFloat(form.value.amount),
      currency: form.value.currency,
      direction: form.value.direction,
      metadata: { ...form.value.metadata }
    }

    if (form.value.due_date) {
      payload.due_date = form.value.due_date
    } else {
      payload.due_date = null
    }

    if (form.value.billing_day) {
      payload.billing_day = parseInt(String(form.value.billing_day), 10)
    } else {
      payload.billing_day = null
    }

    await financeStore.updateObligation(props.obligation.id, payload)
    emit('updated')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || 'Failed to update obligation'
  } finally {
    isSubmitting.value = false
  }
}
</script>