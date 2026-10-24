<template>
  <Teleport to="body">
    <!-- Non-Blocking Right Docked Inspector Panel (no backdrop - board stays interactive) -->
    <div
      v-if="isOpen && task"
      class="fixed top-0 right-0 bottom-0 z-40 w-full sm:w-[400px] lg:w-[420px] pointer-events-none flex flex-col"
    >
      <div class="pointer-events-auto h-full w-full bg-zinc-950/95 backdrop-blur-xl border-l border-zinc-800 shadow-[-16px_0_40px_rgba(0,0,0,0.65)] flex flex-col transition-transform duration-200">
        <!-- Header -->
        <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Task Inspector</span>
            <span v-if="task.project_name" class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 font-mono flex items-center gap-1.5 min-w-0">
              <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ backgroundColor: task.project_color || '#71717a' }" />
              <span class="truncate max-w-[140px]">{{ task.project_name }}</span>
            </span>
          </div>
          <button
            @click="emit('close')"
            class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900 transition-colors"
            title="Close (Esc)"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- Scrollable body -->
        <div class="flex-1 overflow-y-auto px-5 py-4 space-y-6">
          <!-- 1. Title -->
          <input
            v-model="draft.title"
            type="text"
            class="w-full bg-transparent border-none outline-none text-base font-semibold text-zinc-100 font-sans"
            @input="scheduleSave()"
          />

          <!-- 2. Properties Grid -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ti.status') }}</label>
              <select
                v-model="draft.status"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600"
                @change="saveNow()"
              >
                <option value="TODO">{{ t('opt.todo') }}</option>
                <option value="DOING">{{ t('opt.doing') }}</option>
                <option value="DONE">{{ t('opt.done') }}</option>
                <option value="ARCHIVED">{{ t('opt.archived') }}</option>
              </select>
            </div>

            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ti.priority') }}</label>
              <select
                v-model="draft.priority"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600"
                @change="saveNow()"
              >
                <option value="LOW">{{ t('opt.low') }}</option>
                <option value="MEDIUM">{{ t('opt.medium') }}</option>
                <option value="HIGH">{{ t('opt.high') }}</option>
                <option value="URGENT">{{ t('opt.urgent') }}</option>
              </select>
            </div>

            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ti.project') }}</label>
              <select
                v-model="draft.project"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600"
                @change="saveNow()"
              >
                <option :value="null">{{ t('opt.noProject') }}</option>
                <option v-for="p in workspaceStore.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>

            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ti.startDate') }}</label>
              <input
                v-model="draft.start_date"
                type="date"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
                @change="onStartDateChange"
              />
            </div>

            <div class="col-span-2">
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ti.dueDate') }}</label>
              <input
                v-model="draft.deadline"
                type="datetime-local"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
                @change="onDeadlineChange"
              />
              <span
                v-if="task.status !== 'DONE' && task.deadline"
                class="inline-block mt-1.5 text-[10px] font-mono px-1.5 py-0.5 rounded border"
                :class="deadlineBadgeClass"
              >
                {{ task.deadline_info?.label }}
              </span>
            </div>
          </div>

          <!-- 3. Sub-task Checklist -->
          <div class="space-y-2.5">
            <div class="flex items-center justify-between">
              <h4 class="text-[11px] font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                <ListChecks class="w-3.5 h-3.5" /> {{ t('ti.checklist') }}
              </h4>
              <span v-if="draft.checklist.length > 0" class="text-[10px] font-mono text-zinc-500">
                {{ completedCount }}/{{ draft.checklist.length }}
              </span>
            </div>

            <div v-if="draft.checklist.length > 0" class="h-1 rounded-full bg-zinc-900 border border-zinc-800/60 overflow-hidden">
              <div
                class="h-full bg-emerald-500/70 transition-all duration-300"
                :style="{ width: `${progressPct}%` }"
              />
            </div>

            <div class="space-y-1">
              <div
                v-for="(item, idx) in draft.checklist"
                :key="item.id"
                class="flex items-center gap-2 p-1.5 rounded-md bg-zinc-900/40 border border-zinc-800/60 group/checklist"
              >
                <button
                  type="button"
                  @click="toggleChecklistItem(idx)"
                  class="w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors"
                  :class="item.is_completed ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-400' : 'border-zinc-600 hover:border-zinc-400'"
                >
                  <Check v-if="item.is_completed" class="w-3 h-3" />
                </button>
                <input
                  v-model="item.title"
                  type="text"
                  class="flex-1 bg-transparent border-none outline-none text-xs font-sans"
                  :class="item.is_completed ? 'text-zinc-500 line-through' : 'text-zinc-200'"
                  @change="saveNow()"
                />
                <button
                  type="button"
                  @click="removeChecklistItem(idx)"
                  class="p-0.5 rounded text-zinc-600 hover:text-rose-400 opacity-0 group-hover/checklist:opacity-100 transition-all"
                >
                  <Trash2 class="w-3 h-3" />
                </button>
              </div>
            </div>

            <input
              v-model="newChecklistTitle"
              type="text"
              :placeholder="t('ti.addChecklist')"
              class="w-full bg-zinc-900/30 border border-zinc-800/60 rounded-md px-2.5 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-zinc-600 font-sans"
              @keydown.enter.prevent="addChecklistItem"
            />
          </div>

          <!-- 4. Reference Links -->
          <div class="space-y-2.5">
            <h4 class="text-[11px] font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <Link2 class="w-3.5 h-3.5" /> Reference Links
            </h4>

            <div v-if="draft.links.length > 0" class="space-y-1">
              <div
                v-for="(link, idx) in draft.links"
                :key="idx"
                class="flex items-center gap-2 p-1.5 rounded-md bg-zinc-900/40 border border-zinc-800/60 group/link"
              >
                <ExternalLink class="w-3 h-3 text-zinc-500 shrink-0" />
                <a
                  :href="link.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex-1 min-w-0 text-xs text-zinc-300 hover:text-zinc-100 hover:underline truncate"
                  :title="link.url"
                >
                  {{ link.title || link.url }}
                </a>
                <button
                  type="button"
                  @click="removeLink(idx)"
                  class="p-0.5 rounded text-zinc-600 hover:text-rose-400 opacity-0 group-hover/link:opacity-100 transition-all"
                >
                  <Trash2 class="w-3 h-3" />
                </button>
              </div>
            </div>

            <div class="flex gap-1.5">
              <input
                v-model="newLink.title"
                type="text"
                :placeholder="t('ti.linkTitle')"
                class="w-28 bg-zinc-900/30 border border-zinc-800/60 rounded-md px-2 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-zinc-600"
              />
              <input
                v-model="newLink.url"
                type="url"
                placeholder="https://..."
                class="flex-1 min-w-0 bg-zinc-900/30 border border-zinc-800/60 rounded-md px-2 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-zinc-600"
                @keydown.enter.prevent="addLink"
              />
              <button
                type="button"
                @click="addLink"
                class="px-2.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-medium transition-colors"
              >
                <Plus class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- 5. Google Drive Attachments -->
          <div class="space-y-2.5">
            <h4 class="text-[11px] font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <Paperclip class="w-3.5 h-3.5" /> {{ t('ti.drive') }}
            </h4>

            <div v-if="!storageStore.isConnected" class="p-2.5 rounded-md bg-zinc-900/40 border border-dashed border-zinc-800 text-[11px] text-zinc-500">
              {{ t('ti.noDrive') }}
              <RouterLink to="/settings" class="text-zinc-300 underline hover:text-white">{{ t('nav.settings') }}</RouterLink>
              {{ t('ti.toAttach') }}
            </div>

            <template v-else>
              <div
                class="rounded-md border border-dashed transition-colors p-3 text-center cursor-pointer"
                :class="isUploading ? 'border-zinc-600 bg-zinc-900/60' : 'border-zinc-800 hover:border-zinc-600 bg-zinc-900/20'"
                @click="!isUploading && fileInput?.click()"
                @dragover.prevent
                @drop.prevent="handleFileDrop"
              >
                <input
                  ref="fileInput"
                  type="file"
                  class="hidden"
                  @change="handleFileSelected"
                />
                <div v-if="isUploading" class="space-y-1.5">
                  <div class="text-[11px] text-zinc-300 font-mono">Uploading... {{ uploadPct }}%</div>
                  <div class="h-1 rounded-full bg-zinc-800 overflow-hidden">
                    <div class="h-full bg-sky-500/70 transition-all" :style="{ width: `${uploadPct}%` }" />
                  </div>
                </div>
                <div v-else class="text-[11px] text-zinc-500 flex items-center justify-center gap-1.5">
                  <Upload class="w-3.5 h-3.5" />
                  <span>{{ t('ti.dropUpload') }}</span>
                </div>
              </div>

              <div v-if="taskAttachments.length > 0" class="space-y-1">
                <div
                  v-for="attachment in taskAttachments"
                  :key="attachment.id"
                  class="flex items-center gap-2 p-1.5 rounded-md bg-zinc-900/40 border border-zinc-800/60 group/attach"
                >
                  <FileText class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                  <div class="flex-1 min-w-0">
                    <button
                      type="button"
                      class="text-xs text-zinc-300 hover:text-zinc-100 hover:underline truncate block text-left w-full"
                      @click="openAttachmentPreview(attachment)"
                    >
                      {{ attachment.file_name }}
                    </button>
                    <span class="text-[9px] font-mono text-zinc-600">{{ formatFileSize(attachment.file_size) }}</span>
                  </div>
                  <button
                    type="button"
                    class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors shrink-0"
                    title="Preview"
                    @click="openAttachmentPreview(attachment)"
                  >
                    <Eye class="w-3 h-3" />
                  </button>
                  <a
                    v-if="attachment.drive_download_link"
                    :href="attachment.drive_download_link"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors shrink-0"
                    title="Download"
                  >
                    <Download class="w-3 h-3" />
                  </a>
                  <button
                    type="button"
                    @click="attachmentToDelete = attachment"
                    class="p-1 rounded text-zinc-600 hover:text-rose-400 opacity-0 group-hover/attach:opacity-100 transition-all shrink-0"
                    title="Delete"
                  >
                    <Trash2 class="w-3 h-3" />
                  </button>
                </div>
              </div>
            </template>
          </div>

          <!-- 6. Task Notes -->
          <div class="space-y-2">
            <h4 class="text-[11px] font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <FileText class="w-3.5 h-3.5" /> {{ t('ti.notes') }}
            </h4>
            <textarea
              v-model="draft.notes"
              rows="4"
              :placeholder="t('ti.notesPlaceholder')"
              class="w-full bg-zinc-900/40 border border-zinc-800/60 rounded-md px-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-zinc-600 resize-y font-sans leading-relaxed"
              @input="scheduleSave()"
            />
          </div>
        </div>

        <!-- Footer -->
        <div class="px-5 py-3 border-t border-zinc-800/80 flex items-center justify-between shrink-0 bg-zinc-950">
          <button
            type="button"
            @click="showDeleteConfirm = true"
            class="px-2.5 py-1.5 rounded-md text-xs font-medium text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/30 transition-colors flex items-center gap-1.5"
          >
            <Trash2 class="w-3.5 h-3.5" /> {{ t('ti.deleteTask') }}
          </button>

          <div class="flex items-center gap-2">
            <span v-if="isSaving" class="text-[10px] font-mono text-zinc-500 flex items-center gap-1">
              <Loader2 class="w-3 h-3 animate-spin" /> {{ t('ti.saving') }}
            </span>
            <span v-else-if="saveError" class="text-[10px] font-mono text-rose-400">{{ t('ti.saveFailed') }}</span>
            <span v-else class="text-[10px] font-mono text-zinc-600">{{ t('ti.autoSaved') }}</span>
            <button
              type="button"
              @click="emit('close')"
              class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors"
            >
              {{ t('ti.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Task Confirmation -->
    <ConfirmModal
      :is-open="showDeleteConfirm"
      :title="t('ti.deleteConfirmTitle')"
      :message="t('ti.deleteConfirmMsg', { title: task?.title || '' })"
      :confirm-text="t('ti.deleteConfirmBtn')"
      @confirm="handleDeleteTask"
      @cancel="showDeleteConfirm = false"
    />

    <!-- Delete Attachment Confirmation -->
    <ConfirmModal
      :is-open="!!attachmentToDelete"
      :title="t('ti.deleteFileTitle')"
      :message="t('ti.deleteFileMsg', { name: attachmentToDelete?.file_name || '' })"
      :confirm-text="t('ti.deleteFileBtn')"
      @confirm="handleDeleteAttachment"
      @cancel="attachmentToDelete = null"
    />

    <!-- In-app Drive file preview -->
    <DriveFilePreviewModal
      :is-open="attachmentPreview.open"
      :drive-file-id="attachmentPreview.driveFileId"
      :file-name="attachmentPreview.fileName"
      :file-type="attachmentPreview.fileType"
      :file-size="attachmentPreview.fileSize"
      :drive-view-link="attachmentPreview.driveViewLink"
      :drive-download-link="attachmentPreview.driveDownloadLink"
      @close="attachmentPreview.open = false"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  Check,
  Download,
  ExternalLink,
  Eye,
  FileText,
  Link2,
  ListChecks,
  Loader2,
  Paperclip,
  Plus,
  Trash2,
  Upload,
  X
} from 'lucide-vue-next'
import ConfirmModal from '../common/ConfirmModal.vue'
import { t } from '../../i18n'
import DriveFilePreviewModal from '../common/DriveFilePreviewModal.vue'
import { useWorkspaceStore } from '../../stores/workspace'
import { useStorageStore } from '../../stores/storage'
import { useToastStore } from '../../stores/toast'
import type { ProjectAttachment, TaskDocument, TaskStatus } from '../../types/workspace'

const props = defineProps<{
  task: TaskDocument | null
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated', task: TaskDocument): void
  (e: 'deleted', taskId: string): void
  (e: 'refresh'): void
}>()

const workspaceStore = useWorkspaceStore()
const storageStore = useStorageStore()
const toast = useToastStore()

const draft = reactive({
  title: '',
  status: 'TODO' as TaskStatus,
  priority: 'MEDIUM',
  project: null as string | null,
  start_date: '' as string,
  deadline: '' as string,
  notes: '',
  checklist: [] as Array<{ id: string; title: string; is_completed: boolean }>,
  links: [] as Array<{ title: string; url: string }>
})

const isSaving = ref(false)
const saveError = ref(false)
const showDeleteConfirm = ref(false)
const attachmentToDelete = ref<ProjectAttachment | null>(null)
const newChecklistTitle = ref('')
const newLink = reactive({ title: '', url: '' })
const isUploading = ref(false)
const uploadPct = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)
let saveTimer: ReturnType<typeof setTimeout> | null = null
let loadedTaskId = ''
let lastDeadlineValue = ''

// Local per-task attachment list — intentionally separate from
// workspaceStore.attachments so opening the inspector never overwrites
// the project-wide vault listing in the Documents & Links tab.
const taskAttachments = ref<ProjectAttachment[]>([])

const attachmentPreview = reactive({
  open: false,
  driveFileId: '',
  fileName: '',
  fileType: '',
  fileSize: 0,
  driveViewLink: '',
  driveDownloadLink: ''
})

const completedCount = computed(() => draft.checklist.filter(i => i.is_completed).length)
const progressPct = computed(() =>
  draft.checklist.length === 0 ? 0 : Math.round((completedCount.value / draft.checklist.length) * 100)
)

const deadlineBadgeClass = computed(() => {
  switch (props.task?.deadline_info?.urgency) {
    case 'OVERDUE':
    case 'CRITICAL':
      return 'bg-zinc-900 text-rose-400 border-zinc-800'
    case 'WARNING':
    case 'ATTENTION':
      return 'bg-zinc-900 text-zinc-300 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
})

function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function datePartOfDatetimeLocal(value: string): string {
  return value ? value.slice(0, 10) : ''
}

function syncDraft(task: TaskDocument) {
  draft.title = task.title
  draft.status = task.status === 'DRAFTING' ? 'TODO' : task.status === 'WAITING' ? 'DOING' : task.status === 'COMPLETED' ? 'DONE' : task.status
  draft.priority = task.priority
  draft.project = task.project
  draft.start_date = task.start_date || ''
  draft.deadline = toLocalInput(task.deadline)
  draft.notes = task.notes || ''
  draft.checklist = (task.checklist || []).map(i => ({ ...i }))
  draft.links = (task.links || []).map(l => ({ ...l }))
  lastDeadlineValue = draft.deadline
}

watch(
  () => [props.isOpen, props.task?.id],
  async ([isOpen, taskId]) => {
    if (isOpen && props.task && taskId !== loadedTaskId) {
      // Flush pending draft edits for the PREVIOUS task before switching,
      // so jumping directly between Kanban cards never loses changes.
      const previousTaskId = loadedTaskId
      if (previousTaskId && previousTaskId !== String(taskId) && saveTimer) {
        clearTimeout(saveTimer)
        saveTimer = null
        await saveNowFor(previousTaskId)
      }
      loadedTaskId = String(taskId)
      syncDraft(props.task)
      saveError.value = false
      try {
        taskAttachments.value = await workspaceStore.fetchTaskAttachments(String(taskId))
      } catch {
        taskAttachments.value = []
      }
    }
    if (!isOpen) {
      if (saveTimer) {
        clearTimeout(saveTimer)
        saveTimer = null
        if (loadedTaskId) {
          saveNowFor(loadedTaskId)
        }
      }
      loadedTaskId = ''
      attachmentToDelete.value = null
    }
  },
  { immediate: true }
)

// Escape closes the inspector (non-blocking panel has no backdrop click)
function handleEscape(event: KeyboardEvent) {
  if (!props.isOpen) return
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleEscape)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleEscape)
})

function buildPayload(): Record<string, any> {
  return {
    title: draft.title,
    status: draft.status,
    priority: draft.priority,
    project: draft.project,
    start_date: draft.start_date || null,
    deadline: draft.deadline ? new Date(draft.deadline).toISOString() : null,
    notes: draft.notes,
    checklist: draft.checklist.map(i => ({ ...i })),
    links: draft.links.map(l => ({ ...l }))
  }
}

async function saveNowFor(taskId: string) {
  if (!props.isOpen) return
  isSaving.value = true
  saveError.value = false
  try {
    const updated = await workspaceStore.updateTask(taskId, buildPayload())
    emit('updated', updated)
  } catch {
    saveError.value = true
    toast.error(t('ti.saveFailedToast'))
  } finally {
    isSaving.value = false
  }
}

async function saveNow() {
  if (!props.task || !props.isOpen) return
  await saveNowFor(props.task.id)
}

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveTimer = null
    saveNow()
  }, 700)
}

// --- Date co-adjustment (start_date can never exceed deadline) ---

function onDeadlineChange() {
  if (draft.start_date && draft.deadline) {
    const newDate = datePartOfDatetimeLocal(draft.deadline)
    const savedDeadlineDate = datePartOfDatetimeLocal(lastDeadlineValue)
    // Keep single-day tasks single-day, and never let start exceed deadline
    if (savedDeadlineDate === draft.start_date || newDate < draft.start_date) {
      draft.start_date = newDate
    }
  }
  lastDeadlineValue = draft.deadline
  saveNow()
}

function onStartDateChange() {
  if (draft.start_date && draft.deadline) {
    const deadlineDate = datePartOfDatetimeLocal(draft.deadline)
    if (draft.start_date > deadlineDate) {
      // Shift the deadline to match the new start date, keeping the time part
      const timePart = draft.deadline.slice(11) || '17:00'
      draft.deadline = `${draft.start_date}T${timePart}`
      lastDeadlineValue = draft.deadline
    }
  }
  saveNow()
}

// --- Checklist ---
function addChecklistItem() {
  const title = newChecklistTitle.value.trim()
  if (!title) return
  draft.checklist.push({ id: crypto.randomUUID(), title, is_completed: false })
  newChecklistTitle.value = ''
  saveNow()
}

function removeChecklistItem(index: number) {
  draft.checklist.splice(index, 1)
  saveNow()
}

function toggleChecklistItem(index: number) {
  draft.checklist[index].is_completed = !draft.checklist[index].is_completed
  saveNow()
}

// --- Links ---
function addLink() {
  const url = newLink.url.trim()
  if (!url) return
  if (!/^https?:\/\//i.test(url)) {
    toast.error('Link URL must start with http:// or https://')
    return
  }
  draft.links.push({ title: newLink.title.trim() || url, url })
  newLink.title = ''
  newLink.url = ''
  saveNow()
}

function removeLink(index: number) {
  draft.links.splice(index, 1)
  saveNow()
}

// --- Attachments ---
function openAttachmentPreview(attachment: ProjectAttachment) {
  if (!attachment.drive_file_id) return
  attachmentPreview.driveFileId = attachment.drive_file_id
  attachmentPreview.fileName = attachment.file_name
  attachmentPreview.fileType = attachment.file_type
  attachmentPreview.fileSize = attachment.file_size
  attachmentPreview.driveViewLink = attachment.drive_view_link
  attachmentPreview.driveDownloadLink = attachment.drive_download_link
  attachmentPreview.open = true
}

async function handleFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    await uploadFile(input.files[0])
  }
  input.value = ''
}

async function handleFileDrop(event: DragEvent) {
  if (isUploading.value) return
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    await uploadFile(files[0])
  }
}

async function uploadFile(file: File) {
  if (!props.task) return
  isUploading.value = true
  uploadPct.value = 0
  try {
    await storageStore.uploadDirect(file, 'workspace', props.task.id, pct => {
      uploadPct.value = pct
    })
    taskAttachments.value = await workspaceStore.fetchTaskAttachments(props.task.id)
    const currentProjectId = props.task.project
    if (currentProjectId) {
      await workspaceStore.fetchAttachments(currentProjectId).catch(() => {})
    }
    emit('refresh')
    toast.success(`Uploaded "${file.name}" to Drive`)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to upload file to Google Drive')
  } finally {
    isUploading.value = false
    uploadPct.value = 0
  }
}

async function handleDeleteAttachment() {
  const target = attachmentToDelete.value
  if (!target) return
  attachmentToDelete.value = null
  try {
    await workspaceStore.deleteAttachment(target.id)
    if (props.task) {
      taskAttachments.value = await workspaceStore.fetchTaskAttachments(props.task.id)
      const currentProjectId = props.task.project
      if (currentProjectId) {
        await workspaceStore.fetchAttachments(currentProjectId).catch(() => {})
      }
    }
    emit('refresh')
    toast.info(t('ti.fileDeleted'))
  } catch {
    toast.error(t('pd.uploadFailed'))
  }
}

// --- Delete Task ---
async function handleDeleteTask() {
  if (!props.task) return
  const taskId = props.task.id
  showDeleteConfirm.value = false
  emit('close')
  try {
    await workspaceStore.deleteTask(taskId)
    emit('deleted', taskId)
    toast.info(t('ti.taskDeleted'))
  } catch {
    toast.error(t('ti.deleteFailed'))
  }
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, exp)).toFixed(exp === 0 ? 0 : 1)} ${units[exp]}`
}
</script>
