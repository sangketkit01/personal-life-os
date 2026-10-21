from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.workspace.models import WorkspaceProject, TaskDocument, TaskStatus, TaskPriority, Note
from apps.workspace.services import calculate_deadline_info, transition_task_status, get_workspace_overview
from apps.accounts.tokens import generate_access_token

User = get_user_model()


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
            name='งานฟรีแลนซ์ บ. A',
            color='#3B82F6'
        )
        self.client = APIClient()
        token = generate_access_token(self.user)
        self.client.cookies['access_token'] = token

    def test_task_status_transition_and_completion_timestamp(self):
        """ทดสอบการเปลี่ยนสถานะงาน และการแสตมป์ completed_at อัตโนมัติ"""
        task = TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='ส่งใบเสนอราคา',
            status=TaskStatus.DRAFTING
        )
        self.assertIsNone(task.completed_at)

        # 1. ย้ายไปสถานะ COMPLETED
        transition_task_status(task, TaskStatus.COMPLETED)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task.completed_at)

        # 2. ดึงกลับมาทำใหม่เป็น WAITING
        transition_task_status(task, TaskStatus.WAITING)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.WAITING)
        self.assertIsNone(task.completed_at)

    def test_deadline_calculation_and_overdue(self):
        """ทดสอบการคำนวณวันส่งงาน (นับถอยหลัง และงานที่เลยกำหนด)"""
        now = timezone.now()

        # งานที่จะถึงในอีก 2 วัน
        future_dl = now + timedelta(days=2)
        info_future = calculate_deadline_info(future_dl)
        self.assertFalse(info_future['is_overdue'])
        self.assertEqual(info_future['days_left'], 2)
        self.assertEqual(info_future['urgency'], 'ATTENTION')

        # งานที่เลยกำหนดส่งเมื่อวาน
        past_dl = now - timedelta(days=1)
        info_past = calculate_deadline_info(past_dl)
        self.assertTrue(info_past['is_overdue'])
        self.assertEqual(info_past['urgency'], 'OVERDUE')

    def test_workspace_overview_aggregation(self):
        """ทดสอบฟังก์ชันสรุปภาพรวม Workspace ประจำ User"""
        now = timezone.now()
        # 1. งาน Drafting 1 ชิ้น
        TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='ร่างสัญญาจ้าง',
            status=TaskStatus.DRAFTING,
            deadline=now + timedelta(days=1)
        )
        # 2. งาน Waiting 1 ชิ้น (เลยกำหนด)
        TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='รอเซ็นเอกสาร',
            status=TaskStatus.WAITING,
            deadline=now - timedelta(days=2)
        )

        overview = get_workspace_overview(self.user)
        self.assertEqual(overview['pipeline_counts']['drafting'], 1)
        self.assertEqual(overview['pipeline_counts']['waiting'], 1)
        self.assertEqual(overview['pipeline_counts']['total_active'], 2)
        self.assertEqual(overview['overdue_count'], 1)

    def test_api_move_task_status(self):
        """ทดสอบ Action /api/workspace/tasks/{id}/move/ ผ่าน REST API"""
        task = TaskDocument.objects.create(
            user=self.user,
            project=self.project,
            title='ใบกำกับภาษี',
            status=TaskStatus.DRAFTING
        )

        url = f'/api/workspace/tasks/{task.id}/move/'
        res = self.client.post(url, {'status': 'COMPLETED'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'COMPLETED')
        self.assertIsNotNone(res.data['completed_at'])

    def test_multi_user_workspace_isolation(self):
        """ทดสอบความปลอดภัย: User A ไม่สามารถดูหรือย้ายงานของ User B ได้"""
        friend_project = WorkspaceProject.objects.create(
            user=self.friend,
            name='งานลับของเพื่อน'
        )
        friend_task = TaskDocument.objects.create(
            user=self.friend,
            project=friend_project,
            title='งานส่วนตัวเพื่อน'
        )

        # User A พยายามแอบดูงานของเพื่อน
        res_get = self.client.get(f'/api/workspace/tasks/{friend_task.id}/')
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        # User A พยายามแอบย้ายสถานะงานของเพื่อน
        res_move = self.client.post(f'/api/workspace/tasks/{friend_task.id}/move/', {'status': 'COMPLETED'})
        self.assertEqual(res_move.status_code, status.HTTP_404_NOT_FOUND)
