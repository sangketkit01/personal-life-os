<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- ===== Top Metadata Bar (Non-overlapping shrink-0 header) ===== -->
    <div class="shrink-0 px-4 py-2 border-b border-zinc-800/80 flex items-center gap-2 flex-wrap bg-zinc-950/95">
      <!-- Folder selector -->
      <div class="flex items-center gap-1.5 bg-zinc-900/70 border border-zinc-800 hover:border-zinc-700 rounded-md px-2 py-1 transition-colors">
        <Folder class="w-3 h-3 text-zinc-400 shrink-0" />
        <select
          :value="note.folder || ''"
          class="bg-transparent text-[11px] text-zinc-200 outline-none cursor-pointer max-w-[140px]"
          title="Move note to folder"
          @change="setNoteFolder(($event.target as HTMLSelectElement).value || null)"
        >
          <option value="" class="bg-zinc-950 text-zinc-300">No Folder (All Notes)</option>
          <option v-for="folder in workspaceStore.folders" :key="folder.id" :value="folder.id" class="bg-zinc-950 text-zinc-200">
            {{ folder.name }}
          </option>
        </select>
      </div>

      <span class="w-px h-4 bg-zinc-800/80" />

      <!-- Color accent picker -->
      <div class="flex items-center gap-1" title="Note card accent color">
        <button
          v-for="c in NOTE_COLORS"
          :key="c.key"
          type="button"
          class="w-3.5 h-3.5 rounded-full border-2 transition-transform"
          :class="note.color === c.key ? 'scale-110 border-zinc-100' : 'border-transparent opacity-75 hover:opacity-100'"
          :style="{ backgroundColor: c.dot }"
          :title="c.label"
          @click="setNoteColor(c.key)"
        />
      </div>

      <span class="w-px h-4 bg-zinc-800/80" />

      <!-- Pin -->
      <button
        type="button"
        class="p-1.5 rounded-md transition-colors"
        :class="note.is_pinned ? 'text-amber-400 bg-amber-500/10' : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60'"
        :title="note.is_pinned ? 'Unpin note' : 'Pin to top'"
        @click="togglePin"
      >
        <Pin class="w-3.5 h-3.5" :class="{ 'fill-amber-400': note.is_pinned }" />
      </button>

      <!-- Lock / Unlock -->
      <button
        type="button"
        class="p-1.5 rounded-md transition-colors"
        :class="note.is_locked ? 'text-amber-400/90 bg-amber-500/10' : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60'"
        :title="note.is_locked ? 'Remove PIN lock' : 'Lock note with PIN'"
        @click="note.is_locked ? openLockModal('unlock') : openLockModal('set')"
      >
        <Unlock v-if="note.is_locked" class="w-3.5 h-3.5" />
        <Lock v-else class="w-3.5 h-3.5" />
      </button>

      <!-- Copy to Workspace Project -->
      <div class="relative">
        <button
          type="button"
          class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60 transition-colors"
          title="Send copy to a Workspace Project"
          @click="showCopyPopover = !showCopyPopover"
        >
          <FolderKanban class="w-3.5 h-3.5" />
        </button>

        <div
          v-if="showCopyPopover"
          class="absolute z-30 top-full mt-1 left-0 w-56 rounded-lg bg-zinc-950 border border-zinc-700/80 shadow-2xl p-1 max-h-56 overflow-y-auto"
        >
          <div class="px-2 py-1 text-[9px] font-mono uppercase text-zinc-500">Copy to Workspace Project</div>
          <button
            v-for="project in workspaceStore.projects"
            :key="project.id"
            type="button"
            class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-xs text-zinc-300 hover:bg-zinc-900 transition-colors"
            @click="copyToProject(project.id)"
          >
            <span class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: project.color }" />
            <span class="truncate">{{ project.name }}</span>
          </button>
          <div v-if="workspaceStore.projects.length === 0" class="px-2 py-2 text-[11px] text-zinc-500 font-mono">
            No workspace projects yet
          </div>
        </div>
      </div>

      <!-- Move to trash -->
      <button
        type="button"
        class="p-1.5 rounded-md text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
        title="Move note to trash"
        @click="moveToTrash"
      >
        <Trash2 class="w-3.5 h-3.5" />
      </button>

      <!-- Save status & instant save button -->
      <div class="ml-auto flex items-center gap-2">
        <button
          v-if="saveState === 'dirty'"
          type="button"
          class="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-[10px] font-mono text-zinc-200 transition-colors"
          @click="flushAutosave"
        >
          Save now
        </button>
        <span class="text-[10px] font-mono" :class="saveStateClass">{{ saveStateText }}</span>
      </div>
    </div>

    <!-- ===== Locked Guard Screen ===== -->
    <div v-if="locked" class="flex-1 flex flex-col items-center justify-center gap-4 p-10 text-center">
      <div class="w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center">
        <Lock class="w-6 h-6 text-zinc-400" />
      </div>
      <div>
        <p class="text-sm font-medium text-zinc-200">This note is locked</p>
        <p class="text-[11px] text-zinc-500 mt-1">Enter your 4–6 digit PIN to view or edit</p>
      </div>
      <form class="flex items-center gap-2" @submit.prevent="verifyInlinePin">
        <input
          ref="inlinePinInput"
          v-model="inlinePin"
          type="password"
          inputmode="numeric"
          maxlength="6"
          placeholder="••••"
          class="w-40 bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600 text-center font-mono tracking-[0.4em]"
        />
        <button type="submit" class="px-3 py-2 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors">
          Unlock
        </button>
      </form>
    </div>

    <!-- ===== Scrollable Editor Canvas ===== -->
    <div v-else class="flex-1 overflow-y-auto flex flex-col min-h-0">
      <!-- Clean Note Header: Icon Popover + Large Title + Tag Pills -->
      <div class="px-5 pt-4 pb-2 space-y-2">
        <div class="flex items-center gap-2.5">
          <!-- Compact Icon Picker Popover -->
          <div class="relative shrink-0">
            <button
              type="button"
              class="w-8 h-8 rounded-lg bg-zinc-900/70 hover:bg-zinc-800 border border-zinc-800/90 flex items-center justify-center text-zinc-300 transition-colors"
              title="Change note icon"
              @click="showIconPicker = !showIconPicker"
            >
              <component :is="currentIcon" class="w-4 h-4" />
            </button>
            <div
              v-if="showIconPicker"
              class="absolute z-30 top-full mt-1.5 left-0 p-1.5 rounded-lg bg-zinc-950 border border-zinc-700/80 shadow-2xl grid grid-cols-4 gap-1 w-36"
            >
              <button
                v-for="preset in NOTE_ICON_PRESETS"
                :key="preset.key"
                type="button"
                class="w-7 h-7 rounded-md flex items-center justify-center transition-colors"
                :class="editorIcon === preset.key ? 'bg-zinc-800 ring-1 ring-zinc-500 text-zinc-100' : 'hover:bg-zinc-900 text-zinc-400'"
                :title="preset.label"
                @click="selectIcon(preset.key)"
              >
                <component :is="preset.icon" class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- Large Title Input -->
          <input
            ref="titleInput"
            v-model="editorTitle"
            type="text"
            placeholder="Note title..."
            class="flex-1 bg-transparent border-none outline-none text-xl font-semibold text-zinc-100 placeholder-zinc-600 min-w-0"
          />
        </div>

        <!-- Inline Tag Chips + Quick Tag Adder -->
        <div class="flex items-center gap-1.5 flex-wrap pl-0.5">
          <span
            v-for="tag in editorTags"
            :key="tag"
            class="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-zinc-900 text-zinc-300 border border-zinc-800"
          >
            #{{ tag }}
            <button
              type="button"
              class="text-zinc-500 hover:text-zinc-200 transition-colors"
              title="Remove tag"
              @click="removeTag(tag)"
            >
              <X class="w-2.5 h-2.5" />
            </button>
          </span>

          <div class="inline-flex items-center gap-1">
            <Tag class="w-3 h-3 text-zinc-600" />
            <input
              v-model="newTagDraft"
              type="text"
              placeholder="Add tag + Enter..."
              class="bg-transparent text-[11px] font-mono text-zinc-300 placeholder-zinc-600 outline-none w-28 focus:w-36 transition-all"
              @keydown.enter.prevent="commitTagDraft"
              @keydown.,.prevent="commitTagDraft"
              @blur="commitTagDraft"
            />
          </div>
        </div>
      </div>

      <!-- Rich Block Editor (Toolbar + Content) -->
      <div class="px-5 pb-6 flex-1">
        <NotionBlockEditor v-model="editorBlocks" :upload-target-id="note.id" />
      </div>

      <!-- Bottom Status Bar -->
      <div class="mt-auto shrink-0 px-5 py-2 border-t border-zinc-800/60 flex items-center justify-between text-[10px] font-mono text-zinc-500 bg-zinc-950/60">
        <div class="flex items-center gap-3">
          <span>{{ stats.words }} words</span>
          <span>{{ stats.chars }} chars</span>
          <span>{{ stats.blocks }} blocks</span>
        </div>
        <span>Updated {{ lastEdited }}</span>
      </div>
    </div>

    <!-- ===== Lock / Unlock PIN Modal ===== -->
    <div
      v-if="showLockModal"
      class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-sans"
      @click.self="showLockModal = false"
    >
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-sm p-5 shadow-2xl relative">
        <button @click="showLockModal = false" class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors">
          <X class="w-4 h-4" />
        </button>

        <div class="flex items-center gap-3 mb-4">
          <div class="w-9 h-9 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center">
            <Lock class="w-4 h-4 text-zinc-300" />
          </div>
          <div>
            <h3 class="text-sm font-semibold text-zinc-100">
              {{ lockModalMode === 'set' ? 'Lock This Note' : 'Remove Lock' }}
            </h3>
            <p class="text-[11px] text-zinc-500 mt-0.5">
              {{ lockModalMode === 'set' ? 'Protect with a 4-6 digit PIN' : 'Enter your PIN to remove the lock' }}
            </p>
          </div>
        </div>

        <div class="space-y-3">
          <input
            ref="pinModalInput"
            v-model="pinForm.pin"
            type="password"
            inputmode="numeric"
            maxlength="6"
            placeholder="PIN (4-6 digits)"
            class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600 text-center font-mono tracking-[0.4em]"
          />
          <input
            v-if="lockModalMode === 'set'"
            v-model="pinForm.confirm"
            type="password"
            inputmode="numeric"
            maxlength="6"
            placeholder="Confirm PIN"
            class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600 text-center font-mono tracking-[0.4em]"
          />
        </div>

        <div class="flex items-center justify-end gap-2.5 mt-5 pt-3 border-t border-zinc-800/80">
          <button type="button" @click="showLockModal = false" class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors">
            Cancel
          </button>
          <button type="button" @click="submitLockModal" class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors">
            {{ lockModalMode === 'set' ? 'Lock Note' : 'Remove Lock' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import {
  Folder,
  FolderKanban,
  Lock,
  Unlock,
  Pin,
  Tag,
  Trash2,
  X
} from 'lucide-vue-next'
import NotionBlockEditor from '../workspace/NotionBlockEditor.vue'
import { NOTE_ICON_PRESETS, iconComponentFor } from '../../utils/iconPresets'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import { stripHtml } from '../../utils/richText'
import type { Note, NoteBlock, NoteColor } from '../../types/workspace'

const props = defineProps<{
  note: Note
  isVerified: boolean
}>()

const emit = defineEmits<{
  (e: 'verified', noteId: string): void
  (e: 'trashed', noteId: string): void
}>()

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

const NOTE_COLORS: Array<{ key: NoteColor; label: string; dot: string }> = [
  { key: 'DEFAULT', label: 'Default', dot: '#3f3f46' },
  { key: 'AMBER', label: 'Amber', dot: '#fbbf24' },
  { key: 'EMERALD', label: 'Emerald', dot: '#34d399' },
  { key: 'SKY', label: 'Sky', dot: '#38bdf8' },
  { key: 'VIOLET', label: 'Violet', dot: '#a78bfa' },
  { key: 'ROSE', label: 'Rose', dot: '#fb7185' }
]

// ===== Editor state (synced from the active note) =====
const editorTitle = ref('')
const editorIcon = ref('file-text')
const editorTags = ref<string[]>([])
const newTagDraft = ref('')
const editorBlocks = ref<NoteBlock[]>([])
const saveState = ref<'saved' | 'dirty' | 'saving'>('saved')
let saveTimer: ReturnType<typeof setTimeout> | null = null
let suppressSyncWatch = false

const titleInput = ref<HTMLInputElement | null>(null)
const showIconPicker = ref(false)
const showCopyPopover = ref(false)
const lockModalMode = ref<'set' | 'unlock'>('set')
const showLockModal = ref(false)
const pinForm = reactive({ pin: '', confirm: '' })
const pinModalInput = ref<HTMLInputElement | null>(null)
const inlinePin = ref('')
const inlinePinInput = ref<HTMLInputElement | null>(null)


const locked = computed(() => props.note.is_locked && !props.isVerified)

const currentIcon = computed(() => iconComponentFor(editorIcon.value))

watch(locked, (isLockedNow) => {
  if (isLockedNow) {
    inlinePin.value = ''
    nextTick(() => inlinePinInput.value?.focus())
  }
})

function selectIcon(key: string) {
  editorIcon.value = key
  showIconPicker.value = false
  markDirty()
}

function commitTagDraft() {
  const raw = newTagDraft.value.replace(/,/g, '').trim()
  if (!raw) {
    newTagDraft.value = ''
    return
  }
  if (!editorTags.value.includes(raw)) {
    editorTags.value = [...editorTags.value, raw]
    markDirty()
  }
  newTagDraft.value = ''
}

function removeTag(tag: string) {
  editorTags.value = editorTags.value.filter(t => t !== tag)
  markDirty()
}

const stats = computed(() => {
  const text = editorBlocks.value
    .map(b => stripHtml(b.content))
    .join(' ')
    .trim()
  return {
    words: text ? text.split(/\s+/).filter(Boolean).length : 0,
    chars: text.length,
    blocks: editorBlocks.value.length
  }
})

const lastEdited = computed(() => {
  const d = new Date(props.note.updated_at)
  const diffMin = Math.floor((Date.now() - d.getTime()) / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`
  return d.toLocaleDateString('en-GB')
})

const saveStateText = computed(() => {
  switch (saveState.value) {
    case 'dirty':
      return 'Unsaved'
    case 'saving':
      return 'Saving...'
    default:
      return 'Saved'
  }
})

const saveStateClass = computed(() => {
  switch (saveState.value) {
    case 'dirty':
      return 'text-amber-400/90'
    case 'saving':
      return 'text-zinc-400'
    default:
      return 'text-emerald-400/80'
  }
})

function createDefaultParagraphBlock(): NoteBlock {
  return {
    id: crypto.randomUUID(),
    type: 'paragraph',
    content: '',
    indent: 0
  }
}

function syncFromNote() {
  suppressSyncWatch = true
  const rawTitle = props.note.title || ''
  editorTitle.value = rawTitle === 'Untitled' ? '' : rawTitle
  editorIcon.value = props.note.icon || 'file-text'
  editorTags.value = [...(props.note.tags || [])]
  newTagDraft.value = ''

  const incomingBlocks = (props.note.blocks || []).map(b => ({ ...b }))
  if (incomingBlocks.length > 0) {
    editorBlocks.value = incomingBlocks
  } else if ((props.note.content || '').trim()) {
    // Pre-block-era note: the text lives in note.content - lift it into a
    // paragraph block instead of showing an empty page (autosave persists it).
    editorBlocks.value = [{
      id: crypto.randomUUID(),
      type: 'paragraph',
      content: props.note.content,
      indent: 0
    }]
    nextTick(() => {
      suppressSyncWatch = false
    })
    markDirty()
    return
  } else {
    editorBlocks.value = [createDefaultParagraphBlock()]
  }

  nextTick(() => {
    suppressSyncWatch = false
    if (rawTitle === 'Untitled' && !locked.value) {
      titleInput.value?.focus()
    }
  })
  saveState.value = 'saved'
}

watch(
  () => props.note.id,
  () => {
    flushAutosave()
    syncFromNote()
    void migrateLegacyAttachments()
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  flushAutosave()
})

function markDirty() {
  saveState.value = 'dirty'
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveTimer = null
    saveNow()
  }, 1500)
}

function flushAutosave() {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (saveState.value === 'dirty') {
    saveNow()
  }
}

async function saveNow() {
  saveState.value = 'saving'
  try {
    await workspaceStore.updateNote(props.note.id, {
      title: editorTitle.value.trim() || 'Untitled',
      icon: editorIcon.value,
      tags: editorTags.value,
      blocks: editorBlocks.value
    })
    saveState.value = 'saved'
  } catch {
    saveState.value = 'dirty'
    toast.error('Failed to save note')
  }
}

watch(editorTitle, () => {
  if (!suppressSyncWatch) markDirty()
})

watch(editorBlocks, () => {
  if (suppressSyncWatch) return
  markDirty()
}, { deep: true })

// ===== Metadata actions =====
async function togglePin() {
  try {
    await workspaceStore.togglePinNote(props.note.id)
  } catch {
    toast.error('Failed to update pin')
  }
}

async function setNoteColor(color: NoteColor) {
  try {
    await workspaceStore.updateNote(props.note.id, { color })
  } catch {
    toast.error('Failed to update color')
  }
}

async function setNoteFolder(folderId: string | null) {
  try {
    await workspaceStore.updateNote(props.note.id, { folder: folderId })
    await workspaceStore.fetchFolders()
    toast.success(folderId ? 'Moved to folder' : 'Moved to All Notes')
  } catch {
    toast.error('Failed to move note')
  }
}

async function moveToTrash() {
  try {
    await workspaceStore.trashNote(props.note.id)
    toast.info('Note moved to trash')
    emit('trashed', props.note.id)
  } catch {
    toast.error('Failed to trash note')
  }
}

async function copyToProject(projectId: string) {
  try {
    await workspaceStore.copyNoteToProject(props.note.id, projectId)
    toast.success(`Copied "${editorTitle.value.trim() || 'Untitled'}" to project pages`)
    showCopyPopover.value = false
  } catch {
    toast.error('Failed to copy note')
  }
}

// ===== Lock handling =====
function openLockModal(mode: 'set' | 'unlock') {
  lockModalMode.value = mode
  showLockModal.value = true
}

watch(showLockModal, (open) => {
  if (open) {
    pinForm.pin = ''
    pinForm.confirm = ''
    nextTick(() => pinModalInput.value?.focus())
  }
})

async function submitLockModal() {
  const pin = pinForm.pin.trim()

  if (lockModalMode.value === 'set') {
    if (!/^\d{4,6}$/.test(pin)) {
      toast.error('PIN must be 4 to 6 digits')
      return
    }
    if (pin !== pinForm.confirm.trim()) {
      toast.error('PIN confirmation does not match')
      return
    }
    try {
      await workspaceStore.setNoteLock(props.note.id, { is_locked: true, pin })
      showLockModal.value = false
      emit('verified', props.note.id)
      toast.success('Note locked')
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to lock note')
    }
    return
  }

  try {
    await workspaceStore.setNoteLock(props.note.id, { is_locked: false, pin })
    showLockModal.value = false
    toast.success('Lock removed')
  } catch (err: any) {
    toast.error(err?.response?.data?.error || 'Incorrect PIN')
  }
}

async function verifyInlinePin() {
  try {
    const ok = await workspaceStore.verifyNoteLock(props.note.id, inlinePin.value)
    if (ok) {
      inlinePin.value = ''
      emit('verified', props.note.id)
    } else {
      toast.error('Incorrect PIN')
    }
  } catch {
    toast.error('Failed to verify PIN')
  }
}

// ===== Legacy attachments migration (blocks are the single source of truth) =====
// Notes saved before inline file blocks may still hold items in note.attachments.
// Convert any entry not represented by an inline block into a 'file' block.
async function migrateLegacyAttachments() {
  const note = props.note
  if (!note || !note.attachments || note.attachments.length === 0) return
  const blockDriveIds = new Set((note.blocks || []).map(b => b.drive_file_id).filter(Boolean))
  const orphans = note.attachments.filter(a => a.drive_file_id && !blockDriveIds.has(a.drive_file_id))
  if (orphans.length === 0) {
    await workspaceStore.updateNote(note.id, { attachments: [] })
    return
  }
  const migratedBlocks = orphans.map(a => ({
    id: crypto.randomUUID(),
    type: 'file' as const,
    content: '',
    drive_file_id: a.drive_file_id,
    file_url: a.drive_view_link || '',
    file_name: a.file_name,
    file_type: a.file_type || '',
    file_size: a.file_size || 0
  }))
  try {
    await workspaceStore.updateNote(note.id, {
      blocks: [...(note.blocks || []), ...migratedBlocks],
      attachments: []
    })
    toast.info('Legacy attachments converted to inline file blocks')
  } catch {
    toast.error('Failed to migrate legacy attachments')
  }
}
</script>
