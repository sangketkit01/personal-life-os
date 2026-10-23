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
        """Test registration using a valid Invite Code."""
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

        # Verify that invite code usage count increased
        self.invite.refresh_from_db()
        self.assertEqual(self.invite.uses_count, 1)

    def test_login_and_token_rotation(self):
        """Test authentication login and refresh token rotation."""
        login_url = reverse('auth-login')
        res = self.client.post(login_url, {'username': 'boss', 'password': 'Password123!'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', res.cookies)
        self.assertIn('refresh_token', res.cookies)

        # Test GET /api/auth/me/
        me_url = reverse('auth-me')
        res_me = self.client.get(me_url)
        self.assertEqual(res_me.status_code, status.HTTP_200_OK)
        self.assertEqual(res_me.data['username'], 'boss')

        # Test token rotation
        old_refresh = res.cookies['refresh_token'].value
        refresh_url = reverse('auth-refresh')
        res_refresh = self.client.post(refresh_url)
        self.assertEqual(res_refresh.status_code, status.HTTP_200_OK)
        new_refresh = res_refresh.cookies['refresh_token'].value
        self.assertNotEqual(old_refresh, new_refresh)

    def test_invalid_invite_code(self):
        """Test registration with invalid invite code is rejected."""
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
        """API-02 Test: /api/health/ returns healthy status and connects to database."""
        res = self.client.get('/api/health/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()['status'], 'healthy')
        self.assertEqual(res.json()['database'], 'connected')

    def test_audit_logs_recorded_and_listed(self):
        """Item 8 Test: Audit logs are recorded on login and listed via API."""
        # Login
        self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')

        # Check API audit-logs
        res = self.client.get(reverse('auth-audit-logs'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res.data) > 0)
        self.assertEqual(res.data[0]['category'], 'AUTH')
        self.assertEqual(res.data[0]['action'], 'LOGIN')

    def test_refresh_with_expired_access_token(self):
        """Test that with expired access token and valid refresh token, renewal succeeds with 200 OK."""
        import datetime, jwt
        from django.conf import settings

        login_res = self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')
        refresh_token = login_res.cookies['refresh_token'].value

        # Generate expired access token
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
        """Test grace period: duplicate refresh token sent within 60s is accepted without revoking session."""
        login_res = self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')
        initial_refresh = login_res.cookies['refresh_token'].value

        # Request 1: first token rotation
        res1 = self.client.post(reverse('auth-refresh'))
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Request 2 (simulate concurrent tab sending initial refresh token again)
        concurrent_client = APIClient()
        concurrent_client.cookies['refresh_token'] = initial_refresh
        res2 = concurrent_client.post(reverse('auth-refresh'))
        # Must pass grace period (200 OK) instead of being revoked
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

    def test_weak_password_rejected_by_django_validator(self):
        """Test that weak password (digits only or too short) is rejected by Django validator."""
        url = reverse('auth-register')
        data = {
            'username': 'weak_user',
            'email': 'weak@test.com',
            'password': '123',  # too short and numeric only
            'invite_code': 'TEST-INVITE-2026'
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', res.data)

    def test_failed_login_recorded_in_audit_log(self):
        """Test that failed login attempt records ActivityLog with FAILED status."""
        from apps.accounts.models import ActivityLog
        self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'WrongPassword999'}, format='json')

        failed_log = ActivityLog.objects.filter(user=self.admin, action='LOGIN_FAILED', status='FAILED').first()
        self.assertIsNotNone(failed_log)
        self.assertEqual(failed_log.category, 'AUTH')
