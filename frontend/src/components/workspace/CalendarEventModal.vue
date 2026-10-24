<template>
  <div
    v-if="isOpen && event"
    class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-sans"
    @click.self="emit('close')"
  >
    <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-5 shadow-2xl relative">
      <button
        @click="emit('close')"
        class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <X class="w-4 h-4" />
      </button>

      <div class="flex items-center gap-2.5 mb-1">
        <span class="w-7 h-7 rounded-lg bg-violet-500/10 border border-violet-500/30 flex items-center justify-center">
          <CalendarClock class="w-3.5 h-3.5 text-violet-300" />
        </span>
        <h3 class="text-sm font-semibold text-zinc-100">Edit Schedule</h3>
      </div>
      <p class="text-xs text-zinc-500 mb-4">Standalone calendar entry — not part of the Kanban pipeline.</p>

      <div class="space-y-3">
        <input
          v-model="form.title"
          type="text"
          placeholder="Event title"
          class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600"
        />

        <div class="grid grid-cols-2 gap-3">
          <select
            v-model="form.event_type"
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
            v-model="form.project"
            class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
          >
            <option :value="null">No project</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Date</label>
            <input
              v-model="form.date"
              type="date"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
            />
          </div>
          <div>
            <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Time</label>
            <input
              v-model="form.time"
              type="time"
              :disabled="form.is_all_day"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono disabled:opacity-40"
            />
          </div>
        </div>

        <label class="flex items-center gap-2 px-1 cursor-pointer w-fit">
          <input v-model="form.is_all_day" type="checkbox" class="accent-zinc-100" />
          <span class="text-xs text-zinc-300">All day</span>
        </label>

        <textarea
          v-model="form.notes"
          rows="3"
          placeholder="Notes..."
          class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600 resize-y"
        />
      </div>

      <div class="flex items-center justify-between mt-5 pt-3 border-t border-zinc-800/80">
        <button
          type="button"
          @click="showDeleteConfirm = true"
          class="px-2.5 py-1.5 rounded-md text-xs font-medium text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/30 transition-colors flex items-center gap-1.5"
        >
          <Trash2 class="w-3.5 h-3.5" /> Delete
        </button>

        <div class="flex items-center gap-2.5">
          <button
            type="button"
            @click="emit('close')"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            @click="submit"
            class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors shadow-sm"
          >
            Save Changes
          </button>
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
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
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
const form = reactive({
  title: '',
  event_type: 'APPOINTMENT' as CalendarEventType,
  project: null as string | null,
  date: '',
  time: '09:00',
  is_all_day: false,
  notes: ''
})

function toLocalParts(iso: string): { date: string; time: string } {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return { date: '', time: '09:00' }
  const pad = (n: number) => String(n).padStart(2, '0')
  return {
    date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
}

watch(
  () => [props.isOpen, props.event?.id],
  ([open]) => {
    if (open && props.event) {
      const { date, time } = toLocalParts(props.event.start_at)
      form.title = props.event.title
      form.event_type = props.event.event_type
      form.project = props.event.project
      form.date = date
      form.time = time
      form.is_all_day = props.event.is_all_day
      form.notes = props.event.notes || ''
    }
  },
  { immediate: true }
)

async function submit() {
  if (!props.event) return
  const title = form.title.trim()
  if (!title) {
    toast.error('Event title is required')
    return
  }
  if (!form.date) {
    toast.error('Event date is required')
    return
  }
  try {
    const updated = await workspaceStore.updateEvent(props.event.id, {
      title,
      event_type: form.event_type,
      project: props.fixedProjectId || form.project,
      start_at: form.is_all_day
        ? `${form.date}T00:00:00`
        : `${form.date}T${form.time || '09:00'}:00`,
      is_all_day: form.is_all_day,
      notes: form.notes
    })
    toast.success('Schedule updated')
    emit('updated', updated)
  } catch {
    toast.error('Failed to update schedule')
  }
}

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
