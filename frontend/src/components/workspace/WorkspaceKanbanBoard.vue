<template>
  <div class="flex md:grid md:grid-cols-3 gap-4 overflow-x-auto pb-4">
    <div
      v-for="column in columns"
      :key="column.status"
      class="p-3.5 rounded-lg bg-zinc-900/30 border border-zinc-800/80 flex flex-col min-h-[420px] min-w-[280px] md:min-w-0 flex-1 transition-colors"
      :class="{ 'border-zinc-600/80 bg-zinc-900/60': dragOverColumn === column.status }"
      @dragover.prevent="dragOverColumn = column.status"
      @dragleave="dragOverColumn = ''"
      @drop.prevent="handleDrop(column.status)"
    >
      <!-- Column Header -->
      <div class="flex items-center justify-between pb-3 border-b border-zinc-800/80 mb-3">
        <div class="flex items-center gap-2">
          <span
            class="w-2 h-2 rounded-full"
            :class="column.dotClass"
            :style="column.status === 'DOING' ? 'animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;' : ''"
          />
          <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">{{ column.label }}</h3>
        </div>
        <div class="flex items-center gap-1.5">
          <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
            {{ columnTasks(column.status).length }}
          </span>
          <button
            type="button"
            @click="emit('create-task', column.status)"
            class="p-0.5 rounded text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
            :title="`Add task to ${column.label}`"
          >
            <Plus class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <!-- Cards -->
      <div class="space-y-2.5 flex-1 overflow-y-auto">
        <div
          v-if="columnTasks(column.status).length === 0"
          class="p-8 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800/80 rounded"
        >
          {{ column.emptyText }}
        </div>

        <div
          v-for="task in columnTasks(column.status)"
          :key="task.id"
          draggable="true"
          @dragstart="handleDragStart(task, $event)"
          @dragend="dragOverColumn = ''"
          @click="emit('select-task', task)"
          class="p-3 rounded-md bg-zinc-900/70 border border-zinc-800/80 hover:border-zinc-600/80 transition-all cursor-pointer flex flex-col gap-2 active:cursor-grabbing"
          :class="{ 'opacity-40': task.status === 'DONE' }"
        >
          <!-- Top row: project pill + priority badge -->
          <div class="flex items-center justify-between gap-2">
            <span
              v-if="showProjectBadge && task.project_name"
              class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 flex items-center gap-1.5 font-mono min-w-0"
            >
              <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ backgroundColor: task.project_color || '#71717a' }" />
              <span class="text-zinc-300 truncate max-w-[110px]">{{ task.project_name }}</span>
            </span>
            <span
              v-else-if="task.doc_number"
              class="text-[10px] font-mono text-zinc-500 truncate"
            >
              {{ task.doc_number }}
            </span>
            <span
              class="text-[9px] font-mono px-1.5 py-0.5 rounded border uppercase font-semibold shrink-0"
              :class="priorityClass(task.priority)"
            >
              {{ task.priority }}
            </span>
          </div>

          <!-- Title -->
          <h4
            class="text-xs font-medium line-clamp-2 transition-colors"
            :class="task.status === 'DONE' ? 'text-zinc-400 line-through' : 'text-zinc-100'"
          >
            {{ task.title }}
          </h4>

          <!-- Meta row: deadline urgency + checklist progress + icons -->
          <div class="flex items-center gap-1.5 flex-wrap">
            <span
              v-if="task.status !== 'DONE' && task.deadline"
              class="text-[10px] font-mono px-1.5 py-0.5 rounded border"
              :class="deadlineClass(task.deadline_info)"
            >
              {{ task.deadline_info?.label || 'Scheduled' }}
            </span>

            <span
              v-if="checklistTotal(task) > 0"
              class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400"
              :class="{ 'text-emerald-400': checklistCompleted(task) === checklistTotal(task) }"
            >
              ✓ {{ checklistCompleted(task) }}/{{ checklistTotal(task) }}
            </span>

            <span class="ml-auto flex items-center gap-1.5 text-zinc-600">
              <FileText v-if="task.notes" class="w-3 h-3" title="Has notes" />
              <Link2 v-if="(task.links || []).length > 0" class="w-3 h-3" title="Has links" />
              <Paperclip v-if="task.file_url" class="w-3 h-3" title="Has attachment" />
            </span>
          </div>

          <!-- Quick status transition buttons (mobile-friendly) -->
          <div class="pt-1.5 border-t border-zinc-800/60 flex items-center justify-between gap-2">
            <button
              v-if="column.prevStatus"
              type="button"
              @click.stop="emit('move-task', task.id, column.prevStatus!)"
              class="px-1.5 py-0.5 rounded text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 text-[10px] transition-colors flex items-center gap-1"
            >
              <ArrowLeft class="w-3 h-3" />
              <span>{{ column.prevLabel }}</span>
            </button>
            <span v-else />

            <button
              v-if="column.nextStatus"
              type="button"
              @click.stop="emit('move-task', task.id, column.nextStatus!)"
              class="px-2 py-0.5 rounded text-[11px] font-medium transition-colors flex items-center gap-1"
              :class="column.status === 'DOING'
                ? 'bg-zinc-100 hover:bg-white text-zinc-950 font-semibold'
                : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-200'"
            >
              <span>{{ column.nextLabel }}</span>
              <ArrowRight v-if="column.status !== 'DONE'" class="w-3 h-3" />
              <Check v-else class="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowLeft, ArrowRight, Check, FileText, Link2, Paperclip, Plus } from 'lucide-vue-next'
import type { TaskDocument, TaskPriority, TaskStatus, DeadlineInfo } from '../../types/workspace'

const props = defineProps<{
  tasks: TaskDocument[]
  projectId?: string | null
  showProjectBadge?: boolean
}>()

const emit = defineEmits<{
  (e: 'select-task', task: TaskDocument): void
  (e: 'create-task', defaultStatus: TaskStatus): void
  (e: 'move-task', taskId: string, newStatus: TaskStatus): void
}>()

const dragOverColumn = ref('')
const draggedTaskId = ref('')

const columns = [
  {
    status: 'TODO' as TaskStatus,
    label: 'To Do',
    dotClass: 'bg-amber-400',
    emptyText: 'No tasks to do',
    prevStatus: null,
    prevLabel: '',
    nextStatus: 'DOING' as TaskStatus,
    nextLabel: 'Start'
  },
  {
    status: 'DOING' as TaskStatus,
    label: 'Doing / In Progress',
    dotClass: 'bg-sky-400',
    emptyText: 'Nothing in progress',
    prevStatus: 'TODO' as TaskStatus,
    prevLabel: 'Back',
    nextStatus: 'DONE' as TaskStatus,
    nextLabel: 'Complete'
  },
  {
    status: 'DONE' as TaskStatus,
    label: 'Done',
    dotClass: 'bg-emerald-400',
    emptyText: 'No completed tasks',
    prevStatus: 'DOING' as TaskStatus,
    prevLabel: 'Reopen',
    nextStatus: null,
    nextLabel: ''
  }
]

function columnTasks(status: TaskStatus): TaskDocument[] {
  return props.tasks
    .filter(t => t.status === status)
    .sort((a, b) => {
      if (a.position !== b.position) return a.position - b.position
      const aTime = a.deadline ? new Date(a.deadline).getTime() : Infinity
      const bTime = b.deadline ? new Date(b.deadline).getTime() : Infinity
      return aTime - bTime
    })
}

function handleDragStart(task: TaskDocument, event: DragEvent) {
  draggedTaskId.value = task.id
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', task.id)
  }
}

function handleDrop(newStatus: TaskStatus) {
  dragOverColumn.value = ''
  const taskId = draggedTaskId.value || ''
  if (!taskId) return
  const task = props.tasks.find(t => t.id === taskId)
  if (task && task.status !== newStatus) {
    emit('move-task', taskId, newStatus)
  }
  draggedTaskId.value = ''
}

function checklistTotal(task: TaskDocument): number {
  return task.checklist_progress?.total ?? (task.checklist || []).length
}

function checklistCompleted(task: TaskDocument): number {
  return task.checklist_progress?.completed ?? (task.checklist || []).filter(i => i.is_completed).length
}

function priorityClass(priority: TaskPriority): string {
  switch (priority) {
    case 'URGENT':
      return 'bg-zinc-900 text-rose-400 border-zinc-800'
    case 'HIGH':
      return 'bg-zinc-900 text-amber-400 border-zinc-800'
    case 'LOW':
      return 'bg-zinc-900 text-zinc-500 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}

function deadlineClass(info?: DeadlineInfo): string {
  if (!info) return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  switch (info.urgency) {
    case 'OVERDUE':
    case 'CRITICAL':
      return 'bg-zinc-900 text-rose-400 border-zinc-800'
    case 'WARNING':
    case 'ATTENTION':
      return 'bg-zinc-900 text-zinc-300 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-400 border-zinc-800'
  }
}
</script>
