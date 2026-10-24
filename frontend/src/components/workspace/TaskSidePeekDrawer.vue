<template>
  <Teleport to="body">
    <div v-if="isOpen && task" class="fixed inset-0 z-50 flex">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="emit('close')" />

      <!-- Slide-over panel -->
      <div class="relative ml-auto h-full w-full max-w-xl bg-zinc-950 border-l border-zinc-800 z-10 flex flex-col shadow-2xl">
        <!-- Header -->
        <div class="px-5 py-3.5 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
          <div class="flex items-center gap-2 min-w-0">
            <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Task Peek</span>
            <span v-if="task.project_name" class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 font-mono flex items-center gap-1.5 min-w-0">
              <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ backgroundColor: task.project_color || '#71717a' }" />
              <span class="truncate max-w-[140px]">{{ task.project_name }}</span>
            </span>
          </div>
          <button
            @click="emit('close')"
            class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900 transition-colors"
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
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Status</label>
              <select
                v-model="draft.status"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600"
                @change="saveNow()"
              >
                <option value="TODO">To Do</option>
                <option value="DOING">Doing / In Progress</option>
                <option value="DONE">Done</option>
                <option value="ARCHIVED">Archived</option>
              </select>
            </div>

            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Priority</label>
              <select
                v-model="draft.priority"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600"
                @change="saveNow()"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </div>

            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Project</label>
              <select
                v-model="draft.project"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600"
                @change="saveNow()"
              >
                <option :value="null">No project</option>
                <option v-for="p in workspaceStore.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>

            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Start Date</label>
              <input
                v-model="draft.start_date"
                type="date"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
                @change="saveNow()"
              />
            </div>

            <div class="col-span-2">
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Due Date / Deadline</label>
              <input
                v-model="draft.deadline"
                type="datetime-local"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
                @change="saveNow()"
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
                <ListChecks class="w-3.5 h-3.5" /> Checklist
              </h4>
              <span v-if="draft.checklist.length > 0" class="text-[10px] font-mono text-zinc-500">
                {{ completedCount }}/{{ draft.checklist.length }}
              </span>
            </div>

            <!-- Progress bar -->
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
              placeholder="+ Add checklist item... (Enter)"
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
                placeholder="Title"
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
              <Paperclip class="w-3.5 h-3.5" /> Drive Attachments
            </h4>

            <div v-if="!storageStore.isConnected" class="p-2.5 rounded-md bg-zinc-900/40 border border-dashed border-zinc-800 text-[11px] text-zinc-500">
              Google Drive is not connected. Link it in
              <RouterLink to="/settings" class="text-zinc-300 underline hover:text-white">Settings</RouterLink>
              to attach files.
            </div>

            <template v-else>
              <!-- Upload zone -->
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
                  <span>Click or drop a file to upload to Google Drive</span>
                </div>
              </div>

              <!-- Attachment list -->
              <div v-if="taskAttachments.length > 0" class="space-y-1">
                <div
                  v-for="attachment in taskAttachments"
                  :key="attachment.id"
                  class="flex items-center gap-2 p-1.5 rounded-md bg-zinc-900/40 border border-zinc-800/60 group/attach"
                >
                  <FileText class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                  <div class="flex-1 min-w-0">
                    <a
                      v-if="attachment.drive_view_link"
                      :href="attachment.drive_view_link"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-xs text-zinc-300 hover:text-zinc-100 hover:underline truncate block"
                    >
                      {{ attachment.file_name }}
                    </a>
                    <span v-else class="text-xs text-zinc-300 truncate block">{{ attachment.file_name }}</span>
                    <span class="text-[9px] font-mono text-zinc-600">{{ formatFileSize(attachment.file_size) }}</span>
                  </div>
                  <a
                    v-if="attachment.drive_download_link"
                    :href="attachment.drive_download_link"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
                    title="Download"
                  >
                    <Download class="w-3 h-3" />
                  </a>
                  <button
                    type="button"
                    @click="attachmentToDelete = attachment"
                    class="p-1 rounded text-zinc-600 hover:text-rose-400 opacity-0 group-hover/attach:opacity-100 transition-all"
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
              <FileText class="w-3.5 h-3.5" /> Notes
            </h4>
            <textarea
              v-model="draft.notes"
              rows="4"
              placeholder="Detailed instructions, context, acceptance criteria..."
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
            <Trash2 class="w-3.5 h-3.5" /> Delete Task
          </button>

          <div class="flex items-center gap-2">
            <span v-if="isSaving" class="text-[10px] font-mono text-zinc-500 flex items-center gap-1">
              <Loader2 class="w-3 h-3 animate-spin" /> Saving...
            </span>
            <span v-else-if="saveError" class="text-[10px] font-mono text-rose-400">Save failed</span>
            <span v-else class="text-[10px] font-mono text-zinc-600">Auto-saved</span>
            <button
              type="button"
              @click="emit('close')"
              class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Task Confirmation -->
    <ConfirmModal
      :is-open="showDeleteConfirm"
      title="Delete this task?"
      :message="`'${task?.title}' will be permanently removed. This action cannot be undone.`"
      confirm-text="Delete Task"
      @confirm="handleDeleteTask"
      @cancel="showDeleteConfirm = false"
    />

    <!-- Delete Attachment Confirmation -->
    <ConfirmModal
      :is-open="!!attachmentToDelete"
      title="Delete this file?"
      :message="`'${attachmentToDelete?.file_name}' will be removed from Google Drive and this task.`"
      confirm-text="Delete File"
      @confirm="handleDeleteAttachment"
      @cancel="attachmentToDelete = null"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  Check,
  Download,
  ExternalLink,
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

// Local per-task attachment list — intentionally separate from
// workspaceStore.attachments so opening the drawer never overwrites
// the project-wide vault listing in the Documents & Links tab.
const taskAttachments = ref<ProjectAttachment[]>([])

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
}

watch(
  () => [props.isOpen, props.task?.id],
  async ([isOpen, taskId]) => {
    if (isOpen && props.task && taskId !== loadedTaskId) {
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
      loadedTaskId = ''
      attachmentToDelete.value = null
    }
  },
  { immediate: true }
)

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

async function saveNow() {
  if (!props.task || !props.isOpen) return
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  isSaving.value = true
  saveError.value = false
  try {
    const updated = await workspaceStore.updateTask(props.task.id, buildPayload())
    emit('updated', updated)
  } catch {
    saveError.value = true
    toast.error('Failed to save task')
  } finally {
    isSaving.value = false
  }
}

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveTimer = null
    saveNow()
  }, 700)
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
    // Keep the project-wide vault listing in sync when the task belongs to a project
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
    toast.info('Attachment deleted')
  } catch {
    toast.error('Failed to delete attachment')
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
    toast.info('Task deleted')
  } catch {
    toast.error('Failed to delete task')
  }
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, exp)).toFixed(exp === 0 ? 0 : 1)} ${units[exp]}`
}
</script>
