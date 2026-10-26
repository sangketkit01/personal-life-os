import os
import secrets
from urllib.parse import urlparse
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db import models, transaction as db_transaction
from rest_framework import status, views, permissions, response, exceptions
from rest_framework.throttling import ScopedRateThrottle
from .models import User, InviteCode, UserDeviceSession, ActivityLog
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    UserDeviceSessionSerializer,
    InviteCodeSerializer,
    ActivityLogSerializer
)
from .services import log_activity
from .tokens import (
    generate_access_token,
    generate_refresh_token,
    decode_token,
    hash_token,
    get_client_ip,
    get_device_name
)


def set_auth_cookies(res: response.Response, access_token: str, refresh_token: str):
    """Securely attach JWT tokens into HttpOnly cookies."""
    # In local development secure=False, on production (HTTPS) secure=True
    is_secure = not settings.DEBUG

    # Access Token (15-minute validity)
    res.set_cookie(
        key='access_token',
        value=access_token,
        max_age=15 * 60,
        httponly=True,
        samesite='Lax',
        secure=is_secure,
        path='/'
    )

    # Refresh Token (7-day validity)
    res.set_cookie(
        key='refresh_token',
        value=refresh_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        samesite='Lax',
        secure=is_secure,
        path='/'
    )


def clear_auth_cookies(res: response.Response):
    """Helper to clear auth cookies on logout."""
    res.delete_cookie(key='access_token', path='/')
    res.delete_cookie(key='refresh_token', path='/')


def get_current_session_id(request):
    """Extract current session_id from refresh_token or access_token cookie."""
    for cookie_name in ('refresh_token', 'access_token'):
        raw_token = request.COOKIES.get(cookie_name)
        if raw_token:
            try:
                payload = decode_token(raw_token)
                sid = payload.get('session_id')
                if sid:
                    return sid
            except Exception:
                pass
    return None


def _is_request_origin_allowed(request) -> bool:
    """
    Validates Origin / Referer for cookie-issuing endpoints (login & register).
    Allows non-browser / same-origin direct calls, configured CORS / CSRF origins,
    current host, and dev localhost variants. Rejects external cross-origin origins.
    """
    origin = request.META.get('HTTP_ORIGIN')
    referer = request.META.get('HTTP_REFERER')
    header_val = origin or referer
    if not header_val:
        return True

    try:
        parsed = urlparse(header_val)
        target_origin = f"{parsed.scheme}://{parsed.netloc}".lower()
        target_host = (parsed.hostname or '').lower()
    except Exception:
        return False

    allowed_origins = set()
    for o in getattr(settings, 'CORS_ALLOWED_ORIGINS', []):
        allowed_origins.add(o.lower().rstrip('/'))
    for o in getattr(settings, 'CSRF_TRUSTED_ORIGINS', []):
        allowed_origins.add(o.lower().rstrip('/'))

    try:
        req_host = request.get_host().lower()
        allowed_origins.add(f"http://{req_host}")
        allowed_origins.add(f"https://{req_host}")
    except Exception:
        pass

    for port in ('5173', '3000', '8000', '80', '443'):
        allowed_origins.add(f"http://localhost:{port}")
        allowed_origins.add(f"http://127.0.0.1:{port}")
        allowed_origins.add(f"https://localhost:{port}")
        allowed_origins.add(f"https://127.0.0.1:{port}")

    if target_origin in allowed_origins:
        return True

    allowed_hosts = [h.lower() for h in getattr(settings, 'ALLOWED_HOSTS', []) if h != '*']
    if target_host and target_host in allowed_hosts:
        return True

    return False


class RegisterView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_register'

    def post(self, request):
        if not _is_request_origin_allowed(request):
            return response.Response(
                {'error': 'Cross-origin request rejected.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create session for registering device
        device_name = get_device_name(request)
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        session = UserDeviceSession.objects.create(
            user=user,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_hash=''
        )

        access_token = generate_access_token(user, session.id)
        refresh_token = generate_refresh_token(user, session.id)

        session.refresh_token_hash = hash_token(refresh_token)
        session.save(update_fields=['refresh_token_hash'])

        log_activity(user, 'AUTH', 'REGISTER', 'Successfully registered new account', request=request)

        res = response.Response(
            {
                'message': 'Registration successful. Welcome to Personal Life OS',
                'user': UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )
        set_auth_cookies(res, access_token, refresh_token)
        return res


class LoginView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_login'

    def post(self, request):
        if not _is_request_origin_allowed(request):
            return response.Response(
                {'error': 'Cross-origin request rejected.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            # Record failed login attempt in audit log if account exists
            username_input = request.data.get('username')
            if username_input and isinstance(username_input, str):
                user_found = User.objects.filter(
                    models.Q(username__iexact=username_input.strip()) | models.Q(email__iexact=username_input.strip())
                ).first()
                if user_found:
                    log_activity(user_found, 'AUTH', 'LOGIN_FAILED', 'Failed login attempt: invalid credentials', request=request, status='FAILED')
            serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        device_name = get_device_name(request)
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Create session for the logged-in device
        session = UserDeviceSession.objects.create(
            user=user,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_hash=''
        )

        access_token = generate_access_token(user, session.id)
        refresh_token = generate_refresh_token(user, session.id)

        session.refresh_token_hash = hash_token(refresh_token)
        session.save(update_fields=['refresh_token_hash'])

        log_activity(user, 'AUTH', 'LOGIN', f'Logged in via {device_name}', request=request)

        res = response.Response(
            {
                'message': 'Login successful',
                'user': UserSerializer(user).data
            },
            status=status.HTTP_200_OK
        )
        set_auth_cookies(res, access_token, refresh_token)
        return res


class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        session_id = get_current_session_id(request)
        if session_id:
            UserDeviceSession.objects.filter(id=session_id, user=request.user).update(is_revoked=True)

        res = response.Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
        clear_auth_cookies(res)
        log_activity(request.user, 'AUTH', 'LOGOUT', 'Logged out', request=request)
        return res


class RefreshTokenView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_refresh'

    def post(self, request):
        # Origin validation for CSRF protection on cookie-based refresh
        origin = request.META.get('HTTP_ORIGIN')
        if origin:
            allowed_origins = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', []))
            host = request.get_host()
            if origin not in allowed_origins and origin not in (f"http://{host}", f"https://{host}"):
                raise exceptions.PermissionDenied('CSRF validation failed: untrusted Origin.')

        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return response.Response({'detail': 'Refresh token not found.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = decode_token(refresh_token)
        except Exception:
            res = response.Response({'detail': 'Invalid or expired refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(res)
            return res

        if payload.get('token_type') != 'refresh':
            return response.Response({'detail': 'Invalid token type.'}, status=status.HTTP_401_UNAUTHORIZED)

        session_id = payload.get('session_id')
        user_id = payload.get('user_id')

        try:
            with db_transaction.atomic():
                session = UserDeviceSession.objects.select_for_update().get(id=session_id, user_id=user_id)

                if session.is_revoked:
                    res = response.Response({'detail': 'Session has been revoked. Please sign in again.'}, status=status.HTTP_401_UNAUTHORIZED)
                    clear_auth_cookies(res)
                    return res

                # Verify Token Hash: supports active sibling hashes and Grace Period parent hash
                current_hash = hash_token(refresh_token)
                active_hashes = [h for h in session.refresh_token_hash.split(',') if h]
                is_current_token = (current_hash in active_hashes)

                is_grace_token = False
                if not is_current_token and session.previous_refresh_token_hash == current_hash and session.rotated_at:
                    grace_seconds = getattr(settings, 'REFRESH_TOKEN_GRACE_PERIOD_SECONDS', 60)
                    diff_seconds = (timezone.now() - session.rotated_at).total_seconds()
                    if diff_seconds <= grace_seconds:
                        is_grace_token = True

                if not is_current_token and not is_grace_token:
                    # Token Reuse Detected!
                    session.is_revoked = True
                    session.save(update_fields=['is_revoked'])
                    res = response.Response(
                        {'detail': 'Token reuse detected. Session revoked for security.'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                    clear_auth_cookies(res)
                    return res

                user = session.user
                if not user.is_active:
                    return response.Response({'detail': 'User account is deactivated.'}, status=status.HTTP_401_UNAUTHORIZED)

                # Token Rotation: create new access token and refresh token bound to session
                new_access_token = generate_access_token(user, session.id)
                new_refresh_token = generate_refresh_token(user, session.id)
                new_refresh_hash = hash_token(new_refresh_token)

                if is_current_token:
                    session.previous_refresh_token_hash = current_hash
                    session.rotated_at = timezone.now()
                    session.refresh_token_hash = new_refresh_hash
                else:
                    # Grace period concurrent request: keep parent hash & rotated_at intact,
                    # and store sibling hash alongside the first rotated hash (max 3 hashes = 194 chars)
                    sibling_hashes = (active_hashes + [new_refresh_hash])[-3:]
                    session.refresh_token_hash = ','.join(sibling_hashes)

                session.ip_address = get_client_ip(request)
                session.save(update_fields=['previous_refresh_token_hash', 'refresh_token_hash', 'rotated_at', 'ip_address', 'last_active_at'])

            res = response.Response({'message': 'Token refreshed successfully'}, status=status.HTTP_200_OK)
            set_auth_cookies(res, new_access_token, new_refresh_token)
            return res
        except UserDeviceSession.DoesNotExist:
            res = response.Response({'detail': 'Session not found.'}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(res)
            return res


class MeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return response.Response(UserSerializer(request.user).data)

    def patch(self, request):
        """Update the authenticated user's preferences (e.g. preferred_language)."""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password', 'updated_at'])

        # Revoke all other active sessions on password change
        current_session_id = get_current_session_id(request)
        qs = UserDeviceSession.objects.filter(user=user, is_revoked=False)
        if current_session_id:
            qs = qs.exclude(id=current_session_id)
        revoked_count = qs.update(is_revoked=True)

        log_activity(
            user,
            'AUTH',
            'PASSWORD_CHANGED',
            f'Changed account password (revoked {revoked_count} other sessions)',
            request=request
        )
        return response.Response({
            'message': 'Password changed successfully.',
            'revoked_sessions_count': revoked_count
        })


class SessionsListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        current_session_id = get_current_session_id(request)

        # Automatically expire stale sessions inactive for more than 7 days
        cutoff = timezone.now() - timedelta(days=7)
        UserDeviceSession.objects.filter(
            user=request.user,
            is_revoked=False,
            last_active_at__lt=cutoff
        ).update(is_revoked=True)

        sessions = UserDeviceSession.objects.filter(user=request.user, is_revoked=False).order_by('-last_active_at')
        serializer = UserDeviceSessionSerializer(sessions, many=True, context={'current_session_id': current_session_id})
        return response.Response(serializer.data)


class RevokeSessionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = UserDeviceSession.objects.get(id=session_id, user=request.user)
            session.is_revoked = True
            session.save(update_fields=['is_revoked'])
            log_activity(
                request.user,
                'AUTH',
                'SESSION_REVOKED',
                f'Revoked session on {session.device_name} ({session.ip_address})',
                request=request
            )
            return response.Response({'message': 'Device session revoked successfully'})
        except UserDeviceSession.DoesNotExist:
            return response.Response({'detail': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


class RevokeOtherSessionsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_session_id = get_current_session_id(request)
        qs = UserDeviceSession.objects.filter(user=request.user, is_revoked=False)
        if current_session_id:
            qs = qs.exclude(id=current_session_id)
        revoked_count = qs.update(is_revoked=True)

        log_activity(
            request.user,
            'AUTH',
            'REVOKE_OTHER_SESSIONS',
            f'Revoked {revoked_count} other active device sessions',
            request=request
        )
        return response.Response({
            'message': f'Revoked {revoked_count} other sessions successfully.',
            'revoked_count': revoked_count
        })


class TelegramConnectTokenView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.user.generate_telegram_connect_token()
        bot_username = os.getenv('TELEGRAM_BOT_USERNAME', 'PersonalLifeOSBot')
        deep_link = f"https://t.me/{bot_username}?start={token}"
        return response.Response({
            'connect_token': token,
            'deep_link': deep_link,
            'instructions': 'Open this link in Telegram and tap START to connect the bot instantly'
        })


class TelegramTestAlertView(views.APIView):
    """Send a test alert to the connected Telegram chat (one-click check)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.telegram_chat_id:
            return response.Response(
                {'detail': 'Telegram is not connected. Pair the bot from Settings first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or os.getenv('TELEGRAM_BOT_TOKEN', '')
        if not bot_token:
            return response.Response(
                {'detail': 'TELEGRAM_BOT_TOKEN is not configured on the server.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from telegram import Bot
        from apps.bot.i18n import bot_msg
        from apps.bot.markdown_utils import escape_md

        text = (
            f"{bot_msg(user, 'test.title')}\n\n"
            f"{bot_msg(user, 'test.body', username=escape_md(user.username))}"
        )

        async def _send():
            bot = Bot(bot_token)
            try:
                await bot.send_message(
                    chat_id=user.telegram_chat_id,
                    text=text,
                    parse_mode='Markdown'
                )
            finally:
                await bot.shutdown()

        try:
            import asyncio
            asyncio.run(_send())
        except Exception as exc:
            return response.Response(
                {'detail': f'Failed to deliver Telegram message: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        log_activity(user, 'AUTH', 'TELEGRAM_TEST_ALERT', 'Sent Telegram test alert', request=request)
        return response.Response({'message': 'Test alert delivered to your Telegram chat.'})


class TelegramDisconnectView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        user.telegram_chat_id = None
        user.telegram_connect_token = None
        user.save(update_fields=['telegram_chat_id', 'telegram_connect_token', 'updated_at'])
        log_activity(user, 'AUTH', 'TELEGRAM_DISCONNECT', 'Disconnected Telegram Bot', request=request)
        return response.Response({
            'message': 'Telegram account disconnected successfully.',
            'user': UserSerializer(user).data
        })


class InviteCodeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invites = InviteCode.objects.select_related('used_by').filter(created_by=request.user).order_by('-created_at')
        return response.Response(InviteCodeSerializer(invites, many=True).data)

    def post(self, request):
        # Strictly 1 Invite Code = 1 User
        code = None
        for _ in range(10):
            candidate = f"LIFE-{secrets.token_hex(4).upper()}"
            if not InviteCode.objects.filter(code=candidate).exists():
                code = candidate
                break

        if not code:
            return response.Response(
                {'detail': 'Could not generate unique invite code. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        invite = InviteCode.objects.create(
            code=code,
            created_by=request.user,
            max_uses=1
        )
        log_activity(request.user, 'AUTH', 'INVITE_CREATED', f'Generated single-use invite code {code}', request=request)
        return response.Response(InviteCodeSerializer(invite).data, status=status.HTTP_201_CREATED)


class InviteCodeDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, invite_id):
        try:
            invite = InviteCode.objects.get(id=invite_id, created_by=request.user)
            code_str = invite.code
            invite.delete()
            log_activity(request.user, 'AUTH', 'INVITE_DELETED', f'Deleted invite code {code_str}', request=request)
            return response.Response(status=status.HTTP_204_NO_CONTENT)
        except InviteCode.DoesNotExist:
            return response.Response({'detail': 'Invite code not found.'}, status=status.HTTP_404_NOT_FOUND)


class ActivityLogView(views.APIView):
    """API endpoint to retrieve user security and activity audit log."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        logs = ActivityLog.objects.filter(user=request.user).order_by('-created_at')[:50]
        return response.Response(ActivityLogSerializer(logs, many=True).data)
