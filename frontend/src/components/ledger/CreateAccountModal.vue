<template>
  <div
    v-if="isOpen"
    @click.self="emit('close')"
    class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans"
  >
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl relative my-8 max-h-[90vh] overflow-y-auto">
      <button
        @click="emit('close')"
        type="button"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="mb-4">
        <h3 class="text-base font-semibold text-zinc-100 tracking-tight flex items-center gap-2">
          <span>{{ editingAccount ? 'Edit Account' : 'New Account' }}</span>
        </h3>
      </div>

      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4 text-xs font-mono">
        <!-- Account Type Selection -->
        <div>
          <label class="block text-[11px] text-zinc-300 mb-1.5 font-medium">Account Type</label>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="t in accountTypes"
              :key="t.value"
              type="button"
              @click="form.account_type = t.value"
              class="p-2 rounded-lg border text-center transition-all active:scale-[0.98] flex flex-col items-center gap-1"
              :class="form.account_type === t.value
                ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-semibold shadow-sm'
                : 'bg-zinc-900/50 text-zinc-400 border-zinc-800 hover:text-zinc-200 hover:bg-zinc-800/40'"
            >
              <component :is="t.icon" class="w-3.5 h-3.5" />
              <span class="text-[10px]">{{ t.label }}</span>
            </button>
          </div>
        </div>

        <!-- Account Name -->
        <div>
          <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Account Name <span class="text-rose-400">*</span></label>
          <input
            v-model="form.name"
            type="text"
            required
            placeholder="e.g. Payroll Account, Cash Wallet"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono transition-colors"
          />
        </div>

        <!-- Institution Name & Masked Ref -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Financial Institution / Bank</label>
            <input
              v-model="form.institution_name"
              type="text"
              placeholder="e.g. KBank, SCB"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 transition-colors"
            />
          </div>
          <div>
            <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Last 4 Digits (Optional)</label>
            <input
              v-model="form.account_number"
              type="text"
              placeholder="1234"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 transition-colors"
            />
          </div>
        </div>

        <!-- Initial Balance & Currency -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] text-zinc-300 mb-1 font-medium">
              {{ editingAccount ? 'Opening Balance' : 'Initial Balance' }} <span class="text-rose-400">*</span>
            </label>
            <div class="relative">
              <span class="absolute left-3 top-2 text-zinc-500">฿</span>
              <input
                v-model.number="form.initial_balance"
                type="number"
                step="0.01"
                required
                placeholder="0.00"
                class="w-full pl-7 pr-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono transition-colors"
              />
            </div>
          </div>
          <div>
            <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Currency</label>
            <select
              v-model="form.currency"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 transition-colors"
            >
              <option value="THB">THB (฿)</option>
              <option value="USD">USD ($)</option>
            </select>
          </div>
        </div>

        <!-- Credit Limit (Only for Credit Card) -->
        <div v-if="form.account_type === 'CREDIT_CARD'">
          <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Credit Limit (฿)</label>
          <input
            v-model.number="form.credit_limit"
            type="number"
            step="100"
            placeholder="0.00"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono transition-colors"
          />
        </div>

        <!-- Default Account Toggle -->
        <label class="flex items-center gap-2 cursor-pointer pt-1 select-none">
          <input
            v-model="form.is_default"
            type="checkbox"
            class="rounded bg-zinc-900 border-zinc-700 text-zinc-100 accent-zinc-500 w-3.5 h-3.5"
          />
          <span class="text-zinc-300 text-xs">Set as default account for new transactions</span>
        </label>

        <!-- Form Actions -->
        <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="emit('close')"
            class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-sans text-zinc-300 transition-all active:scale-[0.98]"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-sans font-semibold transition-all active:scale-[0.98] disabled:opacity-50 shadow-sm"
          >
            {{ isSubmitting ? 'Saving...' : (editingAccount ? 'Save Changes' : 'Create Account') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onUnmounted } from 'vue'
import { useLedgerStore } from '../../stores/ledger'
import type { LedgerAccount, AccountType } from '../../types/ledger'
import {
  X,
  Building2,
  CreditCard,
  Briefcase,
  Smartphone,
  Banknote
} from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  editingAccount?: LedgerAccount | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

const ledgerStore = useLedgerStore()
const isSubmitting = ref(false)
const errorMessage = ref('')

const accountTypes = [
  { value: 'BANK' as AccountType, label: 'Bank', icon: Building2 },
  { value: 'CREDIT_CARD' as AccountType, label: 'Card', icon: CreditCard },
  { value: 'BROKERAGE_CASH' as AccountType, label: 'Brokerage', icon: Briefcase },
  { value: 'E_WALLET' as AccountType, label: 'Wallet', icon: Smartphone },
  { value: 'CASH' as AccountType, label: 'Cash', icon: Banknote }
]

const form = reactive({
  name: '',
  account_type: 'BANK' as AccountType,
  institution_name: '',
  account_number: '',
  initial_balance: 0,
  currency: 'THB',
  credit_limit: null as number | null,
  is_default: false
})

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.isOpen) {
    emit('close')
  }
}

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      window.addEventListener('keydown', handleKeyDown)
      errorMessage.value = ''
    } else {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }
)

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

watch(
  () => props.editingAccount,
  (acc) => {
    if (acc) {
      form.name = acc.name
      form.account_type = acc.account_type
      form.institution_name = acc.institution_name || ''
      form.account_number = acc.account_number || ''
      form.initial_balance = Number(acc.initial_balance || 0)
      form.currency = acc.currency || 'THB'
      form.credit_limit = acc.credit_limit ? Number(acc.credit_limit) : null
      form.is_default = acc.is_default || false
    } else {
      form.name = ''
      form.account_type = 'BANK'
      form.institution_name = ''
      form.account_number = ''
      form.initial_balance = 0
      form.currency = 'THB'
      form.credit_limit = null
      form.is_default = false
    }
  },
  { immediate: true }
)

async function handleSubmit() {
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    if (props.editingAccount) {
      await ledgerStore.updateAccount(props.editingAccount.id, {
        name: form.name,
        account_type: form.account_type,
        institution_name: form.institution_name,
        account_number: form.account_number,
        credit_limit: form.credit_limit,
        is_default: form.is_default
      })
    } else {
      await ledgerStore.createAccount({
        name: form.name,
        account_type: form.account_type,
        institution_name: form.institution_name,
        account_number: form.account_number,
        initial_balance: form.initial_balance,
        currency: form.currency,
        credit_limit: form.credit_limit,
        is_default: form.is_default
      })
    }
    emit('saved')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.error || err.message || 'Failed to save account.'
  } finally {
    isSubmitting.value = false
  }
}
</script>
