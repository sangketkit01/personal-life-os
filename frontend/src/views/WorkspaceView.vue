<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">Workspace & Pipeline</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            DOCUMENTS & NOTES
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">Multi-stage document pipeline (Drafting ➔ Waiting ➔ Completed) with countdown deadlines and notes</p>
      </div>

      <div class="flex items-center gap-2 flex-wrap">
        <button
          @click="showProjectModal = true"
          class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <FolderPlus class="w-3.5 h-3.5 text-zinc-400" />
          <span>New Project</span>
        </button>
        <button
          @click="showNoteModal = true"
          class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-medium transition-colors flex items-center gap-1.5"
        >
          <FileText class="w-3.5 h-3.5 text-zinc-400" />
          <span>New Note</span>
        </button>
        <button
          @click="showTaskModal = true"
          class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5"
        >
          <Plus class="w-3.5 h-3.5 text-zinc-950" />
          <span>Add Task Document</span>
        </button>
      </div>
    </div>

    <!-- Project Filter Bar -->
    <div class="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-zinc-800/80 text-xs">
      <button
        @click="selectProject(null)"
        class="px-2.5 py-1 rounded-md transition-colors flex items-center gap-2 shrink-0 border"
        :class="[
          workspaceStore.selectedProjectId === null
            ? 'bg-zinc-900 text-zinc-100 border-zinc-700'
            : 'bg-zinc-900/40 text-zinc-400 hover:text-zinc-200 border-zinc-800'
        ]"
      >
        <span>All Projects</span>
        <span class="text-[10px] font-mono px-1 py-0.2 rounded bg-zinc-950 text-zinc-400 border border-zinc-800">
          {{ workspaceStore.tasks.length }}
        </span>
      </button>

      <button
        v-for="p in workspaceStore.projects"
        :key="p.id"
        @click="selectProject(p.id)"
        class="px-2.5 py-1 rounded-md transition-colors flex items-center gap-2 shrink-0 border"
        :class="[
          workspaceStore.selectedProjectId === p.id
            ? 'bg-zinc-900 text-zinc-100 border-zinc-700'
            : 'bg-zinc-900/40 text-zinc-400 hover:text-zinc-200 border-zinc-800'
        ]"
      >
        <span class="w-1.5 h-1.5 rounded-full" :style="{ backgroundColor: p.color }" />
        <span>{{ p.name }}</span>
        <span
          v-if="p.pending_tasks_count > 0"
          class="text-[10px] font-mono px-1 py-0.2 rounded bg-zinc-950 text-zinc-400 border border-zinc-800"
        >
          {{ p.pending_tasks_count }}
        </span>
      </button>
    </div>

    <!-- View Switcher Tabs: Kanban vs Notes -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-1 bg-zinc-900 border border-zinc-800 p-1 rounded-lg">
        <button
          @click="activeView = 'KANBAN'"
          class="px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1.5"
          :class="activeView === 'KANBAN' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
        >
          <Columns3 class="w-3.5 h-3.5" />
          <span>Pipeline (Kanban)</span>
        </button>
        <button
          @click="activeView = 'NOTES'"
          class="px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1.5"
          :class="activeView === 'NOTES' ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
        >
          <FileText class="w-3.5 h-3.5" />
          <span>Project Notes</span>
        </button>
      </div>

      <div class="text-[11px] text-zinc-500 font-mono">
        {{ activeView === 'KANBAN' ? `${pendingTasksCount} active tasks` : `${workspaceStore.notes.length} notes total` }}
      </div>
    </div>

    <!-- 1. KANBAN PIPELINE VIEW (Scrollable on smaller screens) -->
    <div v-if="activeView === 'KANBAN'" class="flex md:grid md:grid-cols-3 gap-4 overflow-x-auto pb-4">
      <!-- COLUMN 1: DRAFTING -->
      <div class="p-3.5 rounded-lg bg-zinc-900/30 border border-zinc-800/80 flex flex-col min-h-[500px] min-w-[300px] md:min-w-0 flex-1">
        <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80 mb-3">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-amber-400" />
            <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Drafting</h3>
          </div>
          <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
            {{ draftingTasks.length }}
          </span>
        </div>

        <div class="space-y-2.5 flex-1 overflow-y-auto">
          <div v-if="draftingTasks.length === 0" class="p-8 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800/80 rounded">
            No tasks in drafting
          </div>

          <div
            v-for="task in draftingTasks"
            :key="task.id"
            class="p-3 rounded-md bg-zinc-900/70 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors flex flex-col justify-between group space-y-2.5"
          >
            <!-- Clickable Card Body opens Edit Modal -->
            <div @click="openEditTaskModal(task)" class="cursor-pointer">
              <div class="flex items-center justify-between gap-2 mb-1.5">
                <span
                  v-if="task.project_name"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 flex items-center gap-1.5 font-mono"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :style="{ backgroundColor: task.project_color || '#71717a' }" />
                  <span class="text-zinc-300 truncate max-w-[120px]">{{ task.project_name }}</span>
                </span>
                <span v-if="task.doc_number" class="text-[10px] font-mono text-zinc-500 ml-auto">
                  {{ task.doc_number }}
                </span>
              </div>

              <h4 class="text-xs font-medium text-zinc-100 line-clamp-2 hover:text-white transition-colors">{{ task.title }}</h4>

              <div v-if="task.deadline" class="mt-2 flex items-center gap-1.5 text-[10px] font-mono">
                <span
                  class="px-1.5 py-0.5 rounded border"
                  :class="getDeadlineBadgeClass(task.deadline_info)"
                >
                  {{ task.deadline_info.label }}
                </span>
              </div>
            </div>

            <!-- Card Bottom Action -->
            <div class="pt-2 border-t border-zinc-800/60 flex items-center justify-between gap-2 text-xs">
              <a
                v-if="task.file_url"
                :href="task.file_url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors flex items-center gap-1 truncate max-w-[130px]"
              >
                <ExternalLink class="w-3 h-3" />
                <span class="truncate">File Link</span>
              </a>
              <span v-else class="text-[10px] text-zinc-600 font-mono">No link</span>

              <button
                @click="moveTask(task.id, 'WAITING')"
                class="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-[11px] font-medium transition-colors ml-auto flex items-center gap-1"
              >
                <span>Sent</span>
                <ArrowRight class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- COLUMN 2: WAITING -->
      <div class="p-3.5 rounded-lg bg-zinc-900/30 border border-zinc-800/80 flex flex-col min-h-[500px] min-w-[300px] md:min-w-0 flex-1">
        <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80 mb-3">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-zinc-400" />
            <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Waiting Review</h3>
          </div>
          <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
            {{ waitingTasks.length }}
          </span>
        </div>

        <div class="space-y-2.5 flex-1 overflow-y-auto">
          <div v-if="waitingTasks.length === 0" class="p-8 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800/80 rounded">
            No documents waiting
          </div>

          <div
            v-for="task in waitingTasks"
            :key="task.id"
            class="p-3 rounded-md bg-zinc-900/70 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors flex flex-col justify-between group space-y-2.5"
          >
            <div @click="openEditTaskModal(task)" class="cursor-pointer">
              <div class="flex items-center justify-between gap-2 mb-1.5">
                <span
                  v-if="task.project_name"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 flex items-center gap-1.5 font-mono"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :style="{ backgroundColor: task.project_color || '#71717a' }" />
                  <span class="text-zinc-300 truncate max-w-[120px]">{{ task.project_name }}</span>
                </span>
                <span v-if="task.doc_number" class="text-[10px] font-mono text-zinc-500 ml-auto">
                  {{ task.doc_number }}
                </span>
              </div>

              <h4 class="text-xs font-medium text-zinc-100 line-clamp-2 hover:text-white transition-colors">{{ task.title }}</h4>

              <div v-if="task.deadline" class="mt-2 flex items-center gap-1.5 text-[10px] font-mono">
                <span
                  class="px-1.5 py-0.5 rounded border"
                  :class="getDeadlineBadgeClass(task.deadline_info)"
                >
                  {{ task.deadline_info.label }}
                </span>
              </div>
            </div>

            <!-- Card Bottom Action -->
            <div class="pt-2 border-t border-zinc-800/60 flex items-center justify-between gap-2 text-xs">
              <button
                @click="moveTask(task.id, 'DRAFTING')"
                class="px-1.5 py-0.5 rounded text-zinc-400 hover:text-zinc-200 text-[10px] transition-colors flex items-center gap-1"
                title="Revise"
              >
                <ArrowLeft class="w-3 h-3" />
                <span>Revise</span>
              </button>

              <button
                @click="moveTask(task.id, 'COMPLETED')"
                class="px-2 py-0.5 rounded bg-zinc-100 hover:bg-white text-zinc-950 text-[11px] font-semibold transition-colors flex items-center gap-1 ml-auto"
              >
                <Check class="w-3 h-3" />
                <span>Complete</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- COLUMN 3: COMPLETED -->
      <div class="p-3.5 rounded-lg bg-zinc-900/30 border border-zinc-800/80 flex flex-col min-h-[500px] min-w-[300px] md:min-w-0 flex-1">
        <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80 mb-3">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-400" />
            <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Completed</h3>
          </div>
          <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
            {{ completedTasks.length }}
          </span>
        </div>

        <div class="space-y-2.5 flex-1 overflow-y-auto">
          <div v-if="completedTasks.length === 0" class="p-8 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800/80 rounded">
            No completed tasks
          </div>

          <div
            v-for="task in completedTasks"
            :key="task.id"
            class="p-3 rounded-md bg-zinc-900/40 border border-zinc-800/60 opacity-70 hover:opacity-100 transition-colors flex flex-col justify-between group space-y-2.5"
          >
            <div @click="openEditTaskModal(task)" class="cursor-pointer">
              <div class="flex items-center justify-between gap-2 mb-1.5">
                <span
                  v-if="task.project_name"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 flex items-center gap-1.5 font-mono"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :style="{ backgroundColor: task.project_color || '#71717a' }" />
                  <span class="text-zinc-300 truncate max-w-[120px]">{{ task.project_name }}</span>
                </span>
              </div>

              <h4 class="text-xs font-medium text-zinc-400 line-through line-clamp-1 hover:text-zinc-200 transition-colors">{{ task.title }}</h4>
              <div v-if="task.completed_at" class="text-[10px] font-mono text-zinc-500 mt-1">
                Settled: {{ new Date(task.completed_at).toLocaleDateString('en-GB') }}
              </div>
            </div>

            <div class="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-xs">
              <button
                @click="moveTask(task.id, 'WAITING')"
                class="px-1.5 py-0.5 rounded text-zinc-500 hover:text-zinc-300 text-[10px] transition-colors"
              >
                Reopen
              </button>
              <a
                v-if="task.file_url"
                :href="task.file_url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[10px] font-mono text-zinc-400 hover:underline"
              >
                View File
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. PROJECT NOTES VIEW -->
    <div v-else class="space-y-4">
      <div v-if="workspaceStore.notes.length === 0" class="p-12 rounded-lg bg-zinc-900/30 border border-zinc-800 text-center space-y-3 font-mono text-xs text-zinc-500">
        <p>No project notes captured yet.</p>
        <button
          @click="showNoteModal = true"
          class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 font-sans transition-colors inline-block"
        >
          + Create first note
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        <div
          v-for="note in workspaceStore.notes"
          :key="note.id"
          class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-700/80 transition-colors flex flex-col justify-between group space-y-3"
        >
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span
                v-if="note.project_name"
                class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800"
              >
                {{ note.project_name }}
              </span>
              <div class="flex items-center gap-1 ml-auto">
                <button
                  @click.stop="handleExportNote(note)"
                  title="Export as .md"
                  class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
                >
                  <Download class="w-3 h-3" />
                </button>
                <button
                  @click="handleTogglePin(note.id)"
                  :title="note.is_pinned ? 'Unpin' : 'Pin'"
                  class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
                >
                  <Pin class="w-3 h-3" :class="{ 'fill-zinc-200 text-zinc-200': note.is_pinned }" />
                </button>
                <button
                  @click="handleDeleteNote(note.id)"
                  class="p-1 rounded text-zinc-600 hover:text-rose-400 transition-colors"
                >
                  <Trash2 class="w-3 h-3" />
                </button>
              </div>
            </div>

            <h3
              @click="openEditNoteModal(note)"
              class="font-medium text-xs text-zinc-100 line-clamp-1 mb-1 cursor-pointer hover:text-white transition-colors"
            >
              {{ note.title }}
            </h3>
            <p class="text-[11px] text-zinc-400 line-clamp-3 leading-relaxed font-mono">
              {{ note.content }}
            </p>
          </div>

          <div class="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[10px] font-mono text-zinc-500">
            <div class="flex items-center gap-1 flex-wrap">
              <span v-for="tag in note.tags" :key="tag" class="px-1 py-0.2 rounded bg-zinc-900 border border-zinc-800">
                #{{ tag }}
              </span>
            </div>
            <span>{{ new Date(note.updated_at).toLocaleDateString('en-GB') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <CreateProjectModal
      :is-open="showProjectModal"
      @close="showProjectModal = false"
      @created="handleProjectCreated"
    />

    <CreateTaskModal
      :is-open="showTaskModal"
      @close="showTaskModal = false"
      @created="handleTaskCreated"
    />

    <EditTaskModal
      :is-open="showEditTaskModal"
      :task="selectedTask"
      @close="showEditTaskModal = false"
      @saved="handleTaskSaved"
      @deleted="handleTaskDeleted"
    />

    <NoteEditorModal
      :is-open="showNoteModal"
      :editing-note="selectedNote"
      @close="showNoteModal = false"
      @saved="handleNoteSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWorkspaceStore } from '../stores/workspace'
import { useToastStore } from '../stores/toast'
import type { TaskStatus, TaskDocument, Note, DeadlineInfo } from '../types/workspace'
import CreateProjectModal from '../components/workspace/CreateProjectModal.vue'
import CreateTaskModal from '../components/workspace/CreateTaskModal.vue'
import EditTaskModal from '../components/workspace/EditTaskModal.vue'
import NoteEditorModal from '../components/workspace/NoteEditorModal.vue'
import {
  Columns3,
  FileText,
  FolderPlus,
  Plus,
  Trash2,
  ExternalLink,
  ArrowRight,
  ArrowLeft,
  Check,
  Pin,
  Download
} from 'lucide-vue-next'

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const activeView = ref<'KANBAN' | 'NOTES'>('KANBAN')
const showProjectModal = ref<boolean>(false)
const showTaskModal = ref<boolean>(false)
const showEditTaskModal = ref<boolean>(false)
const showNoteModal = ref<boolean>(false)
const selectedTask = ref<TaskDocument | null>(null)
const selectedNote = ref<Note | null>(null)

onMounted(async () => {
  await Promise.all([
    workspaceStore.fetchOverview(),
    workspaceStore.fetchProjects(),
    workspaceStore.fetchTasks(),
    workspaceStore.fetchNotes()
  ])
})

const selectProject = async (projectId: string | null) => {
  workspaceStore.selectedProjectId = projectId
  await Promise.all([
    workspaceStore.fetchOverview(projectId || undefined),
    workspaceStore.fetchTasks(),
    workspaceStore.fetchNotes()
  ])
}

const draftingTasks = computed(() => {
  return workspaceStore.tasks.filter(t => t.status === 'DRAFTING')
})

const waitingTasks = computed(() => {
  return workspaceStore.tasks.filter(t => t.status === 'WAITING')
})

const completedTasks = computed(() => {
  return workspaceStore.tasks.filter(t => t.status === 'COMPLETED')
})

const pendingTasksCount = computed(() => {
  return draftingTasks.value.length + waitingTasks.value.length
})

const getDeadlineBadgeClass = (info?: DeadlineInfo) => {
  if (!info) return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  switch (info.urgency) {
    case 'OVERDUE':
    case 'CRITICAL':
      return 'bg-rose-950/20 text-rose-400 border-rose-500/30'
    case 'WARNING':
    case 'ATTENTION':
      return 'bg-amber-950/20 text-amber-400 border-amber-500/30'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

const moveTask = async (taskId: string, newStatus: TaskStatus) => {
  await workspaceStore.moveTaskStatus(taskId, newStatus)
  toast.success(`Task moved to ${newStatus}`)
}

const openEditTaskModal = (task: TaskDocument) => {
  selectedTask.value = task
  showEditTaskModal.value = true
}

const openEditNoteModal = (note: Note) => {
  selectedNote.value = note
  showNoteModal.value = true
}

const handleTogglePin = async (id: string) => {
  await workspaceStore.togglePinNote(id)
}

const handleDeleteNote = async (id: string) => {
  try {
    await workspaceStore.deleteNote(id)
    toast.info('Note deleted')
  } catch (err) {
    toast.error('Failed to delete note')
  }
}

const handleExportNote = (note: Note) => {
  const frontmatter = [
    '---',
    `title: "${(note.title || 'Untitled Note').replace(/"/g, '\\"')}"`,
    `project: "${(note.project_name || 'General').replace(/"/g, '\\"')}"`,
    `tags: [${(note.tags || []).map(t => `"${t.replace(/"/g, '\\"')}"`).join(', ')}]`,
    `date: "${new Date(note.created_at).toISOString().slice(0, 10)}"`,
    '---',
    '',
    note.content
  ].join('\n')

  const blob = new Blob([frontmatter], { type: 'text/markdown;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const slug = (note.title || 'note')
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

const handleProjectCreated = async () => {
  await workspaceStore.fetchProjects()
  toast.success('Project created')
}

const handleTaskCreated = async () => {
  toast.success('Task created')
}

const handleTaskSaved = async () => {
  toast.success('Task saved')
}

const handleTaskDeleted = async () => {
  // Handled
}

const handleNoteSaved = async () => {
  selectedNote.value = null
}
</script>
