<template>
  <div
    v-if="isOpen"
    @click.self="emit('close')"
    class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans"
  >
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-lg p-6 shadow-2xl relative my-8 max-h-[90vh] overflow-y-auto">
      <button
        @click="emit('close')"
        type="button"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="mb-4">
        <h3 class="text-base font-semibold text-zinc-100 tracking-tight">Record Cash Flow Transaction</h3>
        <p class="text-xs text-zinc-500 mt-0.5">
          Record personal income, expenses, and group shared bills with automated Radar debtor sync
        </p>
      </div>

      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4 text-xs font-mono">
        <!-- 1. Type Switcher: Expense vs Income -->
        <div class="flex items-center p-1 rounded-lg bg-zinc-900 border border-zinc-800">
          <button
            type="button"
            @click="form.transaction_type = 'OUTFLOW'"
            class="flex-1 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center justify-center gap-1.5"
            :class="form.transaction_type === 'OUTFLOW' ? 'bg-zinc-800 text-rose-400 shadow-sm font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
          >
            <ArrowUpRight class="w-3.5 h-3.5" />
            <span>Expense (Outflow)</span>
          </button>

          <button
            type="button"
            @click="form.transaction_type = 'INFLOW'"
            class="flex-1 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center justify-center gap-1.5"
            :class="form.transaction_type === 'INFLOW' ? 'bg-zinc-800 text-emerald-400 shadow-sm font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
          >
            <ArrowDownLeft class="w-3.5 h-3.5" />
            <span>Income (Inflow)</span>
          </button>
        </div>

        <!-- 2. Account & Gross Amount -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Account / Wallet <span class="text-rose-400">*</span></label>
            <select
              v-model="form.account"
              required
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 focus:outline-none focus:border-zinc-600 font-mono text-xs"
            >
              <option
                v-for="acc in ledgerStore.accounts"
                :key="acc.id"
                :value="acc.id"
              >
                {{ acc.name }} (฿{{ Number(acc.current_balance || 0).toLocaleString('en-US') }})
              </option>
            </select>
          </div>

          <div>
            <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Total Amount (฿) <span class="text-rose-400">*</span></label>
            <div class="relative">
              <span class="absolute left-3 top-2 text-zinc-500">฿</span>
              <input
                v-model.number="form.gross_amount"
                type="number"
                step="0.01"
                min="0.01"
                required
                placeholder="0.00"
                class="w-full pl-7 pr-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 font-mono font-semibold"
              />
            </div>
          </div>
        </div>

        <!-- 3. Title & Date -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Merchant / Title <span class="text-rose-400">*</span></label>
            <input
              v-model="form.title"
              type="text"
              required
              placeholder="e.g. Haidilao CentralWorld, Monthly Salary"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
            />
          </div>

          <div>
            <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Date</label>
            <input
              v-model="form.transaction_date"
              type="date"
              required
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 focus:outline-none focus:border-zinc-600 font-mono"
            />
          </div>
        </div>

        <!-- 4. Category Selector -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Category</label>
          <select
            v-model="form.category"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 focus:outline-none focus:border-zinc-600 font-mono text-xs"
          >
            <option :value="null">-- General / Uncategorized --</option>
            <optgroup
              v-for="cat in filteredCategories"
              :key="cat.id"
              :label="cat.name"
            >
              <option :value="cat.id">{{ cat.name }}</option>
              <option
                v-for="sub in cat.subcategories"
                :key="sub.id"
                :value="sub.id"
              >
                &nbsp;&nbsp;↳ {{ sub.name }}
              </option>
            </optgroup>
          </select>
        </div>

        <!-- 5. SMART BILL-SPLITTING PANEL (Expense Only) -->
        <div v-if="form.transaction_type === 'OUTFLOW'" class="pt-1">
          <div class="flex items-center justify-between pb-2 border-b border-zinc-800/80">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input
                v-model="isSplit"
                type="checkbox"
                class="rounded bg-zinc-900 border-zinc-700 text-zinc-100 accent-zinc-500 w-3.5 h-3.5"
              />
              <span class="text-zinc-200 text-xs font-semibold flex items-center gap-1.5">
                <Users class="w-3.5 h-3.5 text-zinc-400" />
                <span>Split with Friends</span>
              </span>
            </label>

            <span v-if="isSplit" class="text-[10px] text-zinc-500 font-mono">
              Net Expense: <strong class="text-zinc-100">฿{{ calculatedNetExpense.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</strong>
            </span>
          </div>

          <!-- Expanded Split Configuration -->
          <div v-if="isSplit" class="mt-3 p-3.5 rounded-lg bg-zinc-900/60 border border-zinc-800 space-y-3">
            <!-- Mode Switcher: Equal Split vs Custom -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div class="flex items-center gap-2 text-[11px]">
                <button
                  type="button"
                  @click="splitMode = 'EQUAL'"
                  class="px-2.5 py-1 rounded border transition-colors"
                  :class="splitMode === 'EQUAL' ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-semibold' : 'text-zinc-500 border-transparent hover:text-zinc-300'"
                >
                  Equal Split
                </button>
                <button
                  type="button"
                  @click="splitMode = 'CUSTOM'"
                  class="px-2.5 py-1 rounded border transition-colors"
                  :class="splitMode === 'CUSTOM' ? 'bg-zinc-800 text-zinc-100 border-zinc-600 font-semibold' : 'text-zinc-500 border-transparent hover:text-zinc-300'"
                >
                  Custom Allocation
                </button>
              </div>

              <div v-if="splitMode === 'EQUAL'" class="flex items-center gap-1.5 text-[11px] text-zinc-400">
                <span>Total People (incl. me):</span>
                <input
                  v-model.number="equalSplitPeopleCount"
                  type="number"
                  min="2"
                  max="50"
                  class="w-12 px-1.5 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-center text-zinc-100 font-mono outline-none"
                  @input="handlePeopleCountInput"
                />
              </div>
            </div>

            <!-- Over-allocation Warning (Custom Mode) -->
            <div
              v-if="isOverAllocated"
              class="p-2 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 text-[11px] flex items-center justify-between font-mono"
            >
              <span>Shares (฿{{ friendsTotalShare.toLocaleString('en-US') }}) exceed bill total (฿{{ Number(form.gross_amount).toLocaleString('en-US') }})</span>
              <span class="font-bold">+฿{{ (friendsTotalShare - Number(form.gross_amount)).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>

            <!-- Participant List -->
            <div class="space-y-2">
              <div
                v-for="(p, idx) in participants"
                :key="idx"
                class="flex flex-col sm:flex-row sm:items-center gap-2 p-2 sm:p-0 rounded bg-zinc-950/40 sm:bg-transparent border sm:border-0 border-zinc-800/80"
              >
                <input
                  v-model="p.counterparty_name"
                  type="text"
                  placeholder="Friend Name (e.g. Ball)"
                  class="flex-1 px-2.5 py-1.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-600 text-xs font-mono outline-none focus:border-zinc-700 min-w-0"
                />
                <div class="flex items-center gap-2">
                  <input
                    v-model="p.counterparty_contact"
                    type="text"
                    placeholder="PromptPay / Phone"
                    class="w-32 sm:w-36 px-2 py-1.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-300 placeholder-zinc-600 text-[11px] font-mono outline-none"
                  />
                  <div class="relative w-28 sm:w-32">
                    <span class="absolute left-2 top-1.5 text-zinc-500 text-[11px]">฿</span>
                    <input
                      v-model.number="p.amount"
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      :disabled="splitMode === 'EQUAL'"
                      class="w-full pl-5 pr-2 py-1.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-100 text-xs font-mono text-right outline-none disabled:opacity-70"
                    />
                  </div>
                  <button
                    type="button"
                    @click="removeParticipant(idx)"
                    class="p-1 rounded text-zinc-500 hover:text-rose-400 shrink-0"
                    title="Remove Friend"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div class="flex items-center justify-between pt-1 flex-wrap gap-2">
                <button
                  type="button"
                  @click="addParticipant"
                  class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
                >
                  <Plus class="w-3 h-3" />
                  <span>Add Friend</span>
                </button>

                <button
                  type="button"
                  @click="copySettlementSummary"
                  class="text-[11px] font-mono text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
                >
                  <Copy class="w-3 h-3" />
                  <span>{{ copySuccess ? 'Copied Request!' : 'Copy PromptPay Request' }}</span>
                </button>
              </div>
            </div>

            <!-- Auto Create Radar Debtors Checkbox -->
            <div class="pt-2 border-t border-zinc-800/60">
              <label class="flex items-center gap-2 cursor-pointer select-none">
                <input
                  v-model="autoCreateRadarDebtors"
                  type="checkbox"
                  class="rounded bg-zinc-900 border-zinc-700 text-zinc-100 accent-zinc-500 w-3.5 h-3.5"
                />
                <span class="text-zinc-300 text-[11px]">
                  Auto-create pending Debtors in Financial Radar (Debtors Directory)
                </span>
              </label>
            </div>
          </div>
        </div>

        <!-- Notes -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Notes / Memo (Optional)</label>
          <input
            v-model="form.notes"
            type="text"
            placeholder="e.g. Scanned via PromptPay slip"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
          />
        </div>

        <!-- Form Actions -->
        <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="emit('close')"
            class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-sans text-zinc-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting || !form.gross_amount || !form.title || isOverAllocated"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-sans font-semibold transition-colors disabled:opacity-50"
          >
            {{ isSubmitting ? 'Recording...' : 'Record Transaction' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onUnmounted } from 'vue'
import { useLedgerStore } from '../../stores/ledger'
import type { TransactionType } from '../../types/ledger'
import {
  X,
  ArrowUpRight,
  ArrowDownLeft,
  Users,
  Plus,
  Trash2,
  Copy
} from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created'): void
}>()

const ledgerStore = useLedgerStore()
const isSubmitting = ref(false)
const errorMessage = ref('')
const copySuccess = ref(false)

const isSplit = ref(false)
const splitMode = ref<'EQUAL' | 'CUSTOM'>('EQUAL')
const equalSplitPeopleCount = ref(4)
const autoCreateRadarDebtors = ref(true)

interface ParticipantRow {
  counterparty_name: string
  counterparty_contact: string
  amount: number
}

const participants = ref<ParticipantRow[]>([
  { counterparty_name: 'Ball', counterparty_contact: '', amount: 0 },
  { counterparty_name: 'Earth', counterparty_contact: '', amount: 0 },
  { counterparty_name: 'Bank', counterparty_contact: '', amount: 0 }
])

const form = reactive({
  account: '',
  transaction_type: 'OUTFLOW' as TransactionType,
  category: null as string | null,
  gross_amount: 0,
  title: '',
  notes: '',
  transaction_date: new Date().toISOString().split('T')[0]
})

const filteredCategories = computed(() => {
  const targetType = form.transaction_type === 'INFLOW' ? 'INCOME' : 'EXPENSE'
  return ledgerStore.categories.filter((c) => c.category_type === targetType)
})

const friendsTotalShare = computed(() => {
  return participants.value.reduce((sum, p) => sum + Number(p.amount || 0), 0)
})

const isOverAllocated = computed(() => {
  if (!isSplit.value || splitMode.value !== 'CUSTOM') return false
  return friendsTotalShare.value > Number(form.gross_amount)
})

const calculatedNetExpense = computed(() => {
  if (!isSplit.value) return form.gross_amount
  return Math.max(0, Number(form.gross_amount) - friendsTotalShare.value)
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
      if (!form.account && ledgerStore.accounts.length > 0) {
        const def = ledgerStore.accounts.find((a) => a.is_default) || ledgerStore.accounts[0]
        form.account = def.id
      }
      form.transaction_date = new Date().toISOString().split('T')[0]
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
  () => [form.gross_amount, equalSplitPeopleCount.value, splitMode.value, isSplit.value],
  () => {
    if (isSplit.value && splitMode.value === 'EQUAL') {
      recalculateEqualSplits()
    }
  }
)

function recalculateEqualSplits() {
  const count = Math.max(2, equalSplitPeopleCount.value)
  const perPerson = Number((Number(form.gross_amount) / count).toFixed(2))
  participants.value.forEach((p) => {
    p.amount = perPerson
  })
}

function handlePeopleCountInput() {
  const targetFriends = Math.max(1, equalSplitPeopleCount.value - 1)
  while (participants.value.length < targetFriends) {
    participants.value.push({
      counterparty_name: `Friend ${participants.value.length + 1}`,
      counterparty_contact: '',
      amount: 0
    })
  }
  while (participants.value.length > targetFriends) {
    participants.value.pop()
  }
  recalculateEqualSplits()
}

function addParticipant() {
  participants.value.push({
    counterparty_name: `Friend ${participants.value.length + 1}`,
    counterparty_contact: '',
    amount: splitMode.value === 'EQUAL' && form.gross_amount
      ? Number((Number(form.gross_amount) / (participants.value.length + 2)).toFixed(2))
      : 0
  })
  if (splitMode.value === 'EQUAL') {
    equalSplitPeopleCount.value = participants.value.length + 1
    recalculateEqualSplits()
  }
}

function removeParticipant(idx: number) {
  participants.value.splice(idx, 1)
  if (splitMode.value === 'EQUAL') {
    equalSplitPeopleCount.value = Math.max(2, participants.value.length + 1)
    recalculateEqualSplits()
  }
}

function copySettlementSummary() {
  const text = `Bill: ${form.title || 'Shared Expense'} (฿${Number(form.gross_amount).toLocaleString('en-US')})\n` +
    participants.value.map((p) => `• ${p.counterparty_name}: ฿${Number(p.amount).toLocaleString('en-US')}`).join('\n') +
    `\nMy Net Share: ฿${Number(calculatedNetExpense.value).toLocaleString('en-US')}`

  navigator.clipboard.writeText(text)
  copySuccess.value = true
  setTimeout(() => {
    copySuccess.value = false
  }, 2500)
}

async function handleSubmit() {
  if (isOverAllocated.value) return
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    const payload: any = {
      account: form.account,
      transaction_type: form.transaction_type,
      category: form.category,
      gross_amount: form.gross_amount,
      net_amount: isSplit.value ? calculatedNetExpense.value : form.gross_amount,
      title: form.title,
      notes: form.notes,
      transaction_date: form.transaction_date
    }

    if (isSplit.value && form.transaction_type === 'OUTFLOW' && participants.value.length > 0) {
      payload.splits_payload = participants.value.map((p) => ({
        counterparty_name: p.counterparty_name,
        counterparty_contact: p.counterparty_contact,
        amount: p.amount
      }))
      payload.auto_create_radar_debtors = autoCreateRadarDebtors.value
    }

    await ledgerStore.createTransaction(payload)
    emit('created')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.error || err.message || 'Failed to record transaction.'
  } finally {
    isSubmitting.value = false
  }
}
</script>
