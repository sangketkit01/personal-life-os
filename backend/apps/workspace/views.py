import calendar as calendar_lib
import uuid
from datetime import date
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import viewsets, views, permissions, status, response, mixins
from rest_framework.decorators import action
from apps.accounts.services import log_activity
from .models import (
    WorkspaceProject,
    TaskDocument,
    TaskStatus,
    Note,
    ProjectLink,
    ProjectAttachment,
    CalendarEvent
)
from .serializers import (
    WorkspaceProjectSerializer,
    TaskDocumentSerializer,
    MoveTaskStatusSerializer,
    NoteSerializer,
    ProjectLinkSerializer,
    ProjectAttachmentSerializer,
    CalendarEventSerializer
)
from .services import get_workspace_overview, transition_task_status, normalize_task_status


def _clean_uuid(val):
    if not val:
        return None
    try:
        return str(uuid.UUID(str(val)))
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_iso_date(val):
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


def _parse_month(val):
    """Parse YYYY-MM into (month_start, month_end) date pair."""
    try:
        year, month = str(val).split('-')[:2]
        year, month = int(year), int(month)
        if month < 1 or month > 12:
            return None
        last_day = calendar_lib.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)
    except (ValueError, TypeError):
        return None


class WorkspaceOverviewView(views.APIView):
    """Retrieve workspace overview summary and upcoming deadlines."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw_project_id = request.query_params.get('project_id')
        project_id = _clean_uuid(raw_project_id) if raw_project_id else None
        data = get_workspace_overview(request.user, project_id=project_id)
        return response.Response(data)


class WorkspaceProjectViewSet(viewsets.ModelViewSet):
    """CRUD for workspace projects."""
    serializer_class = WorkspaceProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = WorkspaceProject.objects.filter(user=self.request.user).annotate(
            todo_count=Count('documents', filter=Q(documents__status=TaskStatus.TODO), distinct=True),
            doing_count=Count('documents', filter=Q(documents__status=TaskStatus.DOING), distinct=True),
            done_count=Count('documents', filter=Q(documents__status=TaskStatus.DONE), distinct=True),
            total_tasks_count=Count(
                'documents',
                filter=Q(documents__status__in=[TaskStatus.TODO, TaskStatus.DOING, TaskStatus.DONE]),
                distinct=True
            ),
            pending_tasks_count=Count(
                'documents',
                filter=Q(documents__status__in=[TaskStatus.TODO, TaskStatus.DOING]),
                distinct=True
            ),
            notes_count=Count('notes', distinct=True),
            links_count=Count('links', distinct=True),
            attachments_count=Count('attachments', distinct=True)
        )
        is_archived = self.request.query_params.get('archived')
        if is_archived is not None:
            qs = qs.filter(is_archived=is_archived.lower() == 'true')
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs.order_by('name')


class TaskDocumentViewSet(viewsets.ModelViewSet):
    """CRUD and actions for tasks and documents."""
    serializer_class = TaskDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TaskDocument.objects.filter(user=self.request.user).select_related('project')

        # Filters
        raw_project_id = self.request.query_params.get('project_id')
        project_id = _clean_uuid(raw_project_id) if raw_project_id else None
        status_param = self.request.query_params.get('status')
        priority_param = self.request.query_params.get('priority')

        if project_id:
            qs = qs.filter(project_id=project_id)
        elif raw_project_id:
            qs = qs.none()
        if status_param:
            qs = qs.filter(status=normalize_task_status(status_param))
        if priority_param:
            qs = qs.filter(priority=priority_param.upper())

        # Calendar range filters
        month_range = _parse_month(self.request.query_params.get('month'))
        if month_range:
            month_start, month_end = month_range
            qs = qs.filter(
                Q(deadline__date__gte=month_start, deadline__date__lte=month_end)
                | Q(start_date__gte=month_start, start_date__lte=month_end)
                | Q(start_date__lte=month_start, deadline__date__gte=month_end)
            )

        start_lte = _parse_iso_date(self.request.query_params.get('start_date__lte'))
        if start_lte:
            qs = qs.filter(start_date__lte=start_lte)

        end_date = _parse_iso_date(self.request.query_params.get('end_date'))
        if end_date:
            qs = qs.filter(deadline__date__lte=end_date)

        return qs.order_by('deadline', '-created_at')

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Action to transition task status in Kanban board (Todo -> Doing -> Done)."""
        task = self.get_object()
        serializer = MoveTaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        transition_task_status(task, new_status)
        log_activity(task.user, 'WORKSPACE', 'MOVE_TASK', f'Changed task status of "{task.title}" to {new_status}', request=request)

        return response.Response(TaskDocumentSerializer(task, context={'request': request}).data)


class NoteViewSet(viewsets.ModelViewSet):
    """CRUD for structured Notion-style pages and Markdown notes."""
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Note.objects.filter(user=self.request.user).select_related('project')

        raw_project_id = self.request.query_params.get('project_id')
        project_id = _clean_uuid(raw_project_id) if raw_project_id else None
        tag = self.request.query_params.get('tag')
        is_pinned = self.request.query_params.get('is_pinned')
        search = self.request.query_params.get('search')

        if project_id:
            qs = qs.filter(project_id=project_id)
        elif raw_project_id:
            qs = qs.none()
        if is_pinned is not None:
            qs = qs.filter(is_pinned=is_pinned.lower() == 'true')
        if tag:
            qs = qs.filter(tags__contains=[tag])
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))

        return qs.order_by('-is_pinned', '-updated_at')

    @action(detail=True, methods=['post'], url_path='toggle-pin')
    def toggle_pin(self, request, pk=None):
        """Action to pin / unpin note."""
        note = self.get_object()
        note.is_pinned = not note.is_pinned
        note.save(update_fields=['is_pinned', 'updated_at'])
        return response.Response(NoteSerializer(note, context={'request': request}).data)


class ProjectLinkViewSet(viewsets.ModelViewSet):
    """CRUD for external project links (Website / Canva / Figma / GitHub embeds)."""
    serializer_class = ProjectLinkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ProjectLink.objects.filter(user=self.request.user).select_related('project')

        raw_project_id = self.request.query_params.get('project_id')
        project_id = _clean_uuid(raw_project_id) if raw_project_id else None
        link_type = self.request.query_params.get('link_type')
        is_pinned = self.request.query_params.get('is_pinned')

        if project_id:
            qs = qs.filter(project_id=project_id)
        elif raw_project_id:
            qs = qs.none()
        if link_type:
            qs = qs.filter(link_type=link_type.upper())
        if is_pinned is not None:
            qs = qs.filter(is_pinned=is_pinned.lower() == 'true')

        return qs.order_by('-is_pinned', 'created_at')


class ProjectAttachmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """Read / delete access to project files stored in the Google Drive vault."""
    serializer_class = ProjectAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ProjectAttachment.objects.filter(user=self.request.user).select_related('project', 'task')

        raw_project_id = self.request.query_params.get('project_id')
        project_id = _clean_uuid(raw_project_id) if raw_project_id else None
        task_id = _clean_uuid(self.request.query_params.get('task_id'))

        if project_id:
            qs = qs.filter(project_id=project_id)
        elif raw_project_id:
            qs = qs.none()
        if task_id:
            qs = qs.filter(task_id=task_id)

        return qs.order_by('-uploaded_at')

    def destroy(self, request, *args, **kwargs):
        """Delete attachment record and remove the underlying file from Google Drive."""
        attachment = self.get_object()

        from apps.storage.models import DriveFile
        from apps.storage import services as storage_services

        drive_file = DriveFile.objects.filter(
            drive_file_id=attachment.drive_file_id,
            user=request.user
        ).first()
        if drive_file:
            # delete_file_from_drive tolerates remote failures (already-deleted files)
            storage_services.delete_file_from_drive(request.user, drive_file)

        attachment.delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class CalendarEventViewSet(viewsets.ModelViewSet):
    """CRUD for standalone calendar schedule entries (not tied to the task pipeline)."""
    serializer_class = CalendarEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = CalendarEvent.objects.filter(user=self.request.user).select_related('project')

        raw_project_id = self.request.query_params.get('project_id')
        project_id = _clean_uuid(raw_project_id) if raw_project_id else None
        event_type = self.request.query_params.get('event_type')

        if project_id:
            qs = qs.filter(project_id=project_id)
        elif raw_project_id:
            qs = qs.none()
        if event_type:
            qs = qs.filter(event_type=event_type.upper())

        # Calendar range filter: events starting in the month or spanning across it
        month_range = _parse_month(self.request.query_params.get('month'))
        if month_range:
            month_start, month_end = month_range
            start_dt = timezone.make_aware(
                timezone.datetime(month_start.year, month_start.month, month_start.day, 0, 0)
            )
            end_dt = timezone.make_aware(
                timezone.datetime(month_end.year, month_end.month, month_end.day, 23, 59, 59)
            )
            qs = qs.filter(
                Q(start_at__range=[start_dt, end_dt])
                | Q(end_at__range=[start_dt, end_dt])
                | Q(start_at__lt=start_dt, end_at__gt=end_dt)
            )

        start_lte = _parse_iso_date(self.request.query_params.get('start_date__lte'))
        if start_lte:
            qs = qs.filter(start_at__date__lte=start_lte)

        end_date = _parse_iso_date(self.request.query_params.get('end_date'))
        if end_date:
            qs = qs.filter(start_at__date__gte=end_date)

        return qs.order_by('start_at')
