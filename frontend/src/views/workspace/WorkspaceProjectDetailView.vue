<template>
  <div class="space-y-5 max-w-7xl mx-auto font-sans">
    <!-- ============ 1. Project Header & Properties Bar ============ -->
    <div class="pb-4 border-b border-zinc-800/80 space-y-3">
      <div class="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500">
        <RouterLink to="/workspace" class="hover:text-zinc-300 transition-colors">Workspace</RouterLink>
        <span class="text-zinc-700">/</span>
        <RouterLink to="/workspace" class="hover:text-zinc-300 transition-colors">Projects</RouterLink>
        <span class="text-zinc-700">/</span>
        <span class="text-zinc-300">{{ project?.name || '...' }}</span>
      </div>

      <div class="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
        <div class="flex items-start gap-3 min-w-0">
          <div
            v-if="project"
            class="w-11 h-11 rounded-lg flex items-center justify-center text-lg shrink-0 border"
            :style="{ backgroundColor: `${project.color}1A`, borderColor: `${project.color}40` }"
          >
            {{ iconEmoji(project.icon) }}
          </div>

          <div class="min-w-0">
            <h1 class="text-lg font-semibold text-zinc-100 tracking-tight truncate">{{ project?.name || 'Loading...' }}</h1>
            <div class="flex items-center gap-2 flex-wrap mt-1.5">
              <span
                v-if="project"
                class="text-[9px] font-mono px-1.5 py-0.5 rounded border uppercase font-semibold"
                :class="statusBadgeClass(project.status)"
              >
                {{ project.status.replace('_', ' ') }}
              </span>
              <span
                v-if="project?.category"
                class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 uppercase"
              >
                {{ project.category }}
              </span>
              <span v-if="project?.start_date || project?.target_date" class="text-[10px] font-mono text-zinc-500">
                {{ project?.start_date || '...' }} → {{ project?.target_date || '...' }}
              </span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-4 shrink-0">
          <!-- Task progress -->
          <div v-if="project" class="w-40 hidden sm:block">
            <div class="flex items-center justify-between text-[10px] font-mono text-zinc-500 mb-1">
              <span>Progress</span>
              <span>{{ completedTasksCount }}/{{ totalTasksCount }}</span>
            </div>
            <div class="h-1.5 rounded-full bg-zinc-900 border border-zinc-800/60 overflow-hidden">
              <div
                class="h-full transition-all duration-300"
                :style="{ width: `${progressPct}%`, backgroundColor: project.color }"
              />
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              type="button"
              @click="showProjectModal = true"
              class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-medium transition-colors flex items-center gap-1.5"
            >
              <Pencil class="w-3 h-3" />
              <span>Edit Project</span>
            </button>
            <button
              type="button"
              @click="showDeleteProjectConfirm = true"
              class="p-1.5 rounded-md text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/30 transition-colors"
              title="Delete project"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <!-- ============ 2. Pinned Quick Links Bar ============ -->
      <div class="flex items-center gap-2 flex-wrap pt-1">
        <span
          v-for="link in pinnedLinks"
          :key="link.id"
          class="inline-flex items-center gap-1.5 pl-2.5 pr-1.5 py-1 rounded-md bg-zinc-900/60 border border-zinc-800 group/link"
        >
          <span class="text-[11px]">{{ linkTypeIcon(link.link_type) }}</span>
          <a
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
            class="text-[11px] text-zinc-300 hover:text-zinc-100 transition-colors max-w-[160px] truncate"
            :title="link.url"
          >
            {{ link.title }}
          </a>
          <button
            v-if="isEmbeddable(link)"
            type="button"
            @click="previewLink = link"
            class="p-0.5 rounded text-zinc-500 hover:text-zinc-100 transition-colors"
            title="Preview embed"
          >
            <Eye class="w-3 h-3" />
          </button>
        </span>

        <button
          type="button"
          @click="openLinkModal()"
          class="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-zinc-900/40 border border-dashed border-zinc-800 text-[11px] text-zinc-500 hover:text-zinc-200 hover:border-zinc-600 transition-colors"
        >
          <Plus class="w-3 h-3" />
          Add Link
        </button>
      </div>
    </div>

    <!-- ============ 3. Domain Tabs ============ -->
    <div class="flex items-center gap-1 bg-zinc-900 border border-zinc-800 p-1 rounded-lg w-fit max-w-full overflow-x-auto">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        @click="switchTab(tab.key)"
        class="px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap"
        :class="activeTab === tab.key ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'"
      >
        <component :is="tab.icon" class="w-3.5 h-3.5" />
        <span>{{ tab.label }}</span>
        <span class="text-[10px] font-mono text-zinc-500">{{ tab.count() }}</span>
      </button>
    </div>

    <!-- ======== Tab 1: Kanban Board ======== -->
    <div v-if="activeTab === 'board'">
      <div class="flex items-center justify-between mb-3">
        <p class="text-[11px] font-mono text-zinc-500">Drag cards between columns or use the quick action buttons.</p>
        <button
          @click="openQuickCreate(null, 'TODO')"
          class="px-3 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors flex items-center gap-1.5 shrink-0"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>New Task</span>
        </button>
      </div>

      <WorkspaceKanbanBoard
        :tasks="projectTasks"
        :show-project-badge="false"
        @select-task="openDrawer"
        @create-task="(status: TaskStatus) => openQuickCreate(null, status)"
        @move-task="handleMoveTask"
      />
    </div>

    <!-- ======== Tab 2: Project Calendar ======== -->
    <div v-else-if="activeTab === 'calendar'">
      <WorkspaceCalendarGrid
        :tasks="projectTasks"
        :events="workspaceStore.events"
        :show-project-dot="false"
        @select-task="openDrawer"
        @select-event="openEventModal"
        @create-on-date="openQuickCreate"
      />
    </div>

    <!-- ======== Tab 3: Pages & Notes ======== -->
    <div v-else-if="activeTab === 'pages'" class="grid grid-cols-1 lg:grid-cols-4 gap-4">
      <!-- Pages list sidebar -->
      <div class="lg:col-span-1 space-y-2">
        <button
          @click="createPage"
          class="w-full px-3 py-2 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-medium transition-colors flex items-center justify-center gap-1.5"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>New Page</span>
        </button>

        <div class="space-y-1.5 max-h-[600px] overflow-y-auto pr-1">
          <div
            v-for="note in workspaceStore.notes"
            :key="note.id"
            class="p-2.5 rounded-md border cursor-pointer transition-colors group/page"
            :class="selectedPageId === note.id
              ? 'bg-zinc-900 border-zinc-700'
              : 'bg-zinc-900/30 border-zinc-800/60 hover:border-zinc-700'"
            @click="selectPage(note.id)"
          >
            <div class="flex items-center gap-2">
              <span class="text-xs shrink-0">{{ iconEmoji(note.icon) }}</span>
              <span class="text-xs font-medium text-zinc-200 truncate flex-1">{{ note.title || 'Untitled' }}</span>
              <Pin v-if="note.is_pinned" class="w-3 h-3 text-zinc-400 fill-zinc-400 shrink-0" />
            </div>
            <p class="text-[10px] font-mono text-zinc-600 mt-1 truncate">
              {{ note.content ? note.content.slice(0, 60) : 'Empty page' }}
            </p>
          </div>

          <div
            v-if="workspaceStore.notes.length === 0"
            class="p-6 text-center text-[11px] font-mono text-zinc-600 border border-dashed border-zinc-800 rounded-md"
          >
            No pages yet
          </div>
        </div>
      </div>

      <!-- Page editor -->
      <div class="lg:col-span-3 rounded-lg bg-zinc-900/30 border border-zinc-800/80">
        <template v-if="selectedPage">
          <!-- Page toolbar -->
          <div class="px-4 py-3 border-b border-zinc-800/80 space-y-2.5">
            <div class="flex items-center gap-2 flex-wrap">
              <div class="flex items-center gap-1">
                <button
                  v-for="emoji in ICON_PRESETS"
                  :key="emoji.key"
                  type="button"
                  @click="pageIcon = emoji.key; markPageDirty()"
                  class="w-6 h-6 rounded-md flex items-center justify-center text-xs transition-colors border"
                  :class="pageIcon === emoji.key ? 'bg-zinc-800 border-zinc-600' : 'bg-zinc-900/60 border-zinc-800 hover:border-zinc-700'"
                >
                  {{ emoji.emoji }}
                </button>
              </div>
              <span class="mx-1 w-px h-5 bg-zinc-800 hidden sm:block" />

              <input
                v-model="pageTagsInput"
                type="text"
                placeholder="tags, comma, separated"
                class="flex-1 min-w-[140px] bg-zinc-900/60 border border-zinc-800 rounded-md px-2.5 py-1.5 text-[11px] text-zinc-300 placeholder-zinc-600 outline-none focus:border-zinc-600"
                @change="markPageDirty()"
              />

              <button
                type="button"
                @click="togglePagePin()"
                class="p-1.5 rounded-md transition-colors"
                :class="pagePinned ? 'text-zinc-100 bg-zinc-800' : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60'"
                :title="pagePinned ? 'Unpin page' : 'Pin page'"
              >
                <Pin class="w-3.5 h-3.5" :class="{ 'fill-zinc-100': pagePinned }" />
              </button>
              <button
                type="button"
                @click="showDeletePageConfirm = true"
                class="p-1.5 rounded-md text-zinc-600 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                title="Delete page"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>

            <input
              v-model="pageTitle"
              type="text"
              placeholder="Untitled page..."
              class="w-full bg-transparent border-none outline-none text-lg font-semibold text-zinc-100 placeholder-zinc-700"
              @input="markPageDirty()"
            />

            <div v-if="pageTags.length > 0" class="flex items-center gap-1.5 flex-wrap">
              <span
                v-for="tag in pageTags"
                :key="tag"
                class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800"
              >
                #{{ tag }}
              </span>
            </div>
          </div>

          <!-- Block editor -->
          <div class="p-4">
            <NotionBlockEditor v-model="pageBlocks" :upload-target-id="selectedPageId || undefined" />
            <div class="flex items-center justify-end mt-3">
              <span class="text-[10px] font-mono" :class="pageSaveStateClass">{{ pageSaveStateText }}</span>
            </div>
          </div>
        </template>

        <div v-else class="p-12 text-center space-y-3">
          <BookOpen class="w-8 h-8 text-zinc-700 mx-auto" />
          <p class="text-xs font-mono text-zinc-500">Select a page or create a new one.</p>
        </div>
      </div>
    </div>

    <!-- ======== Tab 4: Documents & Links ======== -->
    <div v-else-if="activeTab === 'files'" class="space-y-6">
      <!-- Section A: Google Drive Project Vault -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono flex items-center gap-2">
            <HardDrive class="w-3.5 h-3.5 text-zinc-500" />
            Google Drive Project Vault
          </h3>
          <span class="text-[10px] font-mono text-zinc-500">{{ projectAttachments.length }} files</span>
        </div>

        <div
          v-if="storageStore.isConnected"
          class="rounded-lg border border-dashed p-5 text-center cursor-pointer transition-colors"
          :class="isUploading ? 'border-zinc-600 bg-zinc-900/60' : 'border-zinc-800 hover:border-zinc-600 bg-zinc-900/20'"
          @click="!isUploading && vaultFileInput?.click()"
          @dragover.prevent
          @drop.prevent="handleVaultDrop"
        >
          <input ref="vaultFileInput" type="file" multiple class="hidden" @change="handleVaultSelected" />
          <template v-if="isUploading">
            <div class="text-[11px] text-zinc-300 font-mono mb-1.5">Uploading... {{ uploadPct }}%</div>
            <div class="h-1 max-w-xs mx-auto rounded-full bg-zinc-800 overflow-hidden">
              <div class="h-full bg-sky-500/70 transition-all" :style="{ width: `${uploadPct}%` }" />
            </div>
          </template>
          <div v-else class="flex flex-col items-center gap-1.5">
            <Upload class="w-5 h-5 text-zinc-500" />
            <p class="text-xs text-zinc-400">Drag & drop files or click to upload to Google Drive</p>
            <p class="text-[10px] font-mono text-zinc-600">Zero-disk vault — files stream directly to your Drive</p>
          </div>
        </div>

        <div
          v-else
          class="rounded-lg bg-zinc-900/40 border border-dashed border-zinc-800 p-4 text-center text-[11px] text-zinc-500"
        >
          Google Drive is not connected. Link it in
          <RouterLink to="/settings" class="text-zinc-300 underline hover:text-white">Settings</RouterLink>
          to enable the project vault.
        </div>

        <!-- Attachments table -->
        <div v-if="projectAttachments.length > 0" class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 overflow-hidden">
          <table class="w-full text-left">
            <thead>
              <tr class="border-b border-zinc-800/80 bg-zinc-900/40">
                <th class="px-4 py-2 text-[10px] font-mono uppercase text-zinc-500">File</th>
                <th class="px-4 py-2 text-[10px] font-mono uppercase text-zinc-500 hidden sm:table-cell">Size</th>
                <th class="px-4 py-2 text-[10px] font-mono uppercase text-zinc-500 hidden md:table-cell">Linked Task</th>
                <th class="px-4 py-2 text-[10px] font-mono uppercase text-zinc-500 hidden md:table-cell">Uploaded</th>
                <th class="px-4 py-2 text-[10px] font-mono uppercase text-zinc-500 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr v-for="attachment in projectAttachments" :key="attachment.id" class="hover:bg-zinc-900/40 transition-colors group/row">
                <td class="px-4 py-2.5">
                  <a
                    v-if="attachment.drive_view_link"
                    :href="attachment.drive_view_link"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-xs text-zinc-200 hover:text-zinc-100 hover:underline flex items-center gap-2"
                  >
                    <FileText class="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                    <span class="truncate max-w-[240px]">{{ attachment.file_name }}</span>
                  </a>
                  <span v-else class="text-xs text-zinc-200 flex items-center gap-2">
                    <FileText class="w-3.5 h-3.5 text-zinc-500" />
                    {{ attachment.file_name }}
                  </span>
                </td>
                <td class="px-4 py-2.5 text-[11px] font-mono text-zinc-500 hidden sm:table-cell">{{ formatFileSize(attachment.file_size) }}</td>
                <td class="px-4 py-2.5 hidden md:table-cell">
                  <span v-if="attachment.task" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
                    Task
                  </span>
                  <span v-else class="text-[10px] font-mono text-zinc-600">—</span>
                </td>
                <td class="px-4 py-2.5 text-[11px] font-mono text-zinc-500 hidden md:table-cell">
                  {{ new Date(attachment.uploaded_at).toLocaleDateString('en-GB') }}
                </td>
                <td class="px-4 py-2.5">
                  <div class="flex items-center justify-end gap-1.5">
                    <a
                      v-if="attachment.drive_download_link"
                      :href="attachment.drive_download_link"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
                      title="Download"
                    >
                      <Download class="w-3.5 h-3.5" />
                    </a>
                    <button
                      type="button"
                      @click="attachmentToDelete = attachment"
                      class="p-1 rounded text-zinc-600 hover:text-rose-400 opacity-0 group-hover/row:opacity-100 transition-all"
                      title="Delete"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Section B: All Project Links Directory -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono flex items-center gap-2">
            <Link2 class="w-3.5 h-3.5 text-zinc-500" />
            All Project Links
          </h3>
          <button
            type="button"
            @click="openLinkModal()"
            class="px-2.5 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs font-medium transition-colors flex items-center gap-1.5"
          >
            <Plus class="w-3 h-3" />
            Add Link
          </button>
        </div>

        <div
          v-if="workspaceStore.links.length === 0"
          class="p-8 text-center text-xs font-mono text-zinc-600 border border-dashed border-zinc-800 rounded-lg"
        >
          No links saved for this project yet
        </div>

        <div v-else class="rounded-lg bg-zinc-900/30 border border-zinc-800/80 overflow-hidden">
          <table class="w-full text-left">
            <thead>
              <tr class="border-b border-zinc-800/80 bg-zinc-900/40">
                <th class="px-4 py-2 text-[10px] font-mono uppercase text-zinc-500">Type</th>
                <th class="px-4 py-2 text-[10px] font-mono uppercase text-zinc-500">Title</th>
                <th class="px-4 py-2 text-[10px] font-mono uppercase text-zinc-500 hidden md:table-cell">URL</th>
                <th class="px-4 py-2 text-[10px] font-mono uppercase text-zinc-500 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-800/50">
              <tr v-for="link in workspaceStore.links" :key="link.id" class="hover:bg-zinc-900/40 transition-colors group/row">
                <td class="px-4 py-2.5">
                  <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800 flex items-center gap-1.5 w-fit">
                    <span>{{ linkTypeIcon(link.link_type) }}</span>
                    {{ link.link_type }}
                  </span>
                </td>
                <td class="px-4 py-2.5">
                  <a
                    :href="link.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-xs text-zinc-200 hover:text-zinc-100 hover:underline"
                  >
                    {{ link.title }}
                  </a>
                </td>
                <td class="px-4 py-2.5 hidden md:table-cell">
                  <span class="text-[10px] font-mono text-zinc-600 truncate block max-w-[220px]">{{ link.url }}</span>
                </td>
                <td class="px-4 py-2.5">
                  <div class="flex items-center justify-end gap-1.5">
                    <button
                      type="button"
                      @click="toggleLinkPin(link)"
                      class="p-1 rounded transition-colors"
                      :class="link.is_pinned ? 'text-zinc-200' : 'text-zinc-600 hover:text-zinc-300'"
                      :title="link.is_pinned ? 'Unpin from header' : 'Pin to header'"
                    >
                      <Pin class="w-3.5 h-3.5" :class="{ 'fill-zinc-200': link.is_pinned }" />
                    </button>
                    <button
                      v-if="isEmbeddable(link)"
                      type="button"
                      @click="previewLink = link"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 transition-colors"
                      title="Preview embed"
                    >
                      <Eye class="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      @click="openLinkModal(link)"
                      class="p-1 rounded text-zinc-500 hover:text-zinc-200 opacity-0 group-hover/row:opacity-100 transition-all"
                      title="Edit"
                    >
                      <Pencil class="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      @click="linkToDelete = link"
                      class="p-1 rounded text-zinc-600 hover:text-rose-400 opacity-0 group-hover/row:opacity-100 transition-all"
                      title="Delete"
                    >
                      <Trash2 class="w-3.5 h-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ============ Drawers & Modals ============ -->
    <!-- Task Side Peek Drawer -->
    <TaskSidePeekDrawer
      :is-open="isDrawerOpen"
      :task="selectedTask"
      @close="closeDrawer"
      @updated="handleTaskUpdated"
      @deleted="handleTaskDeleted"
      @refresh="refreshProjectData"
    />

    <!-- Quick Create (Task or Event) -->
    <CalendarQuickCreateModal
      :is-open="showQuickCreate"
      :projects="workspaceStore.projects"
      :fixed-project-id="projectId"
      :initial-date="quickCreateDate"
      :initial-status="quickCreateStatus"
      @close="showQuickCreate = false"
      @created-task="handleQuickTaskCreated"
      @created-event="refreshProjectData"
    />

    <!-- Edit Event Modal -->
    <CalendarEventModal
      :is-open="isEventModalOpen"
      :event="selectedEvent"
      :projects="workspaceStore.projects"
      :fixed-project-id="projectId"
      @close="isEventModalOpen = false"
      @updated="handleEventUpdated"
      @deleted="handleEventDeleted"
    />

    <!-- Embed Preview Modal -->
    <EmbedPreviewModal
      :is-open="!!previewLink"
      :link="previewLink"
      @close="previewLink = null"
    />

    <!-- Add / Edit Link Modal -->
    <div
      v-if="showLinkModal"
      class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-sans"
      @click.self="showLinkModal = false"
    >
      <div class="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-md p-5 shadow-2xl relative">
        <button
          @click="showLinkModal = false"
          class="absolute top-4 right-4 text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <X class="w-4 h-4" />
        </button>

        <h3 class="text-sm font-semibold text-zinc-100 mb-1">{{ editingLink ? 'Edit Link' : 'Add Link' }}</h3>
        <p class="text-xs text-zinc-500 mb-4">Attach websites, Canva decks, Figma files or repos to this project.</p>

        <div class="space-y-3">
          <input
            v-model="linkForm.title"
            type="text"
            placeholder="Link title (e.g. Landing Design)"
            class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600"
          />
          <input
            v-model="linkForm.url"
            type="url"
            placeholder="https://..."
            class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 placeholder-zinc-600 outline-none focus:border-zinc-600"
          />
          <div class="grid grid-cols-2 gap-3">
            <select
              v-model="linkForm.link_type"
              class="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
            >
              <option value="WEBSITE">Website / App</option>
              <option value="CANVA">Canva Presentation</option>
              <option value="FIGMA">Figma Design</option>
              <option value="GITHUB">GitHub Repository</option>
              <option value="SHEET">Spreadsheet / Doc</option>
              <option value="OTHER">External Resource</option>
            </select>
            <label class="flex items-center gap-2 px-2.5 py-2 bg-zinc-900 border border-zinc-800 rounded-md cursor-pointer">
              <input v-model="linkForm.is_pinned" type="checkbox" class="accent-zinc-100" />
              <span class="text-xs text-zinc-300">Show in header</span>
            </label>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2.5 mt-5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="showLinkModal = false"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            @click="submitLink"
            class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors shadow-sm"
          >
            {{ editingLink ? 'Save Link' : 'Add Link' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Edit Project Modal -->
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

        <h3 class="text-sm font-semibold text-zinc-100 mb-1">Edit Project</h3>
        <p class="text-xs text-zinc-500 mb-4">Update properties of this project.</p>

        <div class="space-y-3.5">
          <div>
            <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Project Name</label>
            <input
              v-model="projectForm.name"
              type="text"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Status</label>
              <select
                v-model="projectForm.status"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
              >
                <option value="PLANNING">Planning</option>
                <option value="ACTIVE">Active</option>
                <option value="ON_HOLD">On Hold</option>
                <option value="COMPLETED">Completed</option>
                <option value="ARCHIVED">Archived</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Category</label>
              <select
                v-model="projectForm.category"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600"
              >
                <option value="GENERAL">General</option>
                <option value="CLIENT">Client</option>
                <option value="INTERNAL">Internal</option>
                <option value="PERSONAL">Personal</option>
                <option value="DEV">Dev</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1.5">Color & Icon</label>
            <div class="flex items-center gap-2 flex-wrap">
              <button
                v-for="color in COLOR_PRESETS"
                :key="color"
                type="button"
                @click="projectForm.color = color"
                class="w-6 h-6 rounded-full border-2 transition-transform"
                :class="projectForm.color === color ? 'scale-110 border-zinc-100' : 'border-transparent'"
                :style="{ backgroundColor: color }"
              />
              <span class="mx-1 w-px h-5 bg-zinc-800" />
              <button
                v-for="emoji in ICON_PRESETS"
                :key="emoji.key"
                type="button"
                @click="projectForm.icon = emoji.key"
                class="w-7 h-7 rounded-md flex items-center justify-center text-sm transition-colors border"
                :class="projectForm.icon === emoji.key ? 'bg-zinc-800 border-zinc-600' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'"
              >
                {{ emoji.emoji }}
              </button>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Start Date</label>
              <input
                v-model="projectForm.start_date"
                type="date"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
              />
            </div>
            <div>
              <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Target Date</label>
              <input
                v-model="projectForm.target_date"
                type="date"
                class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 font-mono"
              />
            </div>
          </div>

          <div>
            <label class="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Description</label>
            <textarea
              v-model="projectForm.description"
              rows="3"
              class="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 outline-none focus:border-zinc-600 resize-y"
            />
          </div>
        </div>

        <div class="flex items-center justify-end gap-2.5 mt-5 pt-3 border-t border-zinc-800/80">
          <button
            type="button"
            @click="showProjectModal = false"
            class="px-3 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            @click="submitProject"
            class="px-3.5 py-1.5 rounded-md bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-semibold transition-colors shadow-sm"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmations -->
    <ConfirmModal
      :is-open="showDeleteProjectConfirm"
      title="Delete this project?"
      :message="`'${project?.name}' and all of its tasks, pages and links will be permanently removed. Uploaded Drive files remain in Google Drive.`"
      confirm-text="Delete Project"
      @confirm="deleteProject"
      @cancel="showDeleteProjectConfirm = false"
    />

    <ConfirmModal
      :is-open="showDeletePageConfirm"
      title="Delete this page?"
      :message="`'${selectedPage?.title || 'Untitled'}' will be permanently removed.`"
      confirm-text="Delete Page"
      @confirm="deletePage"
      @cancel="showDeletePageConfirm = false"
    />

    <ConfirmModal
      :is-open="!!linkToDelete"
      title="Delete this link?"
      :message="`'${linkToDelete?.title}' will be removed from this project.`"
      confirm-text="Delete Link"
      @confirm="deleteLink"
      @cancel="linkToDelete = null"
    />

    <ConfirmModal
      :is-open="!!attachmentToDelete"
      title="Delete this file?"
      :message="`'${attachmentToDelete?.file_name}' will be removed from Google Drive and this project.`"
      confirm-text="Delete File"
      @confirm="deleteAttachment"
      @cancel="attachmentToDelete = null"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BookOpen,
  Calendar,
  Columns3,
  Download,
  Eye,
  FileText,
  HardDrive,
  Link2,
  Pencil,
  Pin,
  Plus,
  Trash2,
  Upload,
  X
} from 'lucide-vue-next'
import { useWorkspaceStore } from '../../stores/workspace'
import { useStorageStore } from '../../stores/storage'
import { useToastStore } from '../../stores/toast'
import ConfirmModal from '../../components/common/ConfirmModal.vue'
import WorkspaceKanbanBoard from '../../components/workspace/WorkspaceKanbanBoard.vue'
import WorkspaceCalendarGrid from '../../components/workspace/WorkspaceCalendarGrid.vue'
import TaskSidePeekDrawer from '../../components/workspace/TaskSidePeekDrawer.vue'
import EmbedPreviewModal from '../../components/workspace/EmbedPreviewModal.vue'
import NotionBlockEditor from '../../components/workspace/NotionBlockEditor.vue'
import CalendarQuickCreateModal from '../../components/workspace/CalendarQuickCreateModal.vue'
import CalendarEventModal from '../../components/workspace/CalendarEventModal.vue'
import type {
  CalendarEvent,
  Note,
  NoteBlock,
  ProjectAttachment,
  ProjectLink,
  ProjectLinkType,
  ProjectStatus,
  TaskDocument,
  TaskStatus,
  WorkspaceProject
} from '../../types/workspace'

const route = useRoute()
const router = useRouter()
const workspaceStore = useWorkspaceStore()
const storageStore = useStorageStore()
const toast = useToastStore()

const projectId = computed(() => String(route.params.id || ''))

const project = ref<WorkspaceProject | null>(null)
const isUploading = ref(false)
const uploadPct = ref(0)

const COLOR_PRESETS = ['#3B82F6', '#8B5CF6', '#EC4899', '#EF4444', '#F59E0B', '#10B981', '#06B6D4', '#71717A']
const ICON_PRESETS = [
  { key: 'briefcase', emoji: '💼' },
  { key: 'rocket', emoji: '🚀' },
  { key: 'target', emoji: '🎯' },
  { key: 'book', emoji: '📚' },
  { key: 'wrench', emoji: '🔧' },
  { key: 'home', emoji: '🏠' },
  { key: 'chart', emoji: '📈' },
  { key: 'palette', emoji: '🎨' }
]

const TABS = [
  { key: 'board', label: 'Kanban Board', icon: Columns3, count: () => projectTasks.value.length },
  { key: 'calendar', label: 'Calendar', icon: Calendar, count: () => projectTasks.value.length + workspaceStore.events.length },
  { key: 'pages', label: 'Pages & Notes', icon: BookOpen, count: () => workspaceStore.notes.length },
  { key: 'files', label: 'Documents & Links', icon: HardDrive, count: () => projectAttachments.value.length + workspaceStore.links.length }
]

// ===== Tab state (synced with ?tab=) =====
const activeTab = ref<string>(['board', 'calendar', 'pages', 'files'].includes(String(route.query.tab)) ? String(route.query.tab) : 'board')

function switchTab(tab: string) {
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

// ===== Data loading (reactive to route param changes) =====
async function loadAllProjectData() {
  if (!projectId.value) return
  await Promise.allSettled([
    loadProject(),
    workspaceStore.fetchTasks({ project_id: projectId.value }),
    workspaceStore.fetchNotes({ project_id: projectId.value }),
    workspaceStore.fetchLinks(projectId.value),
    workspaceStore.fetchAttachments(projectId.value),
    workspaceStore.fetchEvents({ project_id: projectId.value }),
    storageStore.fetchStatus()
  ])
}

watch(projectId, loadAllProjectData, { immediate: true })

async function loadProject() {
  try {
    project.value = await workspaceStore.fetchProjectDetail(projectId.value)
  } catch {
    toast.error('Project not found')
    router.replace('/workspace')
  }
}

async function refreshProjectData() {
  await Promise.allSettled([
    workspaceStore.fetchTasks({ project_id: projectId.value }),
    workspaceStore.fetchProjectDetail(projectId.value).then(p => {
      if (p) project.value = p
    }).catch(() => {}),
    workspaceStore.fetchLinks(projectId.value)
  ])
}

const projectTasks = computed(() => workspaceStore.tasks)
const projectAttachments = computed(() => workspaceStore.attachments)
const pinnedLinks = computed(() => workspaceStore.links.filter(l => l.is_pinned))

// Live progress computed directly from the task list so the header bar
// updates immediately when cards are created or moved between columns.
const totalTasksCount = computed(() => projectTasks.value.filter(t => t.status !== 'ARCHIVED').length)
const completedTasksCount = computed(() => projectTasks.value.filter(t => t.status === 'DONE').length)

const progressPct = computed(() => {
  if (totalTasksCount.value === 0) return 0
  return Math.round((completedTasksCount.value / totalTasksCount.value) * 100)
})

// ===== Task drawer, quick create & event modal =====
const isDrawerOpen = ref(false)
const selectedTask = ref<TaskDocument | null>(null)
const showQuickCreate = ref(false)
const quickCreateDate = ref<string | null>(null)
const quickCreateStatus = ref<TaskStatus>('TODO')

const isEventModalOpen = ref(false)
const selectedEvent = ref<CalendarEvent | null>(null)

function openDrawer(task: TaskDocument) {
  selectedTask.value = task
  isDrawerOpen.value = true
}

function closeDrawer() {
  isDrawerOpen.value = false
}

function openQuickCreate(dateStr: string | null, defaultStatus: TaskStatus = 'TODO') {
  quickCreateDate.value = dateStr
  quickCreateStatus.value = defaultStatus
  showQuickCreate.value = true
}

function openEventModal(event: CalendarEvent) {
  selectedEvent.value = event
  isEventModalOpen.value = true
}

async function handleQuickTaskCreated(task: TaskDocument) {
  showQuickCreate.value = false
  openDrawer(task)
}

async function handleMoveTask(taskId: string, newStatus: TaskStatus) {
  try {
    await workspaceStore.moveTaskStatus(taskId, newStatus)
    toast.success(`Moved to ${newStatus}`)
  } catch {
    toast.error('Failed to move task')
  }
}

function handleTaskUpdated(updated: TaskDocument) {
  selectedTask.value = updated
}

function handleTaskDeleted() {
  selectedTask.value = null
  isDrawerOpen.value = false
  refreshProjectData()
}

function handleEventUpdated(updated: CalendarEvent) {
  selectedEvent.value = updated
  isEventModalOpen.value = false
}

function handleEventDeleted() {
  selectedEvent.value = null
  isEventModalOpen.value = false
}

// ===== Edit / Delete Project =====
const showProjectModal = ref(false)
const showDeleteProjectConfirm = ref(false)
const projectForm = reactive({
  name: '',
  status: 'ACTIVE' as ProjectStatus,
  category: 'GENERAL',
  color: '#3B82F6',
  icon: 'briefcase',
  start_date: '',
  target_date: '',
  description: ''
})

watch(showProjectModal, (open) => {
  if (open && project.value) {
    projectForm.name = project.value.name
    projectForm.status = project.value.status
    projectForm.category = project.value.category || 'GENERAL'
    projectForm.color = project.value.color
    projectForm.icon = project.value.icon
    projectForm.start_date = project.value.start_date || ''
    projectForm.target_date = project.value.target_date || ''
    projectForm.description = project.value.description || ''
  }
})

async function submitProject() {
  if (!projectForm.name.trim()) {
    toast.error('Project name is required')
    return
  }
  try {
    project.value = await workspaceStore.updateProject(projectId.value, {
      name: projectForm.name.trim(),
      status: projectForm.status,
      category: projectForm.category,
      color: projectForm.color,
      icon: projectForm.icon,
      start_date: projectForm.start_date || null,
      target_date: projectForm.target_date || null,
      description: projectForm.description
    })
    showProjectModal.value = false
    toast.success('Project updated')
  } catch {
    toast.error('Failed to update project')
  }
}

async function deleteProject() {
  showDeleteProjectConfirm.value = false
  try {
    await workspaceStore.deleteProject(projectId.value)
    toast.info('Project deleted')
    router.replace('/workspace')
  } catch {
    toast.error('Failed to delete project')
  }
}

// ===== Links =====
const showLinkModal = ref(false)
const editingLink = ref<ProjectLink | null>(null)
const linkToDelete = ref<ProjectLink | null>(null)
const previewLink = ref<ProjectLink | null>(null)
const linkForm = reactive({
  title: '',
  url: '',
  link_type: 'WEBSITE' as ProjectLinkType,
  is_pinned: true
})

function openLinkModal(link?: ProjectLink) {
  editingLink.value = link || null
  linkForm.title = link?.title || ''
  linkForm.url = link?.url || ''
  linkForm.link_type = link?.link_type || 'WEBSITE'
  linkForm.is_pinned = link ? link.is_pinned : true
  showLinkModal.value = true
}

async function submitLink() {
  const title = linkForm.title.trim()
  const url = linkForm.url.trim()
  if (!title || !url) {
    toast.error('Link title and URL are required')
    return
  }
  if (!/^https?:\/\//i.test(url)) {
    toast.error('URL must start with http:// or https://')
    return
  }
  try {
    if (editingLink.value) {
      await workspaceStore.updateLink(editingLink.value.id, { ...linkForm, title, url })
      toast.success('Link updated')
    } else {
      await workspaceStore.createLink({ ...linkForm, title, url, project: projectId.value })
      toast.success('Link added')
    }
    showLinkModal.value = false
  } catch {
    toast.error('Failed to save link')
  }
}

async function toggleLinkPin(link: ProjectLink) {
  try {
    await workspaceStore.updateLink(link.id, { is_pinned: !link.is_pinned })
  } catch {
    toast.error('Failed to update link')
  }
}

async function deleteLink() {
  const target = linkToDelete.value
  linkToDelete.value = null
  if (!target) return
  try {
    await workspaceStore.deleteLink(target.id)
    toast.info('Link deleted')
  } catch {
    toast.error('Failed to delete link')
  }
}

function isEmbeddable(link: ProjectLink): boolean {
  return ['CANVA', 'FIGMA', 'SHEET', 'WEBSITE', 'OTHER'].includes(link.link_type)
}

// ===== Pages & Notes =====
const selectedPageId = ref<string | null>(null)
const pageTitle = ref('')
const pageIcon = ref('file-text')
const pageTagsInput = ref('')
const pagePinned = ref(false)
const pageBlocks = ref<NoteBlock[]>([])
const pageSaveState = ref<'saved' | 'dirty' | 'saving'>('saved')
const showDeletePageConfirm = ref(false)
let pageSaveTimer: ReturnType<typeof setTimeout> | null = null
// Guards the deep watcher from flagging "dirty" when pageBlocks are replaced
// programmatically (select / create / save) rather than typed by the user.
let suppressBlockWatch = false

function setPageBlocks(blocks: NoteBlock[]) {
  suppressBlockWatch = true
  pageBlocks.value = blocks
  nextTick(() => {
    suppressBlockWatch = false
  })
}

const selectedPage = computed(() =>
  workspaceStore.notes.find(n => n.id === selectedPageId.value) || null
)
const pageTags = computed(() =>
  pageTagsInput.value.split(',').map(t => t.trim()).filter(Boolean)
)

const pageSaveStateText = computed(() => {
  switch (pageSaveState.value) {
    case 'dirty':
      return 'Unsaved changes'
    case 'saving':
      return 'Saving...'
    default:
      return 'All changes saved'
  }
})

const pageSaveStateClass = computed(() => {
  switch (pageSaveState.value) {
    case 'dirty':
      return 'text-amber-400/80'
    case 'saving':
      return 'text-zinc-400'
    default:
      return 'text-emerald-400/80'
  }
})

function selectPage(noteId: string) {
  flushPageAutosave()
  selectedPageId.value = noteId
  const note = workspaceStore.notes.find(n => n.id === noteId)
  if (note) {
    pageTitle.value = note.title
    pageIcon.value = note.icon || 'file-text'
    pageTagsInput.value = (note.tags || []).join(', ')
    pagePinned.value = note.is_pinned
    setPageBlocks((note.blocks || []).map(b => ({ ...b })))
  }
  pageSaveState.value = 'saved'
}

function createPage() {
  flushPageAutosave()
  pageTitle.value = ''
  pageIcon.value = 'file-text'
  pageTagsInput.value = ''
  pagePinned.value = false
  setPageBlocks([])
  selectedPageId.value = null
  pageSaveState.value = 'dirty'
  savePage(true)
}

function markPageDirty() {
  pageSaveState.value = 'dirty'
  if (pageSaveTimer) clearTimeout(pageSaveTimer)
  pageSaveTimer = setTimeout(() => {
    pageSaveTimer = null
    savePage()
  }, 2500)
}

function flushPageAutosave() {
  if (pageSaveTimer) {
    clearTimeout(pageSaveTimer)
    pageSaveTimer = null
    if (pageSaveState.value === 'dirty') {
      savePage()
    }
  }
}

async function savePage(force = false) {
  if (!force && pageSaveState.value !== 'dirty' && selectedPageId.value) return
  pageSaveState.value = 'saving'
  try {
    const payload = {
      title: pageTitle.value.trim() || 'Untitled',
      icon: pageIcon.value,
      tags: pageTags.value,
      is_pinned: pagePinned.value,
      blocks: pageBlocks.value,
      project: projectId.value
    }
    let saved: Note
    if (selectedPageId.value) {
      saved = await workspaceStore.updateNote(selectedPageId.value, payload)
    } else {
      saved = await workspaceStore.createNote(payload)
      selectedPageId.value = saved.id
    }
    pageTitle.value = saved.title
    setPageBlocks((saved.blocks || []).map(b => ({ ...b })))
    pageSaveState.value = 'saved'
  } catch {
    pageSaveState.value = 'dirty'
    toast.error('Failed to save page')
  }
}

async function togglePagePin() {
  pagePinned.value = !pagePinned.value
  markPageDirty()
  if (selectedPageId.value) {
    savePage()
  }
}

async function deletePage() {
  showDeletePageConfirm.value = false
  if (!selectedPageId.value) return
  try {
    await workspaceStore.deleteNote(selectedPageId.value)
    selectedPageId.value = null
    toast.info('Page deleted')
  } catch {
    toast.error('Failed to delete page')
  }
}

watch(pageBlocks, () => {
  if (suppressBlockWatch) return
  if (selectedPageId.value || pageTitle.value) {
    markPageDirty()
  }
}, { deep: true })

// ===== Drive Vault =====
const vaultFileInput = ref<HTMLInputElement | null>(null)
const attachmentToDelete = ref<ProjectAttachment | null>(null)

async function handleVaultSelected(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    await uploadVaultFiles(Array.from(input.files))
  }
  input.value = ''
}

async function handleVaultDrop(event: DragEvent) {
  if (isUploading.value) return
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    await uploadVaultFiles(Array.from(files))
  }
}

async function uploadVaultFiles(files: File[]) {
  isUploading.value = true
  uploadPct.value = 0
  try {
    for (const file of files) {
      await storageStore.uploadDirect(file, 'workspace', projectId.value, pct => {
        uploadPct.value = pct
      })
    }
    await workspaceStore.fetchAttachments(projectId.value)
    await workspaceStore.fetchProjectDetail(projectId.value).then(p => {
      if (p) project.value = p
    }).catch(() => {})
    toast.success(`Uploaded ${files.length} file${files.length > 1 ? 's' : ''} to Drive`)
  } catch (err: any) {
    toast.error(err?.message || 'Failed to upload file to Google Drive')
  } finally {
    isUploading.value = false
    uploadPct.value = 0
  }
}

async function deleteAttachment() {
  const target = attachmentToDelete.value
  attachmentToDelete.value = null
  if (!target) return
  try {
    await workspaceStore.deleteAttachment(target.id)
    await workspaceStore.fetchProjectDetail(projectId.value).then(p => {
      if (p) project.value = p
    }).catch(() => {})
    toast.info('File deleted')
  } catch {
    toast.error('Failed to delete file')
  }
}

// ===== Helpers =====
function iconEmoji(icon: string): string {
  return ICON_PRESETS.find(i => i.key === icon)?.emoji || '💼'
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

function linkTypeIcon(type: ProjectLinkType): string {
  switch (type) {
    case 'CANVA':
      return '🎨'
    case 'FIGMA':
      return '🖌️'
    case 'GITHUB':
      return '💻'
    case 'SHEET':
      return '📄'
    case 'WEBSITE':
      return '🌐'
    default:
      return '🔗'
  }
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exp = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, exp)).toFixed(exp === 0 ? 0 : 1)} ${units[exp]}`
}
</script>
