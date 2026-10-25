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
    NoteFolder,
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

        # End before start: stale end_at is auto-cleared instead of rejecting
        res_bad = self.client.post('/api/workspace/events/', {
            'title': 'Backwards Event',
            'start_at': '2026-10-28T15:00:00',
            'end_at': '2026-10-28T14:00:00'
        }, format='json')
        self.assertEqual(res_bad.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(res_bad.data['end_at'])

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

    def test_note_folder_crud_and_count(self):
        """Test NoteFolder CRUD with annotated non-trashed standalone notes count."""
        res = self.client.post('/api/workspace/note-folders/', {
            'name': 'Journal',
            'icon': 'book',
            'color': '#8B5CF6',
            'position': 1
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        folder_id = res.data['id']
        self.assertEqual(res.data['notes_count'], 0)

        # Put a standalone note in the folder
        self.client.post('/api/workspace/notes/', {
            'title': 'Daily Reflection',
            'folder': folder_id
        }, format='json')

        res_list = self.client.get('/api/workspace/note-folders/')
        folders = _results(res_list)
        target = next(f for f in folders if f['id'] == folder_id)
        self.assertEqual(target['notes_count'], 1)

        # Rename
        res_patch = self.client.patch(f'/api/workspace/note-folders/{folder_id}/', {'name': 'Journal 2026'}, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data['name'], 'Journal 2026')

        # Delete folder -> notes keep existing with folder=None (SET_NULL)
        res_del = self.client.delete(f'/api/workspace/note-folders/{folder_id}/')
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Note.objects.filter(title='Daily Reflection', folder__isnull=True).exists())

        # BOLA: User B cannot see or delete User A's folders
        self.client.cookies['access_token'] = generate_access_token(self.friend)
        res_list_b = self.client.get('/api/workspace/note-folders/')
        self.assertEqual(len(_results(res_list_b)), 0)
        res_del_b = self.client.delete(f'/api/workspace/note-folders/{folder_id}/')
        self.assertEqual(res_del_b.status_code, status.HTTP_404_NOT_FOUND)

    def test_standalone_vs_project_note_separation(self):
        """Test standalone=true returns only notes without a project."""
        self.client.post('/api/workspace/notes/', {'title': 'Standalone Note A'}, format='json')
        self.client.post('/api/workspace/notes/', {
            'title': 'Project Page B',
            'project': str(self.project.id)
        }, format='json')

        res = self.client.get('/api/workspace/notes/?standalone=true')
        titles = [n['title'] for n in _results(res)]
        self.assertIn('Standalone Note A', titles)
        self.assertNotIn('Project Page B', titles)

        # Unfiled filter
        res_unfiled = self.client.get('/api/workspace/notes/?standalone=true&folder_id=unfiled')
        self.assertGreaterEqual(len(_results(res_unfiled)), 1)

    def test_note_trash_restore_and_empty_trash(self):
        """Test soft-delete lifecycle: trash -> restore -> empty trash."""
        res = self.client.post('/api/workspace/notes/', {'title': 'Disposable Note'}, format='json')
        note_id = res.data['id']

        # Live list excludes trashed by default; trash it
        res_trash = self.client.post(f'/api/workspace/notes/{note_id}/trash/')
        self.assertEqual(res_trash.status_code, status.HTTP_200_OK)
        self.assertTrue(res_trash.data['is_trashed'])
        self.assertIsNotNone(res_trash.data['trashed_at'])
        self.assertFalse(res_trash.data['is_pinned'])

        res_live = self.client.get('/api/workspace/notes/?standalone=true')
        self.assertNotIn(note_id, [n['id'] for n in _results(res_live)])

        res_trash_list = self.client.get('/api/workspace/notes/?trashed=true')
        self.assertIn(note_id, [n['id'] for n in _results(res_trash_list)])

        # Restore
        res_restore = self.client.post(f'/api/workspace/notes/{note_id}/restore/')
        self.assertEqual(res_restore.status_code, status.HTTP_200_OK)
        self.assertFalse(res_restore.data['is_trashed'])

        # Trash again then empty trash permanently deletes it
        self.client.post(f'/api/workspace/notes/{note_id}/trash/')
        res_empty = self.client.post('/api/workspace/notes/empty-trash/')
        self.assertEqual(res_empty.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res_empty.data['deleted'], 1)
        self.assertFalse(Note.objects.filter(id=note_id).exists())

    def test_note_lock_set_verify_unlock(self):
        """Test PIN locking: set-lock, verify-lock, wrong PIN, unlock."""
        res = self.client.post('/api/workspace/notes/', {'title': 'Secret Note'}, format='json')
        note_id = res.data['id']

        # Lock without PIN is rejected
        res_no_pin = self.client.post(f'/api/workspace/notes/{note_id}/set-lock/', {'is_locked': True}, format='json')
        self.assertEqual(res_no_pin.status_code, status.HTTP_400_BAD_REQUEST)

        # Lock with PIN
        res_lock = self.client.post(f'/api/workspace/notes/{note_id}/set-lock/', {
            'is_locked': True, 'pin': '4321'
        }, format='json')
        self.assertEqual(res_lock.status_code, status.HTTP_200_OK)
        self.assertTrue(res_lock.data['is_locked'])
        self.assertTrue(res_lock.data['has_lock_pin'])
        self.assertNotIn('lock_pin', res_lock.data)  # hash never exposed

        # Wrong PIN fails verification
        res_wrong = self.client.post(f'/api/workspace/notes/{note_id}/verify-lock/', {'pin': '0000'}, format='json')
        self.assertEqual(res_wrong.data['verified'], False)

        # Correct PIN verifies
        res_ok = self.client.post(f'/api/workspace/notes/{note_id}/verify-lock/', {'pin': '4321'}, format='json')
        self.assertEqual(res_ok.data['verified'], True)

        # Unlock with wrong PIN rejected
        res_bad_unlock = self.client.post(f'/api/workspace/notes/{note_id}/set-lock/', {
            'is_locked': False, 'pin': '9999'
        }, format='json')
        self.assertEqual(res_bad_unlock.status_code, status.HTTP_400_BAD_REQUEST)

        # Unlock with correct PIN clears the lock
        res_unlock = self.client.post(f'/api/workspace/notes/{note_id}/set-lock/', {
            'is_locked': False, 'pin': '4321'
        }, format='json')
        self.assertEqual(res_unlock.status_code, status.HTTP_200_OK)
        self.assertFalse(res_unlock.data['is_locked'])
        self.assertFalse(res_unlock.data['has_lock_pin'])

    def test_note_copy_to_project(self):
        """Test copying a standalone note into a project as a Project Page."""
        res = self.client.post('/api/workspace/notes/', {
            'title': 'Research Summary',
            'blocks': [
                {'type': 'numbered', 'content': 'First point', 'indent': 0},
                {'type': 'numbered', 'content': 'Second point', 'indent': 1}
            ],
            'tags': ['research'],
            'color': 'SKY'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        note_id = res.data['id']
        self.assertEqual(res.data['blocks'][1]['indent'], 1)

        res_copy = self.client.post(f'/api/workspace/notes/{note_id}/copy-to-project/', {
            'project_id': str(self.project.id)
        }, format='json')
        self.assertEqual(res_copy.status_code, status.HTTP_201_CREATED)
        copy_data = res_copy.data
        self.assertEqual(str(copy_data['project']), str(self.project.id))
        self.assertEqual(copy_data['title'], 'Research Summary')
        self.assertEqual(len(copy_data['blocks']), 2)
        self.assertFalse(copy_data['is_locked'])

        # Original stays standalone
        original = Note.objects.get(id=note_id)
        self.assertIsNone(original.project)
        self.assertEqual(Note.objects.filter(project=self.project, title='Research Summary').count(), 1)

        # BOLA: cannot copy into User B's project... (reverse) User B cannot read the copy
        self.client.cookies['access_token'] = generate_access_token(self.friend)
        res_forbidden = self.client.post(f'/api/workspace/notes/{note_id}/copy-to-project/', {
            'project_id': str(self.project.id)
        }, format='json')
        self.assertEqual(res_forbidden.status_code, status.HTTP_404_NOT_FOUND)

    def test_note_blocks_with_numbered_and_indent_clamping(self):
        """Test blocks serializer preserves numbered type and clamps indent to 0..4."""
        res = self.client.post('/api/workspace/notes/', {
            'title': 'Indent Test',
            'blocks': [
                {'type': 'numbered', 'content': 'Level 0', 'indent': 0},
                {'type': 'bullet', 'content': 'Too deep', 'indent': 9},
                {'type': 'todo', 'content': 'Negative', 'indent': -3}
            ]
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        blocks = res.data['blocks']
        self.assertEqual(blocks[0]['type'], 'numbered')
        self.assertEqual(blocks[1]['indent'], 4)
        self.assertEqual(blocks[2]['indent'], 0)

        # Plain-text content summary must not contain raw HTML tags
        res_html = self.client.post('/api/workspace/notes/', {
            'title': 'HTML Summary Test',
            'blocks': [
                {'type': 'paragraph', 'content': '<strong>Bold</strong> and <a href="https://x.co">link</a>'}
            ]
        }, format='json')
        self.assertIn('Bold', res_html.data['content'])
        self.assertIn('link', res_html.data['content'])
        self.assertNotIn('<strong>', res_html.data['content'])

    def test_trashed_notes_excluded_from_counts(self):
        """Audit P2: trashed notes must not count toward project notes_count or pinned notes."""
        res = self.client.post('/api/workspace/notes/', {
            'title': 'Counted Note',
            'project': str(self.project.id),
            'is_pinned': True
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        note_id = res.data['id']

        # Before trashing: notes_count = 1 and note appears in pinned list
        res_project = self.client.get('/api/workspace/projects/')
        project_data = next(p for p in _results(res_project) if str(p['id']) == str(self.project.id))
        self.assertEqual(project_data['notes_count'], 1)

        overview = get_workspace_overview(self.user)
        pinned_ids = [n['id'] for n in overview['pinned_notes']]
        self.assertIn(note_id, pinned_ids)

        # Trash the note -> counters drop to zero everywhere
        self.client.post(f'/api/workspace/notes/{note_id}/trash/')

        res_project = self.client.get('/api/workspace/projects/')
        project_data = next(p for p in _results(res_project) if str(p['id']) == str(self.project.id))
        self.assertEqual(project_data['notes_count'], 0)

        overview = get_workspace_overview(self.user)
        pinned_ids = [n['id'] for n in overview['pinned_notes']]
        self.assertNotIn(note_id, pinned_ids)

        # Project pages tab list also excludes trashed notes
        res_pages = self.client.get(f'/api/workspace/notes/?project_id={self.project.id}')
        self.assertNotIn(note_id, [n['id'] for n in _results(res_pages)])

    def test_storage_note_domain_choice_accepted(self):
        """Audit P2: the DriveFile model accepts the new 'note' domain choice."""
        from apps.storage.models import DriveFile, StorageDomain

        self.assertIn('note', StorageDomain.values)
        drive_file = DriveFile.objects.create(
            user=self.user,
            drive_file_id='note-domain-file',
            file_name='attached.pdf',
            file_type='application/pdf',
            file_size=2048,
            domain=StorageDomain.NOTE
        )
        self.assertEqual(drive_file.domain, 'note')
        self.assertTrue(
            DriveFile.objects.filter(user=self.user, domain=StorageDomain.NOTE).exists()
        )

    def test_note_blocks_with_image_audio_table(self):
        """Test image/audio/table blocks persist multimedia and table fields."""
        res = self.client.post('/api/workspace/notes/', {
            'title': 'Multimedia Note',
            'blocks': [
                {
                    'type': 'image',
                    'content': 'Site survey photo',
                    'drive_file_id': 'gdrive_img_001',
                    'file_url': 'https://drive.google.com/file/d/gdrive_img_001/view',
                    'file_name': 'site-survey.png',
                    'file_type': 'image/png',
                    'file_size': 204800,
                    'width': '75%'
                },
                {
                    'type': 'audio',
                    'content': 'Voice memo about requirements',
                    'drive_file_id': 'gdrive_aud_001',
                    'file_name': 'voice-note-20261024.webm',
                    'file_type': 'audio/webm',
                    'file_size': 48000,
                    'duration': 14.5
                },
                {
                    'type': 'table',
                    'rows': [
                        ['Task', 'Owner', 'Status'],
                        ['Survey', 'Anon', 'Done']
                    ]
                }
            ]
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        blocks = res.data['blocks']

        image = blocks[0]
        self.assertEqual(image['type'], 'image')
        self.assertEqual(image['drive_file_id'], 'gdrive_img_001')
        self.assertEqual(image['width'], '75%')
        self.assertEqual(image['file_name'], 'site-survey.png')

        audio = blocks[1]
        self.assertEqual(audio['type'], 'audio')
        self.assertAlmostEqual(audio['duration'], 14.5)
        self.assertEqual(audio['file_type'], 'audio/webm')

        table = blocks[2]
        self.assertEqual(table['type'], 'table')
        self.assertEqual(table['rows'], [['Task', 'Owner', 'Status'], ['Survey', 'Anon', 'Done']])

        # Plain-text summary indexes captions, file names and table cells for search
        content = res.data['content']
        self.assertIn('Site survey photo', content)
        self.assertIn('site-survey.png', content)
        self.assertIn('voice-note-20261024.webm', content)
        self.assertIn('Survey', content)
        self.assertIn('Owner', content)

        # Search finds text inside a table cell and a caption
        res_search = self.client.get('/api/workspace/notes/?search=Anon')
        self.assertIn(res.data['id'], [n['id'] for n in _results(res_search)])
        res_search2 = self.client.get('/api/workspace/notes/?search=voice-note')
        self.assertIn(res.data['id'], [n['id'] for n in _results(res_search2)])

    def test_table_block_validation_and_defaults(self):
        """Test table rows are clamped, rectangularized, and defaulted correctly."""
        res = self.client.post('/api/workspace/notes/', {
            'title': 'Table Bounds',
            'blocks': [
                {'type': 'table'},  # empty -> default 2x3
                {'type': 'table', 'rows': [['A', 'B'], ['one', 'two', 'three']]}  # ragged -> padded
            ]
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        blocks = res.data['blocks']

        self.assertEqual(blocks[0]['rows'], [['Column 1', 'Column 2', 'Column 3'], ['', '', '']])

        padded = blocks[1]['rows']
        self.assertEqual(padded, [['A', 'B', ''], ['one', 'two', 'three']])

        # Invalid rows shape falls back to empty (then default for table type)
        res_bad = self.client.post('/api/workspace/notes/', {
            'title': 'Bad Table',
            'blocks': [{'type': 'table', 'rows': 'not-a-list'}]
        }, format='json')
        self.assertEqual(res_bad.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_bad.data['blocks'][0]['rows'], [['Column 1', 'Column 2', 'Column 3'], ['', '', '']])

        # Invalid width and negative size/duration get sanitized
        res_media = self.client.post('/api/workspace/notes/', {
            'title': 'Media Sanitize',
            'blocks': [
                {
                    'type': 'image',
                    'width': '9999px',
                    'file_size': -5,
                    'drive_file_id': 'x'
                },
                {
                    'type': 'audio',
                    'duration': -3
                }
            ]
        }, format='json')
        self.assertEqual(res_media.data['blocks'][0]['width'], '100%')
        self.assertEqual(res_media.data['blocks'][0]['file_size'], 0)
        self.assertEqual(res_media.data['blocks'][1]['duration'], 0.0)

    def test_create_note_with_blank_title_and_folder(self):
        """Regression test: creating a note with blank title (standalone or inside a folder) succeeds with 201."""
        res_blank = self.client.post('/api/workspace/notes/', {
            'title': '',
            'project': None,
            'folder': None,
        }, format='json')
        self.assertEqual(res_blank.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_blank.data['title'], 'Untitled')
        self.assertEqual(len(res_blank.data['blocks']), 1)
        self.assertEqual(res_blank.data['blocks'][0]['type'], 'paragraph')

        folder_res = self.client.post('/api/workspace/note-folders/', {
            'name': 'Quick Ideas',
            'color': '#38bdf8'
        }, format='json')
        self.assertEqual(folder_res.status_code, status.HTTP_201_CREATED)
        folder_id = folder_res.data['id']

        res_folder = self.client.post('/api/workspace/notes/', {
            'title': '',
            'project': None,
            'folder': folder_id,
        }, format='json')
        self.assertEqual(res_folder.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_folder.data['title'], 'Untitled')
        self.assertEqual(str(res_folder.data['folder']), str(folder_id))
        self.assertEqual(len(res_folder.data['blocks']), 1)


    def test_calendar_event_start_move_clears_stale_end(self):
        """Moving start_at to a later date without end_at clears the stale end_at (no 400)."""
        res = self.client.post('/api/workspace/events/', {
            'title': 'Scheduled Meeting',
            'start_at': '2026-10-28T09:00:00',
            'end_at': '2026-10-28T10:00:00'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        event_id = res.data['id']

        # Move start past the old end without sending end_at -> auto-cleared
        res_move = self.client.patch(f'/api/workspace/events/{event_id}/', {
            'start_at': '2026-11-15T09:00:00'
        }, format='json')
        self.assertEqual(res_move.status_code, status.HTTP_200_OK)
        self.assertIsNone(res_move.data['end_at'])

    def test_note_block_width_align_and_file_type(self):
        """Test arbitrary image widths (25%-100%), align values and the file block type."""
        res = self.client.post('/api/workspace/notes/', {
            'title': 'Width And Align',
            'blocks': [
                {'type': 'image', 'width': '35%', 'align': 'left', 'drive_file_id': 'img1'},
                {'type': 'image', 'width': '68%', 'align': 'right', 'drive_file_id': 'img2'},
                {'type': 'image', 'width': '9999px', 'align': 'diagonal', 'drive_file_id': 'img3'},
                {'type': 'file', 'file_name': 'report.pdf', 'file_type': 'application/pdf', 'file_size': 1024, 'drive_file_id': 'doc1'},
                {'type': 'image', 'width': '10%'}
            ]
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        blocks = res.data['blocks']

        self.assertEqual(blocks[0]['width'], '35%')
        self.assertEqual(blocks[0]['align'], 'left')
        self.assertEqual(blocks[1]['width'], '68%')
        self.assertEqual(blocks[1]['align'], 'right')
        # Invalid width / align fall back to defaults
        self.assertEqual(blocks[2]['width'], '100%')
        self.assertEqual(blocks[2]['align'], 'center')
        self.assertEqual(blocks[2]['width'], '100%')
        self.assertEqual(blocks[4]['width'], '100%')

        # file block persists metadata and is indexed in the text summary
        self.assertEqual(blocks[3]['type'], 'file')
        self.assertEqual(blocks[3]['file_name'], 'report.pdf')
        self.assertIn('report.pdf', res.data['content'])


# ---------------------------------------------------------------------------
# Round 1: MA contracts, infrastructure assets, credentials vault, SSH engine
# ---------------------------------------------------------------------------
import asyncio
import json as _json
import io
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TransactionTestCase

from apps.finance.models import (
    FinancialObligation,
    FlowDirection,
    PaymentHistory,
)
from apps.storage.encryption import decrypt_token, encrypt_token
from apps.workspace.models import (
    ProjectType,
    InfrastructureAsset,
    BillingOwnership,
    ServerCredential,
    ServerRunbook,
)
from apps.workspace.services import (
    sync_project_ma_obligation,
    sync_infra_asset_obligation,
    sync_billing_dates_from_obligation,
    get_project_economics,
)


class InfrastructureBaseTestCase(TestCase):
    """Shared fixture: user + friend + project + one VPS asset."""

    def setUp(self):
        from apps.workspace.models import InfraAssetType, SshAuthType
        self.user = User.objects.create_user(
            username='maowner', email='maowner@test.com', password='Password123!'
        )
        self.friend = User.objects.create_user(
            username='mafriend', email='mafriend@test.com', password='Password123!'
        )
        self.project = WorkspaceProject.objects.create(
            user=self.user, name='Client Shop Platform', color='#3B82F6'
        )
        self.asset = InfrastructureAsset.objects.create(
            user=self.user,
            project=self.project,
            name='prod-web-01',
            asset_type=InfraAssetType.VPS,
            provider='DigitalOcean',
            ip_address='203.0.113.10',
            ssh_port=22,
            ssh_username='root',
            ssh_auth_type=SshAuthType.PASSWORD,
            ssh_password_encrypted=encrypt_token('S3cretPass!'),
            billing_ownership=BillingOwnership.SELF_FUNDED,
            cost_amount=Decimal('650.00'),
            billing_cycle='MONTHLY'
        )
        self.client = APIClient()
        self.client.cookies['access_token'] = generate_access_token(self.user)


class ProjectMASyncTests(InfrastructureBaseTestCase):

    def test_sync_creates_inflow_obligation(self):
        self.project.project_type = ProjectType.MA_CONTRACT
        self.project.client_name = 'ACME Corp'
        self.project.ma_amount = Decimal('12000.00')
        self.project.ma_billing_cycle = 'QUARTERLY'
        self.project.ma_next_billing_date = date.today() + timedelta(days=10)
        self.project.save()

        obligation = sync_project_ma_obligation(self.project)

        self.assertIsNotNone(obligation)
        self.assertEqual(obligation.direction, FlowDirection.INFLOW)
        self.assertEqual(obligation.type, 'SUBSCRIPTION')
        self.assertEqual(obligation.user, self.user)
        self.assertEqual(obligation.metadata.get('source_type'), 'MA_CONTRACT')
        self.assertEqual(obligation.metadata.get('client_name'), 'ACME Corp')
        self.assertEqual(obligation.title, 'MA: Client Shop Platform')
        self.project.refresh_from_db()
        self.assertEqual(self.project.ma_obligation_id, obligation.id)

    def test_sync_updates_existing_obligation(self):
        self.project.ma_amount = Decimal('1000.00')
        self.project.ma_next_billing_date = date.today() + timedelta(days=5)
        self.project.save()
        first = sync_project_ma_obligation(self.project)

        self.project.ma_amount = Decimal('1500.00')
        self.project.ma_next_billing_date = date.today() + timedelta(days=35)
        self.project.save()
        second = sync_project_ma_obligation(self.project)

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.amount, Decimal('1500.00'))
        self.assertEqual(FinancialObligation.objects.filter(user=self.user).count(), 1)

    def test_disabling_ma_cancels_obligation(self):
        self.project.ma_amount = Decimal('1000.00')
        self.project.ma_next_billing_date = date.today()
        self.project.save()
        obligation = sync_project_ma_obligation(self.project)
        self.assertEqual(obligation.status, 'ACTIVE')

        self.project.ma_amount = Decimal('0.00')
        self.project.save()
        result = sync_project_ma_obligation(self.project)
        self.assertIsNone(result)

        obligation.refresh_from_db()
        self.assertEqual(obligation.status, 'CANCELLED')
        self.project.refresh_from_db()
        self.assertIsNone(self.project.ma_obligation)


class InfraAssetSyncTests(InfrastructureBaseTestCase):

    def test_sync_creates_outflow_obligation(self):
        self.asset.sync_to_radar = True
        self.asset.next_billing_date = date.today() + timedelta(days=3)
        self.asset.save()

        obligation = sync_infra_asset_obligation(self.asset)

        self.assertIsNotNone(obligation)
        self.assertEqual(obligation.direction, FlowDirection.OUTFLOW)
        self.assertEqual(obligation.metadata.get('source_type'), 'INFRA_ASSET')
        self.assertEqual(obligation.metadata.get('asset_id'), str(self.asset.id))
        self.assertIn('prod-web-01', obligation.title)
        self.assertIn('DigitalOcean', obligation.title)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.financial_obligation_id, obligation.id)

    def test_client_direct_billing_never_syncs(self):
        self.asset.sync_to_radar = True
        self.asset.billing_ownership = BillingOwnership.CLIENT_DIRECT
        self.asset.next_billing_date = date.today()
        self.asset.save()
        self.assertIsNone(sync_infra_asset_obligation(self.asset))

    def test_disabling_sync_cancels_obligation(self):
        self.asset.sync_to_radar = True
        self.asset.next_billing_date = date.today()
        self.asset.save()
        obligation = sync_infra_asset_obligation(self.asset)

        self.asset.sync_to_radar = False
        self.asset.save()
        self.assertIsNone(sync_infra_asset_obligation(self.asset))
        obligation.refresh_from_db()
        self.assertEqual(obligation.status, 'CANCELLED')


class BillingDateMirrorTests(InfrastructureBaseTestCase):

    def test_ma_obligation_roll_updates_project(self):
        self.project.ma_amount = Decimal('5000.00')
        self.project.ma_next_billing_date = date.today()
        self.project.save()
        obligation = sync_project_ma_obligation(self.project)

        new_due = date.today() + timedelta(days=30)
        obligation.due_date = new_due
        obligation.save()

        sync_billing_dates_from_obligation(obligation)
        self.project.refresh_from_db()
        self.assertEqual(self.project.ma_next_billing_date, new_due)

    def test_infra_obligation_roll_updates_asset(self):
        self.asset.sync_to_radar = True
        self.asset.next_billing_date = date.today()
        self.asset.save()
        obligation = sync_infra_asset_obligation(self.asset)

        new_due = date.today() + timedelta(days=30)
        obligation.due_date = new_due
        obligation.save()

        sync_billing_dates_from_obligation(obligation)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.next_billing_date, new_due)


class ProjectEconomicsTests(InfrastructureBaseTestCase):

    def _make_ma(self):
        self.project.project_type = ProjectType.MA_CONTRACT
        self.project.ma_amount = Decimal('12000.00')
        self.project.ma_billing_cycle = 'QUARTERLY'
        self.project.ma_next_billing_date = date.today()
        self.project.save()
        return sync_project_ma_obligation(self.project)

    def test_margin_projection_and_realized(self):
        self._make_ma()
        # Self-funded server 650/mo + a client-direct one that must be ignored
        InfrastructureAsset.objects.create(
            user=self.user, project=self.project, name='client-paid-db',
            billing_ownership=BillingOwnership.CLIENT_DIRECT,
            cost_amount=Decimal('999.00'), billing_cycle='MONTHLY'
        )

        ma_obligation = self.project.ma_obligation
        PaymentHistory.objects.create(
            user=self.user, obligation=ma_obligation,
            paid_amount=Decimal('12000.00'), note='Q1 MA payment'
        )

        eco = get_project_economics(self.project)

        self.assertEqual(Decimal(eco['monthly_ma_inflow']), Decimal('4000.00'))
        self.assertEqual(Decimal(eco['annual_ma_inflow']), Decimal('48000.00'))
        self.assertEqual(Decimal(eco['monthly_infra_outflow']), Decimal('650.00'))
        self.assertEqual(Decimal(eco['annual_infra_outflow']), Decimal('7800.00'))
        self.assertEqual(Decimal(eco['realized_inflow']), Decimal('12000.00'))
        self.assertEqual(Decimal(eco['realized_net_margin']), Decimal('12000.00'))
        self.assertEqual(Decimal(eco['projected_monthly_margin']), Decimal('3350.00'))
        self.assertEqual(Decimal(eco['margin_pct']), Decimal('100.00'))

    def test_zero_inflow_margin_pct_is_zero(self):
        eco = get_project_economics(self.project)
        self.assertEqual(Decimal(eco['margin_pct']), Decimal('0.00'))
        self.assertEqual(Decimal(eco['monthly_ma_inflow']), Decimal('0.00'))


class CredentialsVaultTests(InfrastructureBaseTestCase):

    def test_secret_never_serialized_and_encrypted_at_rest(self):
        res = self.client.post('/api/workspace/credentials/', {
            'project': str(self.project.id),
            'asset': str(self.asset.id),
            'title': 'Prod DB URI',
            'category': 'DATABASE',
            'username': 'appuser',
            'host_or_url': 'postgres://prod-db:5432/shop',
            'secret': 'postgres://appuser:hunter2@prod-db:5432/shop',
            'notes': 'primary connection string'
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data.get('has_secret'))
        self.assertNotIn('secret', res.data)
        self.assertNotIn('secret_encrypted', res.data)

        credential = ServerCredential.objects.get(id=res.data['id'])
        self.assertNotIn('hunter2', credential.secret_encrypted)
        self.assertEqual(
            decrypt_token(credential.secret_encrypted),
            'postgres://appuser:hunter2@prod-db:5432/shop'
        )

    def test_reveal_returns_plaintext(self):
        credential = ServerCredential.objects.create(
            user=self.user, project=self.project, title='Admin Login',
            secret_encrypted=encrypt_token('adm1n-p4ss')
        )
        res = self.client.post(f'/api/workspace/credentials/{credential.id}/reveal/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['secret'], 'adm1n-p4ss')

    def test_reveal_blocked_for_other_user(self):
        credential = ServerCredential.objects.create(
            user=self.user, project=self.project, title='Admin Login',
            secret_encrypted=encrypt_token('adm1n-p4ss')
        )
        friend_client = APIClient()
        friend_client.cookies['access_token'] = generate_access_token(self.friend)
        res = friend_client.post(f'/api/workspace/credentials/{credential.id}/reveal/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_user_project_rejected(self):
        friend_project = WorkspaceProject.objects.create(
            user=self.friend, name='Friend Project'
        )
        res = self.client.post('/api/workspace/credentials/', {
            'project': str(friend_project.id),
            'title': 'Evil Entry',
            'secret': 'nope'
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class InfrastructureAPITests(InfrastructureBaseTestCase):

    def test_list_isolated_by_user_and_project_filter(self):
        res = self.client.get('/api/workspace/infrastructure/', {
            'project_id': str(self.project.id)
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        rows = _results(res)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'prod-web-01')
        self.assertTrue(rows[0]['has_ssh_password'])
        self.assertNotIn('ssh_password_encrypted', rows[0])

        friend_client = APIClient()
        friend_client.cookies['access_token'] = generate_access_token(self.friend)
        self.assertEqual(len(_results(friend_client.get('/api/workspace/infrastructure/'))), 0)

    def test_write_secret_via_write_only_field(self):
        res = self.client.patch(f'/api/workspace/infrastructure/{self.asset.id}/', {
            'ssh_password': 'NewPass456!'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.asset.refresh_from_db()
        self.assertEqual(decrypt_token(self.asset.ssh_password_encrypted), 'NewPass456!')

    @patch('apps.workspace.ssh_service.open_ssh_client')
    def test_probe_reports_offline_on_unreachable(self, mock_open):
        from apps.workspace.ssh_service import SshConnectionError
        mock_open.side_effect = SshConnectionError('Cannot reach 203.0.113.10:22.')
        res = self.client.post(f'/api/workspace/infrastructure/{self.asset.id}/probe/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['health_status'], 'OFFLINE')
        self.assertIsNotNone(res.data['telemetry'].get('error'))
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.health_status, 'OFFLINE')

    def test_project_detail_includes_economics_and_infra_count(self):
        res = self.client.get(f'/api/workspace/projects/{self.project.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['infra_count'], 1)
        eco = res.data['economics']
        self.assertIsNotNone(eco)
        self.assertEqual(Decimal(eco['monthly_infra_outflow']), Decimal('650.00'))

        listing = self.client.get('/api/workspace/projects/')
        rows = _results(listing)
        mine = next(r for r in rows if r['id'] == str(self.project.id))
        self.assertIsNone(mine['economics'])


class RunbookAPITests(InfrastructureBaseTestCase):

    def test_full_crud_and_execute_requires_command(self):
        res = self.client.post('/api/workspace/runbooks/', {
            'project': str(self.project.id),
            'asset': str(self.asset.id),
            'title': 'Restart nginx',
            'command': 'systemctl restart nginx',
            'working_dir': '/etc/nginx',
            'timeout_seconds': 30
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        runbook = ServerRunbook.objects.get(id=res.data['id'])
        self.assertEqual(runbook.user, self.user)

        res = self.client.post(f'/api/workspace/runbooks/{runbook.id}/execute/')
        self.assertEqual(res.status_code, status.HTTP_502_BAD_GATEWAY)

        runbook.command = '   '
        runbook.save()
        res = self.client.post(f'/api/workspace/runbooks/{runbook.id}/execute/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_user_asset_rejected(self):
        friend_asset = InfrastructureAsset.objects.create(
            user=self.friend,
            project=WorkspaceProject.objects.create(user=self.friend, name='Friend P'),
            name='friend-box'
        )
        res = self.client.post('/api/workspace/runbooks/', {
            'project': str(self.project.id),
            'asset': str(friend_asset.id),
            'title': 'Evil',
            'command': 'ls'
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


TELEMETRY_OUTPUTS = {
    'cat /proc/uptime': ('987654.32 100000\n', '', 0),
    'cat /proc/loadavg': ('0.80 0.50 0.30 1/150 9000\n', '', 0),
    'nproc': ('2\n', '', 0),
    "free -m | awk 'NR==2{printf \"%s %s\", $3,$2}'": ('800 1600', '', 0),
    "df -BM / | awk 'NR==2{printf \"%s %s %s\", $3,$2,$5}'": ('10240M 20480M 51%\n', '', 0),
    'uname -sr': ('Linux 5.15.0-generic\n', '', 0),
    "docker ps -a --format '{{json .}}' 2>/dev/null": (
        '{"ID":"abc123","Names":"web","Image":"nginx:latest","State":"running",'
        '"Status":"Up 3 hours","Ports":"0.0.0.0:80-\u003e80/tcp"}\n'
        '{"ID":"def456","Names":"worker","Image":"redis:7","State":"exited",'
        '"Status":"Exited (0) 5 minutes ago","Ports":""}\n',
        '',
        0
    ),
}


def _fake_run_command(client, command, timeout=15):
    return TELEMETRY_OUTPUTS.get(command, ('', '', 1))


class SshEngineTests(InfrastructureBaseTestCase):

    @patch('apps.workspace.ssh_service._run_command', side_effect=_fake_run_command)
    @patch('apps.workspace.ssh_service.open_ssh_client')
    def test_probe_parses_telemetry_and_containers(self, mock_open, mock_run):
        mock_open.return_value = MagicMock()
        from apps.workspace.ssh_service import probe_server_telemetry

        telemetry = probe_server_telemetry(self.asset)

        self.assertEqual(telemetry['error'], None)
        self.assertEqual(telemetry['ram_pct'], 50.0)
        self.assertEqual(telemetry['disk_pct'], 51.0)
        self.assertEqual(telemetry['cpu_pct'], 40.0)  # load 0.8 / 2 cores
        self.assertEqual(len(telemetry['containers']), 2)
        self.assertEqual(telemetry['containers'][0]['Names'], 'web')
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.health_status, 'ONLINE')
        self.assertIsNotNone(self.asset.last_checked_at)

    @patch('apps.workspace.ssh_service._run_command', side_effect=_fake_run_command)
    @patch('apps.workspace.ssh_service.open_ssh_client')
    def test_probe_flags_warning_over_threshold(self, mock_open, mock_run):
        self.asset.alert_ram_threshold = 45  # ram 50% breaches
        self.asset.save()
        mock_open.return_value = MagicMock()
        from apps.workspace.ssh_service import probe_server_telemetry

        telemetry = probe_server_telemetry(self.asset)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.health_status, 'WARNING')
        self.assertEqual(telemetry['error'], None)

    def test_docker_container_id_injection_blocked(self):
        from apps.workspace.ssh_service import manage_docker_container
        with self.assertRaises(ValueError):
            manage_docker_container(self.asset, 'web; rm -rf /', 'restart')
        with self.assertRaises(ValueError):
            manage_docker_container(self.asset, 'web$(whoami)', 'logs')
        with self.assertRaises(ValueError):
            manage_docker_container(self.asset, 'web', 'exec')

    @patch('apps.workspace.ssh_service._run_command')
    @patch('apps.workspace.ssh_service.open_ssh_client')
    def test_docker_logs_command_shape(self, mock_open, mock_run):
        mock_open.return_value = MagicMock()
        mock_run.return_value = ('log line 1\nlog line 2\n', '', 0)
        from apps.workspace.ssh_service import manage_docker_container

        result = manage_docker_container(self.asset, 'shop-web-1', 'logs', tail=50)
        sent_commands = [c.args[1] for c in mock_run.call_args_list]
        self.assertIn('docker logs --tail 50 shop-web-1 2>&1', sent_commands)
        self.assertIn('log line 1', result['output'])

    @patch('apps.workspace.ssh_service.open_ssh_client')
    def test_execute_quotes_working_dir(self, mock_open):
        mock_client = MagicMock()
        mock_open.return_value = mock_client

        fake_stdout = MagicMock()
        fake_stdout.read.return_value = b'ok'
        fake_stderr = MagicMock()
        fake_stderr.read.return_value = b''
        fake_stdout.channel.recv_exit_status.return_value = 0
        mock_client.exec_command.return_value = (MagicMock(), fake_stdout, fake_stderr)

        from apps.workspace.ssh_service import execute_remote_command
        result = execute_remote_command(self.asset, 'deploy.sh --env prod', '/var/www/my app', 30)

        sent_command = mock_client.exec_command.call_args[0][0]
        self.assertEqual(sent_command, "cd '/var/www/my app' && deploy.sh --env prod")
        self.assertEqual(result['exit_status'], 0)
        self.assertEqual(result['stdout'], 'ok')

    def test_open_client_requires_host(self):
        from apps.workspace.ssh_service import open_ssh_client, SshConnectionError
        self.asset.ip_address = ''
        self.asset.hostname = ''
        self.asset.save()
        with self.assertRaises(SshConnectionError):
            open_ssh_client(self.asset)

    def test_private_key_loaded_from_memory_only(self):
        import paramiko
        from apps.workspace.ssh_service import _load_private_key_from_memory

        key = paramiko.RSAKey.generate(2048)
        buffer = io.StringIO()
        key.write_private_key(buffer)
        material = buffer.getvalue()

        loaded = _load_private_key_from_memory(material, '')
        self.assertIsInstance(loaded, paramiko.RSAKey)
        self.assertEqual(loaded.get_fingerprint(), key.get_fingerprint())


class _FakePtyChannel:
    def __init__(self):
        self.sent = []
        self.resized = []
        self._stream = [b'welcome to ws-box\r\n', b'$ ']

    def recv(self, nbytes):
        if self._stream:
            return self._stream.pop(0)
        return b''

    def send(self, data):
        self.sent.append(data)
        return len(data)

    def resize_pty(self, width, height, width_pixels=0, height_pixels=0):
        self.resized.append((width, height))

    def close(self):
        pass


class SshTerminalConsumerTests(TransactionTestCase):
    """WebSocket auth / BOLA / PTY IO via channels testing utilities."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='wsterm', email='wsterm@test.com', password='Password123!'
        )
        self.friend = User.objects.create_user(
            username='wsfriend', email='wsfriend@test.com', password='Password123!'
        )
        self.project = WorkspaceProject.objects.create(
            user=self.user, name='WS Project'
        )
        self.asset = InfrastructureAsset.objects.create(
            user=self.user, project=self.project, name='ws-box',
            ip_address='198.51.100.7',
            ssh_password_encrypted=encrypt_token('pass')
        )

    def _communicator(self, token=None, asset_id=None):
        from channels.testing import WebsocketCommunicator
        from config.asgi import application

        url = f'/ws/workspace/ssh/{asset_id or self.asset.id}/'
        headers = [(b'cookie', f'access_token={token}'.encode())] if token else []
        return WebsocketCommunicator(application, url, headers=headers)

    def test_unauthenticated_closed_4401(self):
        communicator = self._communicator()
        connected, close_code = asyncio.run(communicator.connect())
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    def test_non_owner_closed_4403(self):
        from channels.db import database_sync_to_async
        from django.db import connections
        communicator = self._communicator(token=generate_access_token(self.friend))

        async def scenario():
            connected, close_code = await communicator.connect()
            assert not connected
            assert close_code == 4403
            # Close ORM connections opened on the thread-sensitive worker so
            # teardown can drop the test database afterwards.
            await database_sync_to_async(connections.close_all)()

        asyncio.run(scenario())

    def test_owner_gets_output_stream_and_input_roundtrip(self):
        from channels.db import database_sync_to_async
        from django.db import connections

        fake_channel = _FakePtyChannel()
        fake_client = MagicMock()
        fake_client.invoke_shell.return_value = fake_channel

        communicator = self._communicator(token=generate_access_token(self.user))

        async def scenario():
            with patch('apps.workspace.consumers.open_ssh_client', return_value=fake_client):
                connected, _subprotocol = await communicator.connect()
                assert connected

                # The PTY-alive handshake frame arrives before any shell output
                ready_frame = _json.loads(await communicator.receive_from())
                assert ready_frame['type'] == 'ready'

                first = await communicator.receive_from()
                payload = _json.loads(first)
                assert payload['type'] == 'output'
                assert 'welcome to ws-box' in payload['data']

                await communicator.send_to(text_data=_json.dumps({
                    'type': 'input', 'data': 'uptime\r'
                }))
                await communicator.send_to(text_data=_json.dumps({
                    'type': 'resize', 'cols': 200, 'rows': 50
                }))
                await asyncio.sleep(0.2)

                assert b'uptime\r' in fake_channel.sent
                assert (200, 50) in fake_channel.resized

                await communicator.disconnect(timeout=10)
                # The consumer's disconnect hook writes an audit log row on
                # the worker thread - close that thread's connections after.
                await database_sync_to_async(connections.close_all)()

        asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Audit Round: PATCH project MA sync, economics consistency, margin fallback
# ---------------------------------------------------------------------------
from apps.workspace.models import ProjectType


class ProjectMAApiSyncTests(InfrastructureBaseTestCase):

    def test_patch_project_creates_and_links_inflow_obligation(self):
        res = self.client.patch(f'/api/workspace/projects/{self.project.id}/', {
            'project_type': 'MA_CONTRACT',
            'client_name': 'ACME Corp',
            'ma_amount': '5000.00',
            'ma_billing_cycle': 'MONTHLY',
            'ma_next_billing_date': str(date.today() + timedelta(days=5))
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db()
        obligation = self.project.ma_obligation
        self.assertIsNotNone(obligation)
        self.assertEqual(obligation.direction, 'INFLOW')
        self.assertEqual(obligation.amount, Decimal('5000.00'))
        self.assertEqual(obligation.user, self.user)
        self.assertEqual(obligation.metadata.get('source_type'), 'MA_CONTRACT')

        # PATCH response must carry freshly computed economics (context fix)
        self.assertIsNotNone(res.data.get('economics'))
        self.assertEqual(Decimal(res.data['economics']['monthly_ma_inflow']), Decimal('5000.00'))

    def test_patch_clearing_ma_cancels_obligation(self):
        self.client.patch(f'/api/workspace/projects/{self.project.id}/', {
            'ma_amount': '1000.00',
            'ma_next_billing_date': str(date.today())
        })
        self.project.refresh_from_db()
        first_id = self.project.ma_obligation_id
        self.assertIsNotNone(first_id)

        self.client.patch(
            f'/api/workspace/projects/{self.project.id}/',
            {'ma_amount': '0.00', 'ma_next_billing_date': None},
            format='json'
        )
        self.project.refresh_from_db()
        self.assertIsNone(self.project.ma_obligation)
        obligation = FinancialObligation.objects.get(id=first_id)
        self.assertEqual(obligation.status, 'CANCELLED')

    def test_create_project_with_ma_syncs_immediately(self):
        res = self.client.post('/api/workspace/projects/', {
            'name': 'Born With MA',
            'ma_amount': '2500.00',
            'ma_billing_cycle': 'MONTHLY',
            'ma_next_billing_date': str(date.today() + timedelta(days=10))
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        project = WorkspaceProject.objects.get(id=res.data['id'])
        self.assertIsNotNone(project.ma_obligation)
        self.assertEqual(project.ma_obligation.direction, 'INFLOW')


class ProjectEconomicsConsistencyTests(InfrastructureBaseTestCase):

    def test_non_ma_contract_with_fee_counts_as_revenue(self):
        # CLIENT_DEV project that simply has a recurring fee configured
        self.project.project_type = ProjectType.CLIENT_DEV
        self.project.ma_amount = Decimal('3000.00')
        self.project.ma_billing_cycle = 'MONTHLY'
        self.project.ma_next_billing_date = date.today()
        self.project.save()

        eco = get_project_economics(self.project)
        self.assertEqual(Decimal(eco['monthly_ma_inflow']), Decimal('3000.00'))
        self.assertEqual(Decimal(eco['annual_ma_inflow']), Decimal('36000.00'))

    def test_margin_pct_falls_back_to_projection_without_history(self):
        # MA fee 5000/mo, self-funded server 650/mo, no payments yet
        self.project.project_type = ProjectType.MA_CONTRACT
        self.project.ma_amount = Decimal('5000.00')
        self.project.ma_billing_cycle = 'MONTHLY'
        self.project.ma_next_billing_date = date.today()
        self.project.save()
        sync_project_ma_obligation(self.project)

        eco = get_project_economics(self.project)
        self.assertEqual(Decimal(eco['realized_inflow']), Decimal('0.00'))
        # fallback: (5000 - 650) / 5000 * 100 = 87.00
        self.assertEqual(Decimal(eco['margin_pct']), Decimal('87.00'))

    def test_margin_pct_prefers_realized_when_available(self):
        self.project.project_type = ProjectType.MA_CONTRACT
        self.project.ma_amount = Decimal('5000.00')
        self.project.ma_billing_cycle = 'MONTHLY'
        self.project.ma_next_billing_date = date.today()
        self.project.save()
        obligation = sync_project_ma_obligation(self.project)
        PaymentHistory.objects.create(
            user=self.user, obligation=obligation,
            paid_amount=Decimal('2500.00'), note='half payment'
        )
        # 650 self-funded infra outflow realized via its synced obligation
        self.asset.sync_to_radar = True
        self.asset.next_billing_date = date.today()
        self.asset.save()
        infra_ob = sync_infra_asset_obligation(self.asset)
        PaymentHistory.objects.create(
            user=self.user, obligation=infra_ob,
            paid_amount=Decimal('650.00'), note='server bill'
        )

        eco = get_project_economics(self.project)
        # realized: (2500 - 650) / 2500 * 100 = 74.00
        self.assertEqual(Decimal(eco['realized_inflow']), Decimal('2500.00'))
        self.assertEqual(Decimal(eco['realized_outflow']), Decimal('650.00'))
        self.assertEqual(Decimal(eco['margin_pct']), Decimal('74.00'))


# ---------------------------------------------------------------------------
# SSH key normalization & empty-string date coercion
# ---------------------------------------------------------------------------
class SSHKeyNormalizationTests(InfrastructureBaseTestCase):

    def test_crlf_key_without_trailing_newline_loads(self):
        """Windows CRLF line endings + missing trailing newline must still load."""
        import paramiko
        from apps.workspace.ssh_service import _load_private_key_from_memory

        key = paramiko.RSAKey.generate(2048)
        buffer = io.StringIO()
        key.write_private_key(buffer)
        mangled = buffer.getvalue().replace('\n', '\r\n').rstrip('\r\n')
        self.assertNotIn('\n', mangled[-5:])

        loaded = _load_private_key_from_memory(mangled, '')
        self.assertIsInstance(loaded, paramiko.RSAKey)
        self.assertEqual(loaded.get_fingerprint(), key.get_fingerprint())


class EmptyDateCoercionTests(InfrastructureBaseTestCase):

    def test_create_and_update_asset_with_empty_date_strings(self):
        res = self.client.post('/api/workspace/infrastructure/', {
            'project': str(self.project.id),
            'name': 'edge-box',
            'asset_type': 'VPS',
            'expiry_date': '',
            'next_billing_date': ''
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        asset = InfrastructureAsset.objects.get(id=res.data['id'])
        self.assertIsNone(asset.expiry_date)
        self.assertIsNone(asset.next_billing_date)

        # Set real dates first, then clear them back via empty strings
        res = self.client.patch(f'/api/workspace/infrastructure/{asset.id}/', {
            'expiry_date': str(date.today() + timedelta(days=30)),
            'next_billing_date': str(date.today() + timedelta(days=5))
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        asset.refresh_from_db()
        self.assertIsNotNone(asset.expiry_date)

        res = self.client.patch(f'/api/workspace/infrastructure/{asset.id}/', {
            'expiry_date': '',
            'next_billing_date': ''
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        asset.refresh_from_db()
        self.assertIsNone(asset.expiry_date)
        self.assertIsNone(asset.next_billing_date)

    def test_project_ma_dates_empty_string_accepted(self):
        res = self.client.patch(f'/api/workspace/projects/{self.project.id}/', {
            'ma_start_date': '',
            'ma_end_date': '',
            'ma_next_billing_date': ''
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertIsNone(self.project.ma_start_date)
        self.assertIsNone(self.project.ma_end_date)
        self.assertIsNone(self.project.ma_next_billing_date)


class BatchedProbeTests(InfrastructureBaseTestCase):

    @patch('apps.workspace.ssh_service._run_command')
    @patch('apps.workspace.ssh_service.open_ssh_client')
    def test_single_shot_batched_probe_parses_all_sections(self, mock_open, mock_run):
        from apps.workspace.ssh_service import (
            probe_server_telemetry, PROBE_BATCH_CMD, PROBE_SECTION_SEP
        )

        combined = PROBE_SECTION_SEP.join([
            '987654.32 100000\n',
            '0.80 0.50 0.30 1/150 9000\n',
            '2\n',
            '800 1600',
            '10240M 20480M 51%\n',
            'Linux 5.15.0-generic\n',
            '{"ID":"abc123","Names":"web","Image":"nginx:latest","State":"running","Status":"Up 3 hours","Ports":""}\n'
            '{"ID":"def456","Names":"worker","Image":"redis:7","State":"exited","Status":"Exited (0) 5 minutes ago","Ports":""}\n',
        ])
        mock_run.return_value = (combined, '', 0)
        mock_open.return_value = MagicMock()

        telemetry = probe_server_telemetry(self.asset)

        # Exactly ONE exec round-trip carrying the batched command
        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(mock_run.call_args[0][1], PROBE_BATCH_CMD)

        self.assertEqual(telemetry['uptime_human'], '11d 10h')
        self.assertEqual(telemetry['load_avg'], 0.8)
        self.assertEqual(telemetry['cpu_pct'], 40.0)
        self.assertEqual(telemetry['ram_used_mb'], 800.0)
        self.assertEqual(telemetry['ram_total_mb'], 1600.0)
        self.assertEqual(telemetry['ram_pct'], 50.0)
        self.assertEqual(telemetry['disk_used_gb'], 10.0)
        self.assertEqual(telemetry['disk_total_gb'], 20.0)
        self.assertEqual(telemetry['disk_pct'], 51.0)
        self.assertEqual(telemetry['kernel'], 'Linux 5.15.0-generic')
        self.assertEqual(len(telemetry['containers']), 2)
        self.assertEqual(telemetry['containers'][0]['Names'], 'web')
        self.assertIsNone(telemetry['error'])
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.health_status, 'ONLINE')
