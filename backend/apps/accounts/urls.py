from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    RefreshTokenView,
    MeView,
    ChangePasswordView,
    SessionsListView,
    RevokeSessionView,
    RevokeOtherSessionsView,
    TelegramConnectTokenView,
    TelegramDisconnectView,
    TelegramTestAlertView,
    InviteCodeView,
    InviteCodeDetailView,
    ActivityLogView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('password/change/', ChangePasswordView.as_view(), name='auth-password-change'),
    path('sessions/', SessionsListView.as_view(), name='auth-sessions'),
    path('sessions/revoke-others/', RevokeOtherSessionsView.as_view(), name='auth-sessions-revoke-others'),
    path('sessions/<uuid:session_id>/revoke/', RevokeSessionView.as_view(), name='auth-session-revoke'),
    path('telegram/connect-token/', TelegramConnectTokenView.as_view(), name='auth-telegram-connect'),
    path('telegram/disconnect/', TelegramDisconnectView.as_view(), name='auth-telegram-disconnect'),
    path('telegram/test/', TelegramTestAlertView.as_view(), name='auth-telegram-test'),
    path('invites/', InviteCodeView.as_view(), name='auth-invites'),
    path('invites/<uuid:invite_id>/', InviteCodeDetailView.as_view(), name='auth-invite-detail'),
    path('audit-logs/', ActivityLogView.as_view(), name='auth-audit-logs'),
]
