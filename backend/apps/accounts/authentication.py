import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions
from .models import UserDeviceSession
from .tokens import decode_token

User = get_user_model()


class CookieJWTAuthentication(authentication.BaseAuthentication):
    """
    Authenticate JWT Access Token from HttpOnly Cookie (or Bearer Header fallback).
    Enforces instant session revocation and Origin verification for cookie-based mutations.
    """

    def authenticate(self, request):
        token = request.COOKIES.get('access_token')
        using_cookie = bool(token)

        # Fallback: Check Authorization Header if not present in cookie
        if not token:
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return None

        # CSRF defense for state-changing requests authenticated via Cookie
        if using_cookie and request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            origin = request.META.get('HTTP_ORIGIN')
            if origin:
                allowed_origins = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', []))
                host = request.get_host()
                if origin not in allowed_origins and origin not in (f"http://{host}", f"https://{host}"):
                    raise exceptions.PermissionDenied('CSRF validation failed: untrusted Origin.')

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Access token has expired. Please refresh.')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if payload.get('token_type') != 'access':
            raise exceptions.AuthenticationFailed('Invalid token type.')

        user_id = payload.get('user_id')
        if not user_id:
            raise exceptions.AuthenticationFailed('Token missing user payload.')

        session_id = payload.get('session_id')
        if session_id:
            session = (
                UserDeviceSession.objects
                .select_related('user')
                .filter(id=session_id, user_id=user_id, is_revoked=False, user__is_active=True)
                .first()
            )
            if not session:
                raise exceptions.AuthenticationFailed('Device session has been revoked or deactivated.')
            return (session.user, token)

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User account not found or deactivated.')

        return (user, token)

    def authenticate_header(self, request):
        return 'Bearer'
