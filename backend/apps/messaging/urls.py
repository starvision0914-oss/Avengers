from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, ChatMessageViewSet

router = DefaultRouter()
router.register(r'rooms', ChatRoomViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('rooms/<int:room_id>/messages/', ChatMessageViewSet.as_view({'get': 'list', 'post': 'create'})),
]
