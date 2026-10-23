import uuid
from django.db import models
from django.conf import settings


class TaskStatus(models.TextChoices):
    DRAFTING = 'DRAFTING', 'In Progress'
    WAITING = 'WAITING', 'Waiting / Blocked'
    COMPLETED = 'COMPLETED', 'Completed'
    ARCHIVED = 'ARCHIVED', 'Archived'


class TaskPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


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
        default=TaskStatus.DRAFTING,
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


class Note(models.Model):
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
    title = models.CharField(max_length=255, verbose_name="Note Title")
    content = models.TextField(blank=True, default='', verbose_name="Markdown Content")
    tags = models.JSONField(default=list, blank=True, verbose_name="Tags")
    is_pinned = models.BooleanField(default=False, verbose_name="Is Pinned")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_notes'
        ordering = ['-is_pinned', '-updated_at']
        verbose_name = 'Note'
        verbose_name_plural = 'Notes'

    def __str__(self):
        return self.title
