<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-lg p-6 shadow-2xl relative my-8">
      <!-- Close button -->
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- Modal Title -->
      <div class="mb-5">
        <h2 class="text-base font-semibold text-zinc-100 tracking-tight">Create Financial Obligation</h2>
        <p class="text-xs text-zinc-500 mt-0.5">Select category to configure recurring settlements or liability alert schedules</p>
      </div>

      <!-- Type Selector Tabs -->
      <div class="grid grid-cols-4 gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-lg mb-4">
        <button
          v-for="t in typeOptions"
          :key="t.value"
          type="button"
          @click="selectedType = t.value"
          class="py-1.5 px-2 rounded text-center transition-colors flex flex-col items-center gap-1"
          :class="[
            selectedType === t.value
              ? 'bg-zinc-800 text-zinc-100 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
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
              :placeholder="titlePlaceholder"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
              {{ selectedType === 'FREE_TRIAL' ? 'Auto-renew (฿)' : 'Amount (฿)' }}
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

        <!-- 1. DYNAMIC FIELDS FOR INSTALLMENT -->
        <div v-if="selectedType === 'INSTALLMENT'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Installment Parameters</div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Total Terms (e.g. 36)</label>
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
                placeholder="e.g. 25"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Lender / Institution</label>
              <input
                v-model="form.metadata.lender"
                type="text"
                placeholder="e.g. Shopee, KBank"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
        </div>

        <!-- 2. DYNAMIC FIELDS FOR FREE TRIAL -->
        <div v-else-if="selectedType === 'FREE_TRIAL'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Trial Hunter Configuration</div>
          <div class="grid grid-cols-2 gap-3">
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
                placeholder="work@gmail.com"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div>
            <label class="block text-[10px] text-zinc-500 mb-1">Direct Cancellation URL</label>
            <input
              v-model="form.metadata.cancel_url"
              type="url"
              placeholder="https://service.com/account/billing/cancel"
              class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            />
          </div>
        </div>

        <!-- 3. DYNAMIC FIELDS FOR SUBSCRIPTIONS -->
        <div v-else-if="selectedType === 'SUBSCRIPTION'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
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
              <label class="block text-[10px] text-zinc-500 mb-1">Billing Day of Month (1-31)</label>
              <input
                v-model.number="form.billing_day"
                type="number"
                min="1"
                max="31"
                placeholder="e.g. 15"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
          </div>
          <div>
            <label class="block text-[10px] text-zinc-500 mb-1">Account Email / Username</label>
            <input
              v-model="form.metadata.account_email"
              type="text"
              placeholder="user@example.com"
              class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            />
          </div>
        </div>

        <!-- 4. DYNAMIC FIELDS FOR DEBTS -->
        <div v-else-if="selectedType === 'DEBT'" class="space-y-3 p-3.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          <div class="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider">Debt Settlement Details</div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Counterparty / Person</label>
              <input
                v-model="form.metadata.counterparty"
                type="text"
                required
                placeholder="e.g. Tum, Freelance Partner"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
            <div>
              <label class="block text-[10px] text-zinc-500 mb-1">Agreed Settlement Date</label>
              <input
                v-model="form.due_date"
                type="date"
                class="w-full px-3 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
              />
            </div>
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
            {{ isSubmitting ? 'Saving...' : 'Create Obligation' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useFinanceStore } from '../../stores/finance'
import type { ObligationType } from '../../types/finance'
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

const typeOptions: Array<{ value: ObligationType; label: string; icon: any }> = [
  { value: 'INSTALLMENT', label: 'Installment', icon: CalendarClock },
  { value: 'FREE_TRIAL', label: 'Free Trial', icon: ShieldAlert },
  { value: 'SUBSCRIPTION', label: 'Subscription', icon: Repeat },
  { value: 'DEBT', label: 'Debt', icon: HandCoins },
]

const selectedType = ref<ObligationType>('INSTALLMENT')
const isSubmitting = ref(false)
const errorMessage = ref('')

const form = ref({
  title: '',
  amount: '',
  due_date: '',
  billing_day: '' as string | number,
  metadata: {} as Record<string, any>,
})

const titlePlaceholder = computed(() => {
  switch (selectedType.value) {
    case 'INSTALLMENT': return 'e.g. Motorcycle Loan, TikTok Shop Installment'
    case 'FREE_TRIAL': return 'e.g. Canva Pro Trial, Notion AI Free Trial'
    case 'SUBSCRIPTION': return 'e.g. Netflix 4K, iCloud 200GB, VPS Cloud'
    case 'DEBT': return 'e.g. Loan from Tum, Equipment purchase'
    default: return ''
  }
})

watch(selectedType, (newType) => {
  errorMessage.value = ''
  if (newType === 'INSTALLMENT') {
    form.value.metadata = { total_terms: 36, current_term: 0, lender: '' }
  } else if (newType === 'FREE_TRIAL') {
    form.value.metadata = { account_email: '', linked_card: '', cancel_url: '' }
  } else if (newType === 'SUBSCRIPTION') {
    form.value.metadata = { billing_cycle: 'MONTHLY', account_email: '', payment_method: '' }
  } else if (newType === 'DEBT') {
    form.value.metadata = { counterparty: '', is_flexible: false }
  }
}, { immediate: true })

async function handleSubmit() {
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    const payload: Record<string, any> = {
      title: form.value.title,
      type: selectedType.value,
      amount: parseFloat(form.value.amount),
      metadata: { ...form.value.metadata },
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
