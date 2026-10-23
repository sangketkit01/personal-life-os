import os
import secrets
from django.conf import settings
from django.utils import timezone
from django.db import models, transaction as db_transaction
from rest_framework import status, views, permissions, response
from rest_framework.throttling import ScopedRateThrottle
from .models import User, InviteCode, UserDeviceSession, ActivityLog
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
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


class RegisterView(views.APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_register'

    def post(self, request):
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

        access_token = generate_access_token(user)
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
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            # Record failed login attempt in audit log if account exists
            username_input = request.data.get('username')
            if username_input and isinstance(username_input, str):
                user_found = User.objects.filter(
                    models.Q(username__iexact=username_input) | models.Q(email__iexact=username_input)
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

        access_token = generate_access_token(user)
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
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            try:
                payload = decode_token(refresh_token)
                session_id = payload.get('session_id')
                if session_id:
                    UserDeviceSession.objects.filter(id=session_id, user=request.user).update(is_revoked=True)
            except Exception:
                pass

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

                # Verify Token Hash: supports both current token and Grace Period
                current_hash = hash_token(refresh_token)
                is_current_token = (session.refresh_token_hash == current_hash)
                
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

                # Token Rotation: create new access token and refresh token
                new_access_token = generate_access_token(user)
                new_refresh_token = generate_refresh_token(user, session.id)

                # Update session hashes: retain previous_refresh_token_hash if during grace window
                if is_current_token:
                    session.previous_refresh_token_hash = session.refresh_token_hash
                    session.rotated_at = timezone.now()

                session.refresh_token_hash = hash_token(new_refresh_token)
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


class SessionsListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        current_session_id = None
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            try:
                payload = decode_token(refresh_token)
                current_session_id = payload.get('session_id')
            except Exception:
                pass

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
            return response.Response({'message': 'Device session revoked successfully'})
        except UserDeviceSession.DoesNotExist:
            return response.Response({'detail': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


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


class InviteCodeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invites = InviteCode.objects.filter(created_by=request.user).order_by('-created_at')
        return response.Response(InviteCodeSerializer(invites, many=True).data)

    def post(self, request):
        raw_max_uses = request.data.get('max_uses', 1)
        try:
            max_uses = int(raw_max_uses)
            if max_uses <= 0 or max_uses > 1000:
                raise ValueError()
        except (ValueError, TypeError):
            return response.Response(
                {'detail': 'max_uses must be a positive integer between 1 and 1000.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate random invite code: e.g. LIFE-ABC8
        random_part = secrets.token_hex(3).upper()
        code = f"LIFE-{random_part}"

        invite = InviteCode.objects.create(
            code=code,
            created_by=request.user,
            max_uses=max_uses
        )
        return response.Response(InviteCodeSerializer(invite).data, status=status.HTTP_201_CREATED)


class ActivityLogView(views.APIView):
    """API endpoint to retrieve user security and activity audit log."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        logs = ActivityLog.objects.filter(user=request.user).order_by('-created_at')[:50]
        return response.Response(ActivityLogSerializer(logs, many=True).data)
