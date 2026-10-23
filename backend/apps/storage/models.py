import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from .encryption import encrypt_token, decrypt_token


class StorageDomain(models.TextChoices):
    LEDGER = 'ledger', 'Ledger'
    FINANCE = 'finance', 'Finance'
    PORTFOLIO = 'portfolio', 'Portfolio'
    WORKSPACE = 'workspace', 'Workspace'
    GENERAL = 'general', 'General'


class GoogleDriveConnection(models.Model):
    """
    Stores authenticated Google Drive OAuth credentials per user.
    Enforces the Zero-Disk policy by delegating all file persistence to Google Drive.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_drive_connection',
        verbose_name="User"
    )
    google_email = models.EmailField(
        blank=True,
        default='',
        verbose_name="Connected Google Email"
    )
    access_token = models.TextField(
        verbose_name="OAuth Access Token"
    )
    refresh_token = models.TextField(
        blank=True,
        default='',
        verbose_name="OAuth Refresh Token"
    )
    token_expiry = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Token Expiration Time"
    )
    root_folder_id = models.CharField(
        max_length=128,
        blank=True,
        default='',
        verbose_name="Root Folder ID"
    )
    subfolder_ids = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Domain Subfolder IDs"
    )
    is_connected = models.BooleanField(
        default=True,
        verbose_name="Is Active Connection"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'storage_google_drive_connections'
        verbose_name = 'Google Drive Connection'
        verbose_name_plural = 'Google Drive Connections'

    def __str__(self):
        status = "Connected" if self.is_connected else "Disconnected"
        return f"{self.user.username} - {self.google_email or 'No Email'} ({status})"

    def get_access_token(self) -> str:
        return decrypt_token(self.access_token)

    def get_refresh_token(self) -> str:
        return decrypt_token(self.refresh_token)

    def set_tokens(self, access_token: str, refresh_token: str = None):
        if access_token:
            self.access_token = encrypt_token(access_token)
        if refresh_token:
            self.refresh_token = encrypt_token(refresh_token)

    def is_token_valid(self):
        """Returns True if access token is still valid with a 60-second safety margin."""
        plain_access_token = self.get_access_token()
        if not plain_access_token or not self.token_expiry:
            return False
        return self.token_expiry > (timezone.now() + timezone.timedelta(seconds=60))


class DriveFile(models.Model):
    """
    Metadata audit ledger of files stored directly in Google Drive.
    Zero bytes are written to local disk.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='drive_files',
        verbose_name="Owner"
    )
    drive_file_id = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name="Google Drive File ID"
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name="Original Filename"
    )
    file_type = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="MIME Type"
    )
    file_size = models.PositiveIntegerField(
        default=0,
        verbose_name="Size in Bytes"
    )
    web_view_link = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Web View URL"
    )
    web_content_link = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Direct Download URL"
    )
    thumbnail_link = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Thumbnail URL"
    )
    domain = models.CharField(
        max_length=32,
        choices=StorageDomain.choices,
        default=StorageDomain.GENERAL,
        verbose_name="Domain"
    )
    target_id = models.CharField(
        max_length=128,
        blank=True,
        default='',
        db_index=True,
        verbose_name="Domain Target Reference ID"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'storage_drive_files'
        ordering = ['-uploaded_at']
        verbose_name = 'Drive File'
        verbose_name_plural = 'Drive Files'

    def __str__(self):
        return f"{self.file_name} ({self.domain})"
