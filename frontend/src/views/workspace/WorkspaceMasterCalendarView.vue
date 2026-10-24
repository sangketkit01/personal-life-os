<template>
  <div class="space-y-5 max-w-7xl mx-auto font-sans">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800/80">
      <div>
        <div class="flex items-center gap-2.5">
          <h1 class="text-lg font-semibold text-zinc-100 tracking-tight">{{ t('cal.title') }}</h1>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-900 text-zinc-400 border border-zinc-800">
            {{ t('cal.badge') }}
          </span>
        </div>
        <p class="text-xs text-zinc-500 mt-1">{{ t('cal.subtitle') }}</p>
      </div>

      <button
        @click="openQuickCreate(null)"
        class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 self-start"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>{{ t('cal.newEntry') }}</span>
      </button>
    </div>

    <!-- Filter Bar -->
    <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
      <select
        v-model="filterProject"
        class="bg-zinc-900/60 border border-zinc-800/80 rounded-md px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-zinc-600"
      >
        <option value="">{{ t('cal.allProjects') }}</option>
        <option v-for="p in workspaceStore.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>

      <select
        v-model="filterPriority"
        class="bg-zinc-900/60 border border-zinc-800/80 rounded-md px-2.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-zinc-600"
      >
        <option value="">{{ t('cal.allPriorities') }}</option>
        <option value="URGENT">Urgent</option>
        <option value="HIGH">High</option>
        <option value="MEDIUM">Medium</option>
        <option value="LOW">Low</option>
      </select>

      <div class="text-[11px] font-mono text-zinc-500 ml-auto">
        {{ t('cal.tasksEvents', { tasks: filteredTasks.length, events: filteredEvents.length }) }}
      </div>
    </div>

    <!-- Calendar Grid -->
    <WorkspaceCalendarGrid
      :tasks="filteredTasks"
      :events="filteredEvents"
      :show-project-dot="true"
      @select-task="openDrawer"
      @select-event="openEventModal"
      @create-on-date="openQuickCreate"
    />

    <!-- Task Side Peek Drawer -->
    <TaskSidePeekDrawer
      :is-open="isDrawerOpen"
      :task="selectedTask"
      @close="closeDrawer"
      @updated="handleTaskUpdated"
      @deleted="handleTaskDeleted"
      @refresh="refreshData"
    />

    <!-- Quick Create (Task or Event) -->
    <CalendarQuickCreateModal
      :is-open="showQuickCreate"
      :projects="workspaceStore.projects"
      :initial-date="quickCreateDate"
      @close="showQuickCreate = false"
      @created-task="handleQuickTaskCreated"
      @created-event="handleQuickEventCreated"
    />

    <!-- Edit Event Modal -->
    <CalendarEventModal
      :is-open="isEventModalOpen"
      :event="selectedEvent"
      :projects="workspaceStore.projects"
      @close="isEventModalOpen = false"
      @updated="handleEventUpdated"
      @deleted="handleEventDeleted"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Plus } from 'lucide-vue-next'
import { useWorkspaceStore } from '../../stores/workspace'
import WorkspaceCalendarGrid from '../../components/workspace/WorkspaceCalendarGrid.vue'
import { t } from '../../i18n'
import TaskSidePeekDrawer from '../../components/workspace/TaskSidePeekDrawer.vue'
import CalendarQuickCreateModal from '../../components/workspace/CalendarQuickCreateModal.vue'
import CalendarEventModal from '../../components/workspace/CalendarEventModal.vue'
import type { CalendarEvent, TaskDocument } from '../../types/workspace'

const workspaceStore = useWorkspaceStore()

const filterProject = ref('')
const filterPriority = ref('')

const isDrawerOpen = ref(false)
const selectedTask = ref<TaskDocument | null>(null)

const showQuickCreate = ref(false)
const quickCreateDate = ref<string | null>(null)

const isEventModalOpen = ref(false)
const selectedEvent = ref<CalendarEvent | null>(null)

onMounted(async () => {
  await refreshData()
})

async function refreshData() {
  const params: Record<string, string> = {}
  if (filterProject.value) params.project_id = filterProject.value
  await Promise.allSettled([
    workspaceStore.fetchProjects(),
    workspaceStore.fetchTasks({ ...(filterProject.value ? { project_id: filterProject.value } : {}) }),
    workspaceStore.fetchEvents(params)
  ])
}

const filteredTasks = computed(() => {
  return workspaceStore.tasks.filter(t => {
    if (filterProject.value && t.project !== filterProject.value) return false
    if (filterPriority.value && t.priority !== filterPriority.value) return false
    return true
  })
})

const filteredEvents = computed(() => {
  return workspaceStore.events.filter(e => {
    if (filterProject.value && e.project !== filterProject.value) return false
    return true
  })
})

function openDrawer(task: TaskDocument) {
  isEventModalOpen.value = false
  selectedTask.value = task
  isDrawerOpen.value = true
}

function closeDrawer() {
  isDrawerOpen.value = false
}

function openQuickCreate(dateStr: string | null) {
  quickCreateDate.value = dateStr
  showQuickCreate.value = true
}

function openEventModal(event: CalendarEvent) {
  isDrawerOpen.value = false
  selectedEvent.value = event
  isEventModalOpen.value = true
}

async function handleQuickTaskCreated(task: TaskDocument) {
  showQuickCreate.value = false
  openDrawer(task)
}

function handleQuickEventCreated() {
  showQuickCreate.value = false
}

function handleTaskUpdated(updated: TaskDocument) {
  selectedTask.value = updated
}

function handleTaskDeleted() {
  selectedTask.value = null
  isDrawerOpen.value = false
}

function handleEventUpdated(updated: CalendarEvent) {
  selectedEvent.value = updated
  isEventModalOpen.value = false
}

function handleEventDeleted() {
  selectedEvent.value = null
  isEventModalOpen.value = false
}
</script>
