import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import type {
  WorkspaceProject,
  TaskDocument,
  Note,
  NoteFolder,
  WorkspaceOverview,
  TaskStatus,
  ProjectLink,
  ProjectAttachment,
  CalendarEvent,
  InfrastructureAsset,
  ServerCredential,
  ServerRunbook,
  RemoteCommandResult,
  InfraTelemetry,
} from '../types/workspace'

export const useWorkspaceStore = defineStore('workspace', () => {
  const overview = ref<WorkspaceOverview | null>(null)
  const projects = ref<WorkspaceProject[]>([])
  const tasks = ref<TaskDocument[]>([])
  const notes = ref<Note[]>([])
  const links = ref<ProjectLink[]>([])
  const attachments = ref<ProjectAttachment[]>([])
  const events = ref<CalendarEvent[]>([])
  const standaloneNotes = ref<Note[]>([])
  const trashedNotes = ref<Note[]>([])
  const standalonePinnedCount = ref(0)
  const folders = ref<NoteFolder[]>([])
  const infraAssets = ref<InfrastructureAsset[]>([])
  const serverCredentials = ref<ServerCredential[]>([])
  const serverRunbooks = ref<ServerRunbook[]>([])
  const isLoading = ref<boolean>(false)
  const isProjectsLoading = ref<boolean>(false)
  const isOverviewLoading = ref<boolean>(false)
  const isNotesLoading = ref<boolean>(false)
  const isInfraLoading = ref<boolean>(false)
  const selectedProjectId = ref<string | null>(null)

  async function fetchOverview(projectId?: string) {
    isOverviewLoading.value = true
    try {
      const params: Record<string, string> = {}
      if (projectId) params.project_id = projectId

      const res = await apiClient.get<WorkspaceOverview>('/workspace/overview/', { params })
      overview.value = res.data
      return res.data
    } finally {
      isOverviewLoading.value = false
    }
  }

  async function fetchProjects() {
    isProjectsLoading.value = true
    try {
      const res = await apiClient.get<WorkspaceProject[]>('/workspace/projects/')
      projects.value = extractList<WorkspaceProject>(res.data)
      return projects.value
    } finally {
      isProjectsLoading.value = false
    }
  }

  async function fetchProjectDetail(id: string) {
    const res = await apiClient.get<WorkspaceProject>(`/workspace/projects/${id}/`)
    return res.data
  }

  async function createProject(data: Record<string, any>) {
    const res = await apiClient.post<WorkspaceProject>('/workspace/projects/', data)
    projects.value.push(res.data)
    await fetchOverview(selectedProjectId.value || undefined)
    return res.data
  }

  async function updateProject(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<WorkspaceProject>(`/workspace/projects/${id}/`, payload)
    const idx = projects.value.findIndex(p => p.id === id)
    if (idx !== -1) {
      projects.value[idx] = res.data
    }
    return res.data
  }

  async function deleteProject(id: string) {
    await apiClient.delete(`/workspace/projects/${id}/`)
    projects.value = projects.value.filter(p => p.id !== id)
    await fetchOverview(selectedProjectId.value || undefined)
  }

  async function fetchTasks(filters: Record<string, string> = {}) {
    isLoading.value = true
    try {
      const params = { ...filters }
      if (selectedProjectId.value) {
        params.project_id = selectedProjectId.value
      }
      const res = await apiClient.get<TaskDocument[]>('/workspace/tasks/', { params })
      tasks.value = extractList<TaskDocument>(res.data)
      return tasks.value
    } finally {
      isLoading.value = false
    }
  }

  async function createTask(data: Record<string, any>) {
    const res = await apiClient.post<TaskDocument>('/workspace/tasks/', data)
    tasks.value.unshift(res.data)
    await fetchOverview(selectedProjectId.value || undefined)
    return res.data
  }

  async function updateTask(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<TaskDocument>(`/workspace/tasks/${id}/`, payload)
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx !== -1) {
      tasks.value[idx] = res.data
    }
    return res.data
  }

  async function moveTaskStatus(id: string, newStatus: TaskStatus) {
    const res = await apiClient.post<TaskDocument>(`/workspace/tasks/${id}/move/`, { status: newStatus })
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx !== -1) {
      tasks.value[idx] = res.data
    }
    await fetchOverview(selectedProjectId.value || undefined)
    return res.data
  }

  async function deleteTask(id: string) {
    await apiClient.delete(`/workspace/tasks/${id}/`)
    tasks.value = tasks.value.filter(t => t.id !== id)
    await fetchOverview(selectedProjectId.value || undefined)
  }

  async function fetchNotes(filters: Record<string, string> = {}) {
    isNotesLoading.value = true
    try {
      const params = { ...filters }
      if (selectedProjectId.value) {
        params.project_id = selectedProjectId.value
      }
      const res = await apiClient.get<Note[]>('/workspace/notes/', { params })
      notes.value = extractList<Note>(res.data)
      return notes.value
    } finally {
      isNotesLoading.value = false
    }
  }

  async function createNote(data: Record<string, any>) {
    const res = await apiClient.post<Note>('/workspace/notes/', data)
    notes.value.unshift(res.data)
    // Standalone notes also join the /notes list immediately
    if (!res.data.project) {
      standaloneNotes.value.unshift(res.data)
    }
    return res.data
  }

  async function updateNote(id: string, data: Partial<Note>) {
    const res = await apiClient.patch<Note>(`/workspace/notes/${id}/`, data)
    const idx = notes.value.findIndex(n => n.id === id)
    if (idx !== -1) {
      notes.value[idx] = res.data
    }
    const sIdx = standaloneNotes.value.findIndex(n => n.id === id)
    if (sIdx !== -1) {
      standaloneNotes.value[sIdx] = res.data
    }
    const tIdx = trashedNotes.value.findIndex(n => n.id === id)
    if (tIdx !== -1) {
      trashedNotes.value[tIdx] = res.data
    }
    return res.data
  }

  async function togglePinNote(id: string) {
    const res = await apiClient.post<Note>(`/workspace/notes/${id}/toggle-pin/`)
    const idx = notes.value.findIndex(n => n.id === id)
    if (idx !== -1) {
      notes.value[idx] = res.data
    }
    notes.value.sort((a, b) => (b.is_pinned ? 1 : 0) - (a.is_pinned ? 1 : 0))
    const sIdx = standaloneNotes.value.findIndex(n => n.id === id)
    if (sIdx !== -1) {
      standaloneNotes.value[sIdx] = res.data
    }
    standaloneNotes.value.sort((a, b) => (b.is_pinned ? 1 : 0) - (a.is_pinned ? 1 : 0))
    return res.data
  }

  async function deleteNote(id: string) {
    await apiClient.delete(`/workspace/notes/${id}/`)
    notes.value = notes.value.filter(n => n.id !== id)
    standaloneNotes.value = standaloneNotes.value.filter(n => n.id !== id)
    trashedNotes.value = trashedNotes.value.filter(n => n.id !== id)
  }

  async function fetchLinks(projectId?: string) {
    const params: Record<string, string> = {}
    if (projectId) params.project_id = projectId
    const res = await apiClient.get<ProjectLink[]>('/workspace/links/', { params })
    links.value = extractList<ProjectLink>(res.data)
    return links.value
  }

  async function createLink(payload: Record<string, any>) {
    const res = await apiClient.post<ProjectLink>('/workspace/links/', payload)
    links.value.push(res.data)
    return res.data
  }

  async function updateLink(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<ProjectLink>(`/workspace/links/${id}/`, payload)
    const idx = links.value.findIndex(l => l.id === id)
    if (idx !== -1) {
      links.value[idx] = res.data
    }
    return res.data
  }

  async function deleteLink(id: string) {
    await apiClient.delete(`/workspace/links/${id}/`)
    links.value = links.value.filter(l => l.id !== id)
  }

  async function fetchAttachments(projectId?: string, taskId?: string) {
    const params: Record<string, string> = {}
    if (projectId) params.project_id = projectId
    if (taskId) params.task_id = taskId
    const res = await apiClient.get<ProjectAttachment[]>('/workspace/attachments/', { params })
    attachments.value = extractList<ProjectAttachment>(res.data)
    return attachments.value
  }

  /** Fetch a single task's attachments WITHOUT overwriting the global project list. */
  async function fetchTaskAttachments(taskId: string): Promise<ProjectAttachment[]> {
    const res = await apiClient.get<ProjectAttachment[]>('/workspace/attachments/', {
      params: { task_id: taskId }
    })
    return extractList<ProjectAttachment>(res.data)
  }

  async function deleteAttachment(id: string) {
    await apiClient.delete(`/workspace/attachments/${id}/`)
    attachments.value = attachments.value.filter(a => a.id !== id)
  }

  async function fetchEvents(filters: Record<string, string> = {}) {
    const params = { ...filters }
    if (selectedProjectId.value) {
      params.project_id = selectedProjectId.value
    }
    const res = await apiClient.get<CalendarEvent[]>('/workspace/events/', { params })
    events.value = extractList<CalendarEvent>(res.data)
    return events.value
  }

  async function createEvent(payload: Record<string, any>) {
    const res = await apiClient.post<CalendarEvent>('/workspace/events/', payload)
    events.value.push(res.data)
    events.value.sort((a, b) => a.start_at.localeCompare(b.start_at))
    return res.data
  }

  async function updateEvent(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<CalendarEvent>(`/workspace/events/${id}/`, payload)
    const idx = events.value.findIndex(e => e.id === id)
    if (idx !== -1) {
      events.value[idx] = res.data
    }
    events.value.sort((a, b) => a.start_at.localeCompare(b.start_at))
    return res.data
  }

  async function deleteEvent(id: string) {
    await apiClient.delete(`/workspace/events/${id}/`)
    events.value = events.value.filter(e => e.id !== id)
  }

  // ===== Standalone notes (/notes) =====

  /** Sidebar badge count - reads only the pagination total, never touches the lists. */
  async function fetchStandalonePinnedCount() {
    const res = await apiClient.get<Record<string, any>>('/workspace/notes/', {
      params: { standalone: 'true', is_pinned: 'true' }
    })
    const data = res.data as any
    standalonePinnedCount.value = typeof data?.count === 'number' ? data.count : extractList<Note>(data).length
    return standalonePinnedCount.value
  }

  async function fetchStandaloneNotes(filters: Record<string, string> = {}) {
    isNotesLoading.value = true
    try {
      // Fetch live and trashed lists in parallel so Smart View badge counts
      // stay accurate no matter which view is currently open.
      const liveParams = { standalone: 'true', ...filters }
      const trashedParams = { standalone: 'true', trashed: 'true', ...filters }
      const [liveRes, trashedRes] = await Promise.all([
        apiClient.get<Note[]>('/workspace/notes/', { params: liveParams }),
        apiClient.get<Note[]>('/workspace/notes/', { params: trashedParams })
      ])
      standaloneNotes.value = extractList<Note>(liveRes.data)
      trashedNotes.value = extractList<Note>(trashedRes.data)
      return standaloneNotes.value
    } finally {
      isNotesLoading.value = false
    }
  }

  async function fetchNote(id: string) {
    const res = await apiClient.get<Note>(`/workspace/notes/${id}/`)
    const idx = standaloneNotes.value.findIndex(n => n.id === id)
    if (idx !== -1) {
      standaloneNotes.value[idx] = res.data
    }
    return res.data
  }

  async function trashNote(id: string) {
    const res = await apiClient.post<Note>(`/workspace/notes/${id}/trash/`)
    standaloneNotes.value = standaloneNotes.value.filter(n => n.id !== id)
    trashedNotes.value.unshift(res.data)
    return res.data
  }

  async function restoreNote(id: string) {
    const res = await apiClient.post<Note>(`/workspace/notes/${id}/restore/`)
    trashedNotes.value = trashedNotes.value.filter(n => n.id !== id)
    standaloneNotes.value.unshift(res.data)
    standaloneNotes.value.sort((a, b) => (b.is_pinned ? 1 : 0) - (a.is_pinned ? 1 : 0))
    return res.data
  }

  async function emptyTrash() {
    const res = await apiClient.post<{ deleted: number }>('/workspace/notes/empty-trash/')
    trashedNotes.value = []
    standaloneNotes.value = standaloneNotes.value.filter(n => !n.is_trashed)
    return res.data
  }

  async function setNoteLock(id: string, payload: { is_locked: boolean; pin?: string; old_pin?: string }) {
    const res = await apiClient.post<Note>(`/workspace/notes/${id}/set-lock/`, payload)
    const idx = standaloneNotes.value.findIndex(n => n.id === id)
    if (idx !== -1) {
      standaloneNotes.value[idx] = res.data
    }
    return res.data
  }

  async function verifyNoteLock(id: string, pin: string): Promise<{ verified: boolean; note?: Note }> {
    const res = await apiClient.post<{ verified: boolean }>(`/workspace/notes/${id}/verify-lock/`, { pin })
    if (res.data.verified) {
      const refreshed = await fetchNote(id)
      return { verified: true, note: refreshed }
    }
    return { verified: false }
  }

  async function copyNoteToProject(id: string, projectId: string) {
    const res = await apiClient.post<Note>(`/workspace/notes/${id}/copy-to-project/`, { project_id: projectId })
    return res.data
  }

  // ===== Note folders =====

  async function fetchFolders() {
    const res = await apiClient.get<NoteFolder[]>('/workspace/note-folders/')
    folders.value = extractList<NoteFolder>(res.data)
    return folders.value
  }

  async function createFolder(payload: Record<string, any>) {
    const res = await apiClient.post<NoteFolder>('/workspace/note-folders/', payload)
    folders.value.push(res.data)
    folders.value.sort((a, b) => a.position - b.position || a.name.localeCompare(b.name))
    return res.data
  }

  async function updateFolder(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<NoteFolder>(`/workspace/note-folders/${id}/`, payload)
    const idx = folders.value.findIndex(f => f.id === id)
    if (idx !== -1) {
      folders.value[idx] = res.data
    }
    return res.data
  }

  async function deleteFolder(id: string) {
    await apiClient.delete(`/workspace/note-folders/${id}/`)
    folders.value = folders.value.filter(f => f.id !== id)
  }


  // ===== MA & Infrastructure =====
  async function fetchInfraAssets(projectId: string) {
    isInfraLoading.value = true
    try {
      const res = await apiClient.get<InfrastructureAsset[]>('/workspace/infrastructure/', {
        params: { project_id: projectId }
      })
      infraAssets.value = extractList<InfrastructureAsset>(res.data)
      return infraAssets.value
    } finally {
      isInfraLoading.value = false
    }
  }

  async function createInfraAsset(payload: Record<string, any>) {
    const res = await apiClient.post<InfrastructureAsset>('/workspace/infrastructure/', payload)
    infraAssets.value.push(res.data)
    return res.data
  }

  async function updateInfraAsset(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<InfrastructureAsset>(`/workspace/infrastructure/${id}/`, payload)
    const idx = infraAssets.value.findIndex(a => a.id === id)
    if (idx !== -1) infraAssets.value[idx] = res.data
    return res.data
  }

  async function linkInfraAssetProject(assetId: string, projectId: string) {
    const res = await apiClient.post<InfrastructureAsset>(
      `/workspace/infrastructure/${assetId}/link-project/`,
      { project_id: projectId }
    )
    const idx = infraAssets.value.findIndex(a => a.id === assetId)
    if (idx !== -1) infraAssets.value[idx] = res.data
    return res.data
  }

  async function unlinkInfraAssetProject(assetId: string, projectId: string) {
    const res = await apiClient.post<InfrastructureAsset>(
      `/workspace/infrastructure/${assetId}/unlink-project/`,
      { project_id: projectId }
    )
    const idx = infraAssets.value.findIndex(a => a.id === assetId)
    if (idx !== -1) infraAssets.value[idx] = res.data
    return res.data
  }

  async function fetchAllUserInfraAssets(): Promise<InfrastructureAsset[]> {
    const res = await apiClient.get<InfrastructureAsset[]>('/workspace/infrastructure/')
    return extractList<InfrastructureAsset>(res.data)
  }

  async function deleteInfraAsset(id: string) {
    await apiClient.delete(`/workspace/infrastructure/${id}/`)
    infraAssets.value = infraAssets.value.filter(a => a.id !== id)
    serverRunbooks.value = serverRunbooks.value.filter(rb => rb.asset !== id)
  }

  async function probeInfraAsset(id: string, confirmHostKey = false) {
    const res = await apiClient.post<{
      health_status: string
      telemetry: InfraTelemetry
      asset: InfrastructureAsset
    }>(`/workspace/infrastructure/${id}/probe/`, confirmHostKey ? { confirm_host_key: true } : {})
    const idx = infraAssets.value.findIndex(a => a.id === id)
    if (idx !== -1) infraAssets.value[idx] = res.data.asset
    return res.data
  }

  async function trustInfraAssetHostKey(id: string, fingerprint?: string) {
    const res = await apiClient.post<{
      detail: string
      ssh_host_fingerprint: string
      asset: InfrastructureAsset
    }>(`/workspace/infrastructure/${id}/trust-host-key/`, { fingerprint })
    const idx = infraAssets.value.findIndex(a => a.id === id)
    if (idx !== -1) infraAssets.value[idx] = res.data.asset
    return res.data
  }

  async function dockerAction(id: string, containerId: string, action: string, tail = 100) {
    const res = await apiClient.post<RemoteCommandResult>(
      `/workspace/infrastructure/${id}/docker/`,
      { container_id: containerId, action, tail }
    )
    return res.data
  }

  async function execInfraCommand(id: string, command: string, workingDir = '', timeout = 60) {
    const res = await apiClient.post<RemoteCommandResult>(
      `/workspace/infrastructure/${id}/exec/`,
      { command, working_dir: workingDir, timeout }
    )
    return res.data
  }

  async function fetchServerCredentials(projectId: string) {
    isInfraLoading.value = true
    try {
      const res = await apiClient.get<ServerCredential[]>('/workspace/credentials/', {
        params: { project_id: projectId }
      })
      serverCredentials.value = extractList<ServerCredential>(res.data)
      return serverCredentials.value
    } finally {
      isInfraLoading.value = false
    }
  }

  async function createServerCredential(payload: Record<string, any>) {
    const res = await apiClient.post<ServerCredential>('/workspace/credentials/', payload)
    serverCredentials.value.push(res.data)
    return res.data
  }

  async function updateServerCredential(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<ServerCredential>(`/workspace/credentials/${id}/`, payload)
    const idx = serverCredentials.value.findIndex(c => c.id === id)
    if (idx !== -1) serverCredentials.value[idx] = res.data
    return res.data
  }

  async function deleteServerCredential(id: string) {
    await apiClient.delete(`/workspace/credentials/${id}/`)
    serverCredentials.value = serverCredentials.value.filter(c => c.id !== id)
  }

  async function revealServerCredential(id: string) {
    const res = await apiClient.post<{ id: string; secret: string }>(
      `/workspace/credentials/${id}/reveal/`
    )
    return res.data.secret
  }

  async function fetchServerRunbooks(projectId?: string, assetId?: string) {
    isInfraLoading.value = true
    try {
      const params: Record<string, string> = {}
      if (projectId) params.project_id = projectId
      if (assetId) params.asset_id = assetId
      const res = await apiClient.get<ServerRunbook[]>('/workspace/runbooks/', { params })
      serverRunbooks.value = extractList<ServerRunbook>(res.data)
      return serverRunbooks.value
    } finally {
      isInfraLoading.value = false
    }
  }

  async function createServerRunbook(payload: Record<string, any>) {
    const res = await apiClient.post<ServerRunbook>('/workspace/runbooks/', payload)
    serverRunbooks.value.push(res.data)
    return res.data
  }

  async function updateServerRunbook(id: string, payload: Record<string, any>) {
    const res = await apiClient.patch<ServerRunbook>(`/workspace/runbooks/${id}/`, payload)
    const idx = serverRunbooks.value.findIndex(rb => rb.id === id)
    if (idx !== -1) serverRunbooks.value[idx] = res.data
    return res.data
  }

  async function deleteServerRunbook(id: string) {
    await apiClient.delete(`/workspace/runbooks/${id}/`)
    serverRunbooks.value = serverRunbooks.value.filter(rb => rb.id !== id)
  }

  async function executeServerRunbook(id: string) {
    const res = await apiClient.post<{ result: RemoteCommandResult; runbook: ServerRunbook }>(
      `/workspace/runbooks/${id}/execute/`
    )
    const idx = serverRunbooks.value.findIndex(rb => rb.id === id)
    if (idx !== -1) serverRunbooks.value[idx] = res.data.runbook
    return res.data
  }

  return {
    overview,
    projects,
    tasks,
    notes,
    links,
    attachments,
    isLoading,
    isProjectsLoading,
    isOverviewLoading,
    isNotesLoading,
    isInfraLoading,
    selectedProjectId,
    fetchOverview,
    fetchProjects,
    fetchProjectDetail,
    createProject,
    updateProject,
    deleteProject,
    fetchTasks,
    createTask,
    updateTask,
    moveTaskStatus,
    deleteTask,
    fetchNotes,
    createNote,
    updateNote,
    togglePinNote,
    deleteNote,
    fetchLinks,
    createLink,
    updateLink,
    deleteLink,
    fetchAttachments,
    fetchTaskAttachments,
    deleteAttachment,
    events,
    fetchEvents,
    createEvent,
    updateEvent,
    deleteEvent,
    standaloneNotes,
    trashedNotes,
    standalonePinnedCount,
    fetchStandalonePinnedCount,
    fetchStandaloneNotes,
    fetchNote,
    trashNote,
    restoreNote,
    emptyTrash,
    setNoteLock,
    verifyNoteLock,
    copyNoteToProject,
    folders,
    fetchFolders,
    infraAssets,
    serverCredentials,
    serverRunbooks,
    fetchInfraAssets,
    createInfraAsset,
    updateInfraAsset,
    deleteInfraAsset,
    linkInfraAssetProject,
    unlinkInfraAssetProject,
    fetchAllUserInfraAssets,
    probeInfraAsset,
    trustInfraAssetHostKey,
    dockerAction,
    execInfraCommand,
    fetchServerCredentials,
    createServerCredential,
    updateServerCredential,
    deleteServerCredential,
    revealServerCredential,
    fetchServerRunbooks,
    createServerRunbook,
    updateServerRunbook,
    deleteServerRunbook,
    executeServerRunbook,
    createFolder,
    updateFolder,
    deleteFolder,
  }
})

function extractList<T>(data: any): T[] {
  return Array.isArray(data) ? data : (data as any)?.results || []
}
