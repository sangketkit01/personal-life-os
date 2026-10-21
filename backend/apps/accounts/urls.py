from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    RefreshTokenView,
    MeView,
    SessionsListView,
    RevokeSessionView,
    TelegramConnectTokenView,
    InviteCodeView,
    ActivityLogView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('sessions/', SessionsListView.as_view(), name='auth-sessions'),
    path('sessions/<uuid:session_id>/revoke/', RevokeSessionView.as_view(), name='auth-session-revoke'),
    path('telegram/connect-token/', TelegramConnectTokenView.as_view(), name='auth-telegram-connect'),
    path('invites/', InviteCodeView.as_view(), name='auth-invites'),
    path('audit-logs/', ActivityLogView.as_view(), name='auth-audit-logs'),
]
