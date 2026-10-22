from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='api-health'),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/workspace/', include('apps.workspace.urls')),
    path('api/portfolio/', include('apps.portfolio.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
