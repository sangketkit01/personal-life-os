from django.contrib import admin
from .models import StockHolding, StockTransaction, StockPriceSnapshot


class StockTransactionInline(admin.TabularInline):
    model = StockTransaction
    extra = 0
    fields = ('transaction_type', 'shares', 'price_per_share', 'fee', 'executed_at')


@admin.register(StockHolding)
class StockHoldingAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'name', 'user', 'asset_type', 'currency', 'updated_at')
    list_filter = ('asset_type', 'currency')
    search_fields = ('ticker', 'name', 'user__username')
    inlines = [StockTransactionInline]


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('holding', 'user', 'transaction_type', 'shares', 'price_per_share', 'fee', 'executed_at')
    list_filter = ('transaction_type', 'executed_at')
    search_fields = ('holding__ticker', 'user__username')


@admin.register(StockPriceSnapshot)
class StockPriceSnapshotAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'price', 'change_pct', 'currency', 'fetched_at')
    search_fields = ('ticker',)
