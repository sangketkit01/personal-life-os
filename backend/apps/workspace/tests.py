from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.workspace.models import (
    WorkspaceProject,
    TaskDocument,
    TaskStatus,
    TaskPriority,
    Note,
    ProjectLink,
    ProjectAttachment,
    CalendarEvent
)
from apps.workspace.services import calculate_deadline_info, transition_task_status, get_workspace_overview
from apps.accounts.tokens import generate_access_token

User = get_user_model()


def _results(res):
    """Extract item list from a (possibly paginated) DRF response."""
    data = res.data
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


class WorkspaceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='worker',
            email='worker@test.com',
            password='Password123!'
        )
        self.friend = User.objects.create_user(
            username='coworker',
            email='coworker@test.com',
            password='Password123!'
        )
        self.project = WorkspaceProject.objects.create(
            user=self.user,
            name='Freelance Project A',
            color='#3B82F6',
            status='ACTIVE',
            category='CLIENT'
        )
        self.client = APIClient()
        token = generate_access_token(self.user)
        self.client.cookies['access_token'] = token

    def test_task_status_transition_and_completion_timestamp(self):
        """Test task status transition and automatic completed_at timestamping."""
        task = TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='Send Quotation',
            status=TaskStatus.TODO
        )
        self.assertIsNone(task.completed_at)

        # 1. Transition to DONE
        transition_task_status(task, TaskStatus.DONE)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.DONE)
        self.assertIsNotNone(task.completed_at)

        # 2. Revert back to DOING
        transition_task_status(task, TaskStatus.DOING)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.DOING)
        self.assertIsNone(task.completed_at)

    def test_legacy_status_aliases_and_normalization(self):
        """Test that legacy pipeline status strings normalize to modern Kanban statuses."""
        from apps.workspace.services import normalize_task_status

        self.assertEqual(normalize_task_status('DRAFTING'), TaskStatus.TODO)
        self.assertEqual(normalize_task_status('WAITING'), TaskStatus.DOING)
        self.assertEqual(normalize_task_status('COMPLETED'), TaskStatus.DONE)
        self.assertEqual(normalize_task_status('doing'), TaskStatus.DOING)

        # Legacy aliases point at the same members as their modern equivalents
        self.assertEqual(TaskStatus.DRAFTING, TaskStatus.TODO)
        self.assertEqual(TaskStatus.WAITING, TaskStatus.DOING)
        self.assertEqual(TaskStatus.COMPLETED, TaskStatus.DONE)

    def test_deadline_calculation_and_overdue(self):
        """Test deadline calculation (countdown and overdue tracking)."""
        now = timezone.now()

        # Task due in 2 days
        future_dl = now + timedelta(days=2)
        info_future = calculate_deadline_info(future_dl)
        self.assertFalse(info_future['is_overdue'])
        self.assertEqual(info_future['days_left'], 2)
        self.assertEqual(info_future['urgency'], 'ATTENTION')

        # Task overdue by 1 day
        past_dl = now - timedelta(days=1)
        info_past = calculate_deadline_info(past_dl)
        self.assertTrue(info_past['is_overdue'])
        self.assertEqual(info_past['urgency'], 'OVERDUE')

    def test_workspace_overview_aggregation(self):
        """Test workspace overview aggregation for user with modern and legacy keys."""
        now = timezone.now()
        # 1. To Do task
        TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='Draft Service Agreement',
            status=TaskStatus.TODO,
            deadline=now + timedelta(days=1)
        )
        # 2. Doing task (overdue)
        TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='Awaiting Signature',
            status=TaskStatus.DOING,
            deadline=now - timedelta(days=2)
        )

        overview = get_workspace_overview(self.user)
        # Modern keys
        self.assertEqual(overview['pipeline_counts']['todo'], 1)
        self.assertEqual(overview['pipeline_counts']['doing'], 1)
        self.assertEqual(overview['pipeline_counts']['done'], 0)
        # Legacy compatibility keys
        self.assertEqual(overview['pipeline_counts']['drafting'], 1)
        self.assertEqual(overview['pipeline_counts']['waiting'], 1)
        self.assertEqual(overview['pipeline_counts']['completed'], 0)
        self.assertEqual(overview['pipeline_counts']['total_active'], 2)
        self.assertEqual(overview['overdue_count'], 1)

    def test_api_move_task_status(self):
        """Test action /api/workspace/tasks/{id}/move/ via REST API."""
        task = TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='Tax Invoice',
            status=TaskStatus.TODO
        )

        url = f'/api/workspace/tasks/{task.id}/move/'
        res = self.client.post(url, {'status': 'DONE'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'DONE')
        self.assertIsNotNone(res.data['completed_at'])

        # Legacy status input must normalize to modern status
        res_legacy = self.client.post(url, {'status': 'COMPLETED'}, format='json')
        self.assertEqual(res_legacy.status_code, status.HTTP_200_OK)
        self.assertEqual(res_legacy.data['status'], 'DONE')

        # Invalid status is rejected
        res_invalid = self.client.post(url, {'status': 'NOT_A_STATUS'}, format='json')
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_multi_user_workspace_isolation(self):
        """Security test: User A cannot read or move tasks owned by User B."""
        friend_project = WorkspaceProject.objects.create(
            user=self.friend,
            name='Friend Private Project'
        )
        friend_task = TaskDocument.objects.create(
            user=self.friend,
            project=friend_project,
            title='Friend Secret Task'
        )

        # User A tries to view friend's task
        res_get = self.client.get(f'/api/workspace/tasks/{friend_task.id}/')
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        # User A tries to move friend's task
        res_move = self.client.post(f'/api/workspace/tasks/{friend_task.id}/move/', {'status': 'DONE'})
        self.assertEqual(res_move.status_code, status.HTTP_404_NOT_FOUND)

    def test_task_checklist_persistence_and_validation(self):
        """Test checklist is stored, auto-completed with ids, and rejects malformed items."""
        res = self.client.post('/api/workspace/tasks/', {
            'project': str(self.project.id),
            'title': 'Build Landing Page',
            'status': 'TODO',
            'checklist': [
                {'title': 'Design hero section', 'is_completed': True},
                {'title': 'Write copy'}
            ]
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        checklist = res.data['checklist']
        self.assertEqual(len(checklist), 2)
        self.assertTrue(all('id' in item for item in checklist))
        self.assertTrue(checklist[0]['is_completed'])
        self.assertFalse(checklist[1]['is_completed'])
        self.assertEqual(res.data['checklist_progress'], {'total': 2, 'completed': 1})

        # Persisted to database
        task = TaskDocument.objects.get(id=res.data['id'])
        self.assertEqual(len(task.checklist), 2)

        # Malformed checklist rejected
        res_bad = self.client.post('/api/workspace/tasks/', {
            'project': str(self.project.id),
            'title': 'Broken Checklist',
            'checklist': [{'is_completed': True}]
        }, format='json')
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_calendar_month_filtering(self):
        """Test /api/workspace/tasks/?month=YYYY-MM returns tasks in that month."""
        # October 2026 tasks
        TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='October Deadline Task',
            deadline=timezone.make_aware(timezone.datetime(2026, 10, 15, 12, 0))
        )
        # Task starting in October without deadline
        TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='October Start Task',
            start_date=date(2026, 10, 5)
        )
        # Task outside October
        TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='November Task',
            deadline=timezone.make_aware(timezone.datetime(2026, 11, 3, 12, 0))
        )

        res = self.client.get('/api/workspace/tasks/?month=2026-10')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [t['title'] for t in _results(res)]
        self.assertIn('October Deadline Task', titles)
        self.assertIn('October Start Task', titles)
        self.assertNotIn('November Task', titles)

    def test_note_creation_with_structured_blocks(self):
        """Test Notion-style notes accept structured blocks JSON and auto-generate content."""
        res = self.client.post('/api/workspace/notes/', {
            'project': str(self.project.id),
            'title': 'Meeting Notes',
            'icon': 'clipboard',
            'blocks': [
                {'type': 'h1', 'content': 'Kickoff Agenda'},
                {'type': 'todo', 'content': 'Prepare wireframes', 'checked': True},
                {'type': 'bullet', 'content': 'Discussed budget'},
                {'type': 'divider', 'content': ''}
            ]
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(len(res.data['blocks']), 4)
        self.assertTrue(all('id' in b for b in res.data['blocks']))
        # Plain-text content auto-generated from blocks for search / previews
        self.assertIn('Kickoff Agenda', res.data['content'])
        self.assertIn('Discussed budget', res.data['content'])

        note = Note.objects.get(id=res.data['id'])
        self.assertEqual(note.icon, 'clipboard')
        self.assertEqual(note.blocks[1]['type'], 'todo')
        self.assertTrue(note.blocks[1]['checked'])

    def test_project_link_crud_and_bola_isolation(self):
        """Test ProjectLink CRUD and that User B cannot attach links to User A's project."""
        res = self.client.post('/api/workspace/links/', {
            'project': str(self.project.id),
            'title': 'Design File',
            'url': 'https://www.figma.com/design/abc123/Spec',
            'link_type': 'FIGMA',
            'is_pinned': True
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        link_id = res.data['id']

        # List & retrieve
        res_list = self.client.get(f'/api/workspace/links/?project_id={self.project.id}')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_results(res_list)), 1)

        # Update
        res_patch = self.client.patch(f'/api/workspace/links/{link_id}/', {'title': 'Updated Design'}, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data['title'], 'Updated Design')

        # User B cannot attach a link to User A's project (BOLA)
        self.client.cookies['access_token'] = generate_access_token(self.friend)
        res_forbidden = self.client.post('/api/workspace/links/', {
            'project': str(self.project.id),
            'title': 'Injected Link',
            'url': 'https://evil.example.com'
        }, format='json')
        self.assertEqual(res_forbidden.status_code, status.HTTP_400_BAD_REQUEST)

        # User B cannot list or delete User A's links
        res_list_b = self.client.get('/api/workspace/links/')
        self.assertEqual(len(_results(res_list_b)), 0)
        res_delete_b = self.client.delete(f'/api/workspace/links/{link_id}/')
        self.assertEqual(res_delete_b.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(ProjectLink.objects.filter(id=link_id).exists())

    def test_project_attachment_bola_isolation(self):
        """Test ProjectAttachment listing respects multi-user isolation."""
        attachment = ProjectAttachment.objects.create(
            user=self.user,
            project=self.project,
            file_name='contract.pdf',
            file_type='application/pdf',
            file_size=1024,
            drive_file_id='drive-file-abc',
            drive_view_link='https://drive.google.com/file/d/drive-file-abc/view'
        )

        res_owner = self.client.get(f'/api/workspace/attachments/?project_id={self.project.id}')
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_results(res_owner)), 1)
        self.assertEqual(_results(res_owner)[0]['file_name'], 'contract.pdf')

        # User B sees nothing and cannot delete User A's attachment
        self.client.cookies['access_token'] = generate_access_token(self.friend)
        res_friend_list = self.client.get('/api/workspace/attachments/')
        self.assertEqual(len(_results(res_friend_list)), 0)

        res_friend_delete = self.client.delete(f'/api/workspace/attachments/{attachment.id}/')
        self.assertEqual(res_friend_delete.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(ProjectAttachment.objects.filter(id=attachment.id).exists())

    def test_project_serializer_includes_new_fields(self):
        """Test WorkspaceProject API exposes status, category and counters."""
        res = self.client.post('/api/workspace/projects/', {
            'name': 'Internal Tooling',
            'status': 'PLANNING',
            'category': 'INTERNAL',
            'start_date': '2026-10-01',
            'target_date': '2026-12-31',
            'description': 'Internal automation tooling'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], 'PLANNING')
        self.assertEqual(res.data['category'], 'INTERNAL')
        self.assertEqual(res.data['start_date'], '2026-10-01')
        self.assertIn('total_tasks_count', res.data)
        self.assertIn('links_count', res.data)
        self.assertIn('attachments_count', res.data)

    def test_task_api_accepts_legacy_status_on_create_and_update(self):
        """Test legacy status aliases are accepted by task create/PATCH and normalized."""
        # Create with legacy status
        res = self.client.post('/api/workspace/tasks/', {
            'project': str(self.project.id),
            'title': 'Legacy Created Task',
            'status': 'DRAFTING'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], 'TODO')
        task_id = res.data['id']

        # PATCH with legacy status
        res_patch = self.client.patch(f'/api/workspace/tasks/{task_id}/', {'status': 'COMPLETED'}, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data['status'], 'DONE')
        self.assertIsNotNone(res_patch.data['completed_at'])

    def test_calendar_event_crud_and_month_filter(self):
        """Test standalone calendar events CRUD and month range filtering."""
        res = self.client.post('/api/workspace/events/', {
            'project': str(self.project.id),
            'title': 'Dentist Appointment',
            'event_type': 'APPOINTMENT',
            'start_at': '2026-10-28T14:30:00',
            'is_all_day': False,
            'notes': 'Annual checkup'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['event_type'], 'APPOINTMENT')
        event_id = res.data['id']

        # Update
        res_patch = self.client.patch(f'/api/workspace/events/{event_id}/', {
            'title': 'Dentist Appointment (rescheduled)',
            'event_type': 'PERSONAL'
        }, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data['event_type'], 'PERSONAL')

        # Month filter returns the event
        res_month = self.client.get('/api/workspace/events/?month=2026-10')
        self.assertEqual(res_month.status_code, status.HTTP_200_OK)
        month_ids = [e['id'] for e in _results(res_month)]
        self.assertIn(event_id, month_ids)

        # Other month does not
        res_other = self.client.get('/api/workspace/events/?month=2026-11')
        other_ids = [e['id'] for e in _results(res_other)]
        self.assertNotIn(event_id, other_ids)

        # Invalid range: end before start
        res_bad = self.client.post('/api/workspace/events/', {
            'title': 'Backwards Event',
            'start_at': '2026-10-28T15:00:00',
            'end_at': '2026-10-28T14:00:00'
        }, format='json')
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)

        # Delete
        res_del = self.client.delete(f'/api/workspace/events/{event_id}/')
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CalendarEvent.objects.filter(id=event_id).exists())

    def test_calendar_event_bola_isolation(self):
        """Security test: User B cannot access or attach events to User A's project."""
        res = self.client.post('/api/workspace/events/', {
            'project': str(self.project.id),
            'title': 'Private Meeting',
            'start_at': '2026-10-29T09:00:00'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        event_id = res.data['id']

        self.client.cookies['access_token'] = generate_access_token(self.friend)

        # User B cannot attach an event to User A's project
        res_forbidden = self.client.post('/api/workspace/events/', {
            'project': str(self.project.id),
            'title': 'Injected Event',
            'start_at': '2026-10-29T10:00:00'
        }, format='json')
        self.assertEqual(res_forbidden.status_code, status.HTTP_400_BAD_REQUEST)

        # User B cannot list or delete User A's events
        res_list = self.client.get('/api/workspace/events/')
        self.assertEqual(len(_results(res_list)), 0)
        res_del = self.client.delete(f'/api/workspace/events/{event_id}/')
        self.assertEqual(res_del.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(CalendarEvent.objects.filter(id=event_id).exists())

    def test_project_attachment_without_project_allowed(self):
        """Test attachments can reference a bare task with project=None (P1 regression)."""
        task = TaskDocument.objects.create(user=self.user, project=None, title='Orphan Task')
        attachment = ProjectAttachment.objects.create(
            user=self.user,
            project=None,
            task=task,
            file_name='notes.txt',
            file_type='text/plain',
            file_size=10,
            drive_file_id='drive-xyz'
        )
        self.assertIsNone(attachment.project)
        self.assertEqual(attachment.task_id, task.id)
