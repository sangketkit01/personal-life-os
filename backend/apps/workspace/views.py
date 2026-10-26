import calendar as calendar_lib
import re
import uuid
from copy import deepcopy
from datetime import date
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import viewsets, views, permissions, status, response, mixins, exceptions
from rest_framework.decorators import action
from apps.accounts.services import log_activity
from .models import (
    WorkspaceProject,
    TaskDocument,
    TaskStatus,
    Note,
    NoteFolder,
    NoteColor,
    ProjectLink,
    ProjectAttachment,
    CalendarEvent,
    InfrastructureAsset,
    ServerCredential,
    ServerRunbook
)
from .serializers import (
    WorkspaceProjectSerializer,
    TaskDocumentSerializer,
    MoveTaskStatusSerializer,
    NoteSerializer,
    is_note_unlocked_for_request,
    get_request_session_id,
    NoteFolderSerializer,
    ProjectLinkSerializer,
    ProjectAttachmentSerializer,
    CalendarEventSerializer,
    InfrastructureAssetSerializer,
    ServerCredentialSerializer,
    ServerRunbookSerializer
)
from .services import get_workspace_overview, transition_task_status, normalize_task_status
from .ssh_service import (
    probe_server_telemetry,
    manage_docker_container,
    execute_remote_command,
    SshConnectionError
)
from apps.storage.encryption import decrypt_token


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
            notes_count=Count('notes', filter=Q(notes__is_trashed=False), distinct=True),
            links_count=Count('links', distinct=True),
            attachments_count=Count('attachments', distinct=True),
            infra_count=Count('infrastructure_assets', distinct=True)
        )
        is_archived = self.request.query_params.get('archived')
        if is_archived is not None:
            qs = qs.filter(is_archived=is_archived.lower() == 'true')
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs.order_by('name')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # MA economics is a multi-query payload: detail + PATCH responses only.
        if self.action in ('retrieve', 'update', 'partial_update'):
            context['include_economics'] = True
        return context


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


class NoteFolderViewSet(viewsets.ModelViewSet):
    """CRUD for standalone note folders."""
    serializer_class = NoteFolderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NoteFolder.objects.filter(user=self.request.user).annotate(
            notes_count=Count(
                'notes',
                filter=Q(notes__project__isnull=True, notes__is_trashed=False),
                distinct=True
            )
        ).order_by('position', 'name')


class NoteViewSet(viewsets.ModelViewSet):
    """CRUD for structured Notion-style pages and standalone notes."""
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Note.objects.filter(user=self.request.user).select_related('project', 'folder')

        raw_project_id = self.request.query_params.get('project_id')
        project_id = _clean_uuid(raw_project_id) if raw_project_id else None
        tag = self.request.query_params.get('tag')
        is_pinned = self.request.query_params.get('is_pinned')
        is_locked = self.request.query_params.get('is_locked')
        color = self.request.query_params.get('color')
        search = self.request.query_params.get('search')
        standalone = self.request.query_params.get('standalone')
        trashed = self.request.query_params.get('trashed')
        folder_id = self.request.query_params.get('folder_id')

        # Trash scoping: default to live notes unless explicitly listing trash
        if trashed is not None:
            qs = qs.filter(is_trashed=trashed.lower() == 'true')
        else:
            qs = qs.filter(is_trashed=False)

        # Standalone notes (no project) vs project pages
        if standalone is not None and standalone.lower() == 'true':
            qs = qs.filter(project__isnull=True)

        if project_id:
            qs = qs.filter(project_id=project_id, is_trashed=False)
        elif raw_project_id:
            qs = qs.none()

        # Folder scoping ('unfiled' = no folder)
        if folder_id:
            if folder_id.lower() == 'unfiled':
                qs = qs.filter(folder__isnull=True)
            else:
                clean_folder = _clean_uuid(folder_id)
                if clean_folder:
                    qs = qs.filter(folder_id=clean_folder)
                else:
                    qs = qs.none()

        if is_pinned is not None:
            qs = qs.filter(is_pinned=is_pinned.lower() == 'true')
        if is_locked is not None:
            qs = qs.filter(is_locked=is_locked.lower() == 'true')
        if color:
            qs = qs.filter(color=color.upper())
        if tag:
            qs = qs.filter(tags__contains=[tag])
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))

        return qs.order_by('-is_pinned', '-updated_at')

    def perform_update(self, serializer):
        note = serializer.instance
        if note.is_locked and note.lock_pin:
            if not is_note_unlocked_for_request(self.request, note):
                raise exceptions.PermissionDenied('Note is locked. PIN verification required.')
        serializer.save()

    @action(detail=True, methods=['post'], url_path='toggle-pin')
    def toggle_pin(self, request, pk=None):
        """Action to pin / unpin note."""
        note = self.get_object()
        note.is_pinned = not note.is_pinned
        note.save(update_fields=['is_pinned', 'updated_at'])
        return response.Response(NoteSerializer(note, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def trash(self, request, pk=None):
        """Move a note to trash (soft delete)."""
        note = self.get_object()
        note.is_trashed = True
        note.trashed_at = timezone.now()
        note.is_pinned = False
        note.save(update_fields=['is_trashed', 'trashed_at', 'is_pinned', 'updated_at'])
        log_activity(request.user, 'WORKSPACE', 'TRASH_NOTE', f'Moved note "{note.title}" to trash', request=request)
        return response.Response(NoteSerializer(note, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a note from trash (bypasses the default live-notes queryset)."""
        note_id = _clean_uuid(pk)
        note = Note.objects.filter(id=note_id, user=request.user).first() if note_id else None
        if not note:
            return response.Response({'error': 'Note not found.'}, status=status.HTTP_404_NOT_FOUND)
        note.is_trashed = False
        note.trashed_at = None
        note.save(update_fields=['is_trashed', 'trashed_at', 'updated_at'])
        return response.Response(NoteSerializer(note, context={'request': request}).data)

    @action(detail=False, methods=['post'], url_path='empty-trash')
    def empty_trash(self, request):
        """Permanently delete every trashed note of the current user."""
        deleted, _ = Note.objects.filter(user=request.user, is_trashed=True).delete()
        return response.Response({'deleted': deleted})

    @action(detail=True, methods=['post'], url_path='set-lock')
    def set_lock(self, request, pk=None):
        """Lock or unlock a note with an optional 4-6 digit PIN."""
        note = self.get_object()
        is_locked = bool(request.data.get('is_locked'))
        pin = str(request.data.get('pin') or '').strip()
        old_pin = str(request.data.get('old_pin') or request.data.get('current_pin') or '').strip()
        is_unlocked = is_note_unlocked_for_request(request, note)

        if is_locked:
            if pin:
                if not re.fullmatch(r'\d{4,6}', pin):
                    return response.Response(
                        {'error': 'PIN must be 4 to 6 digits.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # If modifying an already locked note's PIN, require old PIN or active unlock
                if note.is_locked and note.lock_pin:
                    if not (is_unlocked or (old_pin and check_password(old_pin, note.lock_pin))):
                        return response.Response(
                            {'error': 'Current PIN or active unlock is required to change PIN.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                note.lock_pin = make_password(pin)
            elif not note.lock_pin:
                return response.Response(
                    {'error': 'A 4 to 6 digit PIN is required to lock this note.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Empty pin with an existing hash keeps the current PIN
        else:
            if note.lock_pin:
                provided_pin = pin or old_pin
                if not provided_pin or not check_password(provided_pin, note.lock_pin):
                    return response.Response(
                        {'error': 'Incorrect PIN. Could not remove the lock.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            note.lock_pin = ''

        # Invalidate any active session unlock tokens across this and other user sessions
        session_id = get_request_session_id(request)
        cache.delete(f"note_unlocked:{request.user.id}:{session_id}:{note.id}")
        cache.delete(f"note_unlocked:{request.user.id}:{note.id}")
        try:
            from apps.accounts.models import UserDeviceSession
            user_sids = UserDeviceSession.objects.filter(user_id=request.user.id).values_list('id', flat=True)
            for sid in user_sids:
                cache.delete(f"note_unlocked:{request.user.id}:{sid}:{note.id}")
        except Exception:
            pass
        if hasattr(request, 'session'):
            unlocked = request.session.get('unlocked_notes', [])
            if str(note.id) in unlocked:
                unlocked.remove(str(note.id))
                request.session.modified = True

        note.is_locked = is_locked
        note.save(update_fields=['is_locked', 'lock_pin', 'updated_at'])
        return response.Response(NoteSerializer(note, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='verify-lock')
    def verify_lock(self, request, pk=None):
        """Verify a note's lock PIN for this session."""
        note = self.get_object()
        if not note.is_locked or not note.lock_pin:
            return response.Response({'verified': True})
        pin = str(request.data.get('pin') or '')
        verified = bool(pin) and check_password(pin, note.lock_pin)
        if verified:
            session_id = get_request_session_id(request)
            cache.set(f"note_unlocked:{request.user.id}:{session_id}:{note.id}", True, timeout=3600)
        return response.Response({'verified': verified})

    @action(detail=True, methods=['post'], url_path='copy-to-project')
    def copy_to_project(self, request, pk=None):
        """Duplicate a standalone note into a Workspace Project as a Project Page."""
        note = self.get_object()
        if note.is_locked and note.lock_pin:
            if not is_note_unlocked_for_request(request, note):
                return response.Response(
                    {'error': 'Cannot copy a locked note without PIN verification.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        raw_project_id = request.data.get('project_id')
        project_id = _clean_uuid(raw_project_id) if raw_project_id else None
        if not project_id:
            return response.Response(
                {'error': 'A valid project_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        project = WorkspaceProject.objects.filter(id=project_id, user=request.user).first()
        if not project:
            return response.Response(
                {'error': 'Project not found or does not belong to user.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        duplicate = Note.objects.create(
            user=request.user,
            project=project,
            folder=None,
            title=note.title,
            icon=note.icon,
            content=note.content,
            blocks=deepcopy(note.blocks),
            tags=list(note.tags or []),
            color=note.color,
            is_pinned=False,
            is_locked=False,
            lock_pin='',
            is_trashed=False,
            trashed_at=None,
            attachments=deepcopy(note.attachments)
        )
        log_activity(
            request.user,
            'WORKSPACE',
            'COPY_NOTE_TO_PROJECT',
            f'Copied note "{note.title}" into project "{project.name}"',
            request=request
        )
        return response.Response(
            NoteSerializer(duplicate, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


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


class InfrastructureAssetViewSet(viewsets.ModelViewSet):
    """CRUD + SSH actions for infrastructure assets (VPS, DB, domain, ...)."""
    serializer_class = InfrastructureAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = InfrastructureAsset.objects.filter(
            user=self.request.user
        ).select_related('project').prefetch_related('shared_projects')
        project_id = _clean_uuid(self.request.query_params.get('project_id'))
        if project_id:
            # Include assets shared into this project, not just primary ones.
            qs = qs.filter(
                Q(project_id=project_id) | Q(shared_projects__id=project_id)
            ).distinct()
        return qs.order_by('name')

    def _get_owned_project_or_404(self, project_id):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(WorkspaceProject, id=project_id, user=self.request.user)

    @action(detail=True, methods=['post'], url_path='link-project')
    def link_project(self, request, pk=None):
        """Share this asset with another project owned by the request user."""
        asset = self.get_object()
        project_id = _clean_uuid(request.data.get('project_id'))
        if not project_id:
            return response.Response(
                {'detail': 'project_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        project = self._get_owned_project_or_404(project_id)
        if asset.project_id != project.id:
            asset.shared_projects.add(project)
            asset.save(update_fields=['updated_at'])
        return response.Response(
            InfrastructureAssetSerializer(asset, context={'request': request}).data
        )

    @action(detail=True, methods=['post'], url_path='unlink-project')
    def unlink_project(self, request, pk=None):
        """Detach a project from this asset without deleting the asset itself."""
        from .services import sync_infra_asset_obligation
        asset = self.get_object()
        project_id = _clean_uuid(request.data.get('project_id'))
        if not project_id:
            return response.Response(
                {'detail': 'project_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        project = self._get_owned_project_or_404(project_id)
        if str(asset.project_id) == str(project.id):
            # Removing the primary: promote the first shared project (if any)
            # so the asset always keeps an owner project when possible, and
            # drop it from the M2M so it is not counted twice.
            promoted = asset.shared_projects.first()
            if promoted is not None:
                asset.shared_projects.remove(promoted)
            asset.project = promoted
            asset.save(update_fields=['project', 'updated_at'])
        else:
            asset.shared_projects.remove(project)
        sync_infra_asset_obligation(asset)
        return response.Response(
            InfrastructureAssetSerializer(asset, context={'request': request}).data
        )

    @action(detail=True, methods=['post'], url_path='trust-host-key')
    def trust_host_key(self, request, pk=None):
        """Explicitly confirm and trust the SSH host key for this asset."""
        asset = self.get_object()
        fingerprint = str(request.data.get('fingerprint') or '').strip()
        if fingerprint:
            asset.ssh_host_fingerprint = fingerprint
            asset.save(update_fields=['ssh_host_fingerprint', 'updated_at'])
        else:
            try:
                client = open_ssh_client(asset, timeout=5, accept_new_host_key=True)
                client.close()
            except SshConnectionError as sce:
                return response.Response({'detail': str(sce)}, status=status.HTTP_400_BAD_REQUEST)
        return response.Response({
            'detail': 'Host key trusted successfully.',
            'ssh_host_fingerprint': asset.ssh_host_fingerprint,
            'asset': InfrastructureAssetSerializer(asset, context={'request': request}).data
        })

    @action(detail=True, methods=['post'])
    def probe(self, request, pk=None):
        """Live agentless SSH probe: uptime, CPU, RAM, disk, docker containers."""
        asset = self.get_object()
        confirm = bool(request.data.get('confirm_host_key') or request.query_params.get('confirm_host_key'))
        telemetry = probe_server_telemetry(asset, accept_new_host_key=confirm)
        try:
            log_activity(
                request.user, 'WORKSPACE', 'INFRA_PROBE',
                f'SSH probe on {asset.name}: {asset.health_status}', request=request
            )
        except Exception:
            pass
        return response.Response({
            'health_status': asset.health_status,
            'telemetry': telemetry,
            'asset': InfrastructureAssetSerializer(asset).data
        })

    @action(detail=True, methods=['post'])
    def docker(self, request, pk=None):
        """Start / stop / restart a docker container or fetch its logs."""
        asset = self.get_object()
        container_id = request.data.get('container_id', '')
        docker_action = request.data.get('action', '')
        tail = request.data.get('tail', 100)
        confirm = bool(request.data.get('confirm_host_key') or request.query_params.get('confirm_host_key'))
        try:
            result = manage_docker_container(asset, container_id, docker_action, tail, accept_new_host_key=confirm)
        except ValueError as ve:
            return response.Response({'detail': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except SshConnectionError as sce:
            return response.Response({'detail': str(sce)}, status=status.HTTP_502_BAD_GATEWAY)
        try:
            log_activity(
                request.user, 'WORKSPACE', 'DOCKER_ACTION',
                f'Docker {docker_action} on {asset.name} (container {container_id})', request=request
            )
        except Exception:
            pass
        return response.Response(result)

    @action(detail=True, methods=['post'], url_path='exec')
    def exec_command(self, request, pk=None):
        """Run a quick one-shot command on the asset over SSH."""
        asset = self.get_object()
        command = request.data.get('command', '')
        working_dir = request.data.get('working_dir', '')
        timeout = request.data.get('timeout', 60)
        confirm = bool(request.data.get('confirm_host_key') or request.query_params.get('confirm_host_key'))
        try:
            result = execute_remote_command(asset, command, working_dir, timeout, accept_new_host_key=confirm)
        except ValueError as ve:
            return response.Response({'detail': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except SshConnectionError as sce:
            return response.Response({'detail': str(sce)}, status=status.HTTP_502_BAD_GATEWAY)
        try:
            log_activity(
                request.user, 'WORKSPACE', 'SSH_EXEC',
                f'Command executed on {asset.name} (exit {result.get("exit_status")})', request=request
            )
        except Exception:
            pass
        return response.Response(result)


class ServerCredentialViewSet(viewsets.ModelViewSet):
    """Encrypted secret vault CRUD + audited single-entry reveal."""
    serializer_class = ServerCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ServerCredential.objects.filter(user=self.request.user).select_related('project', 'asset')
        project_id = _clean_uuid(self.request.query_params.get('project_id'))
        if project_id:
            qs = qs.filter(project_id=project_id)
        asset_id = _clean_uuid(self.request.query_params.get('asset_id'))
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        return qs.order_by('title')

    @action(detail=True, methods=['post'])
    def reveal(self, request, pk=None):
        """Decrypt and return the plaintext secret for one vault entry."""
        from apps.storage.encryption import EncryptionError
        credential = self.get_object()
        try:
            secret = decrypt_token(credential.secret_encrypted)
        except EncryptionError:
            return response.Response(
                {'error': 'Failed to decrypt credential secret.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        try:
            log_activity(
                request.user, 'WORKSPACE', 'REVEAL_CREDENTIAL',
                f'Secret revealed: {credential.title}', request=request
            )
        except Exception:
            pass
        return response.Response({'id': str(credential.id), 'secret': secret})


class ServerRunbookViewSet(viewsets.ModelViewSet):
    """User-defined runbook CRUD + remote execution."""
    serializer_class = ServerRunbookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ServerRunbook.objects.filter(user=self.request.user).select_related('project', 'asset')
        project_id = _clean_uuid(self.request.query_params.get('project_id'))
        if project_id:
            qs = qs.filter(project_id=project_id)
        asset_id = _clean_uuid(self.request.query_params.get('asset_id'))
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        return qs.order_by('title')

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute the runbook on its bound asset and persist the last result."""
        runbook = self.get_object()
        if not (runbook.command or '').strip():
            return response.Response(
                {'detail': 'Runbook has no command to execute.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        confirm = bool(request.data.get('confirm_host_key') or request.query_params.get('confirm_host_key'))
        try:
            result = execute_remote_command(
                runbook.asset, runbook.command, runbook.working_dir, runbook.timeout_seconds,
                accept_new_host_key=confirm
            )
        except SshConnectionError as sce:
            return response.Response({'detail': str(sce)}, status=status.HTTP_502_BAD_GATEWAY)

        combined_output = result['stdout']
        if result['stderr']:
            combined_output = (combined_output + '\n' + result['stderr']) if combined_output else result['stderr']
        runbook.last_run_at = timezone.now()
        runbook.last_exit_code = result['exit_status']
        runbook.last_output = combined_output[:20000]
        runbook.save(update_fields=['last_run_at', 'last_exit_code', 'last_output', 'updated_at'])

        try:
            log_activity(
                request.user, 'WORKSPACE', 'RUNBOOK_EXEC',
                f'Runbook {runbook.title} on {runbook.asset.name} (exit {result["exit_status"]})',
                request=request
            )
        except Exception:
            pass
        return response.Response({'result': result, 'runbook': ServerRunbookSerializer(runbook).data})
