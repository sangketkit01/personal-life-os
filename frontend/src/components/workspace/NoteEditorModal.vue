<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto font-sans">
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-2xl p-6 shadow-2xl relative my-8">
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="mb-4">
        <h3 class="text-base font-semibold text-zinc-100 tracking-tight">
          {{ editingNote ? 'Edit Project Note' : 'Create Markdown Note' }}
        </h3>
        <p class="text-xs text-zinc-500 mt-0.5">Capture meeting briefs, architectural notes, and specifications</p>
      </div>

      <div v-if="errorMessage" class="mb-4 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
        {{ errorMessage }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-3.5">
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Note Title</label>
          <input
            v-model="title"
            type="text"
            required
            placeholder="e.g. Client Brief Summary, Auth Requirements"
            class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Project</label>
            <select
              v-model="projectId"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100"
            >
              <option :value="null">-- General (No Project) --</option>
              <option v-for="p in workspaceStore.projects" :key="p.id" :value="p.id">
                {{ p.name }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-zinc-400 mb-1">Tags (Comma-separated)</label>
            <input
              v-model="tagsStr"
              type="text"
              placeholder="meeting, requirement, draft"
              class="w-full px-3 py-2 rounded-md bg-zinc-900 border border-zinc-800 text-xs text-zinc-100 font-mono placeholder-zinc-600"
            />
          </div>
        </div>

        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-[11px] font-mono uppercase tracking-wider text-zinc-400">Content</label>
            <!-- Write vs Preview Mode Tabs -->
            <div class="flex items-center p-0.5 rounded bg-zinc-900 border border-zinc-800 text-[10px] font-mono">
              <button
                type="button"
                @click="mode = 'WRITE'"
                class="px-2 py-0.5 rounded transition-colors"
                :class="mode === 'WRITE' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'"
              >
                Write
              </button>
              <button
                type="button"
                @click="mode = 'PREVIEW'"
                class="px-2 py-0.5 rounded transition-colors"
                :class="mode === 'PREVIEW' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'"
              >
                Preview
              </button>
            </div>
          </div>

          <!-- Write Mode Textarea -->
          <textarea
            v-if="mode === 'WRITE'"
            v-model="content"
            rows="8"
            placeholder="Write notes in Markdown... (# headers, - lists, `code`)"
            class="w-full px-3 py-2.5 rounded-md bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors resize-y leading-relaxed"
          />

          <!-- Live Markdown Preview Box -->
          <div
            v-else
            class="w-full min-h-[192px] max-h-80 overflow-y-auto px-4 py-3 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs leading-relaxed text-zinc-200 font-sans space-y-1"
          >
            <div v-if="!content" class="text-zinc-600 italic font-mono">No content to preview yet.</div>
            <div v-else v-html="renderMarkdown(content)" class="prose-dark"></div>
          </div>
        </div>

        <div class="flex items-center justify-between pt-3 border-t border-zinc-800/80">
          <div class="flex items-center gap-2">
            <input
              id="is_pinned"
              v-model="isPinned"
              type="checkbox"
              class="w-3.5 h-3.5 rounded bg-zinc-900 border-zinc-700 text-zinc-100 focus:ring-0"
            />
            <label for="is_pinned" class="text-xs text-zinc-400 cursor-pointer">
              Pin note to top of project feed
            </label>
          </div>

          <div class="flex items-center gap-2.5">
            <button
              v-if="title || content"
              type="button"
              @click="exportMarkdown"
              class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-zinc-300 transition-colors flex items-center gap-1.5"
              title="Export as .md with YAML Frontmatter"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Export .md</span>
            </button>
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
              {{ isSubmitting ? 'Saving...' : (editingNote ? 'Save Changes' : 'Create Note') }}
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
import type { Note } from '../../types/workspace'
import { renderMarkdown } from '../../utils/markdown'
import { X, Download } from 'lucide-vue-next'

const props = defineProps<{
  isOpen: boolean
  editingNote?: Note | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const title = ref('')
const content = ref('')
const projectId = ref<string | null>(null)
const tagsStr = ref('')
const isPinned = ref(false)
const mode = ref<'WRITE' | 'PREVIEW'>('WRITE')
const isSubmitting = ref(false)
const errorMessage = ref('')

watch(
  () => props.editingNote,
  (note) => {
    mode.value = 'WRITE'
    if (note) {
      title.value = note.title
      content.value = note.content
      projectId.value = note.project
      tagsStr.value = (note.tags || []).join(', ')
      isPinned.value = note.is_pinned
    } else {
      title.value = ''
      content.value = ''
      projectId.value = workspaceStore.selectedProjectId
      tagsStr.value = ''
      isPinned.value = false
    }
  },
  { immediate: true }
)

async function handleSubmit() {
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    const tags = tagsStr.value
      .split(',')
      .map(t => t.trim())
      .filter(t => t.length > 0)

    const payload: any = {
      title: title.value,
      content: content.value,
      tags: tags,
      is_pinned: isPinned.value
    }

    if (projectId.value) {
      payload.project = projectId.value
    }

    if (props.editingNote) {
      await workspaceStore.updateNote(props.editingNote.id, payload)
      toast.success('Note updated')
    } else {
      await workspaceStore.createNote(payload)
      toast.success('Note created')
    }

    emit('saved')
    emit('close')
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || 'Failed to save note'
  } finally {
    isSubmitting.value = false
  }
}

function exportMarkdown() {
  const currentProject = workspaceStore.projects.find(p => p.id === projectId.value)
  const projectName = currentProject ? currentProject.name : 'General'
  const tags = tagsStr.value
    .split(',')
    .map(t => t.trim())
    .filter(t => t.length > 0)

  const dateStr = props.editingNote?.created_at
    ? new Date(props.editingNote.created_at).toISOString().slice(0, 10)
    : new Date().toISOString().slice(0, 10)

  const frontmatter = [
    '---',
    `title: "${(title.value || 'Untitled Note').replace(/"/g, '\\"')}"`,
    `project: "${projectName.replace(/"/g, '\\"')}"`,
    `tags: [${tags.map(t => `"${t.replace(/"/g, '\\"')}"`).join(', ')}]`,
    `date: "${dateStr}"`,
    '---',
    '',
    content.value
  ].join('\n')

  const blob = new Blob([frontmatter], { type: 'text/markdown;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const slug = (title.value || 'note')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
  a.href = url
  a.download = `${slug || 'note'}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  toast.success('Note exported as markdown')
}
</script>
