<template>
  <div v-if="isOpen && obligation" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-xl p-6 shadow-2xl relative my-8">
      <!-- Close button -->
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- Modal Header -->
      <div class="mb-4">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border bg-zinc-900 text-zinc-400 border-zinc-800">
            {{ obligation.type }}
          </span>
          <span v-if="obligation.subtype" class="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border bg-zinc-900 text-zinc-300 border-zinc-800">
            {{ obligation.subtype }}
          </span>
          <span class="text-xs text-zinc-400 font-mono">
            {{ currencySymbol(obligation.currency) }}{{ Number(obligation.amount).toLocaleString('th-TH') }} {{ obligation.currency }}
          </span>
        </div>
        <h2 class="text-base font-semibold text-zinc-100 tracking-tight">{{ obligation.title }}</h2>
        <p class="text-xs text-zinc-500 mt-0.5">Payment settlement logs, verified slips, and contract attachments</p>
      </div>

      <!-- Quick Summary Row -->
      <div class="grid grid-cols-2 gap-3 mb-4 p-3 rounded-lg bg-zinc-900/50 border border-zinc-800/80 font-mono text-xs">
        <div>
          <span class="text-[10px] text-zinc-500 block uppercase">Recorded Payments</span>
          <span class="text-sm font-semibold text-zinc-200">
            {{ (obligation.payment_histories || []).length }} transactions
          </span>
        </div>
        <div class="text-right">
          <span class="text-[10px] text-zinc-500 block uppercase">Total Settled</span>
          <span class="text-sm font-semibold text-emerald-400 tabular-nums">
            {{ currencySymbol(obligation.currency) }}{{ totalPaidAmount.toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
          </span>
        </div>
      </div>

      <!-- Tab Switcher (Transactions vs Documents) -->
      <div class="flex items-center gap-2 border-b border-zinc-800/80 mb-3 text-xs">
        <button
          type="button"
          @click="activeTab = 'TRANSACTIONS'"
          class="pb-2 px-1 border-b-2 font-medium transition-colors"
          :class="activeTab === 'TRANSACTIONS' ? 'border-zinc-100 text-zinc-100' : 'border-transparent text-zinc-400 hover:text-zinc-200'"
        >
          Payment History ({{ (obligation.payment_histories || []).length }})
        </button>
        <button
          type="button"
          @click="activeTab = 'DOCUMENTS'"
          class="pb-2 px-1 border-b-2 font-medium transition-colors flex items-center gap-1.5"
          :class="activeTab === 'DOCUMENTS' ? 'border-zinc-100 text-zinc-100' : 'border-transparent text-zinc-400 hover:text-zinc-200'"
        >
          <span>Documents & Slips</span>
          <span class="text-[10px] font-mono px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
            {{ (obligation.attachments || []).length }}
          </span>
        </button>
      </div>

      <!-- TAB 1: TRANSACTIONS LIST -->
      <div v-if="activeTab === 'TRANSACTIONS'" class="space-y-2.5 max-h-80 overflow-y-auto pr-1">
        <div
          v-if="!obligation.payment_histories || obligation.payment_histories.length === 0"
          class="p-8 text-center border border-dashed border-zinc-800/80 rounded-lg text-xs font-mono text-zinc-500"
        >
          No payment records recorded yet.
        </div>

        <div
          v-for="(hist, idx) in sortedHistories"
          :key="hist.id"
          class="p-3 rounded-lg bg-zinc-900/30 border border-zinc-800/60 hover:border-zinc-700/60 transition-colors flex items-start justify-between gap-3 text-xs font-mono"
        >
          <div class="space-y-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-zinc-200 font-medium font-sans">
                {{ hist.term_number ? `Term ${hist.term_number}` : `Payment #${sortedHistories.length - idx}` }}
              </span>
              <span class="text-[10px] text-zinc-500">
                {{ new Date(hist.paid_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
              </span>
              <!-- Slip attachment pill if any -->
              <span v-if="hist.attachments && hist.attachments.length > 0">
                <a
                  v-for="att in hist.attachments"
                  :key="att.id"
                  :href="att.drive_view_link || att.file_url"
                  target="_blank"
                  class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 transition-colors"
                  title="View Transfer Slip"
                >
                  <FileText class="w-3 h-3 text-zinc-400" />
                  <span>Slip</span>
                  <ExternalLink class="w-2.5 h-2.5 text-zinc-400" />
                </a>
              </span>
            </div>
            <div v-if="hist.note" class="text-[11px] text-zinc-400 font-sans italic">
              "{{ hist.note }}"
            </div>
          </div>

          <div class="text-right shrink-0">
            <span class="text-sm font-semibold text-zinc-100 tabular-nums">
              +{{ currencySymbol(obligation.currency) }}{{ Number(hist.paid_amount).toLocaleString('th-TH', { minimumFractionDigits: 2 }) }}
            </span>
          </div>
        </div>
      </div>

      <!-- TAB 2: ATTACHMENTS & CONTRACTS -->
      <div v-else class="space-y-3.5 max-h-80 overflow-y-auto pr-1">
        <!-- Google Drive Connection Guard -->
        <div
          v-if="!storageStore.isConnected"
          class="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
        >
          <div class="flex items-center gap-2 text-zinc-400 text-xs">
            <HardDrive class="w-4 h-4 text-zinc-500 shrink-0" />
            <span>Google Drive connection required to attach documents and contracts</span>
          </div>
          <router-link
            to="/settings"
            class="text-xs text-zinc-200 hover:underline font-mono shrink-0 font-medium"
          >
            Settings &rarr;
          </router-link>
        </div>

        <!-- Upload Form (Gated) -->
        <div v-else class="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800 text-xs space-y-2.5">
          <div class="flex items-center justify-between text-[11px] font-medium text-zinc-300">
            <span>Upload Document / Slip / Contract</span>
            <span class="text-[10px] text-zinc-500 font-mono">Direct GDrive Cloud</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div>
              <select
                v-model="uploadDocType"
                class="w-full px-2 py-1.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 font-mono"
              >
                <option value="CONTRACT">Contract</option>
                <option value="STATEMENT">e-Statement / Bill</option>
                <option value="SLIP">Payment Slip</option>
                <option value="SCREENSHOT">Screenshot</option>
                <option value="OTHER">Other Document</option>
              </select>
            </div>
            <div class="sm:col-span-2 flex items-center gap-2">
              <label class="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded bg-zinc-900 border border-dashed border-zinc-700 hover:border-zinc-500 cursor-pointer text-xs text-zinc-400 transition-colors truncate">
                <Upload class="w-3.5 h-3.5 text-zinc-400" />
                <span class="truncate">{{ pendingDocFile ? pendingDocFile.name : 'Choose file (PDF, IMG)' }}</span>
                <input type="file" class="hidden" @change="handleDocFileChange" />
              </label>
              <button
                type="button"
                :disabled="!pendingDocFile || isUploading"
                @click="handleUploadDoc"
                class="px-3 py-1.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold disabled:opacity-50 transition-colors shrink-0"
              >
                {{ isUploading ? 'Uploading...' : 'Upload' }}
              </button>
            </div>
          </div>
          <div v-if="storageStore.uploadProgress !== null" class="w-full bg-zinc-800 rounded-full h-1 overflow-hidden">
            <div
              class="bg-zinc-200 h-1 transition-all duration-150"
              :style="{ width: `${storageStore.uploadProgress}%` }"
            ></div>
          </div>
        </div>

        <!-- Document List -->
        <div
          v-if="!obligation.attachments || obligation.attachments.length === 0"
          class="p-6 text-center border border-dashed border-zinc-800/80 rounded-lg text-xs font-mono text-zinc-500"
        >
          No documents or contracts attached yet.
        </div>

        <div
          v-for="att in obligation.attachments"
          :key="att.id"
          class="p-2.5 rounded-lg bg-zinc-900/40 border border-zinc-800/80 flex items-center justify-between gap-3 text-xs font-mono"
        >
          <div class="flex items-center gap-2.5 truncate">
            <FileText class="w-4 h-4 text-zinc-400 shrink-0" />
            <div class="truncate">
              <a
                :href="att.drive_view_link || att.file_url"
                target="_blank"
                class="font-medium text-zinc-200 hover:text-white transition-colors truncate block"
              >
                {{ att.file_name }}
              </a>
              <div class="text-[10px] text-zinc-500 flex items-center gap-2">
                <span class="px-1 py-0.2 rounded bg-zinc-800 text-zinc-300 uppercase text-[9px]">{{ att.file_type }}</span>
                <span>{{ formatBytes(att.file_size) }}</span>
                <span>•</span>
                <span>{{ new Date(att.uploaded_at).toLocaleDateString('en-GB') }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-1.5 shrink-0">
            <a
              :href="att.drive_view_link || att.file_url"
              target="_blank"
              class="p-1 rounded text-zinc-400 hover:text-zinc-200 transition-colors"
              title="Open File"
            >
              <ExternalLink class="w-3.5 h-3.5 text-zinc-400" />
            </a>
            <button
              type="button"
              @click="handleDeleteDoc(att.id)"
              class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
              title="Delete attachment"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="pt-4 mt-4 border-t border-zinc-800/80 flex items-center justify-between text-xs font-mono">
        <span class="text-[11px] text-zinc-500">
          Status: <strong class="text-zinc-300 uppercase">{{ obligation.status }}</strong>
        </span>
        <button
          type="button"
          @click="emit('close')"
          class="px-4 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { currencySymbol } from '../../utils/currency'
import { ref, computed } from 'vue'
import { useFinanceStore } from '../../stores/finance'
import { useStorageStore } from '../../stores/storage'
import { useToastStore } from '../../stores/toast'
import type { FinancialObligation, AttachmentType } from '../../types/finance'
import { X, FileText, ExternalLink, Upload, Trash2, HardDrive } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  obligation: FinancialObligation | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const financeStore = useFinanceStore()
const storageStore = useStorageStore()
const toast = useToastStore()

const activeTab = ref<'TRANSACTIONS' | 'DOCUMENTS'>('TRANSACTIONS')
const uploadDocType = ref<AttachmentType>('CONTRACT')
const pendingDocFile = ref<File | null>(null)
const isUploading = ref(false)

const sortedHistories = computed(() => {
  if (!props.obligation?.payment_histories) return []
  return [...props.obligation.payment_histories].sort((a, b) => {
    return new Date(b.paid_at).getTime() - new Date(a.paid_at).getTime()
  })
})

const totalPaidAmount = computed(() => {
  if (!props.obligation?.payment_histories) return 0
  return props.obligation.payment_histories.reduce((sum, h) => sum + Number(h.paid_amount || 0), 0)
})

function handleDocFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    pendingDocFile.value = target.files[0]
  }
}

async function handleUploadDoc() {
  if (!props.obligation || !pendingDocFile.value) return
  if (!storageStore.isConnected) {
    toast.error('Google Drive connection is required.')
    return
  }
  isUploading.value = true
  try {
    // Zero-Disk Direct GDrive Upload
    await storageStore.uploadDirect(
      pendingDocFile.value,
      'finance',
      props.obligation.id
    )
    pendingDocFile.value = null
    await financeStore.fetchObligations()
    toast.success('Document uploaded to Google Drive')
  } catch (err: any) {
    toast.error(err?.message || 'Failed to upload document')
  } finally {
    isUploading.value = false
  }
}

async function handleDeleteDoc(attachmentId: string) {
  try {
    await financeStore.deleteAttachment(attachmentId)
    await financeStore.fetchObligations()
    toast.info('Document deleted')
  } catch (err: any) {
    toast.error('Failed to delete document')
  }
}

function formatBytes(bytes: number, decimals = 1) {
  if (!bytes) return '0 B'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}
</script>