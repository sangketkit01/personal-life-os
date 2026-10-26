<template>
  <div v-if="isOpen" @click.self="emit('close')" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
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
        <h2 class="text-base font-semibold text-zinc-100 tracking-tight flex items-center gap-2">
          <span>Create Obligation</span>
          <span class="text-xs font-normal text-zinc-500 font-mono">Financial Commitment</span>
        </h2>
      </div>

      <!-- Type Selector Tabs -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-lg mb-4">
        <button
          v-for="t in typeOptions"
          :key="t.value"
          type="button"
          @click="selectedType = t.value"
          class="py-1.5 px-2 rounded text-center transition-all active:scale-[0.98] flex flex-col items-center gap-1"
          :class="[
            selectedType === t.value
              ? 'bg-zinc-800 text-zinc-100 shadow-sm font-semibold'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
          ]"
        >
          <component :is="t.icon" class="w-3.5 h-3.5" />
          <span class="text-[11px] font-medium">{{ t.label }}</span>
        </button>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

        <!-- Linked Project (SUBSCRIPTION & FREE_TRIAL only) -->
        <div v-if="selectedType === 'SUBSCRIPTION' || selectedType === 'FREE_TRIAL'" class="space-y-1.5">
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400">{{ t('fin.linkedProject') }}</label>
          <select
            v-model="form.project"
            class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
          >
            <option :value="null">—</option>
            <option v-for="p in workspaceStore.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="space-y-3.5">
        <!-- Subtype Switcher for INSTALLMENT -->
        <div v-if="selectedType === 'INSTALLMENT'" class="space-y-1.5">
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400">Installment Category</label>
          <div class="grid grid-cols-3 gap-2">
            <button
              type="button"
              @click="selectedSubtype = 'STANDARD'"
              class="px-2.5 py-1.5 rounded border text-xs font-mono transition-colors text-center"
              :class="selectedSubtype === 'STANDARD' ? 'bg-zinc-800 border-zinc-600 text-zinc-100' : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'"
            >
              Standard 0%
            </button>
            <button
              type="button"
              @click="selectedSubtype = 'HIRE_PURCHASE'"
              class="px-2.5 py-1.5 rounded border text-xs font-mono transition-colors text-center"
              :class="selectedSubtype === 'HIRE_PURCHASE' ? 'bg-zinc-800 border-zinc-600 text-zinc-100 font-semibold' : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'"
            >
              Vehicle Hire Purchase
            </button>
            <button
              type="button"
              @click="selectedSubtype = 'BNPL_ACCOUNT'"
              class="px-2.5 py-1.5 rounded border text-xs font-mono transition-colors text-center"
              :class="selectedSubtype === 'BNPL_ACCOUNT' ? 'bg-zinc-800 border-zinc-600 text-zinc-100 font-semibold' : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'"
            >
              BNPL Account
            </button>
          </div>
        </div>

        <!-- Flow Direction & Subtype for DEBT -->
        <div v-if="selectedType === 'DEBT'" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Debt Direction</label>
            <select
              v-model="form.direction"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600"
            >
              <option value="OUTFLOW">My Liability (I owe money / Outflow)</option>
              <option value="INFLOW">Receivable from Debtor (They owe me / Inflow)</option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Debt Type</label>
            <select
              v-model="selectedSubtype"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600"
            >
              <option value="INFORMAL_BORROW">Personal / Peer Loan (Informal)</option>
              <option value="FORMAL_LOAN">Financial Institution / Bank Loan (Formal)</option>
            </select>
          </div>
        </div>

        <!-- Common Title & Amount -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div class="sm:col-span-2">
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Title</label>
            <input
              v-model="form.title"
              type="text"
              required
              :placeholder="titlePlaceholder"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              {{ selectedSubtype === 'BNPL_ACCOUNT' ? 'Monthly Bill ' : (selectedType === 'FREE_TRIAL' ? 'Renew Cost ' : 'Amount ') }}
            </label>
            <input
              v-model="form.amount"
              type="number"
              step="0.01"
              required
              placeholder="0.00"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>
        </div>

        <!-- Currency -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Currency</label>
            <select
              v-model="form.currency"
              required
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600 transition-colors"
            >
              <option value="" disabled>Select currency</option>
              <option value="THB">THB (฿)</option>
              <option value="USD">USD ($)</option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Billing Day of Month (1-31)</label>
            <input
              v-model.number="form.billing_day"
              type="number"
              min="1"
              max="31"
              placeholder="1-31"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
            />
          </div>
        </div>

        <!-- 1. HIRE PURCHASE FIELDS -->
        <div v-if="selectedType === 'INSTALLMENT' && selectedSubtype === 'HIRE_PURCHASE'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-200 uppercase tracking-wider">Hire Purchase Parameters (Vehicle Loan)</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Financed Principal </label>
              <input
                v-model.number="form.metadata.financed_amount"
                type="number"
                step="0.01"
                required
                placeholder="0.00"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Flat Rate Interest (% p.a.)</label>
              <input
                v-model.number="form.metadata.flat_rate_pa"
                type="number"
                step="0.01"
                placeholder="0.00"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Total Terms (Months)</label>
              <input
                v-model.number="form.metadata.total_terms"
                type="number"
                min="1"
                required
                placeholder="Total terms"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Terms Already Paid</label>
              <input
                v-model.number="form.metadata.current_term"
                type="number"
                min="0"
                placeholder="0"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Vehicle Model / Plate</label>
              <input
                v-model="form.metadata.vehicle_model"
                type="text"
                placeholder="e.g. Honda Civic"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Lender / Leasing</label>
              <input
                v-model="form.metadata.lender"
                type="text"
                placeholder="e.g. Krungsri Auto"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
        </div>

        <!-- 2. BNPL ACCOUNT FIELDS -->
        <div v-else-if="selectedType === 'INSTALLMENT' && selectedSubtype === 'BNPL_ACCOUNT'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-200 uppercase tracking-wider">BNPL Credit Line (Revolving Credit)</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Total Credit Limit </label>
              <input
                v-model.number="form.metadata.credit_limit"
                type="number"
                step="0.01"
                required
                placeholder="0.00"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Provider</label>
              <input
                v-model="form.metadata.provider"
                type="text"
                placeholder="e.g. Shopee SPayLater"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Statement Cutoff Day of Month</label>
              <input
                v-model.number="form.metadata.cutoff_day"
                type="number"
                min="1"
                max="31"
                placeholder="1-31"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Payment Due Day of Month</label>
              <input
                v-model.number="form.metadata.due_day"
                type="number"
                min="1"
                max="31"
                placeholder="1-31"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
        </div>

        <!-- 3. STANDARD INSTALLMENT -->
        <div v-else-if="selectedType === 'INSTALLMENT'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Installment Parameters</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Total Terms</label>
              <input
                v-model.number="form.metadata.total_terms"
                type="number"
                min="1"
                required
                placeholder="Total terms"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Terms Already Paid</label>
              <input
                v-model.number="form.metadata.current_term"
                type="number"
                min="0"
                placeholder="0"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div>
            <label class="block text-[10px] text-zinc-500 mb-1">Lender / Institution</label>
            <input
              v-model="form.metadata.lender"
              type="text"
              placeholder="e.g. KBank, Apple Store"
              class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            />
          </div>
        </div>

        <!-- 4. DEBTS -->
        <div v-else-if="selectedType === 'DEBT'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Counterparty & Settlement Details</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Counterparty / Name</label>
              <input
                v-model="form.metadata.counterparty"
                type="text"
                required
                placeholder="e.g. Alex Wong"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Settlement Date</label>
              <input
                v-model="form.due_date"
                type="date"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Contact Phone / Line</label>
              <input
                v-model="form.metadata.contact"
                type="text"
                placeholder="e.g. 081-xxx-xxxx, LINE"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">PromptPay (for Recall)</label>
              <input
                v-model="form.metadata.promptpay"
                type="text"
                placeholder="e.g. PromptPay number"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
        </div>

        <!-- 5. FREE TRIAL -->
        <div v-else-if="selectedType === 'FREE_TRIAL'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Trial Hunter Configuration</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Expiration / Renewal Date</label>
              <input
                v-model="form.due_date"
                type="date"
                required
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Account Email</label>
              <input
                v-model="form.metadata.account_email"
                type="email"
                placeholder="name@example.com"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div>
            <label class="block text-[10px] text-zinc-500 mb-1">Direct Cancellation URL</label>
            <input
              v-model="form.metadata.cancel_url"
              type="url"
              placeholder="https://..."
              class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            />
          </div>
        </div>

        <!-- 6. SUBSCRIPTION -->
        <div v-else-if="selectedType === 'SUBSCRIPTION'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Subscription Schedule</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Billing Cycle</label>
              <select
                v-model="form.metadata.billing_cycle"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              >
                <option value="" disabled>Select billing cycle</option>
                <option value="MONTHLY">Monthly</option>
                <option value="YEARLY">Yearly</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Next Due Date</label>
              <input
                v-model="form.due_date"
                type="date"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div>
            <label class="block text-[10px] text-zinc-500 mb-1">Account Email / Username</label>
            <input
              v-model="form.metadata.account_email"
              type="text"
              placeholder="name@example.com"
              class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            />
          </div>
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
            {{ isSubmitting ? 'Saving...' : 'Create Obligation' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useFinanceStore } from '../../stores/finance'
import type { ObligationType, ObligationSubtype } from '../../types/finance'
import { useWorkspaceStore } from '../../stores/workspace'
import { t } from '../../i18n'
import {
  CalendarClock,
  ShieldAlert,
  Repeat,
  HandCoins,
  X
} from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created'): void
}>()

const financeStore = useFinanceStore()
const workspaceStore = useWorkspaceStore()

const typeOptions: Array<{ value: ObligationType; label: string; icon: any }> = [
  { value: 'INSTALLMENT', label: 'Installment', icon: CalendarClock },
  { value: 'FREE_TRIAL', label: 'Free Trial', icon: ShieldAlert },
  { value: 'SUBSCRIPTION', label: 'Subscription', icon: Repeat },
  { value: 'DEBT', label: 'Debt', icon: HandCoins },
]

const selectedType = ref<ObligationType>('INSTALLMENT')
const selectedSubtype = ref<ObligationSubtype>('STANDARD')
const isSubmitting = ref(false)
const errorMessage = ref('')

const form = ref({
  title: '',
  amount: '',
  currency: '',
  direction: 'OUTFLOW' as 'OUTFLOW' | 'INFLOW',
  due_date: '',
  billing_day: '' as string | number,
  metadata: {} as Record<string, any>,
  project: null as string | null,
})

const titlePlaceholder = computed(() => {
  if (selectedType.value === 'INSTALLMENT') {
    if (selectedSubtype.value === 'HIRE_PURCHASE') return 'e.g. Honda Civic'
    if (selectedSubtype.value === 'BNPL_ACCOUNT') return 'e.g. Shopee SPayLater'
    return 'e.g. MacBook Pro M3'
  }
  if (selectedType.value === 'FREE_TRIAL') return 'e.g. Netflix, Spotify'
  if (selectedType.value === 'SUBSCRIPTION') return 'e.g. ChatGPT Plus'
  if (selectedType.value === 'DEBT') {
    return form.value.direction === 'INFLOW' ? 'e.g. Alex Wong' : 'e.g. KBank'
  }
  return 'Title'
})

onMounted(async () => {
  if (workspaceStore.projects.length === 0) {
    await workspaceStore.fetchProjects().catch(() => {})
  }
})

watch(() => props.isOpen, (open) => {
  if (open) {
    errorMessage.value = ''
    form.value.title = ''
    form.value.amount = ''
    form.value.currency = ''
    form.value.due_date = ''
    form.value.billing_day = ''
    form.value.project = null
    resetMetadata()
  }
})

function resetMetadata() {
  if (selectedType.value === 'INSTALLMENT') {
    if (selectedSubtype.value === 'HIRE_PURCHASE') {
      form.value.metadata = {
        total_terms: null,
        current_term: 0,
        financed_amount: null,
        flat_rate_pa: null,
        vat_pct: 0,
        vehicle_model: '',
        lender: ''
      }
    } else if (selectedSubtype.value === 'BNPL_ACCOUNT') {
      form.value.metadata = {
        credit_limit: null,
        cutoff_day: null,
        due_day: null,
        provider: ''
      }
    } else {
      form.value.metadata = { total_terms: null, current_term: 0, lender: '' }
    }
  } else if (selectedType.value === 'FREE_TRIAL') {
    form.value.metadata = { account_email: '', linked_card: '', cancel_url: '' }
  } else if (selectedType.value === 'SUBSCRIPTION') {
    form.value.metadata = { billing_cycle: '', account_email: '', payment_method: '' }
  } else if (selectedType.value === 'DEBT') {
    form.value.metadata = { counterparty: '', contact: '', promptpay: '' }
  }
}

watch(selectedType, (newType) => {
  errorMessage.value = ''
  if (newType === 'INSTALLMENT') {
    selectedSubtype.value = 'STANDARD'
    form.value.direction = 'OUTFLOW'
  } else if (newType === 'FREE_TRIAL') {
    selectedSubtype.value = 'STANDARD'
    form.value.direction = 'OUTFLOW'
  } else if (newType === 'SUBSCRIPTION') {
    selectedSubtype.value = 'STANDARD'
    form.value.direction = 'OUTFLOW'
  } else if (newType === 'DEBT') {
    selectedSubtype.value = 'INFORMAL_BORROW'
  }
  resetMetadata()
}, { immediate: true })

watch(selectedSubtype, () => {
  resetMetadata()
})

// Auto-calculate Hire Purchase monthly installment (including VAT 7%)
watch(
  () => [
    selectedType.value,
    selectedSubtype.value,
    form.value.metadata?.financed_amount,
    form.value.metadata?.flat_rate_pa,
    form.value.metadata?.total_terms
  ],
  ([type, subtype, financed, rate, terms]) => {
    if (type === 'INSTALLMENT' && subtype === 'HIRE_PURCHASE') {
      const p = Number(financed) || 0
      const r = Number(rate) || 0
      const t = Number(terms) || 0
      if (p > 0 && t > 0) {
        const totalInterest = p * (r / 100) * (t / 12)
        const monthlyPrincipal = p / t
        const monthlyInterest = totalInterest / t
        const vat = Number(form.value.metadata?.vat_pct || 0)
        const monthlyWithVat = (monthlyPrincipal + monthlyInterest) * (1 + vat / 100)
        form.value.amount = String(parseFloat(monthlyWithVat.toFixed(2)))
      }
    }
  },
  { deep: true }
)

async function handleSubmit() {
  if (!form.value.title.trim()) {
    errorMessage.value = 'Title is required'
    return
  }
  if (!form.value.currency) {
    errorMessage.value = 'Please select a currency'
    return
  }
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    const payload: Record<string, any> = {
      title: form.value.title.trim(),
      type: selectedType.value,
      subtype: selectedSubtype.value,
      direction: form.value.direction || 'OUTFLOW',
      currency: form.value.currency || 'THB',
      amount: parseFloat(form.value.amount),
      project: form.value.project,
      metadata: { ...form.value.metadata, subtype: selectedSubtype.value },
    }

    if (form.value.due_date) {
      payload.due_date = form.value.due_date
    }
    if (form.value.billing_day) {
      payload.billing_day = parseInt(String(form.value.billing_day), 10)
    }

    if (selectedType.value === 'FREE_TRIAL') {
      payload.metadata.auto_renew_cost = parseFloat(form.value.amount)
    }

    await financeStore.createObligation(payload)
    emit('created')
    emit('close')

    form.value.title = ''
    form.value.amount = ''
    form.value.due_date = ''
    form.value.billing_day = ''
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || err.response?.data?.metadata || 'Failed to create obligation. Check inputs.'
  } finally {
    isSubmitting.value = false
  }
}
</script>