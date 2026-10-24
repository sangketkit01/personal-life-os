<template>
  <div class="flex h-[calc(100vh-6.5rem)] md:h-[calc(100vh-8.5rem)] min-h-[480px] gap-4 font-sans">
    <!-- ============ 1. Left Pane: Folders & Smart Views ============ -->
    <aside class="hidden lg:flex w-56 shrink-0 flex-col gap-1 overflow-y-auto pr-1">
      <button
        type="button"
        @click="createNote"
        class="w-full px-3 py-2 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 mb-2"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>New Note</span>
      </button>

      <!-- Smart Views -->
      <button
        v-for="view in SMART_VIEWS"
        :key="view.key"
        type="button"
        @click="switchSmartView(view.key)"
        class="flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors text-left border"
        :class="smartView === view.key ? 'bg-zinc-900 text-zinc-100 border-zinc-800' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40 border-transparent'"
      >
        <component :is="view.icon" class="w-3.5 h-3.5 shrink-0" :class="smartView === view.key ? 'text-zinc-300' : 'text-zinc-500'" />
        <span class="flex-1">{{ view.label }}</span>
        <span v-if="smartViewCount(view.key) > 0" class="text-[10px] font-mono text-zinc-500">{{ smartViewCount(view.key) }}</span>
      </button>

      <!-- Folders -->
      <div class="flex items-center justify-between px-2.5 pt-3 pb-1">
        <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-semibold">Folders</span>
        <button type="button" @click="startFolderCreate" class="p-0.5 rounded text-zinc-500 hover:text-zinc-200" title="New folder">
          <FolderPlus class="w-3.5 h-3.5" />
        </button>
      </div>

      <div
        v-for="folder in workspaceStore.folders"
        :key="folder.id"
        class="group/folder flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs transition-colors cursor-pointer border"
        :class="activeFolderId === folder.id ? 'bg-zinc-900 text-zinc-100 border-zinc-800' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40 border-transparent'"
        @click="selectFolder(folder.id)"
      >
        <span class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: folder.color }" />
        <template v-if="editingFolderId === folder.id">
          <input
            v-model="folderEditName"
            class="flex-1 min-w-0 bg-zinc-950 border border-zinc-700 rounded px-1.5 py-0.5 text-xs text-zinc-100 outline-none"
            @keydown.enter.prevent="submitFolderRename(folder.id)"
            @keydown.esc="editingFolderId = null"
            @click.stop
          />
        </template>
        <template v-else>
          <span class="flex-1 truncate">{{ folder.name }}</span>
          <span class="text-[10px] font-mono text-zinc-600">{{ folder.notes_count }}</span>
        </template>
        <span class="hidden group-hover/folder:flex items-center gap-0.5">
          <button type="button" class="p-0.5 text-zinc-500 hover:text-zinc-200" title="Rename" @click.stop="startFolderRename(folder)">
            <Pencil class="w-3 h-3" />
          </button>
          <button type="button" class="p-0.5 text-zinc-600 hover:text-rose-400" title="Delete folder" @click.stop="folderToDelete = folder">
            <Trash2 class="w-3 h-3" />
          </button>
        </span>
      </div>

      <!-- Inline folder creator -->
      <div v-if="isCreatingFolder" class="flex items-center gap-1.5 px-1 py-1">
        <input
          ref="folderCreateInput"
          v-model="newFolderName"
          placeholder="Folder name..."
          class="flex-1 min-w-0 bg-zinc-950 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-100 placeholder-zinc-600 outline-none"
          @keydown.enter.prevent="submitFolderCreate"
          @keydown.esc="isCreatingFolder = false"
        />
        <button type="button" @click="submitFolderCreate" class="p-1 rounded text-zinc-400 hover:text-zinc-100">
          <Check class="w-3 h-3" />
        </button>
      </div>

      <!-- Tags -->
      <template v-if="allTags.length > 0">
        <div class="pt-3 pb-1 px-2.5">
          <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-semibold">Tags</span>
        </div>
        <div class="flex flex-wrap gap-1 px-2 pb-2">
          <button
            v-for="tag in allTags"
            :key="tag"
            type="button"
            @click="toggleTagFilter(tag)"
            class="text-[10px] font-mono px-1.5 py-0.5 rounded border transition-colors"
            :class="activeTag === tag ? 'bg-zinc-800 text-zinc-100 border-zinc-700' : 'bg-zinc-900/40 text-zinc-500 border-zinc-800 hover:text-zinc-300'"
          >
            #{{ tag }}
          </button>
        </div>
      </template>
    </aside>

    <!-- ============ 2. Middle / Main Area ============ -->
    <section class="flex-1 min-w-0 flex flex-col">
      <!-- Search, color filter, sort & view toggle -->
      <div class="flex items-center gap-2 pb-3 flex-wrap">
        <div class="relative flex-1 min-w-[140px] max-w-xs">
          <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
          <input
            v-model="searchText"
            type="text"
            placeholder="Search notes, #tags..."
            class="w-full bg-zinc-900/60 border border-zinc-800/80 rounded-md pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-zinc-600"
          />
        </div>

        <div class="flex items-center gap-1">
          <button
            v-for="c in NOTE_COLORS"
            :key="c.key"
            type="button"
            @click="colorFilter = colorFilter === c.key ? null : c.key"
            class="w-4 h-4 rounded-full border transition-transform"
            :class="colorFilter === c.key ? 'scale-110 border-zinc-100' : 'border-zinc-700'"
            :style="{ backgroundColor: c.dot }"
            :title="c.label"
          />
        </div>

        <select
          v-model="sortBy"
          class="bg-zinc-900/60 border border-zinc-800/80 rounded-md px-2 py-1.5 text-xs text-zinc-300 outline-none focus:border-zinc-600"
        >
          <option value="updated">Last Edited</option>
          <option value="title">Title A-Z</option>
          <option value="created">Oldest First</option>
        </select>

        <div class="flex items-center gap-0.5 bg-zinc-900 border border-zinc-800 p-0.5 rounded-md ml-auto">
          <button
            type="button"
            @click="viewMode = 'split'"
            class="px-2.5 py-1 rounded text-[11px] font-medium transition-colors flex items-center gap-1.5"
            :class="viewMode === 'split' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'"
            title="Split View"
          >
            <Columns2 class="w-3 h-3" />Split
          </button>
          <button
            type="button"
            @click="viewMode = 'grid'"
            class="px-2.5 py-1 rounded text-[11px] font-medium transition-colors flex items-center gap-1.5"
            :class="viewMode === 'grid' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'"
            title="Card Grid View"
          >
            <LayoutGrid class="w-3 h-3" />Grid
          </button>
        </div>
      </div>

      <!-- SPLIT VIEW: list + editor -->
      <div v-if="viewMode === 'split'" class="flex flex-1 min-h-0 gap-4">
        <!-- Note list -->
        <div class="w-72 lg:w-80 shrink-0 overflow-y-auto space-y-1.5 pr-1">
          <div
            v-if="filteredNotes.length === 0"
            class="p-8 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800 rounded-lg"
          >
            {{ emptyStateText }}
          </div>

          <div
            v-for="note in filteredNotes"
            :key="note.id"
            class="p-3 rounded-lg border transition-colors group/note flex gap-2.5 cursor-pointer"
            :class="[
              activeNoteId === note.id ? 'border-zinc-600 bg-zinc-900' : 'border-zinc-800/70 hover:border-zinc-700 bg-zinc-900/30',
              colorTintClass(note.color)
            ]"
            @click="selectNote(note.id)"
          >
            <span class="text-sm shrink-0 mt-0.5">{{ iconEmoji(note.icon) }}</span>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1.5">
                <span class="text-xs font-medium truncate flex-1" :class="note.is_trashed ? 'text-zinc-500 line-through' : 'text-zinc-100'">
                  {{ note.title || 'Untitled' }}
                </span>
                <Lock v-if="note.is_locked" class="w-3 h-3 text-zinc-500 shrink-0" />
                <Pin v-if="note.is_pinned" class="w-3 h-3 text-zinc-400 fill-zinc-400 shrink-0" />
              </div>
              <p class="text-[10px] font-mono text-zinc-500 mt-0.5 truncate">{{ previewText(note) }}</p>
              <div class="flex items-center gap-1.5 mt-1 flex-wrap">
                <span v-if="note.folder_name" class="text-[9px] font-mono px-1 py-0.2 rounded bg-zinc-900 text-zinc-500 border border-zinc-800">{{ note.folder_name }}</span>
                <span v-for="tag in note.tags.slice(0, 2)" :key="tag" class="text-[9px] font-mono text-zinc-600">#{{ tag }}</span>
                <span v-if="note.attachments.length > 0" class="text-[9px] font-mono text-zinc-600">📎 {{ note.attachments.length }}</span>
              </div>
            </div>
            <button
              v-if="smartView === 'trash'"
              type="button"
              class="p-1 rounded text-zinc-500 hover:text-emerald-400 self-center shrink-0"
              title="Restore"
              @click.stop="restoreNote(note.id)"
            >
              <RotateCcw class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Editor canvas -->
        <div class="flex-1 min-w-0 overflow-y-auto rounded-lg bg-zinc-900/30 border border-zinc-800/80">
          <NoteEditorCanvas
            v-if="activeNote"
            :key="activeNote.id"
            :note="activeNote"
            :is-verified="isVerified(activeNote.id)"
            @verified="verifiedNoteIds.add(activeNote!.id)"
            @trashed="handleTrashed"
          />
          <div v-else class="h-full flex flex-col items-center justify-center gap-3 p-12 text-center">
            <StickyNote class="w-8 h-8 text-zinc-700" />
            <p class="text-xs font-mono text-zinc-500">Select a note or create a new one.</p>
          </div>
        </div>
      </div>

      <!-- GRID VIEW: card grid (click opens full editor) -->
      <template v-else>
        <div v-if="activeNote && showGridEditor" class="flex-1 min-h-0 flex flex-col rounded-lg bg-zinc-900/30 border border-zinc-800/80 overflow-hidden">
          <div class="px-4 py-2 border-b border-zinc-800/60 shrink-0">
            <button type="button" @click="showGridEditor = false" class="text-[11px] font-mono text-zinc-400 hover:text-zinc-100 transition-colors flex items-center gap-1.5">
              <ArrowLeft class="w-3 h-3" /> Back to grid
            </button>
          </div>
          <div class="flex-1 min-h-0 overflow-y-auto">
            <NoteEditorCanvas
              :key="activeNote.id"
              :note="activeNote"
              :is-verified="isVerified(activeNote.id)"
              @verified="verifiedNoteIds.add(activeNote!.id)"
              @trashed="handleTrashed"
            />
          </div>
        </div>

        <div v-else class="flex-1 min-h-0 overflow-y-auto">
          <div
            v-if="filteredNotes.length === 0"
            class="p-12 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800 rounded-lg"
          >
            {{ emptyStateText }}
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
            <div
              v-for="note in filteredNotes"
              :key="note.id"
              class="p-4 rounded-lg bg-zinc-900/40 border border-zinc-800/80 hover:border-zinc-600 transition-all flex flex-col gap-2 min-h-[140px] cursor-pointer"
              :class="colorTintClass(note.color)"
              @click="openFromGrid(note.id)"
            >
              <div class="flex items-center gap-1.5 w-full">
                <span class="text-sm">{{ iconEmoji(note.icon) }}</span>
                <span class="text-xs font-semibold truncate flex-1" :class="note.is_trashed ? 'text-zinc-500 line-through' : 'text-zinc-100'">
                  {{ note.title || 'Untitled' }}
                </span>
                <Lock v-if="note.is_locked" class="w-3 h-3 text-zinc-500 shrink-0" />
                <Pin v-if="note.is_pinned" class="w-3 h-3 text-zinc-400 fill-zinc-400 shrink-0" />
              </div>
              <p class="text-[11px] text-zinc-400 line-clamp-4 leading-relaxed">{{ previewText(note) }}</p>
              <div class="mt-auto pt-2 border-t border-zinc-800/50 flex items-center justify-between text-[9px] font-mono text-zinc-600 w-full">
                <span>{{ new Date(note.updated_at).toLocaleDateString('en-GB') }}</span>
                <span class="flex items-center gap-1.5">
                  <span v-if="note.attachments.length > 0">📎 {{ note.attachments.length }}</span>
                  <span v-if="note.folder_name">{{ note.folder_name }}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </section>

    <!-- ============ Modals ============ -->
    <ConfirmModal
      :is-open="!!folderToDelete"
      title="Delete this folder?"
      :message="`Folder '${folderToDelete?.name}' will be removed. Notes inside stay safe and become unfiled.`"
      confirm-text="Delete Folder"
      @confirm="deleteFolder"
      @cancel="folderToDelete = null"
    />

    <ConfirmModal
      :is-open="showEmptyTrashConfirm"
      title="Empty the trash?"
      message="All notes in the trash will be permanently deleted. This cannot be undone."
      confirm-text="Empty Trash"
      @confirm="emptyTrash"
      @cancel="showEmptyTrashConfirm = false"
    />

    <!-- Floating Empty Trash button (trash view only) -->
    <button
      v-if="smartView === 'trash' && filteredNotes.length > 0"
      type="button"
      @click="showEmptyTrashConfirm = true"
      class="fixed bottom-6 right-6 z-30 px-3.5 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs font-medium shadow-2xl transition-colors flex items-center gap-1.5"
    >
      <Trash2 class="w-3.5 h-3.5" />
      Empty Trash
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import {
  ArrowLeft,
  Check,
  FolderPlus,
  Lock,
  LayoutGrid,
  Pencil,
  Pin,
  Plus,
  RotateCcw,
  Search,
  StickyNote,
  Trash2,
  Columns2
} from 'lucide-vue-next'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import NoteEditorCanvas from '../../components/notes/NoteEditorCanvas.vue'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import { stripHtml } from '../../utils/richText'
import type { Note, NoteColor, NoteFolder } from '../../types/workspace'

const SMART_VIEWS = [
  { key: 'all', label: 'All Notes', icon: StickyNote },
  { key: 'pinned', label: 'Pinned', icon: Pin },
  { key: 'locked', label: 'Locked Notes', icon: Lock },
  { key: 'trash', label: 'Trash', icon: Trash2 }
] as const

type SmartViewKey = (typeof SMART_VIEWS)[number]['key']

const NOTE_COLORS: Array<{ key: NoteColor; label: string; dot: string }> = [
  { key: 'DEFAULT', label: 'Default', dot: '#3f3f46' },
  { key: 'AMBER', label: 'Amber', dot: '#fbbf24' },
  { key: 'EMERALD', label: 'Emerald', dot: '#34d399' },
  { key: 'SKY', label: 'Sky', dot: '#38bdf8' },
  { key: 'VIOLET', label: 'Violet', dot: '#a78bfa' },
  { key: 'ROSE', label: 'Rose', dot: '#fb7185' }
]

const workspaceStore = useWorkspaceStore()
const toast = useToastStore()

// ===== View state =====
const smartView = ref<SmartViewKey>('all')
const activeFolderId = ref<string | null>(null)
const activeTag = ref<string | null>(null)
const colorFilter = ref<NoteColor | null>(null)
const searchText = ref('')
const sortBy = ref<'updated' | 'title' | 'created'>('updated')
const viewMode = ref<'split' | 'grid'>('split')
const showGridEditor = ref(false)
const verifiedNoteIds = reactive(new Set<string>())

const folderToDelete = ref<NoteFolder | null>(null)
const showEmptyTrashConfirm = ref(false)
const editingFolderId = ref<string | null>(null)
const folderEditName = ref('')
const isCreatingFolder = ref(false)
const newFolderName = ref('')
const folderCreateInput = ref<HTMLInputElement | null>(null)

const activeNoteId = ref<string | null>(null)

const activeNote = computed(() =>
  workspaceStore.standaloneNotes.find(n => n.id === activeNoteId.value) || null
)

// ===== Data loading =====
onMounted(async () => {
  await Promise.allSettled([
    refreshNotes(),
    workspaceStore.fetchFolders(),
    workspaceStore.fetchProjects()
  ])
})

async function refreshNotes() {
  // One fetch populates both the live list and the separate trashed list,
  // keeping Smart View counts accurate from every view.
  await workspaceStore.fetchStandaloneNotes()
}

function switchSmartView(key: SmartViewKey) {
  smartView.value = key
  activeFolderId.value = null
  showGridEditor.value = false
  if (key === 'trash') {
    activeNoteId.value = null
  }
  refreshNotes()
}

function selectFolder(folderId: string) {
  activeFolderId.value = activeFolderId.value === folderId ? null : folderId
  if (smartView.value === 'trash') smartView.value = 'all'
  refreshNotes()
}

// ===== Derived lists =====
function smartViewCount(key: SmartViewKey): number {
  if (key === 'trash') return workspaceStore.trashedNotes.length
  const notes = workspaceStore.standaloneNotes.filter(n => !n.is_trashed)
  if (key === 'pinned') return notes.filter(n => n.is_pinned).length
  if (key === 'locked') return notes.filter(n => n.is_locked).length
  return notes.length
}

const allTags = computed(() => {
  const tags = new Set<string>()
  for (const note of workspaceStore.standaloneNotes) {
    if (note.is_trashed) continue
    for (const tag of note.tags || []) tags.add(tag)
  }
  return Array.from(tags).sort()
})

const filteredNotes = computed(() => {
  // Trash view reads the dedicated trashed list; every other view reads live notes
  let notes = [...(smartView.value === 'trash'
    ? workspaceStore.trashedNotes
    : workspaceStore.standaloneNotes)]

  if (smartView.value === 'trash') {
    notes = notes.filter(n => n.is_trashed)
  } else {
    notes = notes.filter(n => !n.is_trashed)
    if (smartView.value === 'pinned') notes = notes.filter(n => n.is_pinned)
    if (smartView.value === 'locked') notes = notes.filter(n => n.is_locked)
  }
  if (activeFolderId.value) notes = notes.filter(n => n.folder === activeFolderId.value)
  if (activeTag.value) notes = notes.filter(n => (n.tags || []).includes(activeTag.value!))
  if (colorFilter.value) notes = notes.filter(n => n.color === colorFilter.value)

  const q = searchText.value.trim().toLowerCase()
  if (q) {
    notes = notes.filter(n => {
      const tagHit = (n.tags || []).some(t => t.toLowerCase().includes(q.replace('#', '')))
      return (
        n.title.toLowerCase().includes(q) ||
        stripHtml(n.content).toLowerCase().includes(q) ||
        tagHit
      )
    })
  }

  if (sortBy.value === 'title') {
    notes.sort((a, b) => (a.title || 'Untitled').localeCompare(b.title || 'Untitled'))
  } else if (sortBy.value === 'created') {
    notes.sort((a, b) => a.created_at.localeCompare(b.created_at))
  } else {
    notes.sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
      return b.updated_at.localeCompare(a.updated_at)
    })
  }
  return notes
})

const emptyStateText = computed(() => {
  if (smartView.value === 'trash') return 'Trash is empty'
  if (smartView.value === 'locked') return 'No locked notes'
  if (smartView.value === 'pinned') return 'No pinned notes yet'
  return 'No notes yet. Create your first one!'
})

function previewText(note: Note): string {
  if (note.is_locked && !isVerified(note.id)) return 'This note is locked'
  const blockText = (note.blocks || []).map(b => stripHtml(b.content)).filter(Boolean).join(' ')
  return (blockText || note.content || 'Empty note').slice(0, 90)
}

function colorTintClass(color: NoteColor): string {
  switch (color) {
    case 'AMBER':
      return 'border-l-2 border-l-amber-400/70'
    case 'EMERALD':
      return 'border-l-2 border-l-emerald-400/70'
    case 'SKY':
      return 'border-l-2 border-l-sky-400/70'
    case 'VIOLET':
      return 'border-l-2 border-l-violet-400/70'
    case 'ROSE':
      return 'border-l-2 border-l-rose-400/70'
    default:
      return 'border-l-2 border-l-zinc-700'
  }
}

function iconEmoji(icon: string): string {
  const map: Record<string, string> = {
    'file-text': '📄',
    clipboard: '📋',
    folder: '📁',
    rocket: '🚀',
    target: '🎯',
    book: '📚',
    wrench: '🔧',
    home: '🏠',
    chart: '📈',
    palette: '🎨',
    briefcase: '💼'
  }
  return map[icon] || '📄'
}

function isVerified(noteId: string): boolean {
  return verifiedNoteIds.has(noteId)
}

// ===== Note selection =====
function selectNote(noteId: string) {
  activeNoteId.value = noteId
}

function openFromGrid(noteId: string) {
  activeNoteId.value = noteId
  showGridEditor.value = true
}

function handleTrashed() {
  activeNoteId.value = null
  showGridEditor.value = false
}

// ===== Note actions (list-level) =====
async function createNote() {
  try {
    const created = await workspaceStore.createNote({
      title: '',
      project: null,
      folder: activeFolderId.value
    })
    await Promise.allSettled([refreshNotes(), workspaceStore.fetchFolders()])
    selectNote(created.id)
    showGridEditor.value = true
    toast.success('Note created')
  } catch {
    toast.error('Failed to create note')
  }
}

async function restoreNote(noteId: string) {
  try {
    await workspaceStore.restoreNote(noteId)
    toast.success('Note restored')
  } catch {
    toast.error('Failed to restore note')
  }
}

async function emptyTrash() {
  showEmptyTrashConfirm.value = false
  try {
    const res = await workspaceStore.emptyTrash()
    toast.info(`Deleted ${res.deleted} note${res.deleted === 1 ? '' : 's'} permanently`)
  } catch {
    toast.error('Failed to empty trash')
  }
}

// ===== Folder CRUD =====
function startFolderCreate() {
  isCreatingFolder.value = true
  newFolderName.value = ''
  nextTick(() => folderCreateInput.value?.focus())
}

async function submitFolderCreate() {
  const name = newFolderName.value.trim()
  if (!name) return
  try {
    await workspaceStore.createFolder({ name })
    isCreatingFolder.value = false
    newFolderName.value = ''
    toast.success('Folder created')
  } catch {
    toast.error('Failed to create folder')
  }
}

function startFolderRename(folder: NoteFolder) {
  editingFolderId.value = folder.id
  folderEditName.value = folder.name
}

async function submitFolderRename(folderId: string) {
  const name = folderEditName.value.trim()
  editingFolderId.value = null
  if (!name) return
  try {
    await workspaceStore.updateFolder(folderId, { name })
  } catch {
    toast.error('Failed to rename folder')
  }
}

async function deleteFolder() {
  const folder = folderToDelete.value
  folderToDelete.value = null
  if (!folder) return
  try {
    await workspaceStore.deleteFolder(folder.id)
    if (activeFolderId.value === folder.id) activeFolderId.value = null
    toast.info('Folder deleted')
  } catch {
    toast.error('Failed to delete folder')
  }
}

function toggleTagFilter(tag: string) {
  activeTag.value = activeTag.value === tag ? null : tag
}
</script>
