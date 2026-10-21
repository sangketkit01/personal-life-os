import uuid
import secrets
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_chat_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Telegram Chat ID"
    )
    telegram_connect_token = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="โทเค็นเชื่อมต่อ Telegram"
    )
    invited_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitees',
        verbose_name="ผู้เชิญ"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'ผู้ใช้งาน'
        verbose_name_plural = 'ผู้ใช้งานทั้งหมด'

    def generate_telegram_connect_token(self):
        token = secrets.token_urlsafe(16)
        self.telegram_connect_token = token
        self.save(update_fields=['telegram_connect_token'])
        return token


class InviteCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, verbose_name="รหัสบัตรเชิญ")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_invites',
        verbose_name="ผู้สร้างรหัส"
    )
    used_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invite_code',
        verbose_name="ผู้ที่นำไปใช้"
    )
    max_uses = models.PositiveIntegerField(default=1, verbose_name="จำนวนครั้งที่ใช้ได้")
    uses_count = models.PositiveIntegerField(default=0, verbose_name="ใช้ไปแล้ว (ครั้ง)")
    is_active = models.BooleanField(default=True, verbose_name="เปิดใช้งานอยู่")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="วันหมดอายุของรหัส")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invite_codes'
        ordering = ['-created_at']
        verbose_name = 'บัตรเชิญ (Invite Code)'
        verbose_name_plural = 'บัตรเชิญทั้งหมด'
        constraints = [
            models.CheckConstraint(condition=models.Q(uses_count__lte=models.F('max_uses')), name='invite_uses_lte_max'),
        ]

    def is_valid(self):
        if not self.is_active:
            return False
        if self.uses_count >= self.max_uses:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    def __str__(self):
        return f"{self.code} ({self.uses_count}/{self.max_uses})"


class UserDeviceSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='device_sessions',
        verbose_name="ผู้ใช้งาน"
    )
    refresh_token_hash = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Hash ของ Refresh Token"
    )
    previous_refresh_token_hash = models.CharField(
        max_length=255,
        blank=True,
        default='',
        db_index=True,
        verbose_name="Hash ของ Refresh Token ใบก่อนหน้า (Grace Period)"
    )
    rotated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="เวลาที่ทำการหมุน Token ล่าสุด"
    )
    device_name = models.CharField(max_length=255, verbose_name="ชื่ออุปกรณ์/เบราว์เซอร์")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Address")
    user_agent = models.TextField(blank=True, default='', verbose_name="User Agent")
    last_active_at = models.DateTimeField(auto_now=True, verbose_name="ใช้งานล่าสุดเมื่อ")
    is_revoked = models.BooleanField(default=False, verbose_name="ถูกยกเลิก/เตะออก")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_device_sessions'
        ordering = ['-last_active_at']
        verbose_name = 'เซสชันอุปกรณ์'
        verbose_name_plural = 'เซสชันอุปกรณ์ทั้งหมด'

    def __str__(self):
        return f"{self.user.username} - {self.device_name} ({self.ip_address})"


class ActivityLog(models.Model):
    class Category(models.TextChoices):
        AUTH = 'AUTH', 'การเข้าสู่ระบบ & ความปลอดภัย'
        FINANCE = 'FINANCE', 'การเงิน & ภาระผูกพัน'
        PORTFOLIO = 'PORTFOLIO', 'พอร์ตการลงทุน & หุ้น'
        WORKSPACE = 'WORKSPACE', 'งานและเอกสาร'
        SYSTEM = 'SYSTEM', 'ระบบ'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        verbose_name="ผู้ใช้งาน"
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.SYSTEM,
        db_index=True,
        verbose_name="หมวดหมู่"
    )
    action = models.CharField(max_length=100, verbose_name="การกระทำ")
    description = models.TextField(verbose_name="รายละเอียดเหตุการณ์")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Address")
    device_name = models.CharField(max_length=255, blank=True, default='', verbose_name="อุปกรณ์/เบราว์เซอร์")
    status = models.CharField(max_length=20, default='SUCCESS', verbose_name="สถานะ (SUCCESS/FAILED)")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="เวลาที่เกิดเหตุการณ์")

    class Meta:
        db_table = 'user_activity_logs'
        ordering = ['-created_at']
        verbose_name = 'ประวัติกิจกรรม (Audit Log)'
        verbose_name_plural = 'ประวัติกิจกรรมทั้งหมด'
        indexes = [
            models.Index(fields=['user', '-created_at'], name='act_log_user_created_idx'),
            models.Index(fields=['category', '-created_at'], name='act_log_cat_created_idx'),
        ]

    def __str__(self):
        return f"[{self.category}] {self.action} by {self.user.username} at {self.created_at}"
