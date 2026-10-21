from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, InviteCode, UserDeviceSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'telegram_chat_id', 'invited_by', 'is_staff', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'telegram_chat_id')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Telegram & Invite Info', {'fields': ('telegram_chat_id', 'telegram_connect_token', 'invited_by')}),
    )


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'created_by', 'used_by', 'uses_count', 'max_uses', 'is_active', 'expires_at', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'created_by__username', 'used_by__username')


@admin.register(UserDeviceSession)
class UserDeviceSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'ip_address', 'last_active_at', 'is_revoked', 'created_at')
    list_filter = ('is_revoked',)
    search_fields = ('user__username', 'device_name', 'ip_address')
