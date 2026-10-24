import html as html_lib
import re
import uuid
from rest_framework import serializers
from .models import (
    WorkspaceProject,
    TaskDocument,
    TaskStatus,
    TaskPriority,
    Note,
    NoteFolder,
    NoteColor,
    ProjectLink,
    ProjectLinkType,
    ProjectAttachment,
    CalendarEvent,
    CalendarEventType
)
from .services import calculate_deadline_info, normalize_task_status, transition_task_status

# Accepted status values for API input (modern Kanban + legacy pipeline aliases).
# Declared as (value, label) tuples so ChoiceField validation accepts legacy
# aliases BEFORE validate_status() normalizes them to modern equivalents.
TASK_STATUS_INPUT_CHOICES = list(TaskStatus.choices) + [
    ('DRAFTING', 'Drafting (legacy)'),
    ('WAITING', 'Waiting (legacy)'),
    ('COMPLETED', 'Completed (legacy)'),
]


def strip_html_tags(value: str) -> str:
    """Remove inline HTML tags and unescape entities for clean-text summaries."""
    if not value:
        return ''
    text = re.sub(r'<[^>]*>', ' ', str(value))
    text = html_lib.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def summarize_blocks(blocks) -> str:
    """Build a plain-text summary from structured note blocks for search and previews.

    Includes image/audio captions and file names plus table cell text so
    full-text search (?search=...) finds content inside media and tables.
    """
    if not isinstance(blocks, list):
        return ''
    parts = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get('type') or '')
        pieces = []
        text = strip_html_tags(str(block.get('content') or '')).strip()
        if text:
            pieces.append(text)
        if block_type in ('image', 'audio'):
            file_name = str(block.get('file_name') or '').strip()
            if file_name:
                pieces.append(file_name)
        if block_type == 'table':
            rows = block.get('rows')
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, list):
                        for cell in row:
                            cell_text = str(cell).strip()
                            if cell_text:
                                pieces.append(cell_text)
        combined = ' '.join(pieces).strip()
        if combined:
            parts.append(combined)
    return '\n'.join(parts)


class WorkspaceProjectSerializer(serializers.ModelSerializer):
    pending_tasks_count = serializers.SerializerMethodField()
    total_tasks_count = serializers.SerializerMethodField()
    completed_tasks_count = serializers.SerializerMethodField()
    todo_count = serializers.SerializerMethodField()
    doing_count = serializers.SerializerMethodField()
    notes_count = serializers.SerializerMethodField()
    links_count = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkspaceProject
        fields = (
            'id',
            'name',
            'description',
            'color',
            'icon',
            'status',
            'category',
            'start_date',
            'target_date',
            'is_archived',
            'metadata',
            'pending_tasks_count',
            'total_tasks_count',
            'completed_tasks_count',
            'todo_count',
            'doing_count',
            'notes_count',
            'links_count',
            'attachments_count',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def _annotated(self, obj, attr, fallback_queryset):
        value = getattr(obj, attr, None)
        return value if value is not None else fallback_queryset.count()

    def get_pending_tasks_count(self, obj):
        return self._annotated(
            obj,
            'pending_tasks_count',
            obj.documents.filter(status__in=[TaskStatus.TODO, TaskStatus.DOING])
        )

    def get_total_tasks_count(self, obj):
        return self._annotated(
            obj,
            'total_tasks_count',
            obj.documents.filter(status__in=[TaskStatus.TODO, TaskStatus.DOING, TaskStatus.DONE])
        )

    def get_completed_tasks_count(self, obj):
        return self._annotated(
            obj,
            'done_count',
            obj.documents.filter(status=TaskStatus.DONE)
        )

    def get_todo_count(self, obj):
        return self._annotated(obj, 'todo_count', obj.documents.filter(status=TaskStatus.TODO))

    def get_doing_count(self, obj):
        return self._annotated(obj, 'doing_count', obj.documents.filter(status=TaskStatus.DOING))

    def get_notes_count(self, obj):
        return self._annotated(obj, 'notes_count', obj.notes.filter(is_trashed=False))

    def get_links_count(self, obj):
        return self._annotated(obj, 'links_count', obj.links)

    def get_attachments_count(self, obj):
        return self._annotated(obj, 'attachments_count', obj.attachments)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TaskDocumentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True, default=None)
    project_color = serializers.CharField(source='project.color', read_only=True, default=None)
    deadline_info = serializers.SerializerMethodField()
    checklist_progress = serializers.SerializerMethodField()
    # Explicit override: accept legacy status aliases on create/update too
    status = serializers.ChoiceField(
        choices=TASK_STATUS_INPUT_CHOICES,
        required=False,
        default=TaskStatus.TODO
    )

    class Meta:
        model = TaskDocument
        fields = (
            'id',
            'project',
            'project_name',
            'project_color',
            'title',
            'doc_number',
            'status',
            'priority',
            'deadline',
            'start_date',
            'deadline_info',
            'checklist',
            'checklist_progress',
            'links',
            'position',
            'file_url',
            'notes',
            'metadata',
            'completed_at',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'completed_at', 'created_at', 'updated_at')

    def get_deadline_info(self, obj):
        if obj.status in [TaskStatus.DONE, TaskStatus.ARCHIVED]:
            return {
                'is_overdue': False,
                'urgency': 'NORMAL',
                'label': 'Completed' if obj.status == TaskStatus.DONE else 'Archived'
            }
        return calculate_deadline_info(obj.deadline)

    def get_checklist_progress(self, obj):
        items = obj.checklist if isinstance(obj.checklist, list) else []
        total = len(items)
        done = sum(1 for item in items if isinstance(item, dict) and item.get('is_completed'))
        return {'total': total, 'completed': done}

    def validate_project(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError('You do not have permission to access this project.')
        return value

    def validate_status(self, value):
        return normalize_task_status(value)

    def validate_checklist(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Checklist must be a list of items.')
        cleaned = []
        for item in value:
            if not isinstance(item, dict) or not str(item.get('title', '')).strip():
                raise serializers.ValidationError('Each checklist item requires a non-empty title.')
            cleaned.append({
                'id': str(item.get('id') or uuid.uuid4()),
                'title': str(item.get('title')).strip(),
                'is_completed': bool(item.get('is_completed', False))
            })
        return cleaned

    def validate_links(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Links must be a list of {title, url} objects.')
        cleaned = []
        for item in value:
            if not isinstance(item, dict) or not str(item.get('url', '')).strip():
                raise serializers.ValidationError('Each reference link requires a URL.')
            cleaned.append({
                'title': str(item.get('title') or item.get('url')).strip()[:200],
                'url': str(item.get('url')).strip()
            })
        return cleaned

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        # Set completed_at timestamp if created directly as DONE
        if validated_data.get('status') == TaskStatus.DONE:
            from django.utils import timezone
            validated_data['completed_at'] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from django.utils import timezone
        if 'status' in validated_data:
            new_status = validated_data['status']
            if new_status == TaskStatus.DONE and instance.status != TaskStatus.DONE:
                validated_data['completed_at'] = timezone.now()
            elif new_status != TaskStatus.DONE and instance.status == TaskStatus.DONE:
                validated_data['completed_at'] = None
        return super().update(instance, validated_data)


class MoveTaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TASK_STATUS_INPUT_CHOICES)

    def validate_status(self, value):
        return normalize_task_status(value)


class NoteFolderSerializer(serializers.ModelSerializer):
    notes_count = serializers.SerializerMethodField()

    class Meta:
        model = NoteFolder
        fields = (
            'id',
            'name',
            'icon',
            'color',
            'position',
            'notes_count',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_notes_count(self, obj):
        annotated = getattr(obj, 'notes_count', None)
        if annotated is not None:
            return annotated
        return obj.notes.filter(project__isnull=True, is_trashed=False).count()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NoteSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True, default=None)
    folder_name = serializers.CharField(source='folder.name', read_only=True, default=None)
    has_lock_pin = serializers.SerializerMethodField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default='Untitled')

    class Meta:
        model = Note
        fields = (
            'id',
            'project',
            'project_name',
            'folder',
            'folder_name',
            'title',
            'icon',
            'content',
            'blocks',
            'tags',
            'color',
            'is_pinned',
            'is_locked',
            'has_lock_pin',
            'is_trashed',
            'trashed_at',
            'attachments',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
        # lock_pin is intentionally excluded - it is only managed via the
        # set-lock / verify-lock actions and never exposed or writable here.

    def get_has_lock_pin(self, obj):
        return bool(obj.lock_pin)

    def validate_title(self, value):
        cleaned = (value or '').strip()
        return cleaned if cleaned else 'Untitled'

    def validate_project(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError('You do not have permission to access this project.')
        return value

    def validate_folder(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError('You do not have permission to access this folder.')
        return value

    def validate_color(self, value):
        if value not in NoteColor.values:
            raise serializers.ValidationError('Invalid note color.')
        return value

    MAX_TABLE_ROWS = 50
    MAX_TABLE_COLS = 12
    ALLOWED_IMAGE_WIDTHS = ('50%', '75%', '100%')
    DEFAULT_TABLE_ROWS = [['Column 1', 'Column 2', 'Column 3'], ['', '', '']]

    def _clean_table_rows(self, raw_rows):
        """Normalize table rows into a rectangular 2D list of strings (max 50x12)."""
        if not isinstance(raw_rows, list):
            return []
        cleaned = []
        for row in raw_rows[:self.MAX_TABLE_ROWS]:
            if isinstance(row, list):
                cells = [str(cell) for cell in row[:self.MAX_TABLE_COLS]]
            else:
                cells = [str(row)][:self.MAX_TABLE_COLS]
            cleaned.append(cells)
        if cleaned:
            width = min(max(len(r) for r in cleaned), self.MAX_TABLE_COLS)
            for row in cleaned:
                row.extend([''] * (width - len(row)))
        return cleaned

    def validate_blocks(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Blocks must be a list of content blocks.')
        cleaned = []
        for block in value:
            if not isinstance(block, dict):
                continue
            try:
                indent = int(block.get('indent') or 0)
            except (TypeError, ValueError):
                indent = 0
            try:
                file_size = max(0, int(block.get('file_size') or 0))
            except (TypeError, ValueError):
                file_size = 0
            try:
                duration = max(0.0, float(block.get('duration') or 0))
            except (TypeError, ValueError):
                duration = 0.0

            width = str(block.get('width') or '100%')
            if width not in self.ALLOWED_IMAGE_WIDTHS:
                width = '100%'

            rows = self._clean_table_rows(block.get('rows'))
            if str(block.get('type') or '') == 'table' and not rows:
                rows = [list(r) for r in self.DEFAULT_TABLE_ROWS]

            cleaned.append({
                'id': str(block.get('id') or uuid.uuid4()),
                'type': str(block.get('type') or 'paragraph'),
                'content': str(block.get('content') or ''),
                'checked': bool(block.get('checked', False)),
                'indent': max(0, min(4, indent)),
                'language': str(block.get('language') or ''),
                # Multimedia fields (image / audio blocks)
                'drive_file_id': str(block.get('drive_file_id') or '').strip(),
                'file_url': str(block.get('file_url') or '').strip(),
                'file_name': str(block.get('file_name') or '').strip(),
                'file_type': str(block.get('file_type') or '').strip(),
                'file_size': file_size,
                'width': width,
                'duration': duration,
                # Table field (table blocks)
                'rows': rows
            })
        return cleaned

    def validate_attachments(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Attachments must be a list of Drive file metadata.')
        cleaned = []
        for item in value:
            if not isinstance(item, dict) or not str(item.get('drive_file_id', '')).strip():
                continue
            cleaned.append({
                'id': str(item.get('id') or uuid.uuid4()),
                'file_name': str(item.get('file_name') or 'Untitled'),
                'file_type': str(item.get('file_type') or ''),
                'file_size': int(item.get('file_size') or 0),
                'drive_file_id': str(item.get('drive_file_id')).strip(),
                'drive_view_link': str(item.get('drive_view_link') or ''),
                'uploaded_at': str(item.get('uploaded_at') or '')
            })
        return cleaned

    def _sync_content(self, validated_data):
        blocks = validated_data.get('blocks')
        if blocks is not None and not str(validated_data.get('content') or '').strip():
            validated_data['content'] = summarize_blocks(blocks)
        return validated_data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        if not validated_data.get('title'):
            validated_data['title'] = 'Untitled'
        if not validated_data.get('blocks'):
            validated_data['blocks'] = [{
                'id': str(uuid.uuid4()),
                'type': 'paragraph',
                'content': '',
                'checked': False,
                'indent': 0,
                'language': '',
                'drive_file_id': '',
                'file_url': '',
                'file_name': '',
                'file_type': '',
                'file_size': 0,
                'width': '100%',
                'duration': 0.0,
                'rows': []
            }]
        validated_data = self._sync_content(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._sync_content(validated_data)
        return super().update(instance, validated_data)


class ProjectLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectLink
        fields = (
            'id',
            'project',
            'title',
            'url',
            'link_type',
            'is_pinned',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_project(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError('You do not have permission to access this project.')
        return value

    def validate_link_type(self, value):
        if value not in ProjectLinkType.values:
            raise serializers.ValidationError('Invalid link type.')
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ProjectAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAttachment
        fields = (
            'id',
            'project',
            'task',
            'file_name',
            'file_type',
            'file_size',
            'category',
            'drive_file_id',
            'drive_view_link',
            'drive_download_link',
            'uploaded_at'
        )
        read_only_fields = fields


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = (
            'id',
            'project',
            'title',
            'event_type',
            'start_at',
            'end_at',
            'is_all_day',
            'notes',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_project(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError('You do not have permission to access this project.')
        return value

    def validate_event_type(self, value):
        if value not in CalendarEventType.values:
            raise serializers.ValidationError('Invalid event type.')
        return value

    def validate(self, attrs):
        start_at = attrs.get('start_at')
        end_at = attrs.get('end_at')
        if self.instance is not None:
            start_at = start_at if start_at is not None else self.instance.start_at
            end_at = end_at if end_at is not None else self.instance.end_at
        if start_at and end_at and end_at < start_at:
            raise serializers.ValidationError('End time must be after the start time.')
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
