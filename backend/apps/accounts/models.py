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
        verbose_name="Telegram Connect Token"
    )
    invited_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitees',
        verbose_name="Invited By"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def generate_telegram_connect_token(self):
        token = secrets.token_urlsafe(16)
        self.telegram_connect_token = token
        self.save(update_fields=['telegram_connect_token', 'updated_at'])
        return token


class InviteCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, verbose_name="Invite Code")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_invites',
        verbose_name="Created By"
    )
    used_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invite_code',
        verbose_name="Used By"
    )
    max_uses = models.PositiveIntegerField(default=1, verbose_name="Max Uses")
    uses_count = models.PositiveIntegerField(default=0, verbose_name="Uses Count")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Expires At")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invite_codes'
        ordering = ['-created_at']
        verbose_name = 'Invite Code'
        verbose_name_plural = 'Invite Codes'
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
        verbose_name="User"
    )
    refresh_token_hash = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Refresh Token Hash"
    )
    previous_refresh_token_hash = models.CharField(
        max_length=255,
        blank=True,
        default='',
        db_index=True,
        verbose_name="Previous Refresh Token Hash"
    )
    rotated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Rotated At"
    )
    device_name = models.CharField(max_length=255, verbose_name="Device Name")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Address")
    user_agent = models.TextField(blank=True, default='', verbose_name="User Agent")
    last_active_at = models.DateTimeField(auto_now=True, verbose_name="Last Active At")
    is_revoked = models.BooleanField(default=False, verbose_name="Is Revoked")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_device_sessions'
        ordering = ['-last_active_at']
        verbose_name = 'Device Session'
        verbose_name_plural = 'Device Sessions'

    def __str__(self):
        return f"{self.user.username} - {self.device_name} ({self.ip_address})"


class ActivityLog(models.Model):
    class Category(models.TextChoices):
        AUTH = 'AUTH', 'Authentication & Security'
        FINANCE = 'FINANCE', 'Finance & Obligations'
        PORTFOLIO = 'PORTFOLIO', 'Portfolio & Investments'
        WORKSPACE = 'WORKSPACE', 'Workspace & Documents'
        SYSTEM = 'SYSTEM', 'System'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        verbose_name="User"
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.SYSTEM,
        db_index=True,
        verbose_name="Category"
    )
    action = models.CharField(max_length=100, verbose_name="Action")
    description = models.TextField(verbose_name="Description")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Address")
    device_name = models.CharField(max_length=255, blank=True, default='', verbose_name="Device Name")
    status = models.CharField(max_length=20, default='SUCCESS', verbose_name="Status")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At")

    class Meta:
        db_table = 'user_activity_logs'
        ordering = ['-created_at']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['user', '-created_at'], name='act_log_user_created_idx'),
            models.Index(fields=['category', '-created_at'], name='act_log_cat_created_idx'),
        ]

    def __str__(self):
        return f"[{self.category}] {self.action} by {self.user.username} at {self.created_at}"
