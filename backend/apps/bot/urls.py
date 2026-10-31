from django.urls import path
from .notification_api import NotificationSettingsView

urlpatterns = [path('notifications/', NotificationSettingsView.as_view(), name='notification-settings')]
