<template>
  <div class="max-w-4xl mx-auto space-y-6 font-sans">
    <!-- Breadcrumb & Back Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          @click="router.push('/finance/debts')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Debt Ledger"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-base font-semibold text-zinc-100 tracking-tight">New Debt Record</h1>
            <span
              class="px-2 py-0.5 rounded text-[10px] font-mono uppercase border font-medium"
              :class="form.direction === 'INFLOW' ? 'bg-zinc-900 text-emerald-400 border-emerald-500/30' : 'bg-zinc-900 text-rose-400 border-rose-500/30'"
            >
              {{ form.direction === 'INFLOW' ? 'DEBTOR RECEIVABLE' : 'LIABILITY PAYABLE' }}
            </span>
          </div>
          <p class="text-xs text-zinc-500 mt-0.5">
            Record a peer-to-peer loan, debtor receivable, or personal bank liability with custom terms.
          </p>
        </div>
      </div>
    </div>

    <!-- Main Creation Layout: Form & Live Calculation Preview -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Left: Form Controls (7 cols) -->
      <form @submit.prevent="handleSubmit" class="lg:col-span-7 space-y-5">
        <!-- 1. Direction Switcher: Inflow vs Outflow -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3.5">
          <label class="block text-xs font-mono text-zinc-400 uppercase tracking-wider font-semibold">
            Cash Flow Direction <span class="text-rose-400">*</span>
          </label>

          <div class="grid grid-cols-2 gap-3">
            <button
              type="button"
              @click="form.direction = 'INFLOW'"
              class="p-3.5 rounded-xl border text-left transition-all space-y-1.5"
              :class="form.direction === 'INFLOW'
                ? 'bg-zinc-900 border-emerald-500/40 text-emerald-400 shadow-sm'
                : 'bg-zinc-950/60 border-zinc-800 text-zinc-400 hover:border-zinc-700'"
            >
              <div class="flex items-center gap-2">
                <UserCheck class="w-4 h-4" />
                <span class="font-semibold text-xs font-sans">Money Lent (Receivable)</span>
              </div>
              <p class="text-[11px] text-zinc-500 leading-normal font-mono">
                Someone borrowed from you. An asset to collect back.
              </p>
            </button>

            <button
              type="button"
              @click="form.direction = 'OUTFLOW'"
              class="p-3.5 rounded-xl border text-left transition-all space-y-1.5"
              :class="form.direction === 'OUTFLOW'
                ? 'bg-zinc-900 border-rose-500/40 text-rose-400 shadow-sm'
                : 'bg-zinc-950/60 border-zinc-800 text-zinc-400 hover:border-zinc-700'"
            >
              <div class="flex items-center gap-2">
                <HandCoins class="w-4 h-4" />
                <span class="font-semibold text-xs font-sans">Money Borrowed (Liability)</span>
              </div>
              <p class="text-[11px] text-zinc-500 leading-normal font-mono">
                You borrowed money from a bank or friend. A debt to pay.
              </p>
            </button>
          </div>
        </div>

        <!-- 2. Counterparty & Classification Details -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center justify-between pb-2 border-b border-zinc-800/60">
            <div class="flex items-center gap-2">
              <Users class="w-4 h-4 text-zinc-400" />
              <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Counterparty & Loan Classification
              </h2>
            </div>

            <!-- Subtype Switch -->
            <div class="flex items-center gap-1 p-0.5 bg-zinc-950 border border-zinc-800 rounded-lg text-[10px] font-mono">
              <button
                type="button"
                @click="form.subtype = 'INFORMAL_BORROW'"
                class="px-2 py-0.5 rounded transition-colors"
                :class="form.subtype === 'INFORMAL_BORROW' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
              >
                Informal / Peer
              </button>
              <button
                type="button"
                @click="form.subtype = 'FORMAL_LOAN'"
                class="px-2 py-0.5 rounded transition-colors"
                :class="form.subtype === 'FORMAL_LOAN' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-500 hover:text-zinc-300'"
              >
                Formal Bank Loan
              </button>
            </div>
          </div>

          <!-- Counterparty Name -->
          <div class="space-y-1.5">
            <label class="block text-xs font-mono text-zinc-400">
              {{ form.direction === 'INFLOW' ? 'Debtor Name' : 'Creditor / Lender Name' }} <span class="text-rose-400">*</span>
            </label>
            <input
              v-model="form.counterparty"
              type="text"
              required
              :placeholder="form.direction === 'INFLOW' ? 'e.g. Alex Wong' : (form.subtype === 'FORMAL_LOAN' ? 'e.g. Kasikorn Bank Personal Loan' : 'e.g. Michael Chen')"
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
            />
          </div>

          <!-- Contact & PromptPay Destination -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Contact Phone / LINE ID
              </label>
              <input
                v-model="form.contact"
                type="text"
                placeholder="081-xxx-xxxx"
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
              />
            </div>

            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Settlement PromptPay / Account
              </label>
              <input
                v-model="form.promptpay"
                type="text"
                placeholder="PromptPay / Bank Account"
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors"
              />
            </div>
          </div>
        </div>

        <!-- 3. Financial Terms & Due Date -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center gap-2 pb-2 border-b border-zinc-800/60">
            <CreditCard class="w-4 h-4 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Principal Amount & Timeline
            </h2>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            <!-- Amount -->
            <div class="sm:col-span-2 space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">
                Principal Amount <span class="text-rose-400">*</span>
              </label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-mono text-zinc-500">฿</span>
                <input
                  v-model.number="form.amount"
                  type="number"
                  step="0.01"
                  min="1"
                  required
                  placeholder="5000.00"
                  class="w-full pl-7 pr-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
                />
              </div>
            </div>

            <!-- Currency -->
            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">Currency</label>
              <select
                v-model="form.currency"
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
              >
                <option value="THB">THB (฿)</option>
                <option value="USD">USD ($)</option>
              </select>
            </div>
          </div>

          <!-- Due Date & Flexible Deadline Toggle -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="block text-xs font-mono text-zinc-400">
                Repayment Due Date
              </label>
              <label class="flex items-center gap-2 cursor-pointer text-xs font-mono text-zinc-400">
                <input
                  v-model="form.is_flexible"
                  type="checkbox"
                  class="rounded bg-zinc-950 border-zinc-800 text-zinc-100 focus:ring-0"
                />
                <span>Flexible / No strict deadline</span>
              </label>
            </div>

            <input
              v-if="!form.is_flexible"
              v-model="form.due_date"
              type="date"
              required
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
            />
            <div v-else class="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-800/80 text-[11px] font-mono text-zinc-500">
              Open-ended loan without a fixed cutoff milestone.
            </div>
          </div>

          <!-- Formal Loan Add-ons -->
          <div v-if="form.subtype === 'FORMAL_LOAN'" class="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2 border-t border-zinc-800/60">
            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">Interest Rate (% p.a.)</label>
              <input
                v-model.number="form.interest_rate_pa"
                type="number"
                step="0.01"
                placeholder="15.00"
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
              />
            </div>
            <div class="space-y-1.5">
              <label class="block text-xs font-mono text-zinc-400">Contract / Account Ref</label>
              <input
                v-model="form.contract_no"
                type="text"
                placeholder="LN-987654"
                class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 font-mono outline-none transition-colors"
              />
            </div>
          </div>
        </div>

        <!-- 4. Reason / Notes -->
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center gap-2 pb-2 border-b border-zinc-800/60">
            <FileText class="w-4 h-4 text-zinc-400" />
            <h2 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Context & Reason
            </h2>
          </div>

          <div class="space-y-1.5">
            <textarea
              v-model="form.reason"
              rows="2"
              placeholder="e.g. Lent for overseas flight tickets, promised to transfer back by end of month..."
              class="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 text-xs text-zinc-100 placeholder-zinc-500 font-mono outline-none transition-colors resize-none"
            ></textarea>
          </div>
        </div>

        <!-- Submission Actions -->
        <div class="flex items-center justify-end gap-3 pt-2">
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

      <!-- Right: Live Simulation Preview (5 cols) -->
      <div class="lg:col-span-5 space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/60 border border-zinc-800/90 space-y-4 sticky top-6">
          <div class="flex items-center justify-between pb-2 border-b border-zinc-800/80">
            <div class="flex items-center gap-2">
              <CreditCard class="w-4 h-4 text-zinc-300" />
              <h3 class="text-xs font-semibold font-mono uppercase text-zinc-300">
                Ledger Impact Preview
              </h3>
            </div>
            <span class="text-[10px] font-mono text-zinc-500 uppercase">
              LIVE PREVIEW
            </span>
          </div>

          <!-- Position Badge -->
          <div>
            <div class="flex items-center justify-between">
              <span
                class="text-[9px] font-mono uppercase px-2 py-0.5 rounded border font-semibold"
                :class="form.direction === 'INFLOW' ? 'bg-zinc-950 text-emerald-400 border-emerald-500/30' : 'bg-zinc-950 text-rose-400 border-rose-500/30'"
              >
                {{ form.direction === 'INFLOW' ? 'Receivable (Inflow)' : 'Liability (Outflow)' }}
              </span>
              <span class="text-[10px] font-mono text-zinc-500">
                {{ form.subtype === 'FORMAL_LOAN' ? 'Formal Bank Loan' : 'Informal / IOU' }}
              </span>
            </div>
            <h4 class="text-base font-semibold text-zinc-100 font-sans mt-2">
              {{ form.counterparty || 'Counterparty' }}
            </h4>
          </div>

          <!-- Numbers Grid -->
          <div class="grid grid-cols-2 gap-2.5 p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 font-mono text-xs">
            <div>
              <span class="text-[9px] text-zinc-500 uppercase block">Initial Principal</span>
              <span
                class="font-semibold text-sm tabular-nums"
                :class="form.direction === 'INFLOW' ? 'text-emerald-400' : 'text-rose-400'"
              >
                {{ form.direction === 'INFLOW' ? '+' : '-' }}฿{{ Number(form.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </span>
            </div>
            <div>
              <span class="text-[9px] text-zinc-500 uppercase block">Due Milestone</span>
              <span class="text-zinc-200 font-semibold text-xs">
                {{ form.is_flexible ? 'Flexible' : (form.due_date ? new Date(form.due_date).toLocaleDateString('en-GB') : 'Not set') }}
              </span>
            </div>
          </div>

          <!-- Debtor Recall Template Preview (Only for Inflow / Debtor) -->
          <div v-if="form.direction === 'INFLOW'" class="space-y-2 pt-2 border-t border-zinc-800/60 font-mono text-xs">
            <div class="flex items-center gap-1.5 text-zinc-400 text-[11px] font-semibold">
              <MessageSquare class="w-3.5 h-3.5" />
              <span>Recall Message Preview</span>
            </div>
            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-300 text-[11px] font-sans leading-relaxed">
              {{ simulatedRecallText }}
            </div>
          </div>

          <div class="p-3 rounded-lg bg-zinc-950/70 border border-zinc-800/80 text-[11px] font-sans text-zinc-400 leading-relaxed">
            ℹ️ Full payment history, partial settlements, settlement receipts, and document attachments can be tracked from the dedicated debt dossier page after creation.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDebts } from '../../composables/finance/useDebts'
import { useToastStore } from '../../stores/toast'
import {
  ArrowLeft,
  UserCheck,
  HandCoins,
  Users,
  CreditCard,
  FileText,
  MessageSquare,
  Check
} from 'lucide-vue-next'

const router = useRouter()
const toast = useToastStore()
const { createDebt, isActionLoading } = useDebts()

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

const simulatedRecallText = computed(() => {
  const party = form.counterparty || 'Friend'
  const amt = Number(form.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })
  const due = form.is_flexible ? 'soon' : (form.due_date ? new Date(form.due_date).toLocaleDateString('en-GB') : 'soon')
  const pp = form.promptpay ? `PromptPay: ${form.promptpay}` : 'the designated account'
  return `Hi ${party}, friendly reminder regarding the outstanding balance of ฿${amt} (due: ${due}). When convenient, please transfer to ${pp}. Thank you!`
})

async function handleSubmit() {
  if (!form.counterparty || !form.amount) {
    toast.error('Please specify counterparty name and principal amount')
    return
  }

  try {
    const created = await createDebt({
      title: `${form.direction === 'INFLOW' ? 'Debtor' : 'Liability'}: ${form.counterparty}`,
      direction: form.direction,
      subtype: form.subtype,
      amount: Number(form.amount),
      currency: form.currency,
      due_date: form.is_flexible ? null : form.due_date,
      counterparty: form.counterparty,
      contact: form.contact,
      promptpay: form.promptpay,
      reason: form.reason,
      is_flexible: form.is_flexible,
      interest_rate_pa: Number(form.interest_rate_pa || 0),
      contract_no: form.contract_no
    })

    toast.success(`Debt entry for ${form.counterparty} created!`)
    router.push(`/finance/debts/${created.id}`)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to create debt entry')
  }
}
</script>
