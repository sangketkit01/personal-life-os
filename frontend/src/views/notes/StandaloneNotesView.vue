<template>
  <div class="flex flex-col lg:flex-row h-[calc(100vh-6.5rem)] md:h-[calc(100vh-7.5rem)] min-h-[520px] gap-4 font-sans">
    <!-- ============ 1. Left Pane: Folders & Smart Views ============ -->
    <aside
      class="w-full lg:w-60 shrink-0 flex flex-col gap-1 bg-zinc-950/60 border border-zinc-800/80 rounded-xl p-3 lg:overflow-y-auto"
      :class="{ 'hidden lg:flex': viewMode === 'split' && !!activeNote }"
    >
      <div class="flex items-center justify-between gap-2 mb-2">
        <div class="flex items-center gap-2">
          <StickyNote class="w-4 h-4 text-amber-400" />
          <span class="text-xs font-semibold tracking-tight text-zinc-100">Notes</span>
        </div>
        <button
          type="button"
          @click="createNote()"
          class="px-2.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>New Note</span>
        </button>
      </div>

      <!-- Smart Views -->
      <div class=" flex lg:flex-col gap-1 overflow-x-auto pb-1 lg:pb-0">
        <button
          v-for="view in SMART_VIEWS"
          :key="view.key"
          type="button"
          @click="switchSmartView(view.key)"
          class="flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors text-left border shrink-0"
          :class="[
            !activeFolderId && smartView === view.key
              ? 'bg-zinc-900 text-zinc-100 border-zinc-700/80 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40 border-transparent',
            dragOverTarget === view.key ? 'ring-1 ring-sky-400 bg-sky-500/10 text-sky-200' : ''
          ]"
          @dragover.prevent="view.key === 'all' || view.key === 'trash' ? dragOverTarget = view.key : null"
          @dragleave="dragOverTarget === view.key ? dragOverTarget = null : null"
          @drop.prevent="view.key === 'all' ? onDropToAllNotes() : view.key === 'trash' ? onDropToTrash() : null"
        >
          <component :is="view.icon" class="w-3.5 h-3.5 shrink-0" :class="!activeFolderId && smartView === view.key ? 'text-amber-400' : 'text-zinc-500'" />
          <span class="flex-1">{{ view.label }}</span>
          <span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-900/80 text-zinc-400">{{ smartViewCount(view.key) }}</span>
        </button>
      </div>

      <!-- Folders Header -->
      <div class="flex items-center justify-between px-2 pt-3 pb-1 border-t border-zinc-800/60 mt-1">
        <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-semibold">Folders</span>
        <button
          type="button"
          @click="startFolderCreate"
          class="px-1.5 py-0.5 rounded text-[10px] font-mono text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors flex items-center gap-1"
          title="New folder"
        >
          <FolderPlus class="w-3 h-3" />
          <span>New</span>
        </button>
      </div>

      <!-- Inline folder creator -->
      <div v-if="isCreatingFolder" class="flex items-center gap-1.5 px-1 py-1 bg-zinc-900/60 rounded-md border border-zinc-800 mb-1">
        <input
          ref="folderCreateInput"
          v-model="newFolderName"
          placeholder="Folder name..."
          class="flex-1 min-w-0 bg-transparent px-2 py-1 text-xs text-zinc-100 placeholder-zinc-500 outline-none"
          @keydown.enter.prevent="submitFolderCreate"
          @keydown.esc="isCreatingFolder = false"
        />
        <button type="button" @click="submitFolderCreate" class="p-1 rounded bg-zinc-100 text-zinc-950 hover:bg-white" title="Save folder">
          <Check class="w-3 h-3" />
        </button>
        <button type="button" @click="isCreatingFolder = false" class="p-1 rounded text-zinc-500 hover:text-zinc-300" title="Cancel">
          <X class="w-3 h-3" />
        </button>
      </div>

      <!-- Folder List -->
      <div class="flex lg:flex-col gap-1 overflow-x-auto">
        <div
          v-if="workspaceStore.folders.length === 0 && !isCreatingFolder"
          class="px-2.5 py-2 text-[11px] text-zinc-600 font-mono"
        >
          No folders yet
        </div>

        <div
          v-for="folder in workspaceStore.folders"
          :key="folder.id"
          class="group/folder flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs transition-colors cursor-pointer border shrink-0"
          :class="[
            activeFolderId === folder.id
              ? 'bg-zinc-900 text-zinc-100 border-zinc-700/80 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40 border-transparent',
            dragOverTarget === folder.id ? 'ring-1 ring-sky-400 bg-sky-500/10 text-sky-200' : ''
          ]"
          @click="selectFolder(folder.id)"
          @dragover.prevent="dragOverTarget = folder.id"
          @dragleave="dragOverTarget === folder.id ? dragOverTarget = null : null"
          @drop.prevent.stop="onDropToFolder(folder.id, folder.name)"
        >
          <Folder class="w-3.5 h-3.5 shrink-0" :style="{ color: folder.color || '#a1a1aa' }" />
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
            <span class="flex-1 truncate font-medium">{{ folder.name }}</span>
            <span
              class="text-[10px] font-mono text-zinc-500"
              :class="activeFolderId === folder.id ? 'hidden lg:inline lg:group-hover/folder:hidden' : ' lg:group-hover/folder:hidden'"
            >{{ folderNoteCount(folder.id) }}</span>
          </template>

          <span
            class="items-center gap-0.5 shrink-0"
            :class="activeFolderId === folder.id ? 'flex' : 'hidden lg:group-hover/folder:flex'"
          >
            <button
              type="button"
              class="p-0.5 rounded text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
              title="New note in this folder"
              @click.stop="createNote(folder.id)"
            >
              <Plus class="w-3 h-3" />
            </button>
            <button
              type="button"
              class="p-0.5 rounded text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800"
              title="Rename folder"
              @click.stop="startFolderRename(folder)"
            >
              <Pencil class="w-3 h-3" />
            </button>
            <button
              type="button"
              class="p-0.5 rounded text-zinc-600 hover:text-rose-400 hover:bg-zinc-800"
              title="Delete folder"
              @click.stop="folderToDelete = folder"
            >
              <Trash2 class="w-3 h-3" />
            </button>
          </span>
        </div>
      </div>

      <!-- Tags -->
      <template v-if="allTags.length > 0">
        <div class="pt-3 pb-1 px-2 border-t border-zinc-800/60 mt-1 hidden lg:block">
          <span class="text-[10px] font-mono uppercase tracking-wider text-zinc-500 font-semibold">Tags</span>
        </div>
        <div class="hidden lg:flex flex-wrap gap-1 px-1.5 pb-1">
          <button
            v-for="tag in allTags"
            :key="tag"
            type="button"
            @click="toggleTagFilter(tag)"
            class="text-[10px] font-mono px-1.5 py-0.5 rounded border transition-colors"
            :class="activeTag === tag ? 'bg-zinc-800 text-zinc-100 border-zinc-600' : 'bg-zinc-900/40 text-zinc-500 border-zinc-800 hover:text-zinc-300'"
          >
            #{{ tag }}
          </button>
        </div>
      </template>
    </aside>

    <!-- ============ 2. Middle / Main Area ============ -->
    <section class="flex-1 min-w-0 min-h-0 flex flex-col">
      <!-- Top Context & Filter Bar -->
      <div
      class="flex items-center justify-between gap-2 pb-3 flex-wrap"
      :class="{ 'hidden md:flex': viewMode === 'split' && !!activeNote }"
    >
        <!-- Active Folder / View Title -->
        <div class="flex items-center gap-2 mr-2">
          <h2 class="text-sm font-semibold text-zinc-100 tracking-tight flex items-center gap-1.5">
            <Folder v-if="activeFolder" class="w-4 h-4 text-amber-400" />
            <span>{{ currentScopeTitle }}</span>
          </h2>
          <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
            {{ filteredNotes.length }}
          </span>
          <button
            v-if="smartView !== 'trash'"
            type="button"
            @click="createNote(activeFolderId)"
            class="px-2 py-1 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-[11px] font-medium text-zinc-200 transition-colors flex items-center gap-1"
            :title="activeFolder ? `Add note in ${activeFolder.name}` : 'Add new note'"
          >
            <Plus class="w-3 h-3" />
            <span>Add Note{{ activeFolder ? ` in ${activeFolder.name}` : '' }}</span>
          </button>
        </div>

        <div class="flex items-center gap-2 flex-wrap ml-auto">
          <!-- Search -->
          <div class="relative w-44 sm:w-56">
            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
            <input
              v-model="searchText"
              type="text"
              placeholder="Search notes, #tags..."
              class="w-full bg-zinc-900/60 border border-zinc-800/80 rounded-md pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 outline-none focus:border-zinc-600"
            />
          </div>

          <!-- Color dots -->
          <div class="hidden sm:flex items-center gap-1 bg-zinc-900/50 border border-zinc-800/80 px-2 py-1 rounded-md">
            <button
              v-for="c in NOTE_COLORS"
              :key="c.key"
              type="button"
              @click="colorFilter = colorFilter === c.key ? null : c.key"
              class="w-3.5 h-3.5 rounded-full border transition-transform"
              :class="colorFilter === c.key ? 'scale-125 border-zinc-100' : 'border-zinc-700 opacity-75 hover:opacity-100'"
              :style="{ backgroundColor: c.dot }"
              :title="`Filter by ${c.label}`"
            />
          </div>

          <!-- Sort -->
          <select
            v-model="sortBy"
            class="bg-zinc-900/60 border border-zinc-800/80 rounded-md px-2 py-1.5 text-xs text-zinc-300 outline-none focus:border-zinc-600"
          >
            <option value="updated">Last Edited</option>
            <option value="title">Title A-Z</option>
            <option value="created">Oldest First</option>
          </select>

          <!-- View Mode -->
          <div class="flex items-center gap-0.5 bg-zinc-900 border border-zinc-800 p-0.5 rounded-md">
            <button
              type="button"
              @click="viewMode = 'split'"
              class="px-2 py-1 rounded text-[11px] font-medium transition-colors flex items-center gap-1"
              :class="viewMode === 'split' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'"
              title="Apple Notes Split View"
            >
              <Columns2 class="w-3 h-3" />Split
            </button>
            <button
              type="button"
              @click="viewMode = 'grid'"
              class="px-2 py-1 rounded text-[11px] font-medium transition-colors flex items-center gap-1"
              :class="viewMode === 'grid' ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'"
              title="Samsung Notes Card Grid"
            >
              <LayoutGrid class="w-3 h-3" />Cards
            </button>
          </div>
        </div>
      </div>

      <!-- SPLIT VIEW: list + editor -->
      <div v-if="viewMode === 'split'" class="flex flex-1 min-h-0 gap-3">
        <!-- Note list column -->
        <div
          class="w-full md:w-72 shrink-0 overflow-y-auto space-y-1.5 pr-0.5"
          :class="{ 'hidden md:block': !!activeNote }"
        >
                    <div v-if="workspaceStore.isNotesLoading && filteredNotes.length === 0" class="space-y-2">
            <SkeletonLoader variant="list" :count="5" />
          </div>

<div
            v-else-if="filteredNotes.length === 0"
            class="p-8 text-center space-y-3 border border-dashed border-zinc-800/80 rounded-xl bg-zinc-950/40"
          >
            <StickyNote class="w-7 h-7 text-zinc-700 mx-auto" />
            <p class="text-xs font-mono text-zinc-500">{{ emptyStateText }}</p>
            <button
              v-if="smartView !== 'trash'"
              type="button"
              @click="createNote(activeFolderId)"
              class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors inline-flex items-center gap-1.5"
            >
              <Plus class="w-3.5 h-3.5" />
              <span>Create First Note</span>
            </button>
          </div>

          <div
            v-for="note in filteredNotes"
            :key="note.id"
            draggable="true"
            class="p-3 rounded-xl border transition-all group/note flex gap-2.5 cursor-pointer"
            :class="[
              activeNoteId === note.id
                ? 'border-zinc-600 bg-zinc-900 shadow-sm'
                : 'border-zinc-800/70 hover:border-zinc-700 bg-zinc-950/60 hover:bg-zinc-900/40',
              colorTintClass(note.color),
              draggingNoteId === note.id ? 'opacity-40' : ''
            ]"
            @click="selectNote(note.id)"
            @dragstart="onNoteDragStart($event, note)"
            @dragend="onNoteDragEnd"
          >
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1.5">
                <span class="text-xs font-semibold truncate flex-1" :class="note.is_trashed ? 'text-zinc-500 line-through' : 'text-zinc-100'">
                  {{ displayTitle(note) }}
                </span>
                <Lock v-if="note.is_locked" class="w-3 h-3 text-amber-400/80 shrink-0" />
                <Pin v-if="note.is_pinned" class="w-3 h-3 text-amber-400 fill-amber-400 shrink-0" />
              </div>
              <p class="text-[11px] text-zinc-400 mt-1 line-clamp-2 leading-relaxed">{{ previewText(note) }}</p>
              <div class="flex items-center justify-between gap-1.5 mt-2 text-[10px] font-mono text-zinc-500">
                <span>{{ formatShortDate(note.updated_at) }}</span>
                <div class="flex items-center gap-1.5 truncate">
                  <span v-if="note.folder_name" class="px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 truncate max-w-[100px]">
                    {{ note.folder_name }}
                  </span>
                  <span v-if="note.attachments?.length > 0" class="flex items-center gap-0.5"><Paperclip class="w-3 h-3" />{{ note.attachments.length }}</span>
                </div>
              </div>
            </div>
            <div v-if="smartView === 'trash'" class="flex items-center gap-1 self-center shrink-0">
              <button
                type="button"
                class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-emerald-400 transition-colors"
                title="Restore note"
                @click.stop="restoreNote(note.id)"
              >
                <RotateCcw class="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                class="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors"
                :title="t('nt.deletePermanent')"
                @click.stop="confirmPermanentDelete(note)"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        <!-- Editor canvas -->
        <div
          class="flex-1 min-w-0 min-h-0 flex flex-col rounded-xl bg-zinc-950/70 border border-zinc-800/80 overflow-hidden"
          :class="{ 'hidden md:flex': !activeNote }"
        >
          <div v-if="activeNote" class="md:hidden px-3 py-2 border-b border-zinc-800/80 bg-zinc-950">
            <button type="button" @click="activeNoteId = null" class="text-xs font-mono text-zinc-400 hover:text-zinc-100 flex items-center gap-1.5">
              <ArrowLeft class="w-3.5 h-3.5" /> Back to notes
            </button>
          </div>
          <NoteEditorCanvas
            v-if="activeNote"
            ref="splitEditorRef"
            :key="activeNote.id"
            :note="activeNote"
            :is-verified="isVerified(activeNote.id)"
            @verified="verifiedNoteIds.add(activeNote!.id)"
            @locked="verifiedNoteIds.delete(activeNote!.id)"
            @trashed="handleTrashed"
          />
          <div v-else class="h-full flex flex-col items-center justify-center gap-3 p-12 text-center">
            <div class="w-12 h-12 rounded-2xl bg-zinc-900/80 border border-zinc-800 flex items-center justify-center">
              <StickyNote class="w-5 h-5 text-zinc-500" />
            </div>
            <div>
              <p class="text-xs font-medium text-zinc-300">No note selected</p>
              <p class="text-[11px] text-zinc-500 mt-0.5">Pick a note from the list or start a fresh one.</p>
            </div>
            <button
              v-if="smartView !== 'trash'"
              type="button"
              @click="createNote(activeFolderId)"
              class="mt-1 px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors inline-flex items-center gap-1.5"
            >
              <Plus class="w-3.5 h-3.5" />
              <span>New Note{{ activeFolder ? ` in ${activeFolder.name}` : '' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- GRID VIEW: Samsung Notes style card grid -->
      <template v-else>
        <div v-if="activeNote && showGridEditor" class="flex-1 min-h-0 flex flex-col rounded-xl bg-zinc-950/70 border border-zinc-800/80 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-zinc-800/80 bg-zinc-950 shrink-0">
            <button type="button" @click="showGridEditor = false" class="text-xs font-mono text-zinc-400 hover:text-zinc-100 transition-colors flex items-center gap-1.5">
              <ArrowLeft class="w-3.5 h-3.5" /> Back to all cards
            </button>
          </div>
          <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
            <NoteEditorCanvas
              ref="gridEditorRef"
              :key="activeNote.id"
              :note="activeNote"
              :is-verified="isVerified(activeNote.id)"
              @verified="verifiedNoteIds.add(activeNote!.id)"
              @locked="verifiedNoteIds.delete(activeNote!.id)"
              @trashed="handleTrashed"
            />
          </div>
        </div>

        <div v-else class="flex-1 min-h-0 overflow-y-auto">
                    <div v-if="workspaceStore.isNotesLoading && filteredNotes.length === 0">
            <SkeletonLoader variant="cards" :count="6" />
          </div>

<div
            v-else-if="filteredNotes.length === 0"
            class="p-12 text-center space-y-3 border border-dashed border-zinc-800 rounded-xl bg-zinc-950/40"
          >
            <StickyNote class="w-8 h-8 text-zinc-700 mx-auto" />
            <p class="text-xs font-mono text-zinc-500">{{ emptyStateText }}</p>
            <button
              v-if="smartView !== 'trash'"
              type="button"
              @click="createNote(activeFolderId)"
              class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors inline-flex items-center gap-1.5"
            >
              <Plus class="w-3.5 h-3.5" />
              <span>Create First Note</span>
            </button>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
            <div
              v-for="note in filteredNotes"
              :key="note.id"
              draggable="true"
              class="p-4 rounded-xl bg-zinc-950/70 border border-zinc-800/80 hover:border-zinc-600 transition-all flex flex-col gap-2 min-h-[150px] cursor-pointer shadow-sm"
              :class="[colorTintClass(note.color), draggingNoteId === note.id ? 'opacity-40' : '']"
              @click="openFromGrid(note.id)"
              @dragstart="onNoteDragStart($event, note)"
              @dragend="onNoteDragEnd"
            >
              <div class="flex items-center gap-1.5 w-full">
                <span class="text-xs font-semibold truncate flex-1" :class="note.is_trashed ? 'text-zinc-500 line-through' : 'text-zinc-100'">
                  {{ displayTitle(note) }}
                </span>
                <div v-if="smartView === 'trash'" class="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    class="p-1 rounded-md bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-emerald-400 transition-colors"
                    title="Restore note"
                    @click.stop="restoreNote(note.id)"
                  >
                    <RotateCcw class="w-3 h-3" />
                  </button>
                  <button
                    type="button"
                    class="p-1 rounded-md bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-rose-400 transition-colors"
                    :title="t('nt.deletePermanent')"
                    @click.stop="confirmPermanentDelete(note)"
                  >
                    <Trash2 class="w-3 h-3" />
                  </button>
                </div>
                <Lock v-if="note.is_locked" class="w-3 h-3 text-amber-400/80 shrink-0" />
                <Pin v-if="note.is_pinned" class="w-3 h-3 text-amber-400 fill-amber-400 shrink-0" />
              </div>
              <p class="text-xs text-zinc-400 line-clamp-4 leading-relaxed">{{ previewText(note) }}</p>
              <div class="mt-auto pt-2.5 border-t border-zinc-800/60 flex items-center justify-between text-[10px] font-mono text-zinc-500 w-full">
                <span>{{ formatShortDate(note.updated_at) }}</span>
                <span class="flex items-center gap-1.5">
                  <span v-if="note.attachments?.length > 0" class="flex items-center gap-0.5"><Paperclip class="w-3 h-3" />{{ note.attachments.length }}</span>
                  <span v-if="note.folder_name" class="px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">{{ note.folder_name }}</span>
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
      :is-loading="isDeletingFolder"
      :error-message="deleteFolderError"
      @confirm="deleteFolder"
      @cancel="folderToDelete = null; deleteFolderError = ''"
    />

    <ConfirmModal
      :is-open="showEmptyTrashConfirm"
      title="Empty the trash?"
      message="All notes in the trash will be permanently deleted. This cannot be undone."
      confirm-text="Empty Trash"
      :is-loading="isEmptyingTrash"
      :error-message="emptyTrashError"
      @confirm="emptyTrash"
      @cancel="showEmptyTrashConfirm = false; emptyTrashError = ''"
    />

    <ConfirmModal
      :is-open="!!noteToDeletePermanently"
      :title="t('nt.deletePermanentTitle')"
      :message="t('nt.deletePermanentMsg', { title: noteToDeletePermanently ? displayTitle(noteToDeletePermanently) : '' })"
      :confirm-text="t('nt.deletePermanentBtn')"
      :is-loading="isDeletingNotePermanently"
      :error-message="deleteNotePermanentlyError"
      @confirm="executePermanentDelete"
      @cancel="noteToDeletePermanently = null; deleteNotePermanentlyError = ''"
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
import SkeletonLoader from '../../components/common/SkeletonLoader.vue'
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import {
  ArrowLeft,
  Paperclip,
  Check,
  Columns2,
  Folder,
  FolderPlus,
  LayoutGrid,
  Lock,
  Pencil,
  Pin,
  Plus,
  RotateCcw,
  Search,
  StickyNote,
  Trash2,
  X
} from 'lucide-vue-next'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import NoteEditorCanvas from '../../components/notes/NoteEditorCanvas.vue'
import { onBeforeRouteLeave } from 'vue-router'
import { t } from '../../i18n'
import { useWorkspaceStore } from '../../stores/workspace'
import { useToastStore } from '../../stores/toast'
import { stripHtml } from '../../utils/richText'
import type { Note, NoteColor, NoteFolder } from '../../types/workspace'

const SMART_VIEWS = [
  { key: 'all', label: 'All Notes', icon: StickyNote },
  { key: 'pinned', label: 'Pinned', icon: Pin },
  { key: 'locked', label: 'Locked', icon: Lock },
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

const splitEditorRef = ref<InstanceType<typeof NoteEditorCanvas> | null>(null)
const gridEditorRef = ref<InstanceType<typeof NoteEditorCanvas> | null>(null)

onBeforeRouteLeave(async () => {
  try {
    if (splitEditorRef.value) {
      await splitEditorRef.value.flushAutosave()
    }
    if (gridEditorRef.value) {
      await gridEditorRef.value.flushAutosave()
    }
  } catch {
    toast.error(t('common.saveFailedBeforeLeave'))
    return false
  }
})

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
const isDeletingFolder = ref(false)
const deleteFolderError = ref('')
const showEmptyTrashConfirm = ref(false)
const isEmptyingTrash = ref(false)
const emptyTrashError = ref('')
const noteToDeletePermanently = ref<Note | null>(null)
const isDeletingNotePermanently = ref(false)
const deleteNotePermanentlyError = ref('')
const editingFolderId = ref<string | null>(null)
const folderEditName = ref('')
const isCreatingFolder = ref(false)
const newFolderName = ref('')
const folderCreateInput = ref<HTMLInputElement | null>(null)

const activeNoteId = ref<string | null>(null)

// ===== Drag & drop notes into folders / All Notes / Trash =====
const draggingNoteId = ref<string | null>(null)
const dragOverTarget = ref<string | null>(null)

function onNoteDragStart(event: DragEvent, note: Note) {
  draggingNoteId.value = note.id
  event.dataTransfer?.setData('text/plain', note.id)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function onNoteDragEnd() {
  draggingNoteId.value = null
  dragOverTarget.value = null
}

async function onDropToFolder(folderId: string, folderName: string) {
  const noteId = draggingNoteId.value
  dragOverTarget.value = null
  draggingNoteId.value = null
  if (!noteId) return
  try {
    await workspaceStore.updateNote(noteId, { folder: folderId, is_trashed: false })
    await workspaceStore.fetchFolders()
    toast.success(`Moved to "${folderName}"`)
  } catch {
    toast.error('Failed to move note')
  }
}

async function onDropToAllNotes() {
  const noteId = draggingNoteId.value
  dragOverTarget.value = null
  draggingNoteId.value = null
  if (!noteId) return
  const note = workspaceStore.standaloneNotes.find(n => n.id === noteId)
    || workspaceStore.trashedNotes.find(n => n.id === noteId)
  try {
    if (note && (note.folder || note.is_trashed)) {
      await workspaceStore.updateNote(noteId, { folder: null, is_trashed: false })
      await workspaceStore.fetchFolders()
      toast.success('Removed from folder (moved to All Notes)')
    }
  } catch {
    toast.error('Failed to move note')
  }
}

async function onDropToTrash() {
  const noteId = draggingNoteId.value
  dragOverTarget.value = null
  draggingNoteId.value = null
  if (!noteId) return
  try {
    await workspaceStore.trashNote(noteId)
    toast.info('Note moved to trash', 6000, {
      label: 'Undo',
      onClick: async () => {
        try {
          await workspaceStore.restoreNote(noteId)
          toast.success('Note restored')
        } catch {
          toast.error('Failed to restore note')
        }
      }
    })
  } catch {
    toast.error('Failed to move note to trash')
  }
}

const activeFolder = computed(() =>
  workspaceStore.folders.find(f => f.id === activeFolderId.value) || null
)

const currentScopeTitle = computed(() => {
  if (activeFolder.value) return activeFolder.value.name
  const found = SMART_VIEWS.find(v => v.key === smartView.value)
  return found ? found.label : 'All Notes'
})

const activeNote = computed(() => {
  const list = smartView.value === 'trash'
    ? workspaceStore.trashedNotes
    : workspaceStore.standaloneNotes
  return list.find(n => n.id === activeNoteId.value) || null
})

// ===== Data loading =====
onMounted(async () => {
  await Promise.allSettled([
    refreshNotes(),
    workspaceStore.fetchFolders(),
    workspaceStore.fetchProjects()
  ])
  if (filteredNotes.value.length > 0 && !activeNoteId.value) {
    activeNoteId.value = filteredNotes.value[0].id
  }
})

async function refreshNotes() {
  await workspaceStore.fetchStandaloneNotes()
}

function switchSmartView(key: SmartViewKey) {
  smartView.value = key
  activeFolderId.value = null
  showGridEditor.value = false
  if (key === 'trash') {
    activeNoteId.value = null
  } else if (filteredNotes.value.length > 0) {
    activeNoteId.value = filteredNotes.value[0].id
  }
}

function selectFolder(folderId: string) {
  activeFolderId.value = folderId
  smartView.value = 'all'
  showGridEditor.value = false
  nextTick(() => {
    activeNoteId.value = filteredNotes.value[0]?.id || null
  })
}

function folderNoteCount(folderId: string): number {
  return workspaceStore.standaloneNotes.filter(n => !n.is_trashed && n.folder === folderId).length
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
  if (activeFolder.value) return `No notes in "${activeFolder.value.name}" yet`
  if (smartView.value === 'locked') return 'No locked notes'
  if (smartView.value === 'pinned') return 'No pinned notes yet'
  return 'No notes yet. Create your first one!'
})

function displayTitle(note: Note): string {
  if (note.title && note.title !== 'Untitled') return note.title
  const firstLine = (note.blocks || [])
    .map(b => stripHtml(b.content).trim())
    .find(Boolean)
  return firstLine ? firstLine.slice(0, 48) : 'New Note'
}

function previewText(note: Note): string {
  if (note.is_locked && !isVerified(note.id)) return 'Locked note — Enter PIN to view'
  const blockText = (note.blocks || []).map(b => stripHtml(b.content)).filter(Boolean).join(' ')
  return (blockText || stripHtml(note.content) || 'No additional text').slice(0, 100)
}

function formatShortDate(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ''
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

function colorTintClass(color: NoteColor): string {
  switch (color) {
    case 'AMBER':
      return 'border-l-4 border-l-amber-400/80'
    case 'EMERALD':
      return 'border-l-4 border-l-emerald-400/80'
    case 'SKY':
      return 'border-l-4 border-l-sky-400/80'
    case 'VIOLET':
      return 'border-l-4 border-l-violet-400/80'
    case 'ROSE':
      return 'border-l-4 border-l-rose-400/80'
    default:
      return ''
  }
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
  activeNoteId.value = filteredNotes.value[0]?.id || null
  showGridEditor.value = false
}

// ===== Note actions (list-level) =====
async function createNote(targetFolderId?: string | null) {
  const folderId = targetFolderId !== undefined ? targetFolderId : activeFolderId.value
  if (folderId) {
    activeFolderId.value = folderId
  }
  if (smartView.value === 'trash') {
    smartView.value = 'all'
  }
  try {
    const created = await workspaceStore.createNote({
      title: 'Untitled',
      project: null,
      folder: folderId || null,
      blocks: [
        {
          id: crypto.randomUUID(),
          type: 'paragraph',
          content: '',
          indent: 0
        }
      ]
    })
    selectNote(created.id)
    showGridEditor.value = true
    workspaceStore.fetchFolders()
  } catch (err: any) {
    toast.error(err?.response?.data?.error || 'Failed to create note')
  }
}

async function restoreNote(noteId: string) {
  try {
    await workspaceStore.restoreNote(noteId)
    if (activeNoteId.value === noteId) {
      activeNoteId.value = null
      showGridEditor.value = false
    }
    toast.success('Note restored')
  } catch {
    toast.error('Failed to restore note')
  }
}

function confirmPermanentDelete(note: Note) {
  noteToDeletePermanently.value = note
  deleteNotePermanentlyError.value = ''
}

async function executePermanentDelete() {
  const note = noteToDeletePermanently.value
  if (!note || isDeletingNotePermanently.value) return
  isDeletingNotePermanently.value = true
  deleteNotePermanentlyError.value = ''
  try {
    await workspaceStore.permanentDeleteNote(note.id)
    if (activeNoteId.value === note.id) {
      activeNoteId.value = null
      showGridEditor.value = false
    }
    toast.info(t('nt.notePermanentlyDeleted'))
    noteToDeletePermanently.value = null
  } catch (err: any) {
    deleteNotePermanentlyError.value = err?.response?.data?.error || err?.message || 'Failed to delete note'
  } finally {
    isDeletingNotePermanently.value = false
  }
}

async function emptyTrash() {
  isEmptyingTrash.value = true
  emptyTrashError.value = ''
  try {
    const res = await workspaceStore.emptyTrash()
    showEmptyTrashConfirm.value = false
    toast.info(`Deleted ${res.deleted} note${res.deleted === 1 ? '' : 's'} permanently`)
  } catch (err: any) {
    emptyTrashError.value = err?.response?.data?.error || err?.message || 'Failed to empty trash'
  } finally {
    isEmptyingTrash.value = false
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
    const folder = await workspaceStore.createFolder({ name })
    isCreatingFolder.value = false
    newFolderName.value = ''
    activeFolderId.value = folder.id
    smartView.value = 'all'
    toast.success(`Folder "${folder.name}" created`)
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
    await refreshNotes()
  } catch {
    toast.error('Failed to rename folder')
  }
}

async function deleteFolder() {
  const folder = folderToDelete.value
  if (!folder) return
  isDeletingFolder.value = true
  deleteFolderError.value = ''
  try {
    await workspaceStore.deleteFolder(folder.id)
    if (activeFolderId.value === folder.id) activeFolderId.value = null
    await refreshNotes()
    toast.info('Folder deleted')
    folderToDelete.value = null
  } catch (err: any) {
    deleteFolderError.value = err?.response?.data?.error || err?.message || 'Failed to delete folder'
  } finally {
    isDeletingFolder.value = false
  }
}

function toggleTagFilter(tag: string) {
  activeTag.value = activeTag.value === tag ? null : tag
}
</script>
