from rest_framework import viewsets, views, status
from rest_framework.response import Response
from .models import ChatRoom, ChatMember, ChatMessage
from .serializers import ChatRoomSerializer, ChatMemberSerializer, ChatMessageSerializer


class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.prefetch_related('members', 'messages').all()
    serializer_class = ChatRoomSerializer

    def create(self, request, *args, **kwargs):
        room = ChatRoom.objects.create(
            name=request.data.get('name', '새 채팅방'),
            room_type=request.data.get('room_type', 'group'),
        )
        members = request.data.get('members', [])
        for name in members:
            ChatMember.objects.create(room=room, name=name)
        return Response(ChatRoomSerializer(room).data, status=201)


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        return ChatMessage.objects.filter(room_id=room_id)

    def perform_create(self, serializer):
        serializer.save(room_id=self.kwargs.get('room_id'))
