from rest_framework import viewsets, views, permissions, status, response
from rest_framework.decorators import action
from apps.accounts.services import log_activity
from .models import WorkspaceProject, TaskDocument, Note
from .serializers import (
    WorkspaceProjectSerializer,
    TaskDocumentSerializer,
    MoveTaskStatusSerializer,
    NoteSerializer
)
from .services import get_workspace_overview, transition_task_status


class WorkspaceOverviewView(views.APIView):
    """API ดึงข้อมูลสรุปสถานะ Workspace และงานที่ใกล้ถึงกำหนด"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get('project_id')
        data = get_workspace_overview(request.user, project_id=project_id)
        return response.Response(data)


class WorkspaceProjectViewSet(viewsets.ModelViewSet):
    """CRUD กลุ่มงาน (Projects) สำหรับแยกประเภทงาน"""
    serializer_class = WorkspaceProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = WorkspaceProject.objects.filter(user=self.request.user)
        is_archived = self.request.query_params.get('archived')
        if is_archived is not None:
            qs = qs.filter(is_archived=is_archived.lower() == 'true')
        return qs.order_by('name')


class TaskDocumentViewSet(viewsets.ModelViewSet):
    """CRUD และ Action สำหรับงานและเอกสาร (Task & Documents)"""
    serializer_class = TaskDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TaskDocument.objects.filter(user=self.request.user).select_related('project')

        # ตัวกรอง
        project_id = self.request.query_params.get('project_id')
        status_param = self.request.query_params.get('status')
        priority_param = self.request.query_params.get('priority')

        if project_id:
            qs = qs.filter(project_id=project_id)
        if status_param:
            qs = qs.filter(status=status_param.upper())
        if priority_param:
            qs = qs.filter(priority=priority_param.upper())

        return qs.order_by('deadline', '-created_at')

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Action ย้ายสถานะเอกสารในบอร์ด Kanban (Drafting ➡️ Waiting ➡️ Completed)"""
        task = self.get_object()
        serializer = MoveTaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        transition_task_status(task, new_status)
        log_activity(task.user, 'WORKSPACE', 'MOVE_TASK', f'เปลี่ยนสถานะงาน "{task.title}" เป็น {new_status}', request=request)

        return response.Response(TaskDocumentSerializer(task, context={'request': request}).data)


class NoteViewSet(viewsets.ModelViewSet):
    """CRUD สำหรับสมุดโน้ต Markdown"""
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Note.objects.filter(user=self.request.user).select_related('project')

        project_id = self.request.query_params.get('project_id')
        tag = self.request.query_params.get('tag')
        is_pinned = self.request.query_params.get('is_pinned')

        if project_id:
            qs = qs.filter(project_id=project_id)
        if is_pinned is not None:
            qs = qs.filter(is_pinned=is_pinned.lower() == 'true')
        if tag:
            qs = qs.filter(tags__contains=[tag])

        return qs.order_by('-is_pinned', '-updated_at')

    @action(detail=True, methods=['post'], url_path='toggle-pin')
    def toggle_pin(self, request, pk=None):
        """Action ปักหมุด / ถอนหมุดโน้ต"""
        note = self.get_object()
        note.is_pinned = not note.is_pinned
        note.save(update_fields=['is_pinned', 'updated_at'])
        return response.Response(NoteSerializer(note, context={'request': request}).data)
