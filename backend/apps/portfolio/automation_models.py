"""Persistent user rules and reproducible market-close reports."""
import uuid
from django.conf import settings
from django.db import models


class PriceAlert(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='price_alerts')
    ticker = models.CharField(max_length=30)
    currency = models.CharField(max_length=5)
    condition = models.CharField(max_length=5, choices=[('GTE', 'At or above'), ('LTE', 'At or below')])
    target_price = models.DecimalField(max_digits=24, decimal_places=8)
    is_active = models.BooleanField(default=True)
    revision = models.UUIDField(default=uuid.uuid4, editable=False)
    triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(target_price__gt=0), name='price_alert_positive_target')]
        ordering = ['-created_at']


class MarketCloseReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    market = models.CharField(max_length=10)
    session_date = models.DateField()
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'market', 'session_date'], name='unique_user_market_close')]
