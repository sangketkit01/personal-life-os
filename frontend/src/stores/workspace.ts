import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import type {
  WorkspaceProject,
  TaskDocument,
  Note,
  WorkspaceOverview,
  TaskStatus
} from '../types/workspace'

export const useWorkspaceStore = defineStore('workspace', () => {
  const overview = ref<WorkspaceOverview | null>(null)
  const projects = ref<WorkspaceProject[]>([])
  const tasks = ref<TaskDocument[]>([])
  const notes = ref<Note[]>([])
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
    const list = Array.isArray(res.data) ? res.data : (res.data as any).results || []
    projects.value = list
    return list
  }

  async function createProject(data: { name: string; color?: string; description?: string }) {
    const res = await apiClient.post<WorkspaceProject>('/workspace/projects/', data)
    projects.value.push(res.data)
    await fetchOverview(selectedProjectId.value || undefined)
    return res.data
  }

  async function fetchTasks(filters: Record<string, string> = {}) {
    isLoading.value = true
    try {
      const params = { ...filters }
      if (selectedProjectId.value) {
        params.project_id = selectedProjectId.value
      }
      const res = await apiClient.get<TaskDocument[]>('/workspace/tasks/', { params })
      const list = Array.isArray(res.data) ? res.data : (res.data as any).results || []
      tasks.value = list
      return list
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
    const list = Array.isArray(res.data) ? res.data : (res.data as any).results || []
    notes.value = list
    return list
  }

  async function createNote(data: { title: string; content: string; project?: string | null; tags?: string[] }) {
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

  return {
    overview,
    projects,
    tasks,
    notes,
    isLoading,
    selectedProjectId,
    fetchOverview,
    fetchProjects,
    createProject,
    fetchTasks,
    createTask,
    moveTaskStatus,
    deleteTask,
    fetchNotes,
    createNote,
    updateNote,
    togglePinNote,
    deleteNote,
  }
})
