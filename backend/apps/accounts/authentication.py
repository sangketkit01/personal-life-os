import jwt
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions
from .tokens import decode_token

User = get_user_model()


class CookieJWTAuthentication(authentication.BaseAuthentication):
    """
    ตรวจจับ JWT Access Token จาก HttpOnly Cookie (หรือ Bearer Header)
    """

    def authenticate(self, request):
        token = request.COOKIES.get('access_token')
        
        # Fallback: ถ้าไม่มีใน Cookie ให้ลองดูใน Authorization Header
        if not token:
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return None

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Access Token หมดอายุแล้ว กรุณา Refresh Token')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Token ไม่ถูกต้อง')

        if payload.get('token_type') != 'access':
            raise exceptions.AuthenticationFailed('ประเภท Token ไม่ถูกต้อง')

        user_id = payload.get('user_id')
        if not user_id:
            raise exceptions.AuthenticationFailed('Token ไม่มีข้อมูลผู้ใช้')

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('ไม่พบบัญชีผู้ใช้ หรือผู้ใช้ถูกระงับ')

        return (user, token)
