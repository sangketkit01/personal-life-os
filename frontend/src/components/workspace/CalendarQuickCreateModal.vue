<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4 overflow-hidden font-sans"
    @click.self="emit('close')"
  >
    <div class="relative bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md max-h-[calc(100dvh-1rem)] sm:max-h-[calc(100dvh-2rem)] flex flex-col shadow-2xl overflow-hidden">
      <!-- Fixed Header -->
      <div class="shrink-0 px-4 sm:px-5 py-3.5 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h3 class="text-sm font-semibold text-zinc-100">New Entry</h3>
          <p v-if="initialDate" class="text-[11px] font-mono text-zinc-500">Scheduled for {{ initialDate }}</p>
          <p v-else class="text-xs text-zinc-500">Add a Kanban task or a standalone schedule</p>
        </div>
        <button
          @click="emit('close')"
          class="text-zinc-500 hover:text-zinc-300 transition-colors p-1 cursor-pointer"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4 sm:p-5 space-y-3.5">
        <!-- Type Toggle -->
        <div class="flex items-center gap-0.5 bg-zinc-900 border border-zinc-800 p-0.5 rounded-md w-fit">
        <button
          type="button"
          @click="entryType = 'TASK'"
          class="px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1.5"
          :class="entryType === 'TASK' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'"
        >
          <Columns3 class="w-3 h-3" /> Task
        </button>
        <button
          type="button"
          @click="entryType = 'EVENT'"
          class="px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1.5"
          :class="entryType === 'EVENT' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'"
        >
          <CalendarClock class="w-3 h-3" /> Event
        </button>
      </div>

      <!-- ===== TASK fields ===== -->
      <div v-if="entryType === 'TASK'" class="space-y-3">
        <input
          ref="titleInput"
          v-model="taskForm.title"
          type="text"
          placeholder="What needs to be done?"
          class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600"
          @keydown.enter.prevent="submit"
        />
        <div class="grid grid-cols-2 gap-3">
          <select
            v-model="taskForm.status"
            class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
          >
            <option value="TODO">To Do</option>
            <option value="DOING">Doing / In Progress</option>
            <option value="DONE">Done</option>
          </select>
          <select
            v-model="taskForm.priority"
            class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
          >
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="URGENT">Urgent</option>
          </select>
        </div>
        <select
          v-if="!fixedProjectId"
          v-model="taskForm.project"
          class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
        >
          <option :value="null">No project</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <input
          v-model="taskForm.deadline"
          type="datetime-local"
          class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
        />
      </div>

      <!-- ===== EVENT fields ===== -->
      <div v-else class="space-y-3">
        <input
          ref="titleInput"
          v-model="eventForm.title"
          type="text"
          placeholder="e.g. Dentist appointment, client call..."
          class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600"
          @keydown.enter.prevent="submit"
        />
        <div class="grid grid-cols-2 gap-3">
          <select
            v-model="eventForm.event_type"
            class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
          >
            <option value="APPOINTMENT">Appointment</option>
            <option value="MEETING">Meeting</option>
            <option value="REMINDER">Reminder</option>
            <option value="MILESTONE">Milestone</option>
            <option value="PERSONAL">Personal</option>
            <option value="OTHER">Other</option>
          </select>
          <select
            v-if="!fixedProjectId"
            v-model="eventForm.project"
            class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
          >
            <option :value="null">No project</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <input
            v-model="eventForm.date"
            type="date"
            class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
          />
          <input
            v-model="eventForm.time"
            type="time"
            :disabled="eventForm.is_all_day"
            class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono disabled:opacity-40"
          />
        </div>
        <div>
          <p class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 mb-1">Ends (optional — leave blank for same-day)</p>
          <div class="grid grid-cols-2 gap-3">
            <input
              v-model="eventForm.endDate"
              type="date"
              :disabled="eventForm.is_all_day"
              class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono disabled:opacity-40"
            />
            <input
              v-model="eventForm.endTime"
              type="time"
              :disabled="eventForm.is_all_day"
              class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono disabled:opacity-40"
            />
          </div>
        </div>
        <label class="flex items-center gap-2 px-1 cursor-pointer w-fit">
          <input v-model="eventForm.is_all_day" type="checkbox" class="accent-zinc-100" />
          <span class="text-xs text-zinc-300">All day</span>
        </label>
        <textarea
          v-model="eventForm.notes"
          rows="2"
          placeholder="Notes (optional)"
          class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600 resize-y"
        />
      </div>
      </div>

      <!-- Sticky Footer -->
      <div class="shrink-0 p-4 border-t border-zinc-800/80 bg-zinc-950/90 flex items-center justify-end gap-2.5">
        <button
          type="button"
          @click="emit('close')"
          class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors cursor-pointer"
        >
          Cancel
        </button>
        <button
          type="button"
          @click="submit"
          class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors shadow-sm cursor-pointer"
        >
          Create {{ entryType === 'TASK' ? 'Task' : 'Event' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import { CalendarClock, Columns3, X } from 'lucide-vue-next'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import { useBodyScrollLock } from '../../composables/useBodyScrollLock'
import type { CalendarEvent, TaskDocument, TaskStatus, WorkspaceProject } from '../../types/workspace'

const props = defineProps<{
  isOpen: boolean
  projects: WorkspaceProject[]
  fixedProjectId?: string | null
  initialDate?: string | null
  initialStatus?: TaskStatus
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created-task', task: TaskDocument): void
  (e: 'created-event', event: CalendarEvent): void
}>()

useBodyScrollLock(() => props.isOpen)

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const entryType = ref<'TASK' | 'EVENT'>('TASK')
const titleInput = ref<HTMLInputElement | null>(null)

const taskForm = reactive({
  title: '',
  status: 'TODO' as TaskStatus,
  priority: 'MEDIUM',
  project: null as string | null,
  deadline: ''
})

const eventForm = reactive({
  title: '',
  event_type: 'APPOINTMENT',
  project: null as string | null,
  date: '',
  time: '09:00',
  endDate: '',
  endTime: '',
  is_all_day: false,
  notes: ''
})

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      entryType.value = 'TASK'
      taskForm.title = ''
      taskForm.status = props.initialStatus || 'TODO'
      taskForm.priority = 'MEDIUM'
      taskForm.project = props.fixedProjectId || null
      taskForm.deadline = props.initialDate ? `${props.initialDate}T17:00` : ''

      eventForm.title = ''
      eventForm.event_type = 'APPOINTMENT'
      eventForm.project = props.fixedProjectId || null
      eventForm.date = props.initialDate || ''
      eventForm.time = ''
      eventForm.endDate = ''
      eventForm.endTime = ''
      eventForm.is_all_day = false
      eventForm.notes = ''

      nextTick(() => titleInput.value?.focus())
    }
  }
)

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

/** Build a timezone-aware ISO string from local date + time inputs. */
function buildLocalIso(dateStr: string, timeStr: string): string {
  if (!dateStr) return ''
  const [y, m, d] = dateStr.split('-').map(Number)
  const [hh, mm] = (timeStr || '00:00').split(':').map(Number)
  return new Date(y, (m || 1) - 1, d || 1, hh || 0, mm || 0, 0, 0).toISOString()
}

async function submit() {
  if (entryType.value === 'TASK') {
    const title = taskForm.title.trim()
    if (!title) {
      toast.error('Task title is required')
      return
    }
    try {
      const created = await workspaceStore.createTask({
        title,
        status: taskForm.status,
        priority: taskForm.priority,
        project: props.fixedProjectId || taskForm.project,
        // A date click schedules the DEADLINE only - never a start_date range,
        // so rescheduled single-day tasks stay single-day on the calendar.
        start_date: null,
        deadline: taskForm.deadline ? new Date(taskForm.deadline).toISOString() : null
      })
      toast.success('Task created')
      emit('created-task', created)
    } catch {
      toast.error('Failed to create task')
    }
    return
  }

  const title = eventForm.title.trim()
  if (!title) {
    toast.error('Event title is required')
    return
  }
  const date = eventForm.date || todayIso()
  const endDate = eventForm.endDate || date
  if (endDate < date) {
    toast.error('End date cannot be before the start date')
    return
  }
  const hasEnd = !eventForm.is_all_day && (eventForm.endDate !== '' || eventForm.endTime !== '')
  try {
    const created = await workspaceStore.createEvent({
      title,
      event_type: eventForm.event_type,
      project: props.fixedProjectId || eventForm.project,
      start_at: buildLocalIso(date, eventForm.is_all_day ? '12:00' : (eventForm.time || '09:00')),
      end_at: hasEnd ? buildLocalIso(endDate, eventForm.endTime || eventForm.time || '09:00') : null,
      is_all_day: eventForm.is_all_day,
      notes: eventForm.notes
    })
    toast.success('Event added to calendar')
    emit('created-event', created)
  } catch {
    toast.error('Failed to create event')
  }
}
</script>
