from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TodoMemberViewSet, TodoProjectViewSet, TodoTaskViewSet, TodoCommentViewSet

router = DefaultRouter()
router.register(r'members', TodoMemberViewSet)
router.register(r'projects', TodoProjectViewSet, basename='project')
router.register(r'tasks', TodoTaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
    path('tasks/<int:task_id>/comments/', TodoCommentViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('comments/<int:pk>/', TodoCommentViewSet.as_view({'delete': 'destroy'})),
]
