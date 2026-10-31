"""Short database leases; no transaction is held across network requests."""
import uuid
from contextlib import contextmanager
from functools import wraps
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import SchedulerLease


@contextmanager
def job_lease(key, seconds=180):
    token = str(uuid.uuid4())
    now = timezone.now()
    with transaction.atomic():
        row, _ = SchedulerLease.objects.select_for_update().get_or_create(
            key=key, defaults={'token': '', 'expires_at': now})
        acquired = row.expires_at <= now
        if acquired:
            row.token, row.expires_at = token, now + timedelta(seconds=seconds)
            row.last_started_at = now
            row.save(update_fields=['token', 'expires_at', 'last_started_at'])
    try:
        yield acquired
    finally:
        if acquired:
            SchedulerLease.objects.filter(key=key, token=token).update(expires_at=timezone.now(), last_finished_at=timezone.now())


def leased(key, seconds=600, skipped=None):
    def decorate(function):
        @wraps(function)
        def run(*args, **kwargs):
            name = key(*args, **kwargs) if callable(key) else key
            with job_lease(name, seconds) as acquired:
                return function(*args, **kwargs) if acquired else skipped
        return run
    return decorate
