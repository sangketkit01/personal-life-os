<template>
  <div
    v-if="isOpen && split"
    @click.self="emit('close')"
    class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-hidden font-sans"
  >
    <div class="relative bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col shadow-2xl overflow-hidden">
      <!-- Fixed Header -->
      <div class="shrink-0 px-4 sm:px-6 py-3.5 border-b border-zinc-800 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <UserCheck class="w-4 h-4 text-zinc-400" />
          <h3 class="text-base font-semibold text-zinc-100 tracking-tight flex items-center gap-2">
            <span>Settle Split</span>
          </h3>
        </div>
        <button
          @click="emit('close')"
          type="button"
          class="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <form @submit.prevent="handleSettle" class="flex flex-col flex-1 min-h-0 overflow-hidden text-xs font-mono">
        <div class="flex-1 overflow-y-auto overscroll-contain min-h-0 p-4 sm:p-6 space-y-4">
          <div v-if="errorMessage" class="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {{ errorMessage }}
          </div>

          <!-- Split Context Card -->
          <div class="p-3.5 rounded-lg bg-zinc-900/60 border border-zinc-800 space-y-1.5 text-xs font-mono">
            <div class="flex justify-between items-center">
              <span class="text-zinc-400">Debtor / Friend:</span>
              <span class="text-zinc-100 font-semibold">{{ split.counterparty_name }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-zinc-400">Settlement Amount:</span>
              <span class="text-emerald-400 font-bold text-sm">
                ฿{{ Number(split.amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </span>
            </div>
            <div v-if="split.counterparty_contact" class="flex justify-between items-center text-[11px] text-zinc-500">
              <span>Contact / PromptPay:</span>
              <span>{{ split.counterparty_contact }}</span>
            </div>
            <!-- Consumed Dishes Breakdown -->
            <div v-if="split.items_detail && split.items_detail.length > 0" class="pt-1.5 border-t border-zinc-800 text-[11px] space-y-0.5">
              <span class="text-zinc-500 block text-[10px] uppercase font-semibold">Consumed Dishes:</span>
              <div v-for="(dish, dIdx) in split.items_detail" :key="dIdx" class="flex justify-between text-zinc-300">
                <span>{{ dish.name }}</span>
                <span class="text-zinc-400">฿{{ Number(dish.share).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
              </div>
            </div>
          </div>

          <!-- Deposit Account Selection -->
          <div>
            <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Deposit To Account <span class="text-rose-400">*</span></label>
            <select
              v-model="depositAccountId"
              required
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono transition-colors"
            >
              <option value="" disabled>Select deposit account</option>
              <option
                v-for="acc in depositAccounts"
                :key="acc.id"
                :value="acc.id"
              >
                {{ acc.name }} (฿{{ Number(acc.current_balance || 0).toLocaleString('en-US') }})
              </option>
            </select>
          </div>

          <!-- Settlement Date -->
          <div>
            <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Settlement Date</label>
            <input
              v-model="settlementDate"
              type="date"
              required
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono transition-colors"
            />
          </div>

          <!-- Settlement Note -->
          <div>
            <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Note (Optional)</label>
            <input
              v-model="settlementTitle"
              type="text"
              placeholder="e.g. PromptPay transfer"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono transition-colors"
            />
          </div>

          <!-- Info Notice -->
          <div class="p-2.5 rounded bg-zinc-900/40 border border-zinc-800/60 text-[11px] text-zinc-400 flex items-start gap-2">
            <Check class="w-3.5 h-3.5 text-zinc-400 shrink-0 mt-0.5" />
            <span>Account balance will be credited and the receivable in Financial Radar will be resolved.</span>
          </div>
        </div>

        <!-- Actions (Sticky Footer) -->
        <div class="shrink-0 p-4 border-t border-zinc-800/80 bg-zinc-950/90 flex items-center justify-end gap-2.5">
          <button
            type="button"
            @click="emit('close')"
            class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-sans text-zinc-300 transition-all active:scale-[0.98]"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting || !depositAccountId"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-sans font-semibold transition-all active:scale-[0.98] disabled:opacity-50 flex items-center gap-1.5 shadow-sm cursor-pointer"
          >
            <Check class="w-3.5 h-3.5 text-zinc-950" />
            <span>{{ isSubmitting ? 'Saving...' : 'Confirm Settlement' }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useLedgerStore } from '../../stores/ledger'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import type { TransactionSplitItem } from '../../types/ledger'
import { X, UserCheck, Check } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  split: TransactionSplitItem | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'settled'): void
}>()

useBodyScrollLock(() => props.isOpen)

const ledgerStore = useLedgerStore()
const isSubmitting = ref(false)
const errorMessage = ref('')

const depositAccountId = ref('')
const settlementDate = ref(new Date().toISOString().split('T')[0])
const settlementTitle = ref('')

const depositAccounts = computed(() =>
  ledgerStore.accounts.filter((a) => !a.is_archived)
)

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
    } else {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }
)

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

watch(
  () => props.split,
  (s) => {
    if (s) {
      settlementDate.value = new Date().toISOString().split('T')[0]
      settlementTitle.value = ''
      depositAccountId.value = ''
    }
  },
  { immediate: true }
)

async function handleSettle() {
  if (!props.split) return
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    await ledgerStore.settleSplit(props.split.id, {
      deposit_account_id: depositAccountId.value,
      settlement_date: settlementDate.value,
      settlement_title: settlementTitle.value
    })
    emit('settled')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.error || err.message || 'Settlement failed.'
  } finally {
    isSubmitting.value = false
  }
}
</script>
