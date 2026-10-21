import os
import secrets
from django.conf import settings
from django.utils import timezone
from django.db import models
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
    """ฟังก์ชันกลางสำหรับฝัง JWT ลง HttpOnly Cookie อย่างปลอดภัย"""
    # ใน Localhost secure=False แต่ถ้าบน Production (HTTPS) secure=True
    is_secure = not settings.DEBUG

    # Access Token (อายุ 15 นาที)
    res.set_cookie(
        key='access_token',
        value=access_token,
        max_age=15 * 60,
        httponly=True,
        samesite='Lax',
        secure=is_secure,
        path='/'
    )

    # Refresh Token (อายุ 7 วัน)
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
    """ฟังก์ชันกลางสำหรับลบ Cookie ตอน Logout"""
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

        # สร้าง Session สำหรับเครื่องที่สมัคร
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

        log_activity(user, 'AUTH', 'REGISTER', 'สมัครสมาชิกบัญชีใหม่สำเร็จ', request=request)

        res = response.Response(
            {
                'message': 'สมัครสมาชิกสำเร็จ ยินดีต้อนรับสู่ Personal Life OS',
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
            # บันทึก Failed Login Attempt ลง Audit Log หากพบบัญชีผู้ใช้
            username_input = request.data.get('username')
            if username_input:
                user_found = User.objects.filter(
                    models.Q(username__iexact=username_input) | models.Q(email__iexact=username_input)
                ).first()
                if user_found:
                    log_activity(user_found, 'AUTH', 'LOGIN_FAILED', 'พยายามเข้าสู่ระบบแต่รหัสผ่านไม่ถูกต้อง', request=request, status='FAILED')
            serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        device_name = get_device_name(request)
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # บันทึก Session ใหม่ของอุปกรณ์ที่เข้าสู่ระบบ
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

        log_activity(user, 'AUTH', 'LOGIN', f'เข้าสู่ระบบผ่าน {device_name}', request=request)

        res = response.Response(
            {
                'message': 'เข้าสู่ระบบสำเร็จ',
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

        res = response.Response({'message': 'ออกจากระบบเรียบร้อยแล้ว'}, status=status.HTTP_200_OK)
        clear_auth_cookies(res)
        log_activity(request.user, 'AUTH', 'LOGOUT', 'ออกจากระบบ', request=request)
        return res


class RefreshTokenView(views.APIView):
    # ปลดล็อคไม่ให้ DRF ตรวจจับ access_token ที่หมดอายุ
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_refresh'

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return response.Response({'detail': 'ไม่พบ Refresh Token'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = decode_token(refresh_token)
        except Exception:
            res = response.Response({'detail': 'Refresh Token ไม่ถูกต้องหรือหมดอายุ'}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(res)
            return res

        if payload.get('token_type') != 'refresh':
            return response.Response({'detail': 'Token Type ไม่ถูกต้อง'}, status=status.HTTP_401_UNAUTHORIZED)

        session_id = payload.get('session_id')
        user_id = payload.get('user_id')

        try:
            session = UserDeviceSession.objects.get(id=session_id, user_id=user_id)
        except UserDeviceSession.DoesNotExist:
            res = response.Response({'detail': 'ไม่พบเซสชันนี้ในระบบ'}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(res)
            return res

        if session.is_revoked:
            res = response.Response({'detail': 'เซสชันนี้ถูกยกเลิกแล้ว กรุณาเข้าสู่ระบบใหม่'}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(res)
            return res

        # ตรวจสอบ Token Hash: รองรับทั้ง token ปัจจุบัน และ Grace Period (เช่น เปิดหลายแท็บ หรือคำขอคู่ขนาน)
        current_hash = hash_token(refresh_token)
        is_current_token = (session.refresh_token_hash == current_hash)
        
        is_grace_token = False
        if not is_current_token and session.previous_refresh_token_hash == current_hash and session.rotated_at:
            grace_seconds = getattr(settings, 'REFRESH_TOKEN_GRACE_PERIOD_SECONDS', 60)
            diff_seconds = (timezone.now() - session.rotated_at).total_seconds()
            if diff_seconds <= grace_seconds:
                is_grace_token = True

        if not is_current_token and not is_grace_token:
            # Token Reuse Detected! เมื่อไม่ใช่ทั้ง token ปัจจุบันและไม่ได้อยู่ในช่วง grace period
            session.is_revoked = True
            session.save(update_fields=['is_revoked'])
            res = response.Response(
                {'detail': 'ตรวจพบการนำ Token เก่ามาใช้ เซสชันนี้ถูกยกเลิกเพื่อความปลอดภัย'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            clear_auth_cookies(res)
            return res

        user = session.user
        if not user.is_active:
            return response.Response({'detail': 'บัญชีนี้ถูกระงับ'}, status=status.HTTP_401_UNAUTHORIZED)

        # Token Rotation: สร้าง Access Token ใหม่ และ Refresh Token ใบใหม่
        new_access_token = generate_access_token(user)
        new_refresh_token = generate_refresh_token(user, session.id)

        # เก็บ hash ใบปัจจุบันย้ายไปเป็น previous_refresh_token_hash เพื่อทำ Grace Period 60 วินาที
        session.previous_refresh_token_hash = session.refresh_token_hash
        session.refresh_token_hash = hash_token(new_refresh_token)
        session.rotated_at = timezone.now()
        session.ip_address = get_client_ip(request)
        session.save(update_fields=['previous_refresh_token_hash', 'refresh_token_hash', 'rotated_at', 'ip_address', 'last_active_at'])

        res = response.Response({'message': 'ต่ออายุโทเค็นสำเร็จ'}, status=status.HTTP_200_OK)
        set_auth_cookies(res, new_access_token, new_refresh_token)
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
            return response.Response({'message': 'ยกเลิกเซสชันอุปกรณ์นี้เรียบร้อยแล้ว'})
        except UserDeviceSession.DoesNotExist:
            return response.Response({'detail': 'ไม่พบเซสชันนี้'}, status=status.HTTP_404_NOT_FOUND)


class TelegramConnectTokenView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.user.generate_telegram_connect_token()
        bot_username = os.getenv('TELEGRAM_BOT_USERNAME', 'PersonalLifeOSBot')
        deep_link = f"https://t.me/{bot_username}?start={token}"
        return response.Response({
            'connect_token': token,
            'deep_link': deep_link,
            'instructions': 'เปิดลิงก์นี้ใน Telegram แล้วกดปุ่ม START เพื่อเชื่อมต่อบอทพ่อบ้านทันที'
        })


class InviteCodeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invites = InviteCode.objects.filter(created_by=request.user).order_by('-created_at')
        return response.Response(InviteCodeSerializer(invites, many=True).data)

    def post(self, request):
        # สร้างโค้ดบัตรเชิญอัตโนมัติ เช่น LIFE-ABC8-1234
        random_part = secrets.token_hex(3).upper()
        code = f"LIFE-{random_part}"
        max_uses = int(request.data.get('max_uses', 1))

        invite = InviteCode.objects.create(
            code=code,
            created_by=request.user,
            max_uses=max_uses
        )
        return response.Response(InviteCodeSerializer(invite).data, status=status.HTTP_201_CREATED)


class ActivityLogView(views.APIView):
    """API ดึงประวัติกิจกรรมความปลอดภัย (Security & Activity Log) ของผู้ใช้"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        logs = ActivityLog.objects.filter(user=request.user).order_by('-created_at')[:50]
        return response.Response(ActivityLogSerializer(logs, many=True).data)
