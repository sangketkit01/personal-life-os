export type TaskStatus = 'DRAFTING' | 'WAITING' | 'COMPLETED' | 'ARCHIVED'
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'

export interface DeadlineInfo {
  days_left: number | null
  urgency: 'OVERDUE' | 'CRITICAL' | 'WARNING' | 'ATTENTION' | 'NORMAL' | 'NONE'
  is_overdue: boolean
  label: string
}

export interface WorkspaceProject {
  id: string
  name: string
  description: string
  color: string
  icon: string
  is_archived: boolean
  pending_tasks_count: number
  created_at: string
}

export interface TaskDocument {
  id: string
  project: string | null
  project_name: string | null
  project_color: string | null
  title: string
  doc_number: string | null
  status: TaskStatus
  priority: TaskPriority
  deadline: string | null
  deadline_info: DeadlineInfo
  file_url: string
  notes: string
  metadata: Record<string, any>
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface Note {
  id: string
  project: string | null
  project_name: string | null
  title: string
  content: string
  tags: string[]
  is_pinned: boolean
  created_at: string
  updated_at: string
}

export interface WorkspaceOverview {
  pipeline_counts: {
    drafting: number
    waiting: number
    completed: number
    archived: number
    total_active: number
  }
  overdue_count: number
  upcoming_deadlines_count: number
  upcoming_deadlines: Array<{
    id: string
    title: string
    doc_number: string | null
    project_name: string | null
    project_color: string | null
    status: TaskStatus
    priority: TaskPriority
    deadline: string
    file_url: string
    deadline_info: DeadlineInfo
  }>
  pinned_notes: Array<{
    id: string
    title: string
    project_name: string | null
    tags: string[]
    updated_at: string
  }>
  projects: Array<{
    id: string
    name: string
    color: string
    icon: string
    pending_tasks_count: number
  }>
}
