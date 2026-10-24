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

    def test_single_use_invite_code_and_deletion(self):
        """Test that 1 Invite Code = 1 User strictly (ignores max_uses>1) and can be deleted."""
        self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')

        # Attempt to pass max_uses=500 -> must enforce max_uses=1
        create_res = self.client.post(reverse('auth-invites'), {'max_uses': 500}, format='json')
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_res.data['max_uses'], 1)
        invite_id = create_res.data['id']

        # Another user cannot delete boss's invite code
        other_user = User.objects.create_user(username='other', email='other@test.com', password='Password123!')
        other_client = APIClient()
        other_client.post(reverse('auth-login'), {'username': 'other', 'password': 'Password123!'}, format='json')
        forbidden_del = other_client.delete(reverse('auth-invite-detail', kwargs={'invite_id': invite_id}))
        self.assertEqual(forbidden_del.status_code, status.HTTP_404_NOT_FOUND)

        # Owner can delete the invite code
        del_res = self.client.delete(reverse('auth-invite-detail', kwargs={'invite_id': invite_id}))
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(InviteCode.objects.filter(id=invite_id).exists())

    def test_instant_access_token_revocation_on_logout_and_session_revoke(self):
        """Test that access_token bound to session_id is immediately rejected when session is revoked."""
        login_res = self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')
        access_token = login_res.cookies['access_token'].value

        # Capture the token in a separate client before logout
        stolen_client = APIClient()
        stolen_client.cookies['access_token'] = access_token
        self.assertEqual(stolen_client.get(reverse('auth-me')).status_code, status.HTTP_200_OK)

        # User logs out -> revokes the session in DB
        self.client.post(reverse('auth-logout'))

        # Stolen access_token must be rejected immediately (0-second revocation)
        res_after = stolen_client.get(reverse('auth-me'))
        self.assertEqual(res_after.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_grace_period_both_sibling_tokens_survive(self):
        """Test that after concurrent grace-period refresh, the first rotated token (Token_1) is not wiped out."""
        login_res = self.client.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')
        initial_refresh = login_res.cookies['refresh_token'].value

        # Tab 1 rotates initial_refresh -> gets Token_1
        res1 = self.client.post(reverse('auth-refresh'))
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        token_1 = res1.cookies['refresh_token'].value

        # Tab 2 concurrently sends initial_refresh within grace window -> gets Token_2
        tab2_client = APIClient()
        tab2_client.cookies['refresh_token'] = initial_refresh
        res2 = tab2_client.post(reverse('auth-refresh'))
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # Later, Tab 1 uses Token_1 -> must succeed (200 OK) and NOT trigger false-positive reuse revocation!
        tab1_later = APIClient()
        tab1_later.cookies['refresh_token'] = token_1
        res3 = tab1_later.post(reverse('auth-refresh'))
        self.assertEqual(res3.status_code, status.HTTP_200_OK)

    def test_change_password_revokes_other_sessions(self):
        """Test changing password updates credentials and revokes other active sessions."""
        # Device 1 login
        client1 = APIClient()
        client1.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')

        # Device 2 login
        client2 = APIClient()
        client2.post(reverse('auth-login'), {'username': 'boss', 'password': 'Password123!'}, format='json')

        # Device 1 changes password
        res = client1.post(reverse('auth-password-change'), {
            'current_password': 'Password123!',
            'new_password': 'NewStrongPassword456!'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['revoked_sessions_count'], 1)

        # Device 1 remains authenticated
        self.assertEqual(client1.get(reverse('auth-me')).status_code, status.HTTP_200_OK)
        # Device 2 is immediately revoked
        self.assertEqual(client2.get(reverse('auth-me')).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_does_not_leak_existing_username_without_valid_invite(self):
        """Test that uninvited callers cannot enumerate existing usernames/emails via /api/auth/register/."""
        res = self.client.post(reverse('auth-register'), {
            'username': 'boss',
            'email': 'boss@test.com',
            'password': 'Password123!',
            'invite_code': 'BOGUS-INVITE'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invite_code', res.data)
        self.assertNotIn('username', res.data)
        self.assertNotIn('email', res.data)

    def test_x_forwarded_for_ignored_by_default(self):
        """Test that spoofed X-Forwarded-For header does not forge session IP when TRUST_X_FORWARDED_FOR is False."""
        self.client.post(
            reverse('auth-login'),
            {'username': 'boss', 'password': 'Password123!'},
            format='json',
            HTTP_X_FORWARDED_FOR='203.0.113.99'
        )
        session = UserDeviceSession.objects.filter(user=self.admin).first()
        self.assertEqual(session.ip_address, '127.0.0.1')
