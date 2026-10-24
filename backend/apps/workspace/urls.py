from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkspaceOverviewView,
    WorkspaceProjectViewSet,
    TaskDocumentViewSet,
    NoteViewSet,
    ProjectLinkViewSet,
    ProjectAttachmentViewSet,
    CalendarEventViewSet
)

router = DefaultRouter()
router.register('projects', WorkspaceProjectViewSet, basename='project')
router.register('tasks', TaskDocumentViewSet, basename='task')
router.register('notes', NoteViewSet, basename='note')
router.register('links', ProjectLinkViewSet, basename='project-link')
router.register('attachments', ProjectAttachmentViewSet, basename='project-attachment')
router.register('events', CalendarEventViewSet, basename='calendar-event')

urlpatterns = [
    path('overview/', WorkspaceOverviewView.as_view(), name='workspace-overview'),
    path('', include(router.urls)),
]
