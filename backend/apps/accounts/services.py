from typing import Optional
from .models import ActivityLog
from .tokens import get_client_ip, get_device_name


def log_activity(
    user,
    category: str,
    action: str,
    description: str,
    request=None,
    status: str = 'SUCCESS'
) -> ActivityLog:
    """
    บันทึกกิจกรรมความปลอดภัยลง Audit Log (Security & Activity Trail)
    """
    ip_address = get_client_ip(request) if request else None
    device_name = get_device_name(request) if request else ''

    return ActivityLog.objects.create(
        user=user,
        category=category,
        action=action,
        description=description,
        ip_address=ip_address,
        device_name=device_name,
        status=status
    )
