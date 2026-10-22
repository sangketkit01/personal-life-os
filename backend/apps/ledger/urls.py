from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AccountViewSet,
    CategoryViewSet,
    TransactionViewSet,
    TransactionSplitViewSet,
    CategoryBudgetViewSet
)

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='ledger-account')
router.register(r'categories', CategoryViewSet, basename='ledger-category')
router.register(r'transactions', TransactionViewSet, basename='ledger-transaction')
router.register(r'splits', TransactionSplitViewSet, basename='ledger-split')
router.register(r'budgets', CategoryBudgetViewSet, basename='ledger-budget')

urlpatterns = [
    path('', include(router.urls)),
]
