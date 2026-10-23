<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-lg p-6 shadow-2xl relative my-8">
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="mb-4">
        <h3 class="text-base font-semibold text-zinc-100 tracking-tight">Add Task Document</h3>
        <p class="text-xs text-zinc-500 mt-0.5">Track deliverables, deadlines, and drive attachments in pipeline</p>
      </div>

      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-3.5">
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Document / Task Title</label>
          <input
            v-model="form.title"
            type="text"
            required
            placeholder="e.g. Tax Filing, Project Scope"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Project</label>
            <select
              v-model="form.project"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            >
              <option :value="null">-- General (No Project) --</option>
              <option v-for="p in workspaceStore.projects" :key="p.id" :value="p.id">
                {{ p.name }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Doc Number (Optional)</label>
            <input
              v-model="form.doc_number"
              type="text"
              placeholder="QT-2026-001"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-100 placeholder-zinc-600"
            />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Initial Status</label>
            <select
              v-model="form.status"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            >
              <option value="DRAFTING">Drafting</option>
              <option value="WAITING">Waiting Review</option>
              <option value="COMPLETED">Completed</option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Priority</label>
            <select
              v-model="form.priority"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            >
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
              <option value="URGENT">Urgent</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Deadline</label>
          <input
            v-model="form.deadline"
            type="datetime-local"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono"
          />
        </div>

        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400">Document Attachment</label>
            <div class="flex items-center gap-2">
              <button
                type="button"
                @click="attachmentMode = 'upload'"
                :class="attachmentMode === 'upload' ? 'text-zinc-200 border-b border-zinc-400' : 'text-zinc-500 hover:text-zinc-400'"
                class="text-[11px] font-mono pb-0.5 transition-colors"
              >
                Upload File
              </button>
              <span class="text-zinc-700 text-[10px]">|</span>
              <button
                type="button"
                @click="attachmentMode = 'url'"
                :class="attachmentMode === 'url' ? 'text-zinc-200 border-b border-zinc-400' : 'text-zinc-500 hover:text-zinc-400'"
                class="text-[11px] font-mono pb-0.5 transition-colors"
              >
                Paste Link
              </button>
            </div>
          </div>

          <!-- Mode 1: Direct File Upload to Google Drive -->
          <div v-if="attachmentMode === 'upload'">
            <!-- If Google Drive Disconnected -->
            <div
              v-if="!storageStore.isConnected"
              class="border border-zinc-800/80 bg-zinc-900/30 rounded-lg p-3 text-center space-y-1.5"
            >
              <div class="flex items-center justify-center gap-2 text-zinc-400 text-xs">
                <HardDrive class="w-4 h-4 text-zinc-400" />
                <span>Google Drive Not Connected</span>
              </div>
              <p class="text-[11px] text-zinc-500">
                Direct upload requires Google Drive. Link in settings or paste a link instead.
              </p>
              <button
                type="button"
                @click="router.push('/settings')"
                class="inline-block mt-1 px-2.5 py-1 text-[11px] text-zinc-300 hover:text-white bg-zinc-800 hover:bg-zinc-700 rounded transition-colors"
              >
                Go to Settings
              </button>
            </div>

            <!-- If Google Drive Connected -->
            <div v-else>
              <div v-if="uploadedFileName" class="p-2.5 rounded-md bg-zinc-900 border border-zinc-800 flex items-center justify-between text-xs">
                <div class="flex items-center gap-2 text-zinc-200 truncate">
                  <FileText class="w-4 h-4 text-zinc-400 shrink-0" />
                  <span class="truncate">{{ uploadedFileName }}</span>
                  <span class="text-[10px] text-emerald-400 font-mono">(GDrive)</span>
                </div>
                <button type="button" @click="clearUploadedFile" class="text-zinc-500 hover:text-zinc-300 ml-2">
                  <X class="w-3.5 h-3.5" />
                </button>
              </div>

              <div
                v-else
                @click="fileInputRef?.click()"
                @dragover.prevent
                @drop.prevent="handleFileDrop"
                class="border border-dashed border-zinc-800 hover:border-zinc-700 bg-zinc-900/40 rounded-lg p-3.5 text-center cursor-pointer transition-colors"
              >
                <input
                  ref="fileInputRef"
                  type="file"
                  class="hidden"
                  @change="handleFileSelect"
                />
                <div v-if="isUploading" class="flex flex-col items-center gap-1.5 py-1">
                  <LoaderCircle class="w-4 h-4 animate-spin text-zinc-400" />
                  <span class="text-xs text-zinc-300 font-mono">Uploading directly to Google Drive...</span>
                </div>
                <div v-else class="flex flex-col items-center gap-1">
                  <CloudUpload class="w-4 h-4 text-zinc-400" />
                  <span class="text-xs text-zinc-300">Click or drop document to upload</span>
                  <span class="text-[10px] text-zinc-500">Option B Zero-Disk to Google Drive</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Mode 2: Manual URL Paste -->
          <div v-else>
            <input
              v-model="form.file_url"
              type="url"
              placeholder="https://drive.google.com/... or Notion link"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 font-mono focus:outline-none focus:border-zinc-600"
            />
          </div>
        </div>

        <div class="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="px-4 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {{ isSubmitting ? 'Saving...' : 'Add to Pipeline' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWorkspaceStore } from '../../stores/workspace'
import { useStorageStore } from '../../stores/storage'
import type { TaskStatus, TaskPriority } from '../../types/workspace'
import { X, CloudUpload, HardDrive, FileText, LoaderCircle } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created'): void
}>()

const router = useRouter()
const workspaceStore = useWorkspaceStore()
const storageStore = useStorageStore()

const isSubmitting = ref(false)
const errorMessage = ref('')
const attachmentMode = ref<'upload' | 'url'>('upload')
const fileInputRef = ref<HTMLInputElement | null>(null)
const isUploading = ref(false)
const uploadedFileName = ref('')

const form = ref({
  title: '',
  project: workspaceStore.selectedProjectId,
  doc_number: '',
  status: 'DRAFTING' as TaskStatus,
  priority: 'MEDIUM' as TaskPriority,
  deadline: '',
  file_url: '',
  notes: ''
})

async function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  await uploadFile(target.files[0])
}

async function handleFileDrop(e: DragEvent) {
  if (!e.dataTransfer?.files || e.dataTransfer.files.length === 0) return
  await uploadFile(e.dataTransfer.files[0])
}

async function uploadFile(file: File) {
  isUploading.value = true
  errorMessage.value = ''
  try {
    const saved = await storageStore.uploadDirect(file, 'workspace')
    form.value.file_url = saved.web_view_link || saved.web_content_link
    uploadedFileName.value = file.name
  } catch (err: any) {
    errorMessage.value = err?.message || 'Failed to upload document to Google Drive.'
  } finally {
    isUploading.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

function clearUploadedFile() {
  uploadedFileName.value = ''
  form.value.file_url = ''
}

async function handleSubmit() {
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    const payload: any = {
      title: form.value.title,
      status: form.value.status,
      priority: form.value.priority,
      doc_number: form.value.doc_number || null,
      file_url: form.value.file_url || '',
      notes: form.value.notes || ''
    }

    if (form.value.project) {
      payload.project = form.value.project
    }
    if (form.value.deadline) {
      payload.deadline = new Date(form.value.deadline).toISOString()
    }

    await workspaceStore.createTask(payload)
    emit('created')
    emit('close')

    form.value.title = ''
    form.value.doc_number = ''
    form.value.deadline = ''
    form.value.file_url = ''
    form.value.notes = ''
    uploadedFileName.value = ''
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || 'Failed to create task document'
  } finally {
    isSubmitting.value = false
  }
}
</script>
