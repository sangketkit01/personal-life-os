<template>
  <Teleport to="body">
    <!-- Non-Blocking Right Docked Inspector (calendar grid stays interactive) -->
    <div
      v-if="isOpen && event"
      class="fixed top-0 right-0 bottom-0 z-40 w-full sm:w-[380px] pointer-events-none flex flex-col"
    >
      <div class="pointer-events-auto h-full w-full bg-zinc-950/95 backdrop-blur-xl border-l border-zinc-800 shadow-[-16px_0_40px_rgba(0,0,0,0.65)] flex flex-col transition-transform duration-200">
        <!-- Header -->
        <div class="px-4 py-3 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
          <div class="flex items-center gap-2 min-w-0">
            <span class="w-7 h-7 rounded-lg bg-violet-500/10 border border-violet-500/30 flex items-center justify-center shrink-0">
              <CalendarClock class="w-3.5 h-3.5 text-violet-300" />
            </span>
            <div class="min-w-0">
              <h3 class="text-xs font-semibold text-zinc-100">Edit Schedule</h3>
              <p class="text-[10px] font-mono text-zinc-500">Standalone entry • not in Kanban</p>
            </div>
          </div>
          <button
            @click="emit('close')"
            class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900 transition-colors"
            title="Close (Esc)"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto p-4 space-y-3.5">
          <input
            v-model="form.title"
            type="text"
            placeholder="Event title"
            class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600"
            @input="markDirty"
          />

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Type</label>
              <select
                v-model="form.event_type"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
                @change="markDirty"
              >
                <option value="APPOINTMENT">Appointment</option>
                <option value="MEETING">Meeting</option>
                <option value="REMINDER">Reminder</option>
                <option value="MILESTONE">Milestone</option>
                <option value="PERSONAL">Personal</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <div v-if="!fixedProjectId">
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Project</label>
              <select
                v-model="form.project"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
                @change="markDirty"
              >
                <option :value="null">No project</option>
                <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Date</label>
              <input
                v-model="form.date"
                type="date"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
                @change="markDirty"
              />
            </div>
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Start Time</label>
              <input
                v-model="form.time"
                type="time"
                :disabled="form.is_all_day"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono disabled:opacity-40"
                @change="markDirty"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">End Time (optional)</label>
              <input
                v-model="form.endTime"
                type="time"
                :disabled="form.is_all_day"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono disabled:opacity-40"
                @change="markDirty"
              />
            </div>
            <label class="flex items-center gap-2 px-1 mt-5 cursor-pointer w-fit">
              <input v-model="form.is_all_day" type="checkbox" class="accent-zinc-100" @change="markDirty" />
              <span class="text-xs text-zinc-300">All day</span>
            </label>
          </div>

          <textarea
            v-model="form.notes"
            rows="4"
            placeholder="Notes..."
            class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600 resize-y"
            @input="markDirty"
          />
        </div>

        <!-- Footer -->
        <div class="px-4 py-3 border-t border-zinc-800/80 flex items-center justify-between shrink-0 bg-zinc-950">
          <button
            type="button"
            @click="showDeleteConfirm = true"
            class="px-2.5 py-1.5 rounded-md text-xs font-medium text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/30 transition-colors flex items-center gap-1.5"
          >
            <Trash2 class="w-3.5 h-3.5" /> Delete
          </button>

          <div class="flex items-center gap-2">
            <span class="text-[10px] font-mono" :class="dirty ? 'text-amber-400/80' : 'text-emerald-400/80'">
              {{ saving ? 'Saving...' : dirty ? 'Unsaved changes' : 'All changes saved' }}
            </span>
            <button
              type="button"
              @click="saveNow()"
              class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmModal
      :is-open="showDeleteConfirm"
      title="Delete this schedule?"
      :message="`'${event?.title}' will be removed from the calendar.`"
      confirm-text="Delete Event"
      @confirm="handleDelete"
      @cancel="showDeleteConfirm = false"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { CalendarClock, Trash2, X } from 'lucide-vue-next'
import ConfirmModal from '../common/ConfirmModal.vue'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import type { CalendarEvent, CalendarEventType, WorkspaceProject } from '../../types/workspace'

const props = defineProps<{
  isOpen: boolean
  event: CalendarEvent | null
  projects: WorkspaceProject[]
  fixedProjectId?: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated', event: CalendarEvent): void
  (e: 'deleted', eventId: string): void
}>()

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const showDeleteConfirm = ref(false)
const dirty = ref(false)
const saving = ref(false)
let loadedEventId = ''

const form = reactive({
  title: '',
  event_type: 'APPOINTMENT' as CalendarEventType,
  project: null as string | null,
  date: '',
  time: '09:00',
  endTime: '',
  is_all_day: false,
  notes: ''
})

/** Build a timezone-aware ISO string from local date + time inputs. */
function buildLocalIso(dateStr: string, timeStr: string): string {
  if (!dateStr) return ''
  const [y, m, d] = dateStr.split('-').map(Number)
  const [hh, mm] = (timeStr || '00:00').split(':').map(Number)
  const local = new Date(y, (m || 1) - 1, d || 1, hh || 0, mm || 0, 0, 0)
  return local.toISOString()
}

function toLocalParts(iso: string): { date: string; time: string } {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return { date: '', time: '09:00' }
  const pad = (n: number) => String(n).padStart(2, '0')
  return {
    date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
}

function syncFromEvent(event: CalendarEvent) {
  const { date, time } = toLocalParts(event.start_at)
  const endDate = event.end_at ? toLocalParts(event.end_at) : null
  form.title = event.title
  form.event_type = event.event_type
  form.project = event.project
  form.date = date
  form.time = event.is_all_day ? '12:00' : time
  form.endTime = endDate && endDate.date === date ? endDate.time : ''
  form.is_all_day = event.is_all_day
  form.notes = event.notes || ''
  dirty.value = false
}

function markDirty() {
  dirty.value = true
}

function buildPayload(): Record<string, any> {
  return {
    title: form.title.trim() || 'Untitled',
    event_type: form.event_type,
    project: props.fixedProjectId || form.project,
    // Local-time ISO with explicit timezone - never a naive midnight UTC shift
    start_at: buildLocalIso(form.date, form.is_all_day ? '12:00' : (form.time || '09:00')),
    end_at: form.is_all_day || !form.endTime ? null : buildLocalIso(form.date, form.endTime),
    is_all_day: form.is_all_day,
    notes: form.notes
  }
}

watch(
  () => [props.isOpen, props.event?.id],
  async ([open, eventId]) => {
    if (open && props.event) {
      // Flush unsaved changes for the previous event before switching
      if (loadedEventId && loadedEventId !== String(eventId) && dirty.value) {
        await saveNowFor(loadedEventId)
      }
      loadedEventId = String(eventId)
      syncFromEvent(props.event)
    }
    if (!open) {
      loadedEventId = ''
    }
  },
  { immediate: true }
)

async function saveNowFor(eventId: string) {
  saving.value = true
  try {
    const updated = await workspaceStore.updateEvent(eventId, buildPayload())
    dirty.value = false
    emit('updated', updated)
  } catch {
    toast.error('Failed to update schedule')
  } finally {
    saving.value = false
  }
}

async function saveNow() {
  if (!props.event) return
  await saveNowFor(props.event.id)
}

function handleEscape(event: KeyboardEvent) {
  if (!props.isOpen) return
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleEscape)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleEscape)
})

async function handleDelete() {
  if (!props.event) return
  const eventId = props.event.id
  showDeleteConfirm.value = false
  emit('close')
  try {
    await workspaceStore.deleteEvent(eventId)
    toast.info('Schedule deleted')
    emit('deleted', eventId)
  } catch {
    toast.error('Failed to delete schedule')
  }
}
</script>
