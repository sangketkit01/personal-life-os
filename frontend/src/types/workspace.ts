export type ProjectStatus = 'PLANNING' | 'ACTIVE' | 'ON_HOLD' | 'COMPLETED' | 'ARCHIVED'
export type TaskStatus = 'TODO' | 'DOING' | 'DONE' | 'ARCHIVED' | 'DRAFTING' | 'WAITING' | 'COMPLETED'
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'
export type ProjectLinkType = 'WEBSITE' | 'CANVA' | 'FIGMA' | 'GITHUB' | 'SHEET' | 'OTHER'
export type CalendarEventType = 'APPOINTMENT' | 'MEETING' | 'REMINDER' | 'MILESTONE' | 'PERSONAL' | 'OTHER'
export type NoteColor = 'DEFAULT' | 'AMBER' | 'EMERALD' | 'SKY' | 'VIOLET' | 'ROSE'

export type ProjectType = 'INTERNAL' | 'CLIENT_DEV' | 'MA_CONTRACT'
export type InfraAssetType =
  | 'VPS'
  | 'DEDICATED'
  | 'MANAGED_DB'
  | 'PAAS'
  | 'SAAS'
  | 'API_SERVICE'
  | 'DOMAIN'
  | 'CDN_DNS'
  | 'SSL_CERT'
  | 'STORAGE'
  | 'EMAIL_SMTP'
  | 'LICENSE'
  | 'OTHER'
export type BillingOwnership = 'SELF_FUNDED' | 'CLIENT_REIMBURSED' | 'CLIENT_DIRECT'
export type SshAuthType = 'PASSWORD' | 'PRIVATE_KEY' | 'NONE'
export type CredentialCategory = 'SSH' | 'DATABASE' | 'API_KEY' | 'ENV_VARS' | 'ADMIN_PANEL' | 'OTHER'
export type InfraHealthStatus = 'ONLINE' | 'OFFLINE' | 'WARNING' | 'UNKNOWN'

export interface SlaDetails {
  uptime_target?: string
  response_time?: string
  backup_policy?: string
  monthly_hours_quota?: string
  notes?: string
}

export interface ProjectEconomics {
  currency: string
  monthly_ma_inflow: string
  annual_ma_inflow: string
  realized_inflow: string
  monthly_infra_outflow: string
  annual_infra_outflow: string
  realized_outflow: string
  projected_monthly_margin: string
  realized_net_margin: string
  margin_pct: string
  monthly_server_outflow?: string
  monthly_service_outflow?: string
  shared_assets_count?: number
  self_funded_asset_count: number
}

export interface DockerContainerInfo {
  ID?: string
  Names?: string
  Image?: string
  State?: string
  Status?: string
  Ports?: string
  [key: string]: any
}

export interface InfraTelemetry {
  cpu_pct: number | null
  load_avg: number | null
  ram_used_mb: number | null
  ram_total_mb: number | null
  ram_pct: number | null
  disk_used_gb: number | null
  disk_total_gb: number | null
  disk_pct: number | null
  uptime_seconds: number | null
  uptime_human: string | null
  kernel: string
  containers: DockerContainerInfo[]
  error: string | null
  probe_ms?: number
}

export interface LinkedProjectRef {
  id: string
  name: string
  color: string
}

export interface InfrastructureAsset {
  id: string
  project: string
  shared_projects?: string[]
  project_name?: string | null
  linked_projects?: LinkedProjectRef[]
  is_shared?: boolean
  share_count?: number
  allocated_cost_amount?: string
  name: string
  asset_type: InfraAssetType
  provider: string
  region: string
  os_name: string
  specs: { vcpu?: number; ram_gb?: number; disk_gb?: number; [key: string]: any }
  notes: string
  ip_address: string
  private_ip: string
  hostname: string
  ssh_port: number
  primary_domain: string
  console_url: string
  expiry_date: string | null
  ssh_auth_type: SshAuthType
  ssh_username: string
  has_ssh_password: boolean
  has_ssh_key: boolean
  has_ssh_passphrase: boolean
  watchdog_enabled: boolean
  alert_cpu_threshold: number
  alert_ram_threshold: number
  alert_disk_threshold: number
  health_status: InfraHealthStatus
  last_checked_at: string | null
  last_alerted_at: string | null
  last_telemetry: InfraTelemetry | Record<string, never>
  billing_ownership: BillingOwnership
  cost_amount: string
  cost_currency: string
  billing_cycle: string
  next_billing_date: string | null
  sync_to_radar: boolean
  financial_obligation: string | null
  created_at: string
  updated_at: string
}

export interface ServerCredential {
  id: string
  project: string
  asset: string | null
  title: string
  category: CredentialCategory
  username: string
  host_or_url: string
  has_secret: boolean
  notes: string
  created_at: string
  updated_at: string
}

export interface ServerRunbook {
  id: string
  project: string
  asset: string
  title: string
  description: string
  command: string
  working_dir: string
  timeout_seconds: number
  last_run_at: string | null
  last_exit_code: number | null
  last_output: string
  created_at: string
  updated_at: string
}

export interface RemoteCommandResult {
  command?: string
  stdout: string
  stderr: string
  exit_status: number
  duration_ms: number
  action?: string
  container_id?: string
  output?: string
  telemetry?: InfraTelemetry
}

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
  | 'file'
  | 'table'

export interface NoteBlock {
  id: string
  type: NoteBlockType
  content: string
  checked?: boolean
  indent?: number
  language?: string
  // Image, audio & file blocks (files live in Google Drive, never on disk)
  drive_file_id?: string
  file_url?: string
  file_name?: string
  file_type?: string
  file_size?: number
  width?: string
  align?: 'left' | 'center' | 'right'
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
  project_type: ProjectType
  client_name: string
  client_contact: string
  ma_start_date: string | null
  ma_end_date: string | null
  ma_billing_cycle: string
  ma_amount: string
  ma_currency: string
  ma_next_billing_date: string | null
  sla_details: SlaDetails
  ma_obligation: string | null
  infra_count?: number
  economics?: ProjectEconomics | null
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
