<template>
  <div class="max-w-xl mx-auto py-4 font-sans pb-16 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          type="button"
          @click="router.push('/finance/debts')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
          title="Back to Debts"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Debt Record</h1>
          <p class="text-xs text-zinc-500 mt-0.5">
            Record peer loans, receivables, or personal liabilities
          </p>
        </div>
      </div>
    </div>

    <!-- Direction Selector: Money Lent vs Money Borrowed -->
    <div class="grid grid-cols-2 gap-1 p-1 bg-zinc-900/80 border border-zinc-800 rounded-lg">
      <button
        type="button"
        @click="form.direction = 'INFLOW'"
        class="py-2 px-3 rounded text-xs font-medium transition-colors flex items-center justify-center gap-2"
        :class="form.direction === 'INFLOW' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <UserCheck class="w-3.5 h-3.5 text-zinc-400" />
        <span>Money Lent (Receivable)</span>
      </button>

      <button
        type="button"
        @click="form.direction = 'OUTFLOW'"
        class="py-2 px-3 rounded text-xs font-medium transition-colors flex items-center justify-center gap-2"
        :class="form.direction === 'OUTFLOW' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <HandCoins class="w-3.5 h-3.5 text-zinc-400" />
        <span>Money Borrowed (Liability)</span>
      </button>
    </div>

    <!-- Main Clean Form -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Counterparty & Loan Subtype -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            {{ form.direction === 'INFLOW' ? 'Debtor Name' : 'Creditor / Lender Name' }} <span class="text-rose-400">*</span>
          </label>
          <input
            v-model="form.counterparty"
            type="text"
            required
            :placeholder="form.direction === 'INFLOW' ? 'e.g. John Doe' : 'e.g. Kasikorn Bank, Jane'"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          />
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Loan Category</label>
          <select
            v-model="form.subtype"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option value="INFORMAL_BORROW">Peer / Informal Loan</option>
            <option value="FORMAL_LOAN">Formal Bank Loan</option>
          </select>
        </div>
      </div>

      <!-- Amount & Currency -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">
            Principal Amount <span class="text-rose-400">*</span>
          </label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">
              {{ form.currency === 'USD' ? '$' : '฿' }}
            </span>
            <input
              v-model.number="form.amount"
              type="number"
              step="0.01"
              min="1"
              required
              placeholder="0.00"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-7 pr-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
            />
          </div>
        </div>

        <div>
          <label class="block text-xs font-mono text-zinc-400 mb-1.5">Currency</label>
          <select
            v-model="form.currency"
            class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
          >
            <option value="THB">THB (฿)</option>
            <option value="USD">USD ($)</option>
          </select>
        </div>
      </div>

      <!-- Due Date & Flexible Deadline -->
      <div class="space-y-1.5">
        <div class="flex items-center justify-between">
          <label class="block text-xs font-mono text-zinc-400">
            Repayment Due Date
          </label>
          <label class="flex items-center gap-1.5 cursor-pointer text-xs font-mono text-zinc-400">
            <input
              v-model="form.is_flexible"
              type="checkbox"
              class="rounded bg-zinc-950 border-zinc-800 text-zinc-100 focus:ring-0"
            />
            <span>Flexible / No strict date</span>
          </label>
        </div>

        <input
          v-if="!form.is_flexible"
          v-model="form.due_date"
          type="date"
          required
          class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
        />
      </div>

      <!-- Progressive Disclosure: Contact, Payment & Notes -->
      <div class="pt-1">
        <button
          type="button"
          @click="showAdvanced = !showAdvanced"
          class="text-xs font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <span>{{ showAdvanced ? '- Less Details' : '+ Contact & Settlement Details (Optional)' }}</span>
        </button>

        <div v-if="showAdvanced" class="mt-3 space-y-3 pt-3 border-t border-zinc-800/60">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Phone / Contact ID</label>
              <input
                v-model="form.contact"
                type="text"
                placeholder="e.g. 081-xxx-xxxx, LINE"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>

            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">PromptPay / Settlement Account</label>
              <input
                v-model="form.promptpay"
                type="text"
                placeholder="e.g. PromptPay number"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>
          </div>

          <div v-if="form.subtype === 'FORMAL_LOAN'" class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-zinc-800/40">
            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Interest Rate (% p.a.)</label>
              <input
                v-model.number="form.interest_rate_pa"
                type="number"
                step="0.01"
                placeholder="0.00"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>

            <div>
              <label class="block text-xs font-mono text-zinc-400 mb-1">Contract / Ref Number</label>
              <input
                v-model="form.contract_no"
                type="text"
                placeholder="e.g. LN-998811"
                class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-mono text-zinc-400 mb-1">Notes / Purpose</label>
            <textarea
              v-model="form.reason"
              rows="2"
              placeholder="e.g. Travel tickets, equipment split"
              class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-100 font-mono focus:border-zinc-600 outline-none transition-colors resize-none"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
        <button
          type="button"
          @click="router.push('/finance/debts')"
          class="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-zinc-300 font-medium transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          :disabled="isActionLoading"
          class="px-5 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
        >
          <Check class="w-3.5 h-3.5" />
          <span>{{ isActionLoading ? 'Saving...' : 'Record Debt Entry' }}</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDebts } from '../../composables/finance/useDebts'
import { useToastStore } from '../../stores/toast'
import {
  ArrowLeft,
  UserCheck,
  HandCoins,
  Check
} from 'lucide-vue-next'

const router = useRouter()
const toast = useToastStore()
const { createDebt, isActionLoading } = useDebts()

const showAdvanced = ref(false)

const form = reactive({
  direction: 'INFLOW' as 'INFLOW' | 'OUTFLOW',
  subtype: 'INFORMAL_BORROW' as 'INFORMAL_BORROW' | 'FORMAL_LOAN',
  counterparty: '',
  contact: '',
  promptpay: localStorage.getItem('finance_promptpay_default') || '',
  amount: 5000,
  currency: 'THB',
  due_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
  is_flexible: false,
  interest_rate_pa: 0,
  contract_no: '',
  reason: ''
})

async function handleSubmit() {
  if (!form.counterparty.trim() || !form.amount) {
    toast.error('Please specify counterparty name and principal amount')
    return
  }

  try {
    const created = await createDebt({
      title: `${form.direction === 'INFLOW' ? 'Debtor' : 'Liability'}: ${form.counterparty.trim()}`,
      direction: form.direction,
      subtype: form.subtype,
      amount: Number(form.amount),
      currency: form.currency,
      due_date: form.is_flexible ? null : form.due_date,
      counterparty: form.counterparty.trim(),
      contact: form.contact.trim(),
      promptpay: form.promptpay.trim(),
      reason: form.reason.trim(),
      is_flexible: form.is_flexible,
      interest_rate_pa: Number(form.interest_rate_pa || 0),
      contract_no: form.contract_no.trim()
    })

    toast.success(`Debt entry for ${form.counterparty} created!`)
    router.push(`/finance/debts/${created.id}`)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to create debt entry')
  }
}
</script>
