from datetime import date, timedelta
from typing import Dict, Any, List
from django.db.models import Count, Q
from django.utils import timezone
from .models import WorkspaceProject, TaskDocument, TaskStatus, Note


def calculate_deadline_info(deadline) -> Dict[str, Any]:
    """Calculate remaining time and urgency indicator for a deadline."""
    if not deadline:
        return {
            'days_left': None,
            'urgency': 'NONE',
            'is_overdue': False,
            'label': 'No deadline'
        }

    now = timezone.now()
    today = timezone.localdate()
    deadline_date = timezone.localtime(deadline).date()

    days_diff = (deadline_date - today).days

    if deadline < now:
        return {
            'days_left': days_diff,
            'urgency': 'OVERDUE',
            'is_overdue': True,
            'label': 'Overdue'
        }
    elif days_diff == 0:
        return {
            'days_left': 0,
            'urgency': 'CRITICAL',
            'is_overdue': False,
            'label': 'Due Today'
        }
    elif days_diff == 1:
        return {
            'days_left': 1,
            'urgency': 'WARNING',
            'is_overdue': False,
            'label': 'Due Tomorrow'
        }
    elif days_diff <= 3:
        return {
            'days_left': days_diff,
            'urgency': 'ATTENTION',
            'is_overdue': False,
            'label': f'{days_diff} days left'
        }
    else:
        return {
            'days_left': days_diff,
            'urgency': 'NORMAL',
            'is_overdue': False,
            'label': f'{days_diff} days left'
        }


def transition_task_status(task: TaskDocument, new_status: str) -> TaskDocument:
    """Transition task/document status and automatically update completed_at timestamp."""
    if new_status not in TaskStatus.values:
        raise ValueError(f"Invalid task status: {new_status}")

    task.status = new_status
    if new_status == TaskStatus.COMPLETED:
        task.completed_at = timezone.now()
    else:
        # Reset completed_at if moved back to in-progress
        task.completed_at = None

    task.save()
    return task


def get_workspace_overview(user, project_id: str = None) -> Dict[str, Any]:
    """Retrieve workspace summary and active pipelines for user."""
    tasks_qs = TaskDocument.objects.filter(user=user)
    if project_id:
        tasks_qs = tasks_qs.filter(project_id=project_id)

    # Status counts
    drafting_count = tasks_qs.filter(status=TaskStatus.DRAFTING).count()
    waiting_count = tasks_qs.filter(status=TaskStatus.WAITING).count()
    completed_count = tasks_qs.filter(status=TaskStatus.COMPLETED).count()
    archived_count = tasks_qs.filter(status=TaskStatus.ARCHIVED).count()

    now = timezone.now()
    next_7_days = now + timedelta(days=7)

    # Active tasks (Drafting or Waiting)
    active_tasks = tasks_qs.filter(status__in=[TaskStatus.DRAFTING, TaskStatus.WAITING])

    # Overdue tasks
    overdue_count = active_tasks.filter(deadline__lt=now).count()

    # Upcoming tasks in 7 days (select_related avoids N+1)
    upcoming_tasks = active_tasks.filter(
        deadline__gte=now,
        deadline__lte=next_7_days
    ).select_related('project').order_by('deadline')

    upcoming_list = []
    for t in upcoming_tasks[:5]:
        dl_info = calculate_deadline_info(t.deadline)
        upcoming_list.append({
            'id': str(t.id),
            'title': t.title,
            'doc_number': t.doc_number,
            'project_name': t.project.name if t.project else None,
            'project_color': t.project.color if t.project else None,
            'status': t.status,
            'priority': t.priority,
            'deadline': t.deadline.isoformat(),
            'file_url': t.file_url,
            'deadline_info': dl_info
        })

    # Pinned notes (select_related avoids N+1)
    pinned_notes = Note.objects.filter(user=user, is_pinned=True).select_related('project').order_by('-updated_at')[:5]
    pinned_notes_list = [
        {
            'id': str(n.id),
            'title': n.title,
            'project_name': n.project.name if n.project else None,
            'tags': n.tags,
            'updated_at': n.updated_at.isoformat()
        }
        for n in pinned_notes
    ]

    # Projects annotated with pending task count (Single query avoiding N+1)
    projects = WorkspaceProject.objects.filter(user=user, is_archived=False).annotate(
        pending_tasks_count=Count(
            'documents',
            filter=Q(documents__status__in=[TaskStatus.DRAFTING, TaskStatus.WAITING])
        )
    )
    project_list = [
        {
            'id': str(p.id),
            'name': p.name,
            'color': p.color,
            'icon': p.icon,
            'pending_tasks_count': p.pending_tasks_count
        }
        for p in projects
    ]

    return {
        'pipeline_counts': {
            'drafting': drafting_count,
            'waiting': waiting_count,
            'completed': completed_count,
            'archived': archived_count,
            'total_active': drafting_count + waiting_count
        },
        'overdue_count': overdue_count,
        'upcoming_deadlines_count': len(upcoming_list),
        'upcoming_deadlines': upcoming_list,
        'pinned_notes': pinned_notes_list,
        'projects': project_list
    }
