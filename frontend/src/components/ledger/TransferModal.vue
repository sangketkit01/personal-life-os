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
        <div class="flex items-center gap-2">
          <ArrowRightLeft class="w-4 h-4 text-zinc-400" />
          <h3 class="text-base font-semibold text-zinc-100 tracking-tight">Transfer Between Accounts</h3>
        </div>
        <p class="text-xs text-zinc-500 mt-0.5">
          Atomic double-entry movement between your wallets without inflating income or expenses
        </p>
      </div>

      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleTransfer" class="space-y-4 text-xs font-mono">
        <!-- Source Account -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Source Account (From) <span class="text-rose-400">*</span></label>
          <select
            v-model="form.source_account_id"
            required
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 focus:outline-none focus:border-zinc-600 font-mono"
          >
            <option
              v-for="acc in ledgerStore.accounts"
              :key="acc.id"
              :value="acc.id"
              :disabled="acc.id === form.target_account_id"
            >
              {{ acc.name }} (฿{{ Number(acc.current_balance || 0).toLocaleString('en-US') }})
            </option>
          </select>
        </div>

        <!-- Target Account -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Destination Account (To) <span class="text-rose-400">*</span></label>
          <select
            v-model="form.target_account_id"
            required
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 focus:outline-none focus:border-zinc-600 font-mono"
          >
            <option
              v-for="acc in ledgerStore.accounts"
              :key="acc.id"
              :value="acc.id"
              :disabled="acc.id === form.source_account_id"
            >
              {{ acc.name }} (฿{{ Number(acc.current_balance || 0).toLocaleString('en-US') }})
            </option>
          </select>
        </div>

        <!-- Amount -->
        <div>
          <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Transfer Amount (฿) <span class="text-rose-400">*</span></label>
          <div class="relative">
            <span class="absolute left-3 top-2 text-zinc-500">฿</span>
            <input
              v-model.number="form.amount"
              type="number"
              step="0.01"
              min="0.01"
              required
              placeholder="0.00"
              class="w-full pl-7 pr-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 font-mono text-sm font-semibold"
            />
          </div>
        </div>

        <!-- Date & Title -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Date</label>
            <input
              v-model="form.transaction_date"
              type="date"
              required
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 focus:outline-none focus:border-zinc-600 font-mono"
            />
          </div>
          <div>
            <label class="block text-[10px] uppercase text-zinc-400 mb-1 font-semibold">Transfer Note / Memo</label>
            <input
              v-model="form.title"
              type="text"
              placeholder="e.g. Credit Card Payment"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
            />
          </div>
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
            :disabled="isSubmitting || !form.source_account_id || !form.target_account_id || !form.amount"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-sans font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5"
          >
            <ArrowRightLeft class="w-3.5 h-3.5" />
            <span>{{ isSubmitting ? 'Transferring...' : 'Execute Transfer' }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onUnmounted } from 'vue'
import { useLedgerStore } from '../../stores/ledger'
import { X, ArrowRightLeft } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  defaultSourceId?: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'transferred'): void
}>()

const ledgerStore = useLedgerStore()
const isSubmitting = ref(false)
const errorMessage = ref('')

const form = reactive({
  source_account_id: '',
  target_account_id: '',
  amount: 0,
  transaction_date: new Date().toISOString().split('T')[0],
  title: 'Transfer Between Accounts',
  notes: ''
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
      if (props.defaultSourceId) {
        form.source_account_id = props.defaultSourceId
      } else if (ledgerStore.accounts.length > 0) {
        form.source_account_id = ledgerStore.accounts[0].id
      }

      const other = ledgerStore.accounts.find((a) => a.id !== form.source_account_id)
      if (other) form.target_account_id = other.id

      form.amount = 0
      form.transaction_date = new Date().toISOString().split('T')[0]
      form.title = 'Transfer Between Accounts'
      errorMessage.value = ''
    } else {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }
)

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

async function handleTransfer() {
  if (form.source_account_id === form.target_account_id) {
    errorMessage.value = 'Source and target accounts must be different.'
    return
  }
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    await ledgerStore.transfer({
      source_account_id: form.source_account_id,
      target_account_id: form.target_account_id,
      amount: form.amount,
      transaction_date: form.transaction_date,
      title: form.title,
      notes: form.notes
    })
    emit('transferred')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.error || err.message || 'Transfer failed.'
  } finally {
    isSubmitting.value = false
  }
}
</script>
