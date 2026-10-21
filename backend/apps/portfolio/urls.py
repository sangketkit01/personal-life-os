from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PortfolioOverviewView,
    PortfolioRefreshView,
    MarketStatusView,
    StockHoldingViewSet,
    StockTransactionViewSet,
    StockNewsViewSet,
    StockWatchlistViewSet,
    InvestmentPortfolioViewSet,
    MarketAssetSearchView
)

router = DefaultRouter()
router.register('portfolios', InvestmentPortfolioViewSet, basename='investment-portfolio')
router.register('holdings', StockHoldingViewSet, basename='holding')
router.register('transactions', StockTransactionViewSet, basename='transaction')
router.register('news', StockNewsViewSet, basename='stock-news')
router.register('watchlist', StockWatchlistViewSet, basename='portfolio-watchlist')

urlpatterns = [
    path('overview/', PortfolioOverviewView.as_view(), name='portfolio-overview'),
    path('refresh/', PortfolioRefreshView.as_view(), name='portfolio-refresh'),
    path('market-status/', MarketStatusView.as_view(), name='market-status'),
    path('search/', MarketAssetSearchView.as_view(), name='portfolio-search'),
    path('', include(router.urls)),
]
