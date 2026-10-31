"""Notification preferences, durable deliveries and shared scheduler leases."""
import datetime
from django.conf import settings
from django.db import models


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    briefing = models.BooleanField(default=True)
    bills = models.BooleanField(default=True)
    tasks = models.BooleanField(default=True)
    calendar = models.BooleanField(default=True)
    portfolio_news = models.BooleanField(default=True)
    watchlist_news = models.BooleanField(default=False)
    market_close = models.BooleanField(default=False)
    price_alerts = models.BooleanField(default=True)
    infrastructure = models.BooleanField(default=True)
    briefing_time = models.TimeField(default=datetime.time(8, 30))
    timezone = models.CharField(max_length=64, default='Asia/Bangkok')
    quiet_start = models.TimeField(null=True, blank=True)
    quiet_end = models.TimeField(null=True, blank=True)


class NotificationDelivery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.CharField(max_length=30)
    event_key = models.CharField(max_length=200)
    payload = models.JSONField(default=dict)
    reference = models.JSONField(default=dict)
    status = models.CharField(max_length=12, default='PENDING', db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(db_index=True)
    retry_not_before = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    message_id = models.BigIntegerField(null=True, blank=True)
    error = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'event_key'], name='unique_user_notification_event')]
        ordering = ['-created_at']


class SchedulerLease(models.Model):
    key = models.CharField(primary_key=True, max_length=100)
    token = models.CharField(max_length=36)
    expires_at = models.DateTimeField()
    last_started_at = models.DateTimeField(null=True, blank=True)
    last_finished_at = models.DateTimeField(null=True, blank=True)
