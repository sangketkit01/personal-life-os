<template>
  <div class="space-y-4">
    <!-- Calendar Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <h3 class="text-sm font-semibold text-zinc-100 font-mono tracking-tight">{{ monthLabel }}</h3>
        <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
          {{ monthTasks.length }} tasks
        </span>
        <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-violet-300 border border-zinc-800">
          {{ monthEvents.length }} events
        </span>
      </div>

      <div class="flex items-center gap-2">
        <!-- View Toggle -->
        <div class="flex items-center gap-0.5 bg-zinc-900 border border-zinc-800 p-0.5 rounded-md">
          <button
            type="button"
            @click="viewMode = 'month'"
            class="px-2.5 py-1 rounded text-[11px] font-medium transition-colors"
            :class="viewMode === 'month' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'"
          >
            <LayoutGrid class="w-3 h-3 inline mr-1" />{{ t('cal.grid') }}
          </button>
          <button
            type="button"
            @click="viewMode = 'agenda'"
            class="px-2.5 py-1 rounded text-[11px] font-medium transition-colors"
            :class="viewMode === 'agenda' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'"
          >
            <List class="w-3 h-3 inline mr-1" />{{ t('cal.agenda') }}
          </button>
        </div>

        <!-- Navigation -->
        <div class="flex items-center gap-1">
          <button
            type="button"
            @click="shiftMonth(-1)"
            class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
            :title="t('cal.prevMonth')"
          >
            <ChevronLeft class="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            @click="goToday"
            class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-[11px] font-medium transition-colors"
          >
            {{ t('cal.today') }}
          </button>
          <button
            type="button"
            @click="shiftMonth(1)"
            class="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
            :title="t('cal.nextMonth')"
          >
            <ChevronRight class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>

    <!-- MONTH GRID -->
    <div v-if="viewMode === 'month'" class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 overflow-hidden">
      <!-- Weekday header -->
      <div class="grid grid-cols-7 border-b border-zinc-800/80 bg-zinc-900/40">
        <div
          v-for="day in WEEKDAYS"
          :key="day"
          class="px-2 py-2 text-[10px] font-mono uppercase tracking-wider text-zinc-500 text-center"
        >
          {{ day }}
        </div>
      </div>

      <!-- Day cells -->
      <div class="grid grid-cols-7">
        <div
          v-for="cell in calendarCells"
          :key="cell.key"
          class="min-h-[68px] sm:min-h-[92px] border-b border-r border-zinc-800/50 p-1 sm:p-1.5 group/cell relative transition-colors"
          :class="cell.isCurrentMonth ? 'bg-zinc-950/40' : 'bg-zinc-950/80'"
          @click="emit('create-on-date', cell.key)"
        >
          <!-- Day number -->
          <div class="flex items-center justify-between mb-1">
            <span
              class="text-[11px] font-mono w-5 h-5 flex items-center justify-center rounded-full"
              :class="cell.isToday
                ? 'bg-zinc-100 text-zinc-950 font-bold'
                : cell.isCurrentMonth ? 'text-zinc-400' : 'text-zinc-700'"
            >
              {{ cell.dayNumber }}
            </span>
            <button
              type="button"
              class="w-4 h-4 rounded bg-zinc-900 border border-zinc-800 text-zinc-500 items-center justify-center hidden group-hover/cell:flex hover:text-zinc-100 hover:border-zinc-600 transition-colors"
              :title="t('cal.addEntry')"
              @click.stop="emit('create-on-date', cell.key)"
            >
              <Plus class="w-2.5 h-2.5" />
            </button>
          </div>

          <!-- Event pills (standalone schedules, not tied to the task pipeline) -->
          <div class="space-y-1">
            <button
              v-for="es in cell.eventSegments.slice(0, 2)"
              :key="es.event.id"
              type="button"
              @click.stop="emit('select-event', es.event)"
              class="w-full text-left px-1.5 py-0.5 text-[10px] truncate flex items-center gap-1 border bg-violet-500/10 border-violet-500/30 text-violet-300 transition-colors hover:bg-violet-500/20"
              :class="{
                'rounded': es.seg === 'single',
                'rounded-l rounded-r-none': es.seg === 'start',
                'rounded-none': es.seg === 'mid',
                'rounded-r rounded-l-none': es.seg === 'end'
              }"
              :title="`${EVENT_TYPE_LABEL[es.event.event_type] || t('cal.event')}${es.event.is_all_day ? ' (' + t('cal.allDay') + ')' : ''}`"
            >
              <Clock v-if="!es.event.is_all_day && (es.seg === 'single' || es.seg === 'start')" class="w-2.5 h-2.5 shrink-0 hidden sm:inline" />
              <span class="truncate">{{ es.event.title }}</span>
            </button>

            <!-- Task pills -->
            <button
              v-for="task in cell.tasks.slice(0, cell.events.length > 0 ? 2 : 3)"
              :key="task.id"
              type="button"
              @click.stop="emit('select-task', task)"
              class="w-full text-left px-1.5 py-0.5 rounded text-[10px] truncate flex items-center gap-1 border transition-colors"
              :class="pillClass(task)"
              :title="task.title"
            >
              <span
                v-if="showProjectDot && task.project_color"
                class="w-1 h-1 rounded-full shrink-0"
                :style="{ backgroundColor: task.project_color }"
              />
              <span class="truncate" :class="{ 'line-through': task.status === 'DONE' }">{{ task.title }}</span>
            </button>

            <div
              v-if="cell.events.length + cell.tasks.length > 4"
              class="text-[9px] font-mono text-zinc-500 pl-1"
            >
              +{{ cell.events.length + cell.tasks.length - 4 }} more
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AGENDA LIST -->
    <div v-else class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 divide-y divide-zinc-800/50">
      <div
        v-if="agendaCount === 0"
        class="p-10 text-center text-xs font-mono text-zinc-600"
      >
        {{ t('cal.nothingScheduled') }}
      </div>

      <!-- Event rows -->
      <div
        v-for="item in eventAgendaItems"
        :key="'ev-' + item.event.id"
        class="px-4 py-2.5 flex items-center gap-3 hover:bg-zinc-900/40 transition-colors cursor-pointer"
        @click="emit('select-event', item.event)"
      >
        <div class="w-12 shrink-0 text-center">
          <div class="text-xs font-mono font-semibold text-zinc-200">{{ formatDay(item.dateKey) }}</div>
          <div class="text-[9px] font-mono uppercase text-zinc-500">{{ formatWeekday(item.dateKey) }}</div>
        </div>

        <div class="w-1 h-8 rounded-full shrink-0 bg-violet-400/70" />

        <div class="flex-1 min-w-0">
          <div class="text-xs font-medium text-zinc-100 truncate">{{ item.event.title }}</div>
          <div class="text-[10px] font-mono text-zinc-500 flex items-center gap-2">
            <span class="uppercase">{{ EVENT_TYPE_LABEL[item.event.event_type] || 'Event' }}</span>
            <span v-if="!item.event.is_all_day">{{ formatTime(item.event.start_at) }}</span>
            <span v-else>{{ t('cal.allDay') }}</span>
          </div>
        </div>

        <span class="text-[9px] font-mono px-1.5 py-0.5 rounded border uppercase shrink-0 bg-zinc-900 text-violet-300 border-violet-500/30">
          Event
        </span>
      </div>

      <!-- Task rows -->
      <div
        v-for="item in taskAgendaItems"
        :key="'tk-' + item.task.id + item.dateKey"
        class="px-4 py-2.5 flex items-center gap-3 hover:bg-zinc-900/40 transition-colors cursor-pointer"
        @click="emit('select-task', item.task)"
      >
        <div class="w-12 shrink-0 text-center">
          <div class="text-xs font-mono font-semibold text-zinc-200">{{ formatDay(item.dateKey) }}</div>
          <div class="text-[9px] font-mono uppercase text-zinc-500">{{ formatWeekday(item.dateKey) }}</div>
        </div>

        <div class="w-1 h-8 rounded-full shrink-0" :style="{ backgroundColor: agendaBarColor(item.task) }" />

        <div class="flex-1 min-w-0">
          <div class="text-xs font-medium text-zinc-100 truncate" :class="{ 'line-through text-zinc-500': item.task.status === 'DONE' }">
            {{ item.task.title }}
          </div>
          <div class="text-[10px] font-mono text-zinc-500 flex items-center gap-2">
            <span v-if="item.task.project_name">{{ item.task.project_name }}</span>
            <span v-if="item.task.deadline && item.dateKey === dateKeyOfDeadline(item.task)">
              {{ formatTime(item.task.deadline) }}
            </span>
          </div>
        </div>

        <span
          class="text-[9px] font-mono px-1.5 py-0.5 rounded border uppercase shrink-0"
          :class="statusPillClass(item.task.status)"
        >
          {{ item.task.status }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight, Clock, LayoutGrid, List, Plus } from 'lucide-vue-next'
import { t } from '../../i18n'
import type { CalendarEvent, CalendarEventType, TaskDocument, TaskStatus } from '../../types/workspace'

const props = defineProps<{
  tasks: TaskDocument[]
  events: CalendarEvent[]
  projectId?: string | null
  showProjectDot?: boolean
}>()

const emit = defineEmits<{
  (e: 'select-task', task: TaskDocument): void
  (e: 'select-event', event: CalendarEvent): void
  (e: 'create-on-date', dateStr: string): void
}>()

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MAX_SPAN_DAYS = 60

const EVENT_TYPE_LABEL: Record<CalendarEventType, string> = {
  APPOINTMENT: 'Appointment',
  MEETING: 'Meeting',
  REMINDER: 'Reminder',
  MILESTONE: 'Milestone',
  PERSONAL: 'Personal',
  OTHER: 'Other'
}

const viewMode = ref<'month' | 'agenda'>('month')
const cursor = ref(new Date())

const monthLabel = computed(() =>
  cursor.value.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
)

function toDateKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function dateKeyOfDeadline(task: TaskDocument): string {
  return task.deadline ? toDateKey(new Date(task.deadline)) : ''
}

/** All calendar dates a task occupies (start_date → deadline, capped). */
function taskDates(task: TaskDocument): Set<string> {
  const dates = new Set<string>()
  const start = task.start_date ? new Date(`${task.start_date}T00:00:00`) : null
  const end = task.deadline ? new Date(task.deadline) : null

  if (start && end && !isNaN(start.getTime()) && !isNaN(end.getTime())) {
    // Guard against legacy data with start_date > deadline:
    // the task must NEVER vanish - pin it to its deadline day instead.
    if (toDateKey(start) > toDateKey(end)) {
      dates.add(toDateKey(end))
      return dates
    }
    const cursorDate = new Date(start)
    let count = 0
    while (cursorDate <= end && count < MAX_SPAN_DAYS) {
      dates.add(toDateKey(cursorDate))
      cursorDate.setDate(cursorDate.getDate() + 1)
      count++
    }
  } else if (end && !isNaN(end.getTime())) {
    dates.add(toDateKey(end))
  } else if (start && !isNaN(start.getTime())) {
    dates.add(toDateKey(start))
  }
  return dates
}

/** All calendar dates an event occupies (start_at → end_at, capped). */
function eventDates(event: CalendarEvent): Set<string> {
  const dates = new Set<string>()
  const start = new Date(event.start_at)
  const end = event.end_at ? new Date(event.end_at) : null

  if (isNaN(start.getTime())) return dates

  if (end && !isNaN(end.getTime())) {
    const cursorDate = new Date(start)
    let count = 0
    while (cursorDate <= end && count < MAX_SPAN_DAYS) {
      dates.add(toDateKey(cursorDate))
      cursorDate.setDate(cursorDate.getDate() + 1)
      count++
    }
  } else {
    dates.add(toDateKey(start))
  }
  return dates
}

const monthTasks = computed(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const monthStart = new Date(year, month, 1)
  const monthEnd = new Date(year, month + 1, 0, 23, 59, 59)

  return props.tasks.filter(task => {
    for (const key of taskDates(task)) {
      const d = new Date(`${key}T12:00:00`)
      if (d >= monthStart && d <= monthEnd) return true
    }
    return false
  })
})

const monthEvents = computed(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const monthStart = new Date(year, month, 1)
  const monthEnd = new Date(year, month + 1, 0, 23, 59, 59)

  return props.events.filter(event => {
    for (const key of eventDates(event)) {
      const d = new Date(`${key}T12:00:00`)
      if (d >= monthStart && d <= monthEnd) return true
    }
    return false
  })
})

interface EventSegment {
  event: CalendarEvent
  seg: 'start' | 'mid' | 'end' | 'single'
}

interface CalendarCell {
  key: string
  dayNumber: number
  isCurrentMonth: boolean
  isToday: boolean
  tasks: TaskDocument[]
  events: CalendarEvent[]
  eventSegments: EventSegment[]
}

const calendarCells = computed<CalendarCell[]>(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const todayKey = toDateKey(new Date())

  const firstDay = new Date(year, month, 1)
  const gridStart = new Date(firstDay)
  gridStart.setDate(gridStart.getDate() - firstDay.getDay())

  const tasksByDate = new Map<string, TaskDocument[]>()
  for (const task of monthTasks.value) {
    for (const key of taskDates(task)) {
      if (!tasksByDate.has(key)) tasksByDate.set(key, [])
      tasksByDate.get(key)!.push(task)
    }
  }

  const eventsByDate = new Map<string, CalendarEvent[]>()
  const segmentsByDate = new Map<string, EventSegment[]>()
  for (const event of monthEvents.value) {
    const startKey = toDateKey(new Date(event.start_at))
    const endKey = event.end_at ? toDateKey(new Date(event.end_at)) : startKey
    for (const key of eventDates(event)) {
      if (!eventsByDate.has(key)) eventsByDate.set(key, [])
      eventsByDate.get(key)!.push(event)
      // One continuous bar across days: start cap, straight middle, end cap.
      const seg: EventSegment['seg'] =
        key === startKey && key === endKey ? 'single'
        : key === startKey ? 'start'
        : key === endKey ? 'end'
        : 'mid'
      if (!segmentsByDate.has(key)) segmentsByDate.set(key, [])
      segmentsByDate.get(key)!.push({ event, seg })
    }
  }

  const cells: CalendarCell[] = []
  for (let i = 0; i < 42; i++) {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    const key = toDateKey(d)
    cells.push({
      key,
      dayNumber: d.getDate(),
      isCurrentMonth: d.getMonth() === month,
      isToday: key === todayKey,
      tasks: (tasksByDate.get(key) || []).sort((a, b) => (a.deadline ? new Date(a.deadline).getTime() : 0) - (b.deadline ? new Date(b.deadline).getTime() : 0)),
      events: (eventsByDate.get(key) || []).sort((a, b) => a.start_at.localeCompare(b.start_at)),
      eventSegments: (segmentsByDate.get(key) || []).sort((a, b) => a.event.start_at.localeCompare(b.event.start_at))
    })
  }
  return cells
})

interface EventAgendaItem {
  dateKey: string
  event: CalendarEvent
}

interface TaskAgendaItem {
  dateKey: string
  task: TaskDocument
}

const eventAgendaItems = computed<EventAgendaItem[]>(() => {
  const items: EventAgendaItem[] = []
  for (const event of monthEvents.value) {
    for (const key of eventDates(event)) {
      const d = new Date(`${key}T12:00:00`)
      if (d.getMonth() === cursor.value.getMonth() && d.getFullYear() === cursor.value.getFullYear()) {
        items.push({ dateKey: key, event })
      }
    }
  }
  return items.sort((a, b) => a.dateKey.localeCompare(b.dateKey))
})

const taskAgendaItems = computed<TaskAgendaItem[]>(() => {
  const items: TaskAgendaItem[] = []
  for (const task of monthTasks.value) {
    for (const key of taskDates(task)) {
      const d = new Date(`${key}T12:00:00`)
      if (d.getMonth() === cursor.value.getMonth() && d.getFullYear() === cursor.value.getFullYear()) {
        items.push({ dateKey: key, task })
      }
    }
  }
  return items.sort((a, b) => a.dateKey.localeCompare(b.dateKey))
})

const agendaCount = computed(() => eventAgendaItems.value.length + taskAgendaItems.value.length)

function shiftMonth(delta: number) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

function goToday() {
  cursor.value = new Date()
}

function formatDay(dateKey: string): string {
  return new Date(`${dateKey}T12:00:00`).getDate().toString().padStart(2, '0')
}

function formatWeekday(dateKey: string): string {
  return new Date(`${dateKey}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short' })
}

function formatTime(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

function isOverdue(task: TaskDocument): boolean {
  return (
    task.status !== 'DONE' &&
    task.status !== 'ARCHIVED' &&
    !!task.deadline &&
    new Date(task.deadline) < new Date()
  )
}

function pillClass(task: TaskDocument): string {
  if (isOverdue(task)) return 'bg-zinc-900 border-zinc-700 text-rose-400'
  switch (task.status) {
    case 'DONE':
      return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
    case 'DOING':
      return 'bg-sky-500/10 border-sky-500/30 text-sky-300'
    default:
      return 'bg-zinc-900 border-zinc-800 text-zinc-300'
  }
}

function statusPillClass(status: TaskStatus): string {
  switch (status) {
    case 'DONE':
      return 'bg-zinc-900 text-emerald-400 border-zinc-800'
    case 'DOING':
      return 'bg-zinc-900 text-sky-300 border-zinc-800'
    case 'ARCHIVED':
      return 'bg-zinc-900 text-zinc-500 border-zinc-800'
    default:
      return 'bg-zinc-900 text-zinc-300 border-zinc-800'
  }
}

function agendaBarColor(task: TaskDocument): string {
  if (isOverdue(task)) return '#fb7185'
  if (task.status === 'DONE') return '#34d399'
  if (task.status === 'DOING') return '#38bdf8'
  return '#fbbf24'
}
</script>
