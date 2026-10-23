<template>
  <div v-if="isOpen && obligation" @click.self="emit('close')" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl relative my-8 max-h-[90vh] overflow-y-auto">
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
          <div v-if="statementMonth" class="flex justify-between text-zinc-400 text-[11px] pb-1 border-b border-zinc-800/60">
            <span>Statement Cycle:</span>
            <span class="text-amber-400 font-semibold">{{ statementMonth }}</span>
          </div>
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>Active Sub-Orders:</span>
            <span class="text-zinc-200">{{ (obligation.sub_orders || obligation.summary?.sub_orders || []).length }} items</span>
          </div>
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>Statement Due:</span>
            <span class="text-zinc-100 font-semibold">฿{{ Number(paidAmount || obligation.summary?.current_bill_amount || obligation.amount).toLocaleString('en-US') }}</span>
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

        <!-- Account / Ledger Sync Selector -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="text-[11px] font-mono uppercase tracking-wider text-zinc-400">
              {{ obligation.direction === 'INFLOW' ? 'Deposit to Account' : 'Deduct from Account' }}
            </label>
            <span class="text-[10px] text-zinc-500 font-mono">Ledger 2-Way Sync</span>
          </div>
          <select
            v-model="selectedAccountId"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600 transition-colors"
          >
            <option value="">-- No Account Link (Radar Status Only) --</option>
            <option
              v-for="acc in ledgerStore.activeAccounts"
              :key="acc.id"
              :value="acc.id"
            >
              {{ acc.name }} ({{ acc.currency }} {{ Number(acc.current_balance).toLocaleString('en-US', { minimumFractionDigits: 2 }) }})
            </option>
          </select>

          <!-- Real-time account balance & low balance warning -->
          <div v-if="selectedAccountInfo" class="mt-1.5 text-[10px] font-mono flex items-center justify-between">
            <span :class="isInsufficientBalance ? 'text-rose-400 font-medium' : 'text-zinc-500'">
              {{ isInsufficientBalance ? '⚠️ Insufficient balance in this account' : 'Auto-links cash flow transaction' }}
            </span>
            <span class="text-zinc-400">Avail: ฿{{ Number(selectedAccountInfo.current_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
          </div>
        </div>

        <!-- Note -->
        <div>
          <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Note (Optional)</label>
          <input
            v-model="note"
            type="text"
            placeholder="e.g. Transfer slip / Reference"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 hover:border-zinc-700 focus:outline-none focus:border-zinc-500 transition-colors"
          />
        </div>

        <!-- Slip File Upload (Gated by Google Drive Connection) -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="block text-[11px] text-zinc-300 font-medium">Attach Payment Slip</label>
            <span v-if="storageStore.isConnected" class="text-[10px] text-zinc-500 font-mono">
              Direct GDrive Cloud
            </span>
          </div>

          <!-- When Google Drive is NOT connected -->
          <div
            v-if="!storageStore.isConnected"
            class="p-2.5 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs flex items-center justify-between gap-2"
          >
            <div class="flex items-center gap-2 text-zinc-400 text-[11px]">
              <HardDrive class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
              <span>Connect Google Drive in Settings to attach slips</span>
            </div>
            <router-link
              to="/settings"
              class="text-[10px] text-zinc-200 hover:underline font-mono shrink-0 font-medium"
            >
              Settings &rarr;
            </router-link>
          </div>

          <!-- When Google Drive IS connected -->
          <div v-else class="space-y-1.5">
            <div class="flex items-center gap-2">
              <label class="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-zinc-900 border border-dashed border-zinc-700 hover:border-zinc-500 cursor-pointer text-xs text-zinc-400 hover:text-zinc-200 transition-colors">
                <Upload class="w-3.5 h-3.5 text-zinc-400" />
                <span class="truncate">{{ selectedFile ? selectedFile.name : 'Select slip file (JPG, PNG, PDF)' }}</span>
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
                class="p-2 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                title="Remove file"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
            <div v-if="storageStore.uploadProgress !== null" class="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
              <div
                class="bg-zinc-200 h-1 transition-all duration-150"
                :style="{ width: `${storageStore.uploadProgress}%` }"
              ></div>
            </div>
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
            :disabled="isSubmitting || isInsufficientBalance"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            {{ isSubmitting ? 'Posting...' : (obligation.direction === 'INFLOW' ? 'Confirm Receipt' : 'Confirm Payment') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useFinanceStore } from '../../stores/finance'
import { useLedgerStore } from '../../stores/ledger'
import { useStorageStore } from '../../stores/storage'
import type { FinancialObligation } from '../../types/finance'
import { X, Upload, Trash2, HardDrive } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  obligation: FinancialObligation | null
  initialAmount?: number | string
  statementMonth?: string
  initialNote?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'paid'): void
}>()

const financeStore = useFinanceStore()
const ledgerStore = useLedgerStore()
const storageStore = useStorageStore()

const paidAmount = ref('')
const selectedAccountId = ref('')
const note = ref('')
const selectedFile = ref<File | null>(null)
const isSubmitting = ref(false)
const errorMessage = ref('')

const selectedAccountInfo = computed(() => {
  return ledgerStore.accounts.find(a => a.id === selectedAccountId.value) || null
})

const isInsufficientBalance = computed(() => {
  if (!selectedAccountInfo.value || props.obligation?.direction === 'INFLOW') return false
  if (selectedAccountInfo.value.account_type === 'CREDIT_CARD') return false
  return Number(selectedAccountInfo.value.current_balance) < parseFloat(paidAmount.value || '0')
})

onMounted(() => {
  if (ledgerStore.accounts.length === 0) {
    ledgerStore.fetchAccounts().catch(() => {})
  }
  storageStore.fetchStatus().catch(() => {})
})

watch(() => [props.obligation, props.initialAmount, props.statementMonth, props.initialNote], () => {
  errorMessage.value = ''
  note.value = props.initialNote || ''
  selectedAccountId.value = ''
  selectedFile.value = null
  const ob = props.obligation
  if (!ob) return

  if (props.initialAmount !== undefined && props.initialAmount !== '') {
    paidAmount.value = String(props.initialAmount)
  } else if (ob.direction === 'INFLOW' || ob.type === 'DEBT') {
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
    let driveFileId = ''
    let driveViewLink = ''
    let driveDownloadLink = ''
    let fileName = ''
    let fileSize = 0

    // Direct Google Drive upload (Zero-Disk)
    if (selectedFile.value) {
      const uploaded = await storageStore.uploadDirect(selectedFile.value, 'finance')
      driveFileId = uploaded.drive_file_id
      driveViewLink = uploaded.web_view_link
      driveDownloadLink = uploaded.web_content_link
      fileName = uploaded.file_name
      fileSize = uploaded.file_size
    }

    await financeStore.payObligation(props.obligation.id, {
      paid_amount: parseFloat(paidAmount.value),
      statement_month: props.statementMonth || undefined,
      note: note.value,
      drive_file_id: driveFileId || undefined,
      drive_view_link: driveViewLink || undefined,
      drive_download_link: driveDownloadLink || undefined,
      file_name: fileName || undefined,
      file_size: fileSize || undefined,
      account_id: selectedAccountId.value || undefined
    })
    if (selectedAccountId.value) {
      ledgerStore.fetchAccounts().catch(() => {})
      ledgerStore.fetchSummary().catch(() => {})
    }
    emit('paid')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || err.message || 'Failed to record settlement'
  } finally {
    isSubmitting.value = false
  }
}
</script>
