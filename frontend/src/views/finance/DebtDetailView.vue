<template>
  <div class="max-w-7xl mx-auto space-y-6 font-sans">
    <!-- Top Bar: Back Link, Debt Identity & Master Actions -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div class="flex items-center gap-3">
        <button
          @click="router.push('/finance/debts')"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Back to Debt Ledger"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>

        <div>
          <div class="flex flex-wrap items-center gap-2">
            <span
              class="text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-semibold"
              :class="debt?.direction === 'INFLOW' ? 'bg-zinc-900 text-emerald-400 border-emerald-500/30' : 'bg-zinc-900 text-rose-400 border-rose-500/30'"
            >
              {{ debt?.direction === 'INFLOW' ? 'Debtor (Receivable)' : 'Liability (Payable)' }}
            </span>
            <h1 class="text-lg font-semibold text-zinc-100 tracking-tight font-sans">
              {{ debt?.metadata?.counterparty || debt?.title || 'Debt Dossier' }}
            </h1>
            <span
              class="text-[9px] font-mono px-2 py-0.2 rounded border uppercase font-medium"
              :class="debt?.status === 'ACTIVE' ? 'bg-zinc-900 text-zinc-300 border-zinc-700' : 'bg-zinc-900 text-zinc-500 border-zinc-800'"
            >
              {{ debt?.status || 'ACTIVE' }}
            </span>
          </div>
          <div class="flex flex-wrap items-center gap-3 text-xs text-zinc-500 font-mono mt-0.5">
            <span v-if="debt?.metadata?.contact">📞 {{ debt.metadata.contact }}</span>
            <span v-if="debt?.metadata?.promptpay">PromptPay: {{ debt.metadata.promptpay }}</span>
            <span>Due: {{ debt?.due_date ? new Date(debt.due_date).toLocaleDateString('en-GB') : (debt?.metadata?.is_flexible ? 'Flexible' : 'Not set') }}</span>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex flex-wrap items-center gap-2 self-start sm:self-auto">
        <button
          @click="showEditModal = true"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
          title="Edit Details"
        >
          <Edit2 class="w-4 h-4" />
        </button>

        <button
          @click="confirmDeleteDebt"
          class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-500 hover:text-rose-400 transition-colors"
          title="Delete Record"
        >
          <Trash2 class="w-4 h-4" />
        </button>

        <button
          v-if="debt?.status === 'ACTIVE'"
          @click="showPayModal = true"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Check class="w-3.5 h-3.5 text-zinc-950" />
          <span>Record Repayment</span>
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="p-16 text-center text-xs font-mono text-zinc-500">
      Loading debt dossier...
    </div>

    <div v-else-if="debt" class="space-y-6">
      <!-- 4 Key High-Contrast Metrics Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <!-- Card 1: Initial Loan -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Initial Principal</span>
          <div class="text-xl font-semibold font-mono text-zinc-100 tabular-nums">
            ฿{{ Number(debt.amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">Original loan amount</span>
        </div>

        <!-- Card 2: Total Repaid -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono uppercase text-zinc-500 block">Total Repaid</span>
            <span class="text-[10px] font-mono text-zinc-400">
              {{ debt.summary?.progress_pct || 0 }}% settled
            </span>
          </div>
          <div class="text-xl font-semibold font-mono text-emerald-400 tabular-nums">
            ฿{{ Number(debt.summary?.total_paid || 0).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </div>
          <!-- Progress bar -->
          <div class="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden mt-1.5">
            <div
              class="h-full bg-emerald-500 rounded-full transition-all duration-300"
              :style="{ width: `${Math.min(100, Number(debt.summary?.progress_pct || 0))}%` }"
            />
          </div>
        </div>

        <!-- Card 3: Outstanding Balance -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Remaining Balance</span>
          <div
            class="text-xl font-semibold font-mono tabular-nums"
            :class="debt.direction === 'INFLOW' ? 'text-amber-400' : 'text-rose-400'"
          >
            ฿{{ Number(debt.summary?.remaining_balance ?? debt.amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">Unpaid balance</span>
        </div>

        <!-- Card 4: Due Date -->
        <div class="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-1">
          <span class="text-[10px] font-mono uppercase text-zinc-500 block">Due Milestone</span>
          <div class="text-xl font-semibold font-mono text-zinc-200">
            {{ debt.due_date ? new Date(debt.due_date).toLocaleDateString('en-GB') : (debt.metadata?.is_flexible ? 'Flexible' : 'No deadline') }}
          </div>
          <span class="text-[10px] text-zinc-500 font-mono block">
            {{ debt.status === 'COMPLETED' ? 'Settled in full' : 'Awaiting payment' }}
          </span>
        </div>
      </div>

      <!-- Quick Recall Template Generator (For Debtor Receivables) -->
      <div
        v-if="debt.direction === 'INFLOW' && debt.status === 'ACTIVE'"
        class="p-5 rounded-xl bg-zinc-900/50 border border-emerald-500/30 space-y-3 font-mono text-xs"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2 text-emerald-400 font-semibold text-xs">
            <MessageSquare class="w-4 h-4" />
            <span>One-Click Friendly Reminder Template</span>
          </div>
          <span class="text-[10px] text-zinc-500">
            Due: {{ debt.due_date ? new Date(debt.due_date).toLocaleDateString('en-GB') : 'Flexible' }}
          </span>
        </div>

        <!-- Editable Message Box -->
        <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-300 font-sans text-xs select-all leading-relaxed">
          {{ recallMessageText }}
        </div>

        <!-- Action Buttons -->
        <div class="flex flex-wrap items-center gap-2.5 font-sans pt-1">
          <button
            @click="copyRecallMessage"
            class="py-1.5 px-3 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium transition-colors flex items-center gap-1.5"
          >
            <Check v-if="copiedRecall" class="w-3.5 h-3.5 text-zinc-300" />
            <Copy v-else class="w-3.5 h-3.5 text-zinc-400" />
            <span>{{ copiedRecall ? 'Copied to Clipboard!' : 'Copy Text' }}</span>
          </button>

          <a
            :href="lineShareUrl"
            target="_blank"
            class="py-1.5 px-3 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium transition-colors flex items-center gap-1.5"
          >
            <Send class="w-3.5 h-3.5 text-zinc-400" />
            <span>Share via LINE / Chat</span>
          </a>
        </div>
      </div>

      <!-- Segmented Workspace Tabs -->
      <div class="border-b border-zinc-800/80">
        <div class="flex items-center gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="px-4 py-2 text-xs font-mono transition-colors border-b-2 flex items-center gap-2"
            :class="[
              activeTab === tab.id
                ? 'border-zinc-200 text-zinc-100 font-semibold bg-zinc-900/30'
                : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/20'
            ]"
          >
            <component :is="tab.icon" class="w-3.5 h-3.5" />
            <span>{{ tab.label }}</span>
            <span
              v-if="tab.badge"
              class="px-1.5 py-0.2 rounded text-[10px] font-mono bg-zinc-900 border border-zinc-800 text-zinc-400"
            >
              {{ tab.badge }}
            </span>
          </button>
        </div>
      </div>

      <!-- TAB 1: RUNNING REPAYMENT HISTORY LEDGER -->
      <div v-if="activeTab === 'LEDGER'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/60">
            <div>
              <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Repayment Audit Trail
              </h3>
              <p class="text-xs text-zinc-500 mt-0.5">
                All settlement payments recorded against this loan.
              </p>
            </div>

            <button
              v-if="debt.status === 'ACTIVE'"
              @click="showPayModal = true"
              class="px-3.5 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold font-sans transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Plus class="w-3.5 h-3.5 text-zinc-950" />
              <span>Record Repayment</span>
            </button>
          </div>

          <div v-if="!debt.payment_histories || debt.payment_histories.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500 bg-zinc-950/40 rounded-lg border border-zinc-800">
            No repayment records logged yet.
          </div>

          <div v-else class="rounded-lg border border-zinc-800 overflow-hidden bg-zinc-950/60">
            <table class="w-full text-left text-xs font-mono">
              <thead>
                <tr class="border-b border-zinc-800 text-[10px] text-zinc-500 uppercase tracking-wider bg-zinc-950">
                  <th class="py-2.5 pl-4">Payment Timestamp</th>
                  <th class="py-2.5 text-right">Repaid Amount</th>
                  <th class="py-2.5">Notes & Receipt Reference</th>
                  <th class="py-2.5 text-right pr-4">Slip Attachment</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-800/60">
                <tr
                  v-for="p in debt.payment_histories"
                  :key="p.id"
                  class="hover:bg-zinc-900/30 transition-colors"
                >
                  <td class="py-2.5 pl-4 text-zinc-300">
                    {{ new Date(p.paid_at).toLocaleString('en-GB') }}
                  </td>
                  <td class="py-2.5 text-right font-semibold text-emerald-400 tabular-nums">
                    ฿{{ Number(p.paid_amount).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
                  </td>
                  <td class="py-2.5 text-zinc-400">
                    {{ p.note || 'Partial settlement' }}
                  </td>
                  <td class="py-2.5 text-right pr-4">
                    <span v-if="p.attachments && p.attachments.length > 0" class="text-zinc-300">
                      <a :href="p.attachments[0].drive_view_link || p.attachments[0].file_url || p.attachments[0].file" target="_blank" class="hover:underline flex items-center justify-end gap-1 text-[11px]">
                        <FileText class="w-3 h-3 text-zinc-400" />
                        <span>Slip</span>
                      </a>
                    </span>
                    <span v-else class="text-[10px] text-zinc-600">None</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 2: DOSSIER & SPECIFICATIONS -->
      <div v-if="activeTab === 'DOSSIER'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="pb-3 border-b border-zinc-800/60">
            <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Counterparty & Contract Specifications
            </h3>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 font-mono text-xs">
            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Counterparty</span>
              <span class="text-zinc-200 font-semibold">{{ debt.metadata?.counterparty || debt.title }}</span>
            </div>

            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Contact Information</span>
              <span class="text-zinc-200">{{ debt.metadata?.contact || 'N/A' }}</span>
            </div>

            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Settlement PromptPay / Account</span>
              <span class="text-zinc-200">{{ debt.metadata?.promptpay || 'N/A' }}</span>
            </div>

            <div class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Loan Classification</span>
              <span class="text-zinc-200">{{ debt.subtype === 'FORMAL_LOAN' ? 'Formal Bank Loan' : 'Informal / Peer IOU' }}</span>
            </div>

            <div v-if="debt.subtype === 'FORMAL_LOAN'" class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Interest Rate</span>
              <span class="text-zinc-200">{{ debt.metadata?.interest_rate_pa || 0 }}% p.a.</span>
            </div>

            <div v-if="debt.subtype === 'FORMAL_LOAN'" class="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
              <span class="text-[10px] text-zinc-500 uppercase block">Contract Ref</span>
              <span class="text-zinc-200">{{ debt.metadata?.contract_no || 'N/A' }}</span>
            </div>
          </div>

          <!-- Reason / Context -->
          <div v-if="debt.metadata?.reason" class="p-4 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1 font-mono text-xs">
            <span class="text-[10px] text-zinc-500 uppercase block">Context / Reason for Loan</span>
            <p class="text-zinc-300 font-sans leading-relaxed">{{ debt.metadata.reason }}</p>
          </div>
        </div>
      </div>

      <!-- TAB 3: DOCUMENT VAULT (PROMISSORY NOTES & SLIPS) -->
      <div v-if="activeTab === 'DOCS'" class="space-y-4">
        <div class="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-zinc-800/60">
            <div>
              <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                Promissory Notes & Evidence Vault
              </h3>
              <p class="text-xs text-zinc-500 mt-0.5">
                Upload signed promissory notes, chat screenshots, and repayment transfer slips.
              </p>
            </div>

            <div
              v-if="!storageStore.isConnected"
              class="p-2.5 rounded bg-zinc-950/60 border border-zinc-800 text-xs flex items-center justify-between gap-3 font-mono"
            >
              <div class="flex items-center gap-2 text-zinc-400">
                <HardDrive class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <span>Google Drive required to upload documents</span>
              </div>
              <router-link
                to="/settings"
                class="text-zinc-200 hover:underline font-mono text-xs font-medium shrink-0"
              >
                Settings &rarr;
              </router-link>
            </div>

            <div v-else class="space-y-2">
              <label class="px-3.5 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs font-mono transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm">
                <Upload class="w-3.5 h-3.5 text-zinc-400" />
                <span>{{ isActionLoading ? 'Uploading...' : 'Upload Document' }}</span>
                <input
                  type="file"
                  class="hidden"
                  accept=".pdf,.png,.jpg,.jpeg,.webp"
                  @change="handleFileUpload"
                />
              </label>
              <div v-if="storageStore.uploadProgress !== null" class="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
                <div
                  class="bg-zinc-200 h-1 transition-all duration-150"
                  :style="{ width: `${storageStore.uploadProgress}%` }"
                ></div>
              </div>
            </div>
          </div>

          <div v-if="!debt.attachments || debt.attachments.length === 0" class="p-8 text-center text-xs font-mono text-zinc-500 bg-zinc-950/40 rounded-lg border border-zinc-800">
            No uploaded contracts or evidence slips found.
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div
              v-for="att in debt.attachments"
              :key="att.id"
              class="p-3.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 flex items-center justify-between font-mono text-xs hover:border-zinc-700 transition-colors"
            >
              <div class="flex items-center gap-2.5 truncate">
                <FileText class="w-4 h-4 text-zinc-400 shrink-0" />
                <div class="truncate">
                  <a
                    :href="att.drive_view_link || att.file_url || att.file"
                    target="_blank"
                    class="text-zinc-200 hover:underline truncate block font-medium"
                  >
                    {{ att.file_name || 'Attached Loan Document' }}
                  </a>
                  <span class="text-[10px] text-zinc-500">
                    {{ att.file_size ? `${Math.round(att.file_size / 1024)} KB` : '' }} • {{ new Date(att.uploaded_at).toLocaleDateString('en-GB') }}
                  </span>
                </div>
              </div>

              <div class="flex items-center gap-1.5">
                <a
                  :href="att.drive_download_link || att.drive_view_link || att.file_url || att.file"
                  target="_blank"
                  download
                  class="p-1 rounded text-zinc-400 hover:text-white transition-colors"
                  title="Download File"
                >
                  <Download class="w-3.5 h-3.5" />
                </a>
                <button
                  @click="handleDeleteAttachment(att.id)"
                  class="p-1 rounded text-zinc-500 hover:text-rose-400 transition-colors"
                  title="Delete Document"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <PayModal
      :is-open="showPayModal"
      :obligation="debt"
      @close="showPayModal = false"
      @paid="handlePaymentFinished"
    />

    <EditObligationModal
      :is-open="showEditModal"
      :obligation="debt"
      @close="showEditModal = false"
      @updated="refreshDebt"
    />

    <ConfirmModal
      :is-open="confirmModal.isOpen"
      :title="confirmModal.title"
      :message="confirmModal.message"
      :confirm-text="confirmModal.confirmText"
      :is-danger="confirmModal.isDanger"
      @confirm="executeConfirmModal"
      @cancel="confirmModal.isOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDebts } from '../../composables/finance/useDebts'
import { useStorageStore } from '../../stores/storage'
import { useToastStore } from '../../stores/toast'
import PayModal from '../../components/finance/PayModal.vue'
import EditObligationModal from '../../components/finance/EditObligationModal.vue'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import {
  ArrowLeft,
  Check,
  Edit2,
  Trash2,
  MessageSquare,
  Copy,
  Send,
  History,
  FileText,
  Upload,
  Download,
  HardDrive
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const storageStore = useStorageStore()
const {
  currentDebt: debt,
  isLoading,
  isActionLoading,
  fetchDebtById,
  deleteDebt,
  deleteAttachment
} = useDebts()

const debtId = computed(() => route.params.id as string)
const activeTab = ref<'LEDGER' | 'DOSSIER' | 'DOCS'>('LEDGER')
const copiedRecall = ref(false)

const showPayModal = ref(false)
const showEditModal = ref(false)

const confirmModal = reactive({
  isOpen: false,
  title: '',
  message: '',
  confirmText: 'Delete',
  isDanger: true,
  action: () => {}
})

function executeConfirmModal() {
  confirmModal.isOpen = false
  confirmModal.action()
}

const tabs = computed<Array<{ id: 'LEDGER' | 'DOSSIER' | 'DOCS'; label: string; icon: any; badge?: string }>>(() => [
  { id: 'LEDGER', label: 'Repayment Ledger', icon: History, badge: debt.value?.payment_histories?.length ? `${debt.value.payment_histories.length}` : undefined },
  { id: 'DOSSIER', label: 'Counterparty Dossier', icon: FileText },
  { id: 'DOCS', label: 'Evidence & Slips Vault', icon: FileText, badge: debt.value?.attachments?.length ? `${debt.value.attachments.length}` : undefined }
])

onMounted(async () => {
  if (debtId.value) {
    await refreshDebt()
  }
})

async function refreshDebt() {
  try {
    await fetchDebtById(debtId.value)
  } catch (err: any) {
    toast.error('Failed to load debt record')
  }
}

const recallMessageText = computed(() => {
  if (!debt.value) return ''
  if (debt.value.summary?.recall_template) return debt.value.summary.recall_template

  const party = debt.value.metadata?.counterparty || debt.value.title || 'Friend'
  const rem = Number(debt.value.summary?.remaining_balance ?? debt.value.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })
  const due = debt.value.due_date ? new Date(debt.value.due_date).toLocaleDateString('en-GB') : 'soon'
  const pp = debt.value.metadata?.promptpay ? `PromptPay: ${debt.value.metadata.promptpay}` : 'the designated account'
  return `Hi ${party}, friendly reminder regarding the outstanding balance of ฿${rem} (due: ${due}). When convenient, please transfer to ${pp}. Thank you!`
})

const lineShareUrl = computed(() => {
  return `https://line.me/R/msg/text/?${encodeURIComponent(recallMessageText.value)}`
})

async function copyRecallMessage() {
  try {
    await navigator.clipboard.writeText(recallMessageText.value)
    copiedRecall.value = true
    toast.success('Recall message copied to clipboard!')
    setTimeout(() => {
      copiedRecall.value = false
    }, 2500)
  } catch {
    toast.error('Failed to copy to clipboard')
  }
}

async function handlePaymentFinished() {
  await refreshDebt()
  toast.success('Repayment recorded!')
}

async function handleFileUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  if (!storageStore.isConnected) {
    toast.error('Google Drive connection is required')
    return
  }

  try {
    await storageStore.uploadDirect(file, 'finance', debtId.value)
    toast.success('Document uploaded to Google Drive vault')
    target.value = ''
    await refreshDebt()
  } catch (err: any) {
    toast.error(err?.message || 'Failed to upload file')
  }
}

function handleDeleteAttachment(attachmentId: string) {
  confirmModal.title = 'Delete Attached Document'
  confirmModal.message = 'Are you sure you want to delete this attached document from your vault?'
  confirmModal.confirmText = 'Delete Document'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await deleteAttachment(attachmentId, debtId.value)
      toast.success('Document deleted')
    } catch (err: any) {
      toast.error('Failed to delete document')
    }
  }
  confirmModal.isOpen = true
}

function confirmDeleteDebt() {
  confirmModal.title = 'Delete Debt Record'
  confirmModal.message = 'Are you sure you want to delete this debt record? All repayment logs will be removed.'
  confirmModal.confirmText = 'Delete Debt'
  confirmModal.isDanger = true
  confirmModal.action = async () => {
    try {
      await deleteDebt(debtId.value)
      toast.success('Debt record deleted')
      router.push('/finance/debts')
    } catch (err: any) {
      toast.error('Failed to delete debt record')
    }
  }
  confirmModal.isOpen = true
}
</script>
