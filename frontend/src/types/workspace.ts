export type ProjectStatus = 'PLANNING' | 'ACTIVE' | 'ON_HOLD' | 'COMPLETED' | 'ARCHIVED'
export type TaskStatus = 'TODO' | 'DOING' | 'DONE' | 'ARCHIVED' | 'DRAFTING' | 'WAITING' | 'COMPLETED'
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'
export type ProjectLinkType = 'WEBSITE' | 'CANVA' | 'FIGMA' | 'GITHUB' | 'SHEET' | 'OTHER'
export type CalendarEventType = 'APPOINTMENT' | 'MEETING' | 'REMINDER' | 'MILESTONE' | 'PERSONAL' | 'OTHER'
export type NoteColor = 'DEFAULT' | 'AMBER' | 'EMERALD' | 'SKY' | 'VIOLET' | 'ROSE'

export type NoteBlockType =
  | 'h1'
  | 'h2'
  | 'h3'
  | 'paragraph'
  | 'todo'
  | 'bullet'
  | 'numbered'
  | 'callout'
  | 'code'
  | 'quote'
  | 'divider'
  | 'image'
  | 'audio'
  | 'table'

export interface NoteBlock {
  id: string
  type: NoteBlockType
  content: string
  checked?: boolean
  indent?: number
  language?: string
  // Image & audio blocks (files live in Google Drive, never on disk)
  drive_file_id?: string
  file_url?: string
  file_name?: string
  file_type?: string
  file_size?: number
  width?: '50%' | '75%' | '100%'
  duration?: number
  // Table block (row 0 is the header row)
  rows?: string[][]
}

export interface ChecklistItem {
  id: string
  title: string
  is_completed: boolean
}

export interface TaskReferenceLink {
  title: string
  url: string
}

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
  status: ProjectStatus
  category: string
  start_date: string | null
  target_date: string | null
  is_archived: boolean
  metadata: Record<string, any>
  pending_tasks_count: number
  total_tasks_count: number
  completed_tasks_count: number
  todo_count: number
  doing_count: number
  notes_count: number
  links_count: number
  attachments_count: number
  created_at: string
  updated_at: string
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
  start_date: string | null
  deadline_info: DeadlineInfo
  checklist: ChecklistItem[]
  checklist_progress: { total: number; completed: number }
  links: TaskReferenceLink[]
  position: number
  file_url: string
  notes: string
  metadata: Record<string, any>
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface NoteAttachment {
  id: string
  file_name: string
  file_type: string
  file_size: number
  drive_file_id: string
  drive_view_link: string
  uploaded_at: string
}

export interface NoteFolder {
  id: string
  name: string
  icon: string
  color: string
  position: number
  notes_count: number
  created_at: string
  updated_at: string
}

export interface Note {
  id: string
  project: string | null
  project_name: string | null
  folder: string | null
  folder_name: string | null
  title: string
  icon: string
  content: string
  blocks: NoteBlock[]
  tags: string[]
  color: NoteColor
  is_pinned: boolean
  is_locked: boolean
  has_lock_pin: boolean
  is_trashed: boolean
  trashed_at: string | null
  attachments: NoteAttachment[]
  created_at: string
  updated_at: string
}

export interface ProjectLink {
  id: string
  project: string
  title: string
  url: string
  link_type: ProjectLinkType
  is_pinned: boolean
  created_at: string
  updated_at: string
}

export interface ProjectAttachment {
  id: string
  project: string | null
  task: string | null
  file_name: string
  file_type: string
  file_size: number
  category: string
  drive_file_id: string
  drive_view_link: string
  drive_download_link: string
  uploaded_at: string
}

export interface CalendarEvent {
  id: string
  project: string | null
  title: string
  event_type: CalendarEventType
  start_at: string
  end_at: string | null
  is_all_day: boolean
  notes: string
  created_at: string
  updated_at: string
}

export interface WorkspaceOverview {
  pipeline_counts: {
    todo: number
    doing: number
    done: number
    // Legacy keys kept for backward compatibility
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
    todo_count: number
    doing_count: number
    done_count: number
    total_tasks_count: number
    pending_tasks_count: number
    notes_count: number
    links_count: number
    attachments_count: number
  }>
}
