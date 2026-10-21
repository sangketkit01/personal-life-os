from django.http import JsonResponse
from django.db import connection
from django.utils import timezone


def health_check(request):
    """
    Lightweight system health check.
    Pings PostgreSQL with SELECT 1 and returns server status in <5ms.
    """
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = True
    except Exception:
        db_ok = False

    status_code = 200 if db_ok else 503
    return JsonResponse({
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": timezone.now().isoformat(),
        "service": "Personal Life OS API"
    }, status=status_code)
