<template>
  <div v-if="isOpen && task" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-lg p-6 shadow-2xl relative my-8">
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="mb-4">
        <h3 class="text-base font-semibold text-zinc-100 tracking-tight">Edit Task Document</h3>
        <p class="text-xs text-zinc-500 mt-0.5">Update deliverable status, priority, deadline, or attachments</p>
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
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Doc Number</label>
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
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Status</label>
            <select
              v-model="form.status"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            >
              <option value="DRAFTING">Drafting</option>
              <option value="WAITING">Waiting Review</option>
              <option value="COMPLETED">Completed</option>
              <option value="ARCHIVED">Archived</option>
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

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Document Link / Drive URL</label>
          <input
            v-model="form.file_url"
            type="url"
            placeholder="https://drive.google.com/..."
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono"
          />
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Notes</label>
          <textarea
            v-model="form.notes"
            rows="3"
            placeholder="Additional requirements or context..."
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <div class="flex items-center justify-between pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="handleDelete"
            class="px-2.5 py-1.5 rounded-md text-xs text-rose-400 hover:bg-rose-950/20 transition-colors flex items-center gap-1 font-mono"
          >
            <Trash2 class="w-3.5 h-3.5" />
            <span>Delete</span>
          </button>

          <div class="flex items-center gap-2">
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
              {{ isSubmitting ? 'Saving...' : 'Save Changes' }}
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import type { TaskDocument, TaskStatus, TaskPriority } from '../../types/workspace'
import apiClient from '../../api/client'
import { X, Trash2 } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  task: TaskDocument | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
  (e: 'deleted'): void
}>()

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const isSubmitting = ref(false)
const errorMessage = ref('')

const form = ref({
  title: '',
  project: null as string | null,
  doc_number: '',
  status: 'DRAFTING' as TaskStatus,
  priority: 'MEDIUM' as TaskPriority,
  deadline: '',
  file_url: '',
  notes: ''
})

watch(() => props.task, (t) => {
  if (t) {
    form.value.title = t.title
    form.value.project = t.project
    form.value.doc_number = t.doc_number || ''
    form.value.status = t.status
    form.value.priority = t.priority
    form.value.file_url = t.file_url || ''
    form.value.notes = t.notes || ''
    if (t.deadline) {
      const d = new Date(t.deadline)
      d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
      form.value.deadline = d.toISOString().slice(0, 16)
    } else {
      form.value.deadline = ''
    }
  }
}, { immediate: true })

async function handleSubmit() {
  if (!props.task) return
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

    payload.project = form.value.project || null
    if (form.value.deadline) {
      payload.deadline = new Date(form.value.deadline).toISOString()
    } else {
      payload.deadline = null
    }

    await apiClient.patch(`/workspace/tasks/${props.task.id}/`, payload)
    await Promise.all([
      workspaceStore.fetchOverview(workspaceStore.selectedProjectId || undefined),
      workspaceStore.fetchTasks()
    ])
    toast.success('Task updated successfully')
    emit('saved')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || 'Failed to update task document'
  } finally {
    isSubmitting.value = false
  }
}

async function handleDelete() {
  if (!props.task) return
  try {
    await workspaceStore.deleteTask(props.task.id)
    toast.info('Task deleted')
    emit('deleted')
    emit('close')
  } catch (err) {
    toast.error('Failed to delete task')
  }
}
</script>
