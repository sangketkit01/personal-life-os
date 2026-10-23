import jwt
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions
from .tokens import decode_token

User = get_user_model()


class CookieJWTAuthentication(authentication.BaseAuthentication):
    """
    Authenticate JWT Access Token from HttpOnly Cookie (or Bearer Header fallback).
    """

    def authenticate(self, request):
        token = request.COOKIES.get('access_token')
        
        # Fallback: Check Authorization Header if not present in cookie
        if not token:
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return None

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

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User account not found or deactivated.')

        return (user, token)
