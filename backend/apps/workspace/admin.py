from django.contrib import admin
from .models import WorkspaceProject, TaskDocument, Note


@admin.register(WorkspaceProject)
class WorkspaceProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'color', 'icon', 'is_archived', 'created_at')
    list_filter = ('is_archived', 'color')
    search_fields = ('name', 'user__username')


@admin.register(TaskDocument)
class TaskDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'project', 'doc_number', 'status', 'priority', 'deadline', 'completed_at')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('title', 'doc_number', 'notes', 'user__username')


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'project', 'is_pinned', 'updated_at')
    list_filter = ('is_pinned', 'project')
    search_fields = ('title', 'content', 'user__username')
