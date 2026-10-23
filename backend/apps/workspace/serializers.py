from rest_framework import serializers
from .models import WorkspaceProject, TaskDocument, TaskStatus, TaskPriority, Note
from .services import calculate_deadline_info, transition_task_status


class WorkspaceProjectSerializer(serializers.ModelSerializer):
    pending_tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkspaceProject
        fields = ('id', 'name', 'description', 'color', 'icon', 'is_archived', 'pending_tasks_count', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_pending_tasks_count(self, obj):
        return obj.documents.filter(status__in=[TaskStatus.DRAFTING, TaskStatus.WAITING]).count()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TaskDocumentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True, default=None)
    project_color = serializers.CharField(source='project.color', read_only=True, default=None)
    deadline_info = serializers.SerializerMethodField()

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
            'deadline_info',
            'file_url',
            'notes',
            'metadata',
            'completed_at',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'completed_at', 'created_at', 'updated_at')

    def get_deadline_info(self, obj):
        if obj.status in [TaskStatus.COMPLETED, TaskStatus.ARCHIVED]:
            return {
                'is_overdue': False,
                'urgency': 'NORMAL',
                'label': 'Completed' if obj.status == TaskStatus.COMPLETED else 'Archived'
            }
        return calculate_deadline_info(obj.deadline)

    def validate_project(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError('You do not have permission to access this project.')
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        # Set completed_at timestamp if created directly as COMPLETED
        if validated_data.get('status') == TaskStatus.COMPLETED:
            from django.utils import timezone
            validated_data['completed_at'] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from django.utils import timezone
        if 'status' in validated_data:
            new_status = validated_data['status']
            if new_status == TaskStatus.COMPLETED and instance.status != TaskStatus.COMPLETED:
                validated_data['completed_at'] = timezone.now()
            elif new_status != TaskStatus.COMPLETED and instance.status == TaskStatus.COMPLETED:
                validated_data['completed_at'] = None
        return super().update(instance, validated_data)


class MoveTaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TaskStatus.choices)


class NoteSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True, default=None)

    class Meta:
        model = Note
        fields = ('id', 'project', 'project_name', 'title', 'content', 'tags', 'is_pinned', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_project(self, value):
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError('You do not have permission to access this project.')
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
