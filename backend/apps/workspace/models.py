import uuid
from django.db import models
from django.conf import settings


class ProjectStatus(models.TextChoices):
    PLANNING = 'PLANNING', 'Planning'
    ACTIVE = 'ACTIVE', 'Active'
    ON_HOLD = 'ON_HOLD', 'On Hold'
    COMPLETED = 'COMPLETED', 'Completed'
    ARCHIVED = 'ARCHIVED', 'Archived'


class TaskStatus(models.TextChoices):
    TODO = 'TODO', 'To Do'
    DOING = 'DOING', 'Doing'
    DONE = 'DONE', 'Done'
    ARCHIVED = 'ARCHIVED', 'Archived'


# Legacy status aliases mapped to modern equivalents so existing callers
# (bot dispatcher, callbacks, legacy tests) keep working without regression.
TaskStatus.DRAFTING = TaskStatus.TODO
TaskStatus.WAITING = TaskStatus.DOING
TaskStatus.COMPLETED = TaskStatus.DONE

LEGACY_STATUS_MAP = {
    'DRAFTING': TaskStatus.TODO,
    'WAITING': TaskStatus.DOING,
    'COMPLETED': TaskStatus.DONE,
}


class TaskPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


class ProjectLinkType(models.TextChoices):
    WEBSITE = 'WEBSITE', 'Website / App'
    CANVA = 'CANVA', 'Canva Presentation'
    FIGMA = 'FIGMA', 'Figma Design'
    GITHUB = 'GITHUB', 'GitHub Repository'
    SHEET = 'SHEET', 'Spreadsheet / Doc'
    OTHER = 'OTHER', 'External Resource'


class CalendarEventType(models.TextChoices):
    APPOINTMENT = 'APPOINTMENT', 'Appointment'
    MEETING = 'MEETING', 'Meeting'
    REMINDER = 'REMINDER', 'Reminder'
    MILESTONE = 'MILESTONE', 'Milestone'
    PERSONAL = 'PERSONAL', 'Personal'
    OTHER = 'OTHER', 'Other'


class NoteColor(models.TextChoices):
    DEFAULT = 'DEFAULT', 'Default Zinc'
    AMBER = 'AMBER', 'Amber Gold'
    EMERALD = 'EMERALD', 'Emerald Green'
    SKY = 'SKY', 'Sky Blue'
    VIOLET = 'VIOLET', 'Violet Purple'
    ROSE = 'ROSE', 'Rose Pink'


class WorkspaceProject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_projects',
        verbose_name="User"
    )
    name = models.CharField(max_length=100, verbose_name="Project Name")
    description = models.TextField(blank=True, default='', verbose_name="Description")
    color = models.CharField(max_length=20, default='#3B82F6', verbose_name="Project Color (Hex)")
    icon = models.CharField(max_length=50, default='briefcase', verbose_name="Icon")
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.ACTIVE,
        db_index=True,
        verbose_name="Project Status"
    )
    category = models.CharField(max_length=50, blank=True, default='GENERAL', verbose_name="Category")
    start_date = models.DateField(null=True, blank=True, verbose_name="Start Date")
    target_date = models.DateField(null=True, blank=True, verbose_name="Target Date")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Project Metadata")
    is_archived = models.BooleanField(default=False, verbose_name="Is Archived")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_projects'
        ordering = ['name']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class TaskDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_documents',
        verbose_name="User"
    )
    project = models.ForeignKey(
        WorkspaceProject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name="Project"
    )
    title = models.CharField(max_length=255, verbose_name="Task Title")
    doc_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Doc Number"
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
        db_index=True,
        verbose_name="Status"
    )
    priority = models.CharField(
        max_length=10,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
        verbose_name="Priority"
    )
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Deadline"
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Start Date"
    )
    checklist = models.JSONField(default=list, blank=True, verbose_name="Sub-task Checklist")
    links = models.JSONField(default=list, blank=True, verbose_name="Task Reference Links")
    position = models.PositiveIntegerField(default=0, verbose_name="Board Position")
    file_url = models.TextField(
        blank=True,
        default='',
        verbose_name="File URL / Drive Link"
    )
    notes = models.TextField(blank=True, default='', verbose_name="Notes")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'task_documents'
        ordering = ['deadline', '-created_at']
        verbose_name = 'Task Document'
        verbose_name_plural = 'Task Documents'

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"


class NoteFolder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='note_folders',
        verbose_name="User"
    )
    name = models.CharField(max_length=100, verbose_name="Folder Name")
    icon = models.CharField(max_length=50, default='folder', verbose_name="Folder Icon")
    color = models.CharField(max_length=20, default='#a1a1aa', verbose_name="Folder Color")
    position = models.PositiveIntegerField(default=0, verbose_name="Sort Position")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_note_folders'
        ordering = ['position', 'name']
        verbose_name = 'Note Folder'
        verbose_name_plural = 'Note Folders'

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Note(models.Model):
    """
    Unified note model:
    - project = None  -> Standalone Note (shown in /notes)
    - project = <UUID> -> Workspace Project Page (shown in project detail)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name="User"
    )
    project = models.ForeignKey(
        WorkspaceProject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes',
        verbose_name="Project"
    )
    folder = models.ForeignKey(
        NoteFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes',
        verbose_name="Folder"
    )
    title = models.CharField(max_length=255, verbose_name="Note Title")
    icon = models.CharField(max_length=50, default='file-text', verbose_name="Page Icon")
    content = models.TextField(blank=True, default='', verbose_name="Markdown Content")
    blocks = models.JSONField(default=list, blank=True, verbose_name="Structured Content Blocks")
    tags = models.JSONField(default=list, blank=True, verbose_name="Tags")
    color = models.CharField(
        max_length=20,
        choices=NoteColor.choices,
        default=NoteColor.DEFAULT,
        verbose_name="Card Color Accent"
    )
    is_pinned = models.BooleanField(default=False, verbose_name="Is Pinned")
    is_locked = models.BooleanField(default=False, verbose_name="Is Locked")
    lock_pin = models.CharField(max_length=128, blank=True, default='', verbose_name="Hashed Lock PIN")
    is_trashed = models.BooleanField(default=False, db_index=True, verbose_name="In Trash")
    trashed_at = models.DateTimeField(null=True, blank=True, verbose_name="Trashed At")
    attachments = models.JSONField(default=list, blank=True, verbose_name="Drive Attachments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_notes'
        ordering = ['-is_pinned', '-updated_at']
        verbose_name = 'Note'
        verbose_name_plural = 'Notes'

    def __str__(self):
        return self.title


class ProjectLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_project_links',
        verbose_name="User"
    )
    project = models.ForeignKey(
        WorkspaceProject,
        on_delete=models.CASCADE,
        related_name='links',
        verbose_name="Project"
    )
    title = models.CharField(max_length=200, verbose_name="Link Title")
    url = models.URLField(max_length=1000, verbose_name="Resource URL")
    link_type = models.CharField(
        max_length=20,
        choices=ProjectLinkType.choices,
        default=ProjectLinkType.WEBSITE,
        verbose_name="Link Type"
    )
    is_pinned = models.BooleanField(default=True, verbose_name="Show in Project Header")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_project_links'
        ordering = ['-is_pinned', 'created_at']
        verbose_name = 'Project Link'
        verbose_name_plural = 'Project Links'

    def __str__(self):
        return f"{self.title} ({self.project.name})"


class ProjectAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_attachments',
        verbose_name="User"
    )
    project = models.ForeignKey(
        WorkspaceProject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments',
        verbose_name="Project"
    )
    task = models.ForeignKey(
        TaskDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attachments',
        verbose_name="Linked Task"
    )
    file_name = models.CharField(max_length=255, verbose_name="File Name")
    file_type = models.CharField(max_length=100, blank=True, default='', verbose_name="MIME Type")
    file_size = models.PositiveIntegerField(default=0, verbose_name="File Size (Bytes)")
    category = models.CharField(max_length=50, blank=True, default='DOCUMENT', verbose_name="Category")
    drive_file_id = models.CharField(max_length=128, db_index=True, verbose_name="Google Drive File ID")
    drive_view_link = models.URLField(max_length=500, blank=True, default='', verbose_name="Drive View Link")
    drive_download_link = models.URLField(max_length=500, blank=True, default='', verbose_name="Drive Download Link")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workspace_project_attachments'
        ordering = ['-uploaded_at']
        verbose_name = 'Project Attachment'
        verbose_name_plural = 'Project Attachments'

    def __str__(self):
        project_label = self.project.name if self.project else "Unassigned"
        return f"{self.file_name} ({project_label})"


class CalendarEvent(models.Model):
    """
    Standalone calendar schedule entry (appointment, meeting, reminder, etc.).
    Independent from the Kanban task pipeline - no status workflow attached.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='calendar_events',
        verbose_name="User"
    )
    project = models.ForeignKey(
        WorkspaceProject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name="Project"
    )
    title = models.CharField(max_length=255, verbose_name="Event Title")
    event_type = models.CharField(
        max_length=20,
        choices=CalendarEventType.choices,
        default=CalendarEventType.APPOINTMENT,
        verbose_name="Event Type"
    )
    start_at = models.DateTimeField(db_index=True, verbose_name="Starts At")
    end_at = models.DateTimeField(null=True, blank=True, verbose_name="Ends At")
    is_all_day = models.BooleanField(default=False, verbose_name="All Day")
    notes = models.TextField(blank=True, default='', verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_calendar_events'
        ordering = ['start_at']
        verbose_name = 'Calendar Event'
        verbose_name_plural = 'Calendar Events'

    def __str__(self):
        return f"{self.title} @ {self.start_at:%Y-%m-%d %H:%M}"
