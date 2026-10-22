from django.contrib import admin
from .models import Account, Category, Transaction, TransactionSplit, TransactionAttachment, CategoryBudget


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'account_type', 'currency', 'current_balance', 'is_default', 'is_archived')
    list_filter = ('account_type', 'currency', 'is_default', 'is_archived')
    search_fields = ('name', 'institution_name', 'account_number', 'user__username')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'parent', 'is_system', 'user')
    list_filter = ('category_type', 'is_system')
    search_fields = ('name',)


class TransactionSplitInline(admin.TabularInline):
    model = TransactionSplit
    fk_name = 'transaction'
    extra = 0


class TransactionAttachmentInline(admin.TabularInline):
    model = TransactionAttachment
    extra = 0


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'title', 'user', 'account', 'transaction_type', 'gross_amount', 'net_amount', 'is_split')
    list_filter = ('transaction_type', 'is_split', 'transaction_date')
    search_fields = ('title', 'notes', 'user__username')
    inlines = [TransactionSplitInline, TransactionAttachmentInline]


@admin.register(TransactionSplit)
class TransactionSplitAdmin(admin.ModelAdmin):
    list_display = ('counterparty_name', 'transaction', 'amount', 'is_settled', 'settled_at')
    list_filter = ('is_settled',)
    search_fields = ('counterparty_name', 'counterparty_contact', 'transaction__title')


@admin.register(CategoryBudget)
class CategoryBudgetAdmin(admin.ModelAdmin):
    list_display = ('period_month', 'category', 'user', 'limit_amount')
    list_filter = ('period_month',)
