import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import type {
  WorkspaceProject,
  TaskDocument,
  Note,
  WorkspaceOverview,
  TaskStatus,
  ProjectLink,
  ProjectAttachment,
  CalendarEvent
} from '../types/workspace'

export const useWorkspaceStore = defineStore('workspace', () => {
  const overview = ref<WorkspaceOverview | null>(null)
  const projects = ref<WorkspaceProject[]>([])
  const tasks = ref<TaskDocument[]>([])
  const notes = ref<Note[]>([])
  const links = ref<ProjectLink[]>([])
  const attachments = ref<ProjectAttachment[]>([])
  const events = ref<CalendarEvent[]>([])
  const isLoading = ref<boolean>(false)
  const selectedProjectId = ref<string | null>(null)

  async function fetchOverview(projectId?: string) {
    const params: Record<string, string> = {}
    if (projectId) params.project_id = projectId

    const res = await apiClient.get<WorkspaceOverview>('/workspace/overview/', { params })
    overview.value = res.data
    return res.data
  }

  async function fetchProjects() {
    const res = await apiClient.get<WorkspaceProject[]>('/workspace/projects/')
    projects.value = extractList<WorkspaceProject>(res.data)
    return projects.value
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
    const params = { ...filters }
    if (selectedProjectId.value) {
      params.project_id = selectedProjectId.value
    }
    const res = await apiClient.get<Note[]>('/workspace/notes/', { params })
    notes.value = extractList<Note>(res.data)
    return notes.value
  }

  async function createNote(data: Record<string, any>) {
    const res = await apiClient.post<Note>('/workspace/notes/', data)
    notes.value.unshift(res.data)
    return res.data
  }

  async function updateNote(id: string, data: Partial<Note>) {
    const res = await apiClient.patch<Note>(`/workspace/notes/${id}/`, data)
    const idx = notes.value.findIndex(n => n.id === id)
    if (idx !== -1) {
      notes.value[idx] = res.data
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
    return res.data
  }

  async function deleteNote(id: string) {
    await apiClient.delete(`/workspace/notes/${id}/`)
    notes.value = notes.value.filter(n => n.id !== id)
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

  return {
    overview,
    projects,
    tasks,
    notes,
    links,
    attachments,
    isLoading,
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
  }
})

function extractList<T>(data: any): T[] {
  return Array.isArray(data) ? data : (data as any)?.results || []
}
