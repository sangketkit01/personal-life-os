from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FinancialObligationViewSet, FinancialOverviewView

router = DefaultRouter()
router.register('obligations', FinancialObligationViewSet, basename='obligation')

urlpatterns = [
    path('overview/', FinancialOverviewView.as_view(), name='finance-overview'),
    path('', include(router.urls)),
]
