from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkspaceOverviewView,
    WorkspaceProjectViewSet,
    TaskDocumentViewSet,
    NoteViewSet
)

router = DefaultRouter()
router.register('projects', WorkspaceProjectViewSet, basename='project')
router.register('tasks', TaskDocumentViewSet, basename='task')
router.register('notes', NoteViewSet, basename='note')

urlpatterns = [
    path('overview/', WorkspaceOverviewView.as_view(), name='workspace-overview'),
    path('', include(router.urls)),
]
