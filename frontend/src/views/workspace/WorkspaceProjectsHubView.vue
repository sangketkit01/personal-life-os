<template>
  <div class="space-y-6 max-w-7xl mx-auto font-sans">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">{{ t('ws.title') }}</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            {{ t('ws.badge') }}
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">{{ t('ws.subtitle') }}</p>
      </div>

      <button
        @click="openCreateModal()"
        class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 self-start"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>{{ t('ws.newProject') }}</span>
      </button>
    </div>

    <!-- Top Metric Strip -->
    <SkeletonLoader
      v-if="workspaceStore.isProjectsLoading && workspaceStore.projects.length === 0 && !workspaceStore.overview"
      variant="metrics"
      :count="4"
    />

    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
      <div class="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80">
        <div class="flex items-center gap-2 mb-2">
          <FolderKanban class="w-3.5 h-3.5 text-zinc-500" />
          <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500">{{ t('ws.metric.active') }}</span>
        </div>
        <div class="text-2xl font-semibold text-zinc-100 font-mono">{{ metricActiveProjects }}</div>
        <div class="text-[10px] font-mono text-zinc-600 mt-1">{{ t('ws.metric.inPlanning', { count: metricPlanning }) }}</div>
      </div>

      <div class="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80">
        <div class="flex items-center gap-2 mb-2">
          <Activity class="w-3.5 h-3.5 text-sky-400/70" />
          <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500">{{ t('ws.metric.inProgress') }}</span>
        </div>
        <div class="text-2xl font-semibold text-zinc-100 font-mono">{{ metricDoing }}</div>
        <div class="text-[10px] font-mono text-zinc-600 mt-1">{{ t('ws.metric.inBacklog', { count: metricTodo }) }}</div>
      </div>

      <div class="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80">
        <div class="flex items-center gap-2 mb-2">
          <CalendarClock class="w-3.5 h-3.5 text-amber-400/70" />
          <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500">{{ t('ws.metric.dueIn7') }}</span>
        </div>
        <div class="text-2xl font-semibold text-zinc-100 font-mono">{{ metricDueSoon }}</div>
        <div class="text-[10px] font-mono mt-1" :class="metricOverdue > 0 ? 'text-rose-400' : 'text-zinc-600'">
          {{ t('ws.metric.overdue', { count: metricOverdue }) }}
        </div>
      </div>

      <div class="p-4 rounded-lg bg-zinc-900/30 border border-zinc-800/80">
        <div class="flex items-center gap-2 mb-2">
          <BookOpen class="w-3.5 h-3.5 text-zinc-500" />
          <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500">{{ t('ws.metric.knowledge') }}</span>
        </div>
        <div class="text-2xl font-semibold text-zinc-100 font-mono">{{ metricNotes }}</div>
        <div class="text-[10px] font-mono text-zinc-600 mt-1">{{ t('ws.metric.acrossAll') }}</div>
      </div>
    </div>

    <!-- Filter Tabs + Search -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div class="flex items-center gap-1 bg-zinc-900 border border-zinc-800 p-1 rounded-lg">
        <button
          v-for="tab in filterTabs"
          :key="tab.key"
          @click="activeFilter = tab.key"
          class="px-3 py-1 rounded text-xs font-medium transition-colors"
          :class="activeFilter === tab.key ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
        >
          {{ t(tab.labelKey) }}
          <span class="ml-1 text-[10px] font-mono text-zinc-500">{{ filteredProjects(tab.key).length }}</span>
        </button>
      </div>

      <div class="relative w-full sm:w-64">
        <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('ws.searchProjects')"
          class="w-full bg-zinc-900/60 border border-zinc-800/80 rounded-md pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-zinc-600"
        />
      </div>
    </div>

    <!-- Projects Grid -->
    <SkeletonLoader
      v-if="workspaceStore.isProjectsLoading && workspaceStore.projects.length === 0"
      variant="cards"
      :count="6"
    />

    <div v-else-if="visibleProjects.length === 0" class="p-12 rounded-lg bg-zinc-900/30 border border-zinc-800 text-center space-y-3">
      <FolderKanban class="w-8 h-8 text-zinc-700 mx-auto" />
      <p class="text-xs font-mono text-zinc-500">{{ t('ws.empty') }}</p>
      <button
        @click="openCreateModal()"
        class="px-3 py-1.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-medium transition-colors inline-block"
      >
        {{ t('ws.createFirst') }}
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
      <div
        v-for="project in visibleProjects"
        :key="project.id"
        class="rounded-lg bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-600/80 transition-all cursor-pointer flex flex-col overflow-hidden group"
        @click="router.push(`/workspace/projects/${project.id}`)"
      >
        <!-- Color accent bar -->
        <div class="h-1" :style="{ backgroundColor: project.color }" />

        <div class="p-4 space-y-3 flex-1 flex flex-col">
          <div class="flex items-start justify-between gap-2">
            <div class="flex items-center gap-2.5 min-w-0">
              <div
                class="w-8 h-8 rounded-md flex items-center justify-center text-sm shrink-0 border"
                :style="{ backgroundColor: `${project.color}1A`, borderColor: `${project.color}40` }"
              >
                <component :is="iconComponentFor(project.icon)" class="w-4 h-4" />
              </div>
              <div class="min-w-0">
                <h3 class="text-sm font-semibold text-zinc-100 truncate group-hover:text-white transition-colors">{{ project.name }}</h3>
                <div class="flex items-center gap-1.5 mt-0.5">
                  <span
                    class="text-[9px] font-mono px-1.5 py-0.2 rounded border uppercase font-semibold"
                    :class="statusBadgeClass(project.status)"
                  >
                    {{ project.status.replace('_', ' ') }}
                  </span>
                  <span v-if="project.category" class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-500 border border-zinc-800 uppercase">
                    {{ project.category }}
                  </span>
                </div>
              </div>
            </div>

            <button
              type="button"
              @click.stop="openEditModal(project)"
              class="p-1 rounded text-zinc-600 hover:text-zinc-200 hover:bg-zinc-800 transition-colors shrink-0"
              :title="t('ws.editProject')"
            >
              <Pencil class="w-3.5 h-3.5" />
            </button>
          </div>

          <p v-if="project.description" class="text-[11px] text-zinc-400 line-clamp-2 leading-relaxed">
            {{ project.description }}
          </p>

          <!-- Completion progress -->
          <div class="mt-auto space-y-1.5">
            <div class="flex items-center justify-between text-[10px] font-mono text-zinc-500">
              <span>{{ t('ws.taskProgress') }}</span>
              <span>{{ project.completed_tasks_count }}/{{ project.total_tasks_count }} ({{ progressPct(project) }}%)</span>
            </div>
            <div class="h-1.5 rounded-full bg-zinc-900 border border-zinc-800/60 overflow-hidden">
              <div
                class="h-full transition-all duration-300"
                :style="{ width: `${progressPct(project)}%`, backgroundColor: project.color }"
              />
            </div>
          </div>

          <!-- Counters footer -->
          <div class="pt-2.5 border-t border-zinc-800/60 flex items-center justify-between text-[10px] font-mono text-zinc-500">
            <span class="flex items-center gap-1" title="Tasks"><ListTodo class="w-3 h-3" /> {{ project.total_tasks_count }}</span>
            <span class="flex items-center gap-1" title="Pages"><StickyNote class="w-3 h-3" /> {{ project.notes_count }}</span>
            <span class="flex items-center gap-1" title="Links"><Link2 class="w-3 h-3" /> {{ project.links_count }}</span>
            <span class="flex items-center gap-1" title="Files"><Paperclip class="w-3 h-3" /> {{ project.attachments_count }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Create / Edit Project Modal -->
    <div
      v-if="showProjectModal"
      class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-sans overflow-y-auto"
      @click.self="showProjectModal = false"
    >
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-lg p-5 shadow-2xl relative my-8">
        <button
          @click="showProjectModal = false"
          class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <X class="w-4 h-4" />
        </button>

        <h3 class="text-sm font-semibold text-zinc-100 mb-1">
          {{ editingProject ? t('ws.modal.edit') : t('ws.modal.create') }}
        </h3>
        <p class="text-xs text-zinc-500 mb-4">{{ t('ws.modal.subtitle') }}</p>

        <div class="space-y-3.5">
          <div>
            <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ws.modal.name') }}</label>
            <input
              v-model="form.name"
              type="text"
              :placeholder="t('ws.modal.namePlaceholder')"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600"
            />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ws.modal.status') }}</label>
              <select
                v-model="form.status"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
              >
                <option value="PLANNING">{{ t('st.status.planning') }}</option>
                <option value="ACTIVE">{{ t('st.status.active') }}</option>
                <option value="ON_HOLD">{{ t('st.status.onHold') }}</option>
                <option value="COMPLETED">{{ t('st.status.completed') }}</option>
                <option value="ARCHIVED">{{ t('st.status.archived') }}</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ws.modal.category') }}</label>
              <select
                v-model="form.category"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
              >
                <option value="GENERAL">{{ t('st.category.general') }}</option>
                <option value="CLIENT">{{ t('st.category.client') }}</option>
                <option value="INTERNAL">{{ t('st.category.internal') }}</option>
                <option value="PERSONAL">{{ t('st.category.personal') }}</option>
                <option value="DEV">{{ t('st.category.dev') }}</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1.5">{{ t('ws.modal.colorIcon') }}</label>
            <div class="flex items-center gap-2 flex-wrap">
              <button
                v-for="color in COLOR_PRESETS"
                :key="color"
                type="button"
                @click="form.color = color"
                class="w-6 h-6 rounded-full border-2 transition-transform"
                :class="form.color === color ? 'scale-110 border-zinc-100' : 'border-transparent'"
                :style="{ backgroundColor: color }"
              />
              <span class="mx-1 w-px h-5 bg-zinc-800" />
              <button
                v-for="preset in PROJECT_ICON_PRESETS"
                :key="preset.key"
                type="button"
                @click="form.icon = preset.key"
                class="w-7 h-7 rounded-md flex items-center justify-center transition-colors border"
                :class="form.icon === preset.key ? 'bg-zinc-800 border-zinc-600 text-zinc-100' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700 text-zinc-400'"
                :title="preset.label"
              >
                <component :is="preset.icon" class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ws.modal.startDate') }}</label>
              <input
                v-model="form.start_date"
                type="date"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
              />
            </div>
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ws.modal.targetDate') }}</label>
              <input
                v-model="form.target_date"
                type="date"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
              />
            </div>
          </div>

          <div>
            <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">{{ t('ws.modal.description') }}</label>
            <textarea
              v-model="form.description"
              rows="3"
              :placeholder="t('ws.modal.descPlaceholder')"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600 resize-y"
            />
          </div>
        </div>

        <div class="flex items-center justify-end gap-2.5 mt-5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="showProjectModal = false"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            {{ t('cancel') }}
          </button>
          <button
            type="button"
            @click="submitProject"
            :disabled="isSubmitting"
            class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors shadow-sm disabled:opacity-50"
          >
            {{ editingProject ? t('ws.modal.saveBtn') : t('ws.modal.createBtn') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import SkeletonLoader from '../../components/common/SkeletonLoader.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Activity,
  CalendarClock,
  FolderKanban,
  Link2,
  ListTodo,
  Paperclip,
  Pencil,
  Plus,
  Search,
  StickyNote,
  X
} from 'lucide-vue-next'
import { PROJECT_ICON_PRESETS, iconComponentFor } from '../../utils/iconPresets'
import { t } from '../../i18n'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import type { ProjectStatus, WorkspaceProject } from '../../types/workspace'

const router = useRouter()
const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const COLOR_PRESETS = ['#3B82F6', '#8B5CF6', '#EC4899', '#EF4444', '#F59E0B', '#10B981', '#06B6D4', '#71717A']
type FilterKey = 'active' | 'done' | 'archived'

const filterTabs: Array<{ key: FilterKey; labelKey: string }> = [
  { key: 'active', labelKey: 'ws.tab.active' },
  { key: 'done', labelKey: 'ws.tab.done' },
  { key: 'archived', labelKey: 'ws.tab.archived' }
]

const activeFilter = ref<FilterKey>('active')
const searchQuery = ref('')
const showProjectModal = ref(false)
const editingProject = ref<WorkspaceProject | null>(null)
const isSubmitting = ref(false)

const form = reactive({
  name: '',
  status: 'ACTIVE' as ProjectStatus,
  category: 'GENERAL',
  color: '#3B82F6',
  icon: 'briefcase',
  start_date: '',
  target_date: '',
  description: ''
})

onMounted(async () => {
  await Promise.allSettled([
    workspaceStore.fetchProjects(),
    workspaceStore.fetchOverview(),
    workspaceStore.fetchTasks()
  ])
})

const filteredProjects = (key: FilterKey) => {
  return workspaceStore.projects.filter(p => {
    if (key === 'archived') return p.is_archived || p.status === 'ARCHIVED'
    if (key === 'done') return !p.is_archived && p.status !== 'ARCHIVED' && (p.status === 'COMPLETED' || p.status === 'ON_HOLD')
    return !p.is_archived && ['PLANNING', 'ACTIVE'].includes(p.status)
  })
}

const visibleProjects = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return filteredProjects(activeFilter.value).filter(p => {
    if (!q) return true
    return p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q) || p.category.toLowerCase().includes(q)
  })
})

const metricActiveProjects = computed(() => filteredProjects('active').length)
const metricPlanning = computed(() =>
  workspaceStore.projects.filter(p => !p.is_archived && p.status === 'PLANNING').length
)
const metricDoing = computed(() => workspaceStore.overview?.pipeline_counts?.doing || 0)
const metricTodo = computed(() => workspaceStore.overview?.pipeline_counts?.todo || 0)
const metricNotes = computed(() =>
  workspaceStore.projects.reduce((sum, p) => sum + (p.notes_count || 0), 0)
)

const metricDueSoon = computed(() => {
  const now = Date.now()
  const in7Days = now + 7 * 24 * 60 * 60 * 1000
  return workspaceStore.tasks.filter(t => {
    if (t.status === 'DONE' || t.status === 'ARCHIVED' || !t.deadline) return false
    const dl = new Date(t.deadline).getTime()
    return dl >= now && dl <= in7Days
  }).length
})

const metricOverdue = computed(() => {
  const now = Date.now()
  return workspaceStore.tasks.filter(t => {
    if (t.status === 'DONE' || t.status === 'ARCHIVED' || !t.deadline) return false
    return new Date(t.deadline).getTime() < now
  }).length
})

function progressPct(project: WorkspaceProject): number {
  const total = project.total_tasks_count || 0
  if (total === 0) return 0
  return Math.round(((project.completed_tasks_count || 0) / total) * 100)
}

function statusBadgeClass(status: ProjectStatus): string {
  switch (status) {
    case 'ACTIVE':
      return 'bg-zinc-900 text-emerald-400 border-zinc-800'
    case 'PLANNING':
      return 'bg-zinc-900 text-sky-300 border-zinc-800'
    case 'ON_HOLD':
      return 'bg-zinc-900 text-amber-400 border-zinc-800'
    case 'COMPLETED':
      return 'bg-zinc-900 text-zinc-300 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-500 border-zinc-800'
  }
}

function openCreateModal() {
  editingProject.value = null
  form.name = ''
  form.status = 'ACTIVE'
  form.category = 'GENERAL'
  form.color = '#3B82F6'
  form.icon = 'briefcase'
  form.start_date = ''
  form.target_date = ''
  form.description = ''
  showProjectModal.value = true
}

function openEditModal(project: WorkspaceProject) {
  editingProject.value = project
  form.name = project.name
  form.status = project.status
  form.category = project.category || 'GENERAL'
  form.color = project.color
  form.icon = project.icon
  form.start_date = project.start_date || ''
  form.target_date = project.target_date || ''
  form.description = project.description || ''
  showProjectModal.value = true
}

async function submitProject() {
  if (!form.name.trim()) {
    toast.error('Project name is required')
    return
  }
  isSubmitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      status: form.status,
      category: form.category,
      color: form.color,
      icon: form.icon,
      start_date: form.start_date || null,
      target_date: form.target_date || null,
      description: form.description
    }
    if (editingProject.value) {
      await workspaceStore.updateProject(editingProject.value.id, payload)
      toast.success('Project updated')
    } else {
      await workspaceStore.createProject(payload)
      toast.success('Project created')
    }
    showProjectModal.value = false
    await Promise.allSettled([workspaceStore.fetchProjects(), workspaceStore.fetchOverview()])
  } catch (err: any) {
    toast.error(err?.response?.data?.name?.[0] || 'Failed to save project')
  } finally {
    isSubmitting.value = false
  }
}
</script>
