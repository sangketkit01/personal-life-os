<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-[65] flex items-center justify-center p-4 font-sans">
      <div class="absolute inset-0 bg-black/75 backdrop-blur-sm" @click="emit('close')" />

      <div class="relative w-full max-w-2xl max-h-[85vh] flex flex-col rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden">
        <!-- Header -->
        <div class="flex items-center justify-between px-5 py-3.5 border-b border-zinc-800 shrink-0">
          <div class="flex items-center gap-2">
            <Zap class="w-4 h-4 text-amber-400" />
            <h3 class="text-sm font-semibold text-zinc-100">{{ t('rb.title') }}</h3>
            <span class="text-[10px] font-mono text-zinc-500 truncate max-w-[220px]">{{ asset.name }}</span>
          </div>
          <button type="button" @click="emit('close')" class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-100 transition-colors">
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="flex-1 min-h-0 overflow-y-auto p-5 space-y-4">
          <!-- Create / Edit form -->
          <form
            v-if="formOpen"
            @submit.prevent="saveRunbook"
            class="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800 space-y-3"
          >
            <p class="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
              {{ editingId ? t('rb.editing') : t('rb.creating') }}
            </p>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('rb.fields.title') }}</span>
                <input v-model="form.title" type="text" required maxlength="150"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-950 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
              <label class="block">
                <span class="text-[11px] text-zinc-400 font-mono">{{ t('rb.fields.timeout') }}</span>
                <input v-model.number="form.timeout_seconds" type="number" min="1" max="600"
                  class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-950 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
              </label>
            </div>

            <label class="block">
              <span class="text-[11px] text-zinc-400 font-mono">{{ t('rb.fields.description') }}</span>
              <input v-model="form.description" type="text" maxlength="300"
                class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-950 border border-zinc-800 text-xs text-zinc-100 focus:outline-none focus:border-zinc-600" />
            </label>

            <label class="block">
              <span class="text-[11px] text-zinc-400 font-mono">{{ t('rb.fields.workingDir') }}</span>
              <input v-model="form.working_dir" type="text" placeholder="/var/www/app"
                class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-950 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600" />
            </label>

            <label class="block">
              <span class="text-[11px] text-zinc-400 font-mono">{{ t('rb.fields.command') }}</span>
              <textarea v-model="form.command" required rows="4"
                class="mt-1 w-full px-2.5 py-1.5 rounded-md bg-zinc-950 border border-zinc-800 text-xs text-zinc-100 font-mono focus:outline-none focus:border-zinc-600"
                :placeholder="t('rb.fields.commandPlaceholder')" />
            </label>

            <div class="flex items-center gap-2 pt-1">
              <button type="submit" :disabled="isSaving"
                class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50">
                <Save class="w-3.5 h-3.5" />
                {{ t('rb.save') }}
              </button>
              <button type="button" @click="formOpen = false"
                class="px-3 py-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 text-xs transition-colors">
                {{ t('common.cancel') }}
              </button>
            </div>
          </form>

          <!-- Runbook list (fully user-defined, no presets) -->
          <div v-if="runbooks.length === 0 && !formOpen" class="p-8 text-center">
            <Zap class="w-6 h-6 text-zinc-600 mx-auto mb-2" />
            <p class="text-xs text-zinc-400">{{ t('rb.empty') }}</p>
          </div>

          <div
            v-for="rb in runbooks"
            :key="rb.id"
            class="p-3.5 rounded-lg bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-colors"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="text-xs font-semibold text-zinc-100 truncate">{{ rb.title }}</p>
                <p v-if="rb.description" class="text-[11px] text-zinc-500 mt-0.5 truncate">{{ rb.description }}</p>
                <p class="text-[10px] font-mono text-zinc-500 mt-1 truncate">
                  <span v-if="rb.working_dir" class="text-sky-400/80">{{ rb.working_dir }} $ </span>{{ rb.command }}
                </p>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <button type="button" @click="handleRunClick(rb)" :disabled="executingId === rb.id"
                  class="px-2 py-1 rounded bg-emerald-600/90 hover:bg-emerald-500 text-white text-[10px] font-semibold transition-colors flex items-center gap-1 disabled:opacity-50">
                  <Play class="w-3 h-3" :class="{ 'animate-pulse': executingId === rb.id }" />
                  {{ executingId === rb.id ? t('rb.running') : t('rb.execute') }}
                </button>
                <button type="button" @click="openEdit(rb)"
                  class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors">
                  <Pencil class="w-3 h-3" />
                </button>
                <button type="button" @click="confirmDelete = rb; deleteError = ''"
                  class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors">
                  <Trash2 class="w-3 h-3" />
                </button>
              </div>
            </div>

            <!-- Last / live result -->
            <div v-if="results[rb.id]" class="mt-3 rounded-md border border-zinc-800 overflow-hidden">
              <div class="flex items-center justify-between gap-2 px-2.5 py-1.5 bg-zinc-900/80 border-b border-zinc-800">
                <div class="flex items-center gap-2 text-[10px] font-mono">
                  <span
                    class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-semibold"
                    :class="results[rb.id].exit_status === 0 ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60' : 'bg-rose-950 text-rose-400 border border-rose-800/60'"
                  >
                    <CheckCircle2 v-if="results[rb.id].exit_status === 0" class="w-3 h-3" />
                    <XCircle v-else class="w-3 h-3" />
                    exit {{ results[rb.id].exit_status }}
                  </span>
                  <span class="text-zinc-500">{{ results[rb.id].duration_ms }} ms</span>
                </div>
                <span class="text-[10px] font-mono text-zinc-600">{{ t('rb.output') }}</span>
              </div>
              <pre class="p-2.5 bg-[#0d0f14] text-[11px] font-mono text-zinc-300 whitespace-pre-wrap break-all max-h-56 overflow-y-auto m-0">{{ results[rb.id].stdout || results[rb.id].stderr || t('rb.noOutput') }}</pre>
            </div>
            <p v-else-if="rb.last_run_at" class="mt-2 text-[10px] font-mono text-zinc-600">
              {{ t('rb.lastRun') }}: {{ formatDateTime(rb.last_run_at) }} · exit {{ rb.last_exit_code ?? '—' }}
            </p>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-5 py-3 border-t border-zinc-800 shrink-0">
          <button type="button" @click="openCreate"
            class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5">
            <Plus class="w-3.5 h-3.5" />
            {{ t('rb.new') }}
          </button>
        </div>
      </div>

      <ConfirmModal
        :is-open="!!confirmDelete"
        :title="t('rb.deleteTitle')"
        :message="t('rb.deleteMessage', { title: confirmDelete?.title || '' })"
        :confirm-text="t('common.delete')"
        :cancel-text="t('common.cancel')"
        :is-loading="isDeleting"
        :error-message="deleteError"
        @confirm="doDelete"
        @cancel="confirmDelete = null; deleteError = ''"
      />
      <ConfirmModal
        :is-open="!!confirmExecute"
        :title="t('term.confirmRunbookTitle') || 'Confirm Runbook Execution'"
        :message="`'${confirmExecute?.title}':\n${confirmExecute?.command}\nExecute on server '${asset.name}'?`"
        :confirm-text="t('rb.execute') || 'Execute'"
        :cancel-text="t('common.cancel')"
        :is-danger="false"
        :is-loading="isExecutingConfirmed"
        :error-message="executeError"
        @confirm="doConfirmedExecute"
        @cancel="confirmExecute = null; executeError = ''"
      />
      <ConfirmModal
        :is-open="!!confirmTrustHostKey"
        :title="confirmTrustHostKey?.errorInfo.isMismatch ? t('infra.hostKey.mismatchTitle') : t('infra.hostKey.verifyRequired')"
        :message="`${confirmTrustHostKey?.errorInfo.isMismatch ? t('infra.hostKey.mismatchDesc') : t('infra.hostKey.verifyDesc')}\n\n${t('infra.hostKey.fingerprint')}: ${confirmTrustHostKey?.errorInfo.remoteFingerprint}\n\nTrust this host key and execute '${confirmTrustHostKey?.rb.title}'?`"
        :confirm-text="t('infra.hostKey.confirmTrust')"
        :cancel-text="t('common.cancel')"
        :is-danger="confirmTrustHostKey?.errorInfo.isMismatch"
        :is-loading="isTrustingHostKey"
        @confirm="doTrustHostKeyAndRerun"
        @cancel="confirmTrustHostKey = null"
      />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Zap, X, Plus, Pencil, Trash2, Play, Save, CheckCircle2, XCircle } from 'lucide-vue-next'
import { t, formatLocaleDate } from '../../i18n'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import { parseSshHostKeyError, type SshHostKeyErrorInfo } from '../../utils/sshSafety'
import ConfirmModal from '../common/ConfirmModal.vue'
import type { InfrastructureAsset, ServerRunbook, RemoteCommandResult } from '../../types/workspace'

const props = defineProps<{
  isOpen: boolean
  asset: InfrastructureAsset
  projectId: string
}>()

const emit = defineEmits<{ (e: 'close'): void }>()

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const runbooks = ref<ServerRunbook[]>([])
const formOpen = ref(false)
const editingId = ref<string | null>(null)
const isSaving = ref(false)
const executingId = ref<string | null>(null)
const confirmDelete = ref<ServerRunbook | null>(null)
const isDeleting = ref(false)
const deleteError = ref('')
const confirmExecute = ref<ServerRunbook | null>(null)
const isExecutingConfirmed = ref(false)
const executeError = ref('')
const results = ref<Record<string, RemoteCommandResult>>({})

function handleRunClick(rb: ServerRunbook) {
  executeError.value = ''
  confirmExecute.value = rb
}

async function doConfirmedExecute() {
  if (!confirmExecute.value || isExecutingConfirmed.value) return
  isExecutingConfirmed.value = true
  executeError.value = ''
  try {
    await execute(confirmExecute.value)
    confirmExecute.value = null
  } catch (err: any) {
    executeError.value = err?.response?.data?.detail || err?.message || t('rb.execError')
  } finally {
    isExecutingConfirmed.value = false
  }
}

const emptyForm = () => ({
  title: '',
  description: '',
  command: '',
  working_dir: '',
  timeout_seconds: 60
})
const form = ref(emptyForm())

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  formOpen.value = true
}

function openEdit(rb: ServerRunbook) {
  editingId.value = rb.id
  form.value = {
    title: rb.title,
    description: rb.description,
    command: rb.command,
    working_dir: rb.working_dir,
    timeout_seconds: rb.timeout_seconds
  }
  formOpen.value = true
}

async function saveRunbook() {
  if (!form.value.title.trim() || !form.value.command.trim()) return
  isSaving.value = true
  try {
    const payload = { ...form.value, project: props.projectId, asset: props.asset.id }
    if (editingId.value) {
      await workspaceStore.updateServerRunbook(editingId.value, payload)
      toast.success(t('rb.updated'))
    } else {
      await workspaceStore.createServerRunbook(payload)
      toast.success(t('rb.created'))
    }
    formOpen.value = false
    await load()
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('rb.saveFailed'))
  } finally {
    isSaving.value = false
  }
}

const confirmTrustHostKey = ref<{ rb: ServerRunbook; errorInfo: SshHostKeyErrorInfo } | null>(null)
const isTrustingHostKey = ref(false)

async function doTrustHostKeyAndRerun() {
  if (!confirmTrustHostKey.value || isTrustingHostKey.value) return
  isTrustingHostKey.value = true
  const { rb, errorInfo } = confirmTrustHostKey.value
  try {
    await workspaceStore.trustInfraAssetHostKey(props.asset.id, errorInfo.remoteFingerprint)
    toast.success(t('infra.hostKey.trustSuccess'))
    confirmTrustHostKey.value = null
    confirmExecute.value = null
    executeError.value = ''
    await execute(rb)
  } catch (err: any) {
    toast.error(err?.response?.data?.detail || t('infra.hostKey.trustFailed'))
  } finally {
    isTrustingHostKey.value = false
  }
}

async function execute(rb: ServerRunbook) {
  executingId.value = rb.id
  try {
    const res = await workspaceStore.executeServerRunbook(rb.id)
    results.value[rb.id] = res.result
    if (res.result.exit_status === 0) {
      toast.success(t('rb.execOk', { ms: String(res.result.duration_ms) }))
    } else {
      const failMsg = t('rb.execFail', { code: String(res.result.exit_status) })
      toast.error(failMsg)
      throw new Error(failMsg)
    }
    return res
  } catch (err: any) {
    const errText = err?.response?.data?.detail || err?.message || t('rb.execError')
    const hostKeyInfo = parseSshHostKeyError(errText)
    if (hostKeyInfo.isHostKeyError) {
      confirmExecute.value = null
      executeError.value = ''
      confirmTrustHostKey.value = { rb, errorInfo: hostKeyInfo }
    } else {
      toast.error(errText)
    }
    throw err
  } finally {
    executingId.value = null
  }
}

async function doDelete() {
  if (!confirmDelete.value) return
  isDeleting.value = true
  deleteError.value = ''
  try {
    await workspaceStore.deleteServerRunbook(confirmDelete.value.id)
    toast.success(t('rb.deleted'))
    confirmDelete.value = null
    await load()
  } catch (err: any) {
    deleteError.value = err?.response?.data?.detail || t('rb.deleteFailed')
  } finally {
    isDeleting.value = false
  }
}

async function load() {
  try {
    runbooks.value = await workspaceStore.fetchServerRunbooks(props.projectId, props.asset.id)
  } catch {
    toast.error(t('rb.loadFailed'))
  }
}

function formatDateTime(iso: string) {
  return formatLocaleDate(iso, 'datetime')
}

watch(() => props.isOpen, (open) => {
  if (open) {
    results.value = {}
    formOpen.value = false
    load()
  }
})
</script>
