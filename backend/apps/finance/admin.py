from django.contrib import admin
from .models import FinancialObligation, PaymentHistory


class PaymentHistoryInline(admin.TabularInline):
    model = PaymentHistory
    extra = 0
    readonly_fields = ('paid_at',)


@admin.register(FinancialObligation)
class FinancialObligationAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'direction', 'amount', 'currency', 'status', 'due_date', 'billing_day', 'updated_at')
    list_filter = ('type', 'status', 'direction')
    search_fields = ('title',)
    inlines = [PaymentHistoryInline]


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('obligation', 'paid_amount', 'term_number', 'paid_at')
    list_filter = ('paid_at',)
    search_fields = ('obligation__title', 'note')
