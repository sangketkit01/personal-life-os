from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FinancialObligationViewSet, FinancialOverviewView, ObligationAttachmentViewSet

router = DefaultRouter()
router.register('obligations', FinancialObligationViewSet, basename='obligation')
router.register('attachments', ObligationAttachmentViewSet, basename='attachment')

urlpatterns = [
    path('overview/', FinancialOverviewView.as_view(), name='finance-overview'),
    path('', include(router.urls)),
]
