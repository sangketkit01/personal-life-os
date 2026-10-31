<template>
  <div v-if="isOpen && obligation" @click.self="handleClose" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 font-sans overflow-hidden">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md shadow-2xl relative flex flex-col max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] overflow-hidden">
      <!-- Fixed Header -->
      <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
        <div>
          <div class="text-[10px] font-mono uppercase tracking-wider text-zinc-400 mb-0.5">
            {{ obligation.direction === 'INFLOW' ? 'Record Repayment' : (obligation.subtype === 'BNPL_ACCOUNT' ? 'BNPL Statement Settlement' : (obligation.type === 'INSTALLMENT' ? 'Term Settlement' : (obligation.type === 'DEBT' ? 'Debt Settlement' : 'Record Payment'))) }}
          </div>
          <h3 class="text-sm font-semibold text-zinc-100">{{ obligation.title }}</h3>
        </div>
        <button
          @click="handleClose"
          type="button"
          class="text-zinc-500 hover:text-zinc-300 transition-colors p-1"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Form -->
      <form @submit.prevent="handlePay" class="flex flex-col flex-1 min-h-0 overflow-hidden">
        <div class="p-4 sm:p-5 space-y-3.5 overflow-y-auto overscroll-contain flex-1 min-h-0">
          <!-- Error message -->
          <div v-if="errorMessage" class="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {{ errorMessage }}
          </div>

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
            <span class="text-zinc-100 font-semibold">{{ currencySymbol(obligation.currency) }}{{ Number(paidAmount || obligation.summary?.current_bill_amount || obligation.amount).toLocaleString('en-US') }}</span>
          </div>
        </div>

        <!-- Debt Context -->
        <div v-if="obligation.type === 'DEBT'" class="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono space-y-1">
          <div class="flex justify-between text-zinc-400 text-[11px]">
            <span>{{ obligation.direction === 'INFLOW' ? 'Remaining to collect:' : 'Outstanding Balance:' }}</span>
            <span class="font-semibold" :class="obligation.direction === 'INFLOW' ? 'text-emerald-400' : 'text-zinc-100'">
              {{ currencySymbol(obligation.currency) }}{{ Number(obligation.summary?.remaining_balance || obligation.amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
            </span>
          </div>
        </div>

        <!-- Itemized Subscription Context -->
        <div v-if="isItemizedSubscription" class="space-y-3">
          <div class="text-[11px] font-mono text-zinc-400 bg-zinc-900/60 p-2.5 rounded border border-zinc-800 flex items-center justify-between">
            <span>{{ obligation.title }} · {{ obligation.summary?.billing_cycle || obligation.metadata?.billing_cycle || 'Monthly' }}</span>
            <span class="text-zinc-300 font-semibold">ครบกำหนด: {{ formatDate(obligation.due_date) }}</span>
          </div>

          <!-- 1. Fixed Items (Read-only) -->
          <div v-if="cycleFixedItems.length > 0" class="space-y-1.5 p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
            <div class="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mb-1">ราคาคงที่</div>
            <div v-for="it in cycleFixedItems" :key="it.id" class="flex items-center justify-between text-zinc-300 py-0.5">
              <span>{{ it.name }}</span>
              <span class="font-semibold text-zinc-100 font-mono">{{ currencySymbol(obligation.currency) }}{{ Number(it.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
            </div>
          </div>

          <!-- 2. Dynamic Items (Per-cycle Inputs) -->
          <div v-if="cycleDynamicItems.length > 0" class="space-y-2 p-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
            <div class="flex items-center justify-between">
              <span class="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider">กรอกยอดรอบนี้</span>
              <div class="flex items-center gap-2">
                <span v-if="draftStatus === 'saving'" class="text-[10px] text-zinc-400 font-mono flex items-center gap-1">
                  <LoaderCircle class="w-3 h-3 animate-spin text-zinc-400" /> กำลังบันทึก...
                </span>
                <span v-else-if="draftStatus === 'saved'" class="text-[10px] text-emerald-400 font-mono">
                  ✓ บันทึกแบบร่างแล้ว
                </span>
                <span v-else-if="draftStatus === 'error'" class="text-[10px] text-rose-400 font-mono" :title="draftError">
                  ⚠️ บันทึกไม่สำเร็จ
                </span>
                <span v-if="itemizedPendingCount > 0" class="text-[10px] text-amber-400 font-medium">
                  รอกรอก {{ itemizedPendingCount }} รายการ
                </span>
                <span v-else class="text-[10px] text-emerald-400 font-medium">
                  กรอกครบแล้ว
                </span>
              </div>
            </div>

            <div v-for="it in cycleDynamicItems" :key="it.id" class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 py-1 border-b border-zinc-800/40 last:border-b-0">
              <span class="text-zinc-200 text-xs">{{ it.name }}</span>
              <div class="relative w-full sm:w-36">
                <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-[10px] text-zinc-500 font-mono">
                  {{ currencySymbol(obligation.currency) }}
                </span>
                <input
                  v-model="it.amount"
                  @input="onDynamicAmountChange(it.id)"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="ยังไม่กรอก"
                  class="w-full bg-zinc-950 border border-zinc-800 rounded pl-6 pr-2.5 py-1 text-xs text-zinc-100 font-mono text-right focus:border-zinc-600 outline-none"
                />
              </div>
            </div>
          </div>

          <!-- 3. Real-time Summary Card -->
          <div class="p-3 rounded-md bg-zinc-900/80 border border-zinc-800 flex items-center justify-between text-xs font-mono">
            <div>
              <span class="text-[10px] text-zinc-400 uppercase tracking-wider block">
                {{ itemizedPendingCount === 0 ? 'ยอดชำระทั้งหมด' : 'ยอดที่ทราบ (ส่วนคงที่)' }}
              </span>
              <span class="text-base font-bold tabular-nums" :class="itemizedPendingCount === 0 ? 'text-zinc-100' : 'text-amber-400'">
                {{ currencySymbol(obligation.currency) }}{{ itemizedPendingCount === 0 ? (itemizedTotalAmount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) : itemizedFixedTotal.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
              </span>
            </div>
            <div v-if="itemizedPendingCount > 0" class="text-right text-[10px] text-amber-400 leading-tight">
              <span>ยังรอกรอกยอดอีก</span><br/>
              <span class="font-bold">{{ itemizedPendingCount }} รายการ</span>
            </div>
            <div v-else class="text-right text-[10px] text-emerald-400 leading-tight">
              <span>ยอดครบถ้วน</span><br/>
              <span class="font-bold">พร้อมบันทึกชำระ</span>
            </div>
          </div>
        </div>

        <!-- Standard Amount to pay -->
        <div v-else>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">
            {{ obligation.direction === 'INFLOW' ? 'Repayment Amount Received' : (obligation.subtype === 'BNPL_ACCOUNT' ? 'Bill Amount to Settle' : (obligation.type === 'DEBT' ? 'Settlement Amount (Partial Allowed)' : 'Payment Amount')) }}
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
              <span v-if="isInsufficientBalance" class="flex items-center gap-1 justify-center"><AlertTriangle class="w-3 h-3" /> Insufficient balance in this account</span>
              <span v-else>Auto-links cash flow transaction</span>
            </span>
            <span class="text-zinc-400">Avail: {{ currencySymbol(selectedAccountInfo?.currency || 'THB') }}{{ Number(selectedAccountInfo.current_balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
          </div>
        </div>

        <!-- Note -->
        <div>
          <label class="block text-[11px] text-zinc-300 mb-1 font-medium">Note (Optional)</label>
          <input
            v-model="note"
            type="text"
            placeholder="e.g. Transfer slip / reference"
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
        </div>

        <!-- Action Buttons (Sticky Footer) -->
        <div class="flex items-center justify-end gap-2.5 p-4 border-t border-zinc-800/80 shrink-0 bg-zinc-950/90">
          <button
            type="button"
            @click="handleClose"
            class="px-3.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-all active:scale-[0.98]"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting || isInsufficientBalance || (isItemizedSubscription && itemizedPendingCount > 0)"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            {{ isSubmitting ? 'Posting...' : submitButtonText }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { currencySymbol } from '../../utils/currency'
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useFinanceStore } from '../../stores/finance'
import { useLedgerStore } from '../../stores/ledger'
import { useStorageStore } from '../../stores/storage'
import { useToastStore } from '../../stores/toast'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import type { FinancialObligation } from '../../types/finance'
import {
  AlertTriangle,
  X,
  Upload,
  Trash2,
  HardDrive,
  LoaderCircle
} from 'lucide-vue-next'

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

useBodyScrollLock(() => props.isOpen)

const financeStore = useFinanceStore()
const ledgerStore = useLedgerStore()
const storageStore = useStorageStore()
const toast = useToastStore()

const paidAmount = ref('')
const selectedAccountId = ref('')
const note = ref('')
const selectedFile = ref<File | null>(null)
const isSubmitting = ref(false)
const errorMessage = ref('')

const draftStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const draftError = ref('')

interface CycleItemDraft {
  id: string
  name: string
  type: 'FIXED' | 'DYNAMIC'
  amount: number | string | null
}

const isItemizedSubscription = computed(() => {
  return props.obligation?.type === 'SUBSCRIPTION' && !!props.obligation?.metadata?.is_itemized
})

const cycleKey = computed(() => {
  return props.obligation?.summary?.cycle_key ||
    props.obligation?.summary?.current_cycle?.cycle_key ||
    props.obligation?.metadata?.current_cycle?.cycle_key ||
    undefined
})

const cycleDraftItems = ref<CycleItemDraft[]>([])

const cycleFixedItems = computed(() => {
  return cycleDraftItems.value.filter(it => it.type === 'FIXED')
})

const cycleDynamicItems = computed(() => {
  return cycleDraftItems.value.filter(it => it.type === 'DYNAMIC')
})

const itemizedFixedTotal = computed(() => {
  const sum = cycleFixedItems.value.reduce((acc, it) => acc + (Number(it.amount) || 0), 0)
  return Math.round((sum + Number.EPSILON) * 100) / 100
})

const itemizedDynamicTotal = computed(() => {
  const sum = cycleDynamicItems.value.reduce((acc, it) => {
    if (it.amount === '' || it.amount === null || it.amount === undefined) return acc
    return acc + Number(it.amount)
  }, 0)
  return Math.round((sum + Number.EPSILON) * 100) / 100
})

const itemizedPendingCount = computed(() => {
  return cycleDynamicItems.value.filter(it => it.amount === '' || it.amount === null || it.amount === undefined).length
})

const itemizedTotalAmount = computed(() => {
  if (itemizedPendingCount.value > 0) return null
  const total = itemizedFixedTotal.value + itemizedDynamicTotal.value
  return Math.round((total + Number.EPSILON) * 100) / 100
})

let draftDebounceTimer: any = null

async function saveDraftNow() {
  if (!props.obligation || !isItemizedSubscription.value) return
  draftStatus.value = 'saving'
  draftError.value = ''
  try {
    const itemsPayload = cycleDraftItems.value.map(it => {
      let amt: number | null = null
      if (it.amount !== '' && it.amount !== null && it.amount !== undefined) {
        amt = Math.round((parseFloat(String(it.amount)) + Number.EPSILON) * 100) / 100
      }
      return { id: it.id, amount: amt }
    })
    await financeStore.saveCycleBillDraft(props.obligation.id, itemsPayload, cycleKey.value)
    draftStatus.value = 'saved'
  } catch (err: any) {
    draftStatus.value = 'error'
    draftError.value = err.response?.data?.detail || err.message || 'Failed to save draft'
    toast.error(`ไม่สามารถบันทึกแบบร่างบิลได้: ${draftError.value}`)
  }
}

async function flushDraft() {
  if (draftDebounceTimer) {
    clearTimeout(draftDebounceTimer)
    draftDebounceTimer = null
    await saveDraftNow()
  }
}

async function handleClose() {
  await flushDraft()
  emit('close')
}

onBeforeUnmount(() => {
  if (draftDebounceTimer) {
    clearTimeout(draftDebounceTimer)
    draftDebounceTimer = null
  }
})

let activeDraftSessionId = 0
const userEditedItemIds = ref<Set<string>>(new Set())

function onDynamicAmountChange(itemId?: string) {
  if (itemId) {
    userEditedItemIds.value.add(itemId)
  }
  if (itemizedPendingCount.value === 0 && itemizedTotalAmount.value !== null) {
    paidAmount.value = itemizedTotalAmount.value.toFixed(2)
  } else {
    paidAmount.value = ''
  }

  draftStatus.value = 'idle'
  clearTimeout(draftDebounceTimer)
  draftDebounceTimer = setTimeout(async () => {
    await saveDraftNow()
  }, 500)
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return dateStr
  }
}

const submitButtonText = computed(() => {
  if (props.obligation?.type === 'SUBSCRIPTION') {
    if (props.obligation.summary?.is_terminated) {
      return 'ชำระบิลสุดท้าย'
    }
    if (isItemizedSubscription.value && Number(paidAmount.value || 0) === 0 && itemizedPendingCount.value === 0) {
      return 'บันทึกการชำระ (฿0.00)'
    }
    return 'บันทึกการชำระ'
  }
  return props.obligation?.direction === 'INFLOW' ? 'Confirm Receipt' : 'Confirm Payment'
})

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

// When modal opens or target changes, initialize form and fetch freshest draft if itemized
watch(() => [props.isOpen, props.obligation, props.initialAmount, props.statementMonth, props.initialNote], async ([isOpen, ob]) => {
  if (!isOpen) {
    activeDraftSessionId++
    userEditedItemIds.value.clear()
    return
  }

  const sessionId = ++activeDraftSessionId
  userEditedItemIds.value.clear()
  errorMessage.value = ''
  note.value = props.initialNote || ''
  selectedAccountId.value = ''
  selectedFile.value = null

  if (!ob) return

  if (isItemizedSubscription.value) {
    const rawCycle = (ob as any).summary?.current_cycle || (ob as any).metadata?.current_cycle
    const rawItems = (rawCycle && Array.isArray(rawCycle.items))
      ? rawCycle.items
      : (((ob as any).metadata?.items && Array.isArray((ob as any).metadata.items)) ? (ob as any).metadata.items : [])
    cycleDraftItems.value = rawItems.map((it: any) => ({
      id: it.id,
      name: it.name,
      type: it.type || 'FIXED',
      amount: (it.amount !== null && it.amount !== undefined) ? String(it.amount) : ''
    }))
    if (itemizedPendingCount.value === 0 && itemizedTotalAmount.value !== null) {
      paidAmount.value = itemizedTotalAmount.value.toFixed(2)
    } else {
      paidAmount.value = ''
    }

    const targetObId = (ob as any).id
    const targetCk = cycleKey.value
    try {
      const res = await financeStore.fetchCycleBill(targetObId)
      // Guard against stale responses: modal closed, obligation switched, or session changed
      if (!props.isOpen || activeDraftSessionId !== sessionId || props.obligation?.id !== targetObId) {
        return
      }
      // Guard against mismatched cycle: verify cycle_key still matches the current active cycle
      if (res && res.cycle_key && targetCk && res.cycle_key !== targetCk) {
        return
      }
      if (res && Array.isArray(res.items)) {
        // Merge without overwriting values that the user has already typed or cleared during load
        cycleDraftItems.value = res.items.map((it: any) => {
          const currentItem = cycleDraftItems.value.find(c => c.id === it.id)
          if (userEditedItemIds.value.has(it.id) && currentItem) {
            return currentItem
          }
          return {
            id: it.id,
            name: it.name,
            type: it.type || 'FIXED',
            amount: (it.amount !== null && it.amount !== undefined) ? String(it.amount) : ''
          }
        })
        if (itemizedPendingCount.value === 0 && itemizedTotalAmount.value !== null) {
          paidAmount.value = itemizedTotalAmount.value.toFixed(2)
        } else {
          paidAmount.value = ''
        }
      }
    } catch {
      // Retain initialized values
    }
  } else if (props.initialAmount !== undefined && props.initialAmount !== '') {
    paidAmount.value = String(props.initialAmount)
  } else if ((ob as any).direction === 'INFLOW' || (ob as any).type === 'DEBT') {
    paidAmount.value = String((ob as any).summary?.remaining_balance || (ob as any).amount)
  } else if ((ob as any).subtype === 'BNPL_ACCOUNT') {
    paidAmount.value = String((ob as any).summary?.current_bill_amount || (ob as any).amount)
  } else {
    paidAmount.value = String((ob as any).amount)
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

  // Ensure any pending debounce timer is cleared so it won't fire after payment!
  clearTimeout(draftDebounceTimer)
  draftDebounceTimer = null

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

    const finalAmount = Math.round((parseFloat(paidAmount.value || '0') + Number.EPSILON) * 100) / 100
    const cycleItemsPayload = isItemizedSubscription.value ? cycleDraftItems.value.map(it => {
      let amt: number | null = null
      if (it.amount !== '' && it.amount !== null && it.amount !== undefined) {
        amt = Math.round((parseFloat(String(it.amount)) + Number.EPSILON) * 100) / 100
      }
      return { id: it.id, amount: amt }
    }) : undefined

    await financeStore.payObligation(props.obligation.id, {
      paid_amount: finalAmount,
      statement_month: props.statementMonth || undefined,
      note: note.value,
      drive_file_id: driveFileId || undefined,
      drive_view_link: driveViewLink || undefined,
      drive_download_link: driveDownloadLink || undefined,
      file_name: fileName || undefined,
      file_size: fileSize || undefined,
      account_id: selectedAccountId.value || undefined,
      cycle_key: cycleKey.value,
      cycle_items: cycleItemsPayload
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
