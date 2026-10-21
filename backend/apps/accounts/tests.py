from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import InviteCode, UserDeviceSession

User = get_user_model()


class AuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='boss',
            email='boss@test.com',
            password='Password123!'
        )
        self.invite = InviteCode.objects.create(
            code='TEST-INVITE-2026',
            created_by=self.admin,
            max_uses=2
        )

    def test_register_with_invite_code(self):
        """ทดสอบการสมัครสมาชิกโดยใช้ Invite Code"""
        url = reverse('auth-register')
        data = {
            'username': 'friend_user',
            'email': 'friend@test.com',
            'password': 'Password123!',
            'invite_code': 'TEST-INVITE-2026'
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', res.cookies)
        self.assertIn('refresh_token', res.cookies)
        self.assertTrue(res.cookies['access_token']['httponly'])

        # ตรวจสอบว่าโควตา Invite ถูกนับเพิ่ม
        self.invite.refresh_from_db()
        self.assertEqual(self.invite.uses_count, 1)

    def test_login_and_token_rotation(self):
        """ทดสอบการล็อกอิน และการหมุนเวียน Refresh Token"""
        login_url = reverse('auth-login')
        res = self.client.post(login_url, {'username': 'boss', 'password': 'Password123!'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', res.cookies)
        self.assertIn('refresh_token', res.cookies)

        # ทดสอบเรียก /api/auth/me/
        me_url = reverse('auth-me')
        res_me = self.client.get(me_url)
        self.assertEqual(res_me.status_code, status.HTTP_200_OK)
        self.assertEqual(res_me.data['username'], 'boss')

        # ทดสอบ Token Rotation
        old_refresh = res.cookies['refresh_token'].value
        refresh_url = reverse('auth-refresh')
        res_refresh = self.client.post(refresh_url)
        self.assertEqual(res_refresh.status_code, status.HTTP_200_OK)
        new_refresh = res_refresh.cookies['refresh_token'].value
        self.assertNotEqual(old_refresh, new_refresh)

    def test_invalid_invite_code(self):
        """ทดสอบสมัครด้วย Invite Code มั่ว ต้องโดนปฏิเสธ"""
        url = reverse('auth-register')
        data = {
            'username': 'intruder',
            'email': 'hacker@test.com',
            'password': 'Password123!',
            'invite_code': 'FAKE-CODE-999'
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_health_check_endpoint(self):
        """API-02 Test: ทดสอบ /api/health/ คืนค่าสถานะ healthy และเชื่อมต่อฐานข้อมูลได้"""
        res = self.client.get('/api/health/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()['status'], 'healthy')
        self.assertEqual(res.json()['database'], 'connected')

    def test_audit_logs_recorded_and_listed(self):
        """Item 8 Test: ทดสอบการบันทึก Audit Log เมื่อ Login และสามารถเรียกดูได้ผ่าน API"""
        # Login
        self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')

        # ตรวจสอบ API audit-logs
        res = self.client.get(reverse('auth-audit-logs'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res.data) > 0)
        self.assertEqual(res.data[0]['category'], 'AUTH')
        self.assertEqual(res.data[0]['action'], 'LOGIN')

    def test_refresh_with_expired_access_token(self):
        """ทดสอบว่าเมื่อ access_token หมดอายุ แต่ refresh_token ยังอยู่ ต้องต่ออายุสำเร็จ 200 OK ไม่ใช่ 403"""
        import datetime, jwt
        from django.conf import settings

        login_res = self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')
        refresh_token = login_res.cookies['refresh_token'].value

        # สร้าง Expired Access Token
        now = datetime.datetime.now(datetime.timezone.utc)
        expired_access = jwt.encode({
            'token_type': 'access',
            'user_id': str(self.admin.id),
            'username': self.admin.username,
            'iat': now - datetime.timedelta(minutes=30),
            'exp': now - datetime.timedelta(minutes=15)
        }, settings.SECRET_KEY, algorithm='HS256')

        new_client = APIClient()
        new_client.cookies['access_token'] = expired_access
        new_client.cookies['refresh_token'] = refresh_token

        res = new_client.post(reverse('auth-refresh'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', res.cookies)
        self.assertIn('refresh_token', res.cookies)

    def test_grace_period_concurrent_refresh(self):
        """ทดสอบ Grace Period: หากส่ง Refresh Token ใบเดิมซ้ำภายใน 60 วินาที ต้องไม่ถูกเตะออกจากระบบ"""
        login_res = self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')
        initial_refresh = login_res.cookies['refresh_token'].value

        # Request 1: ทำการหมุน Token ครั้งแรก
        res1 = self.client.post(reverse('auth-refresh'))
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Request 2 (จำลองคำขอคู่ขนานจากอีกแท็บที่ส่ง initial_refresh มาซ้ำ)
        concurrent_client = APIClient()
        concurrent_client.cookies['refresh_token'] = initial_refresh
        res2 = concurrent_client.post(reverse('auth-refresh'))
        # ต้องผ่าน Grace Period (200 OK) ไม่ใช่ถูก Revoke
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

    def test_weak_password_rejected_by_django_validator(self):
        """ทดสอบว่ารหัสผ่านที่อ่อนแอ (เช่น ตัวเลขล้วน หรือสั้นเกินไป) ต้องถูกปฏิเสธโดย Django Validator"""
        url = reverse('auth-register')
        data = {
            'username': 'weak_user',
            'email': 'weak@test.com',
            'password': '123',  # สั้นเกินไปและตัวเลขล้วน
            'invite_code': 'TEST-INVITE-2026'
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', res.data)

    def test_failed_login_recorded_in_audit_log(self):
        """ทดสอบว่าเมื่อกรอกรหัสผ่านผิด ระบบจะบันทึก ActivityLog สถานะ FAILED"""
        from apps.accounts.models import ActivityLog
        self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'WrongPassword999'}, format='json')

        failed_log = ActivityLog.objects.filter(user=self.admin, action='LOGIN_FAILED', status='FAILED').first()
        self.assertIsNotNone(failed_log)
        self.assertEqual(failed_log.category, 'AUTH')
