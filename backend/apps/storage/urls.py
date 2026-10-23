from django.urls import path
from .views import (
    GoogleAuthUrlView,
    GoogleAuthCallbackView,
    GoogleDriveStatusView,
    InitiateUploadView,
    CompleteUploadView,
    DisconnectGoogleDriveView,
    DriveFileListView,
    DriveFileDetailView
)

urlpatterns = [
    path('auth/url/', GoogleAuthUrlView.as_view(), name='storage-google-auth-url'),
    path('auth/callback/', GoogleAuthCallbackView.as_view(), name='storage-google-auth-callback'),
    path('status/', GoogleDriveStatusView.as_view(), name='storage-status'),
    path('initiate-upload/', InitiateUploadView.as_view(), name='storage-initiate-upload'),
    path('complete-upload/', CompleteUploadView.as_view(), name='storage-complete-upload'),
    path('disconnect/', DisconnectGoogleDriveView.as_view(), name='storage-disconnect'),
    path('files/', DriveFileListView.as_view(), name='storage-file-list'),
    path('files/<uuid:pk>/', DriveFileDetailView.as_view(), name='storage-file-detail'),
]
