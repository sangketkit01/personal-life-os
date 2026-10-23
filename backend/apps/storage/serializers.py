from rest_framework import serializers
from django.core.validators import RegexValidator
from .models import GoogleDriveConnection, DriveFile, StorageDomain


class GoogleDriveStatusSerializer(serializers.ModelSerializer):
    is_connected = serializers.BooleanField()
    google_email = serializers.EmailField()
    root_folder_id = serializers.CharField()
    subfolder_ids = serializers.JSONField()

    class Meta:
        model = GoogleDriveConnection
        fields = [
            'is_connected',
            'google_email',
            'root_folder_id',
            'subfolder_ids',
            'created_at',
            'updated_at'
        ]


class InitiateUploadSerializer(serializers.Serializer):
    domain = serializers.ChoiceField(choices=StorageDomain.choices, default=StorageDomain.GENERAL)
    file_name = serializers.CharField(max_length=255)
    file_type = serializers.CharField(max_length=100, default='application/octet-stream')
    file_size = serializers.IntegerField(min_value=1, max_value=52428800)  # max 50MB per single attachment


class CompleteUploadSerializer(serializers.Serializer):
    drive_file_id = serializers.CharField(
        max_length=128,
        validators=[
            RegexValidator(
                r'^[a-zA-Z0-9_-]+$',
                message="Invalid Google Drive file ID format."
            )
        ]
    )
    domain = serializers.ChoiceField(choices=StorageDomain.choices, default=StorageDomain.GENERAL)
    target_id = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')
    file_name = serializers.CharField(max_length=255)
    file_type = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    category = serializers.ChoiceField(
        choices=['CONTRACT', 'SLIP', 'STATEMENT', 'SCREENSHOT', 'OTHER'],
        required=False,
        default='OTHER'
    )
    file_size = serializers.IntegerField(min_value=0, default=0)


class DriveFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriveFile
        fields = [
            'id',
            'drive_file_id',
            'file_name',
            'file_type',
            'file_size',
            'web_view_link',
            'web_content_link',
            'thumbnail_link',
            'domain',
            'target_id',
            'uploaded_at'
        ]
        read_only_fields = fields
