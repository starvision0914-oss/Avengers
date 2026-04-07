from django.db import models


class ChatRoom(models.Model):
    name = models.CharField(max_length=200)
    room_type = models.CharField(max_length=20, default='group', choices=[('direct', '1:1'), ('group', '그룹')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_rooms'


class ChatMember(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='members')
    name = models.CharField(max_length=50)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'chat_members'
        unique_together = ['room', 'name']


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=50)
    content = models.TextField()
    message_type = models.CharField(max_length=20, default='text', choices=[('text', '텍스트'), ('file', '파일'), ('image', '이미지')])
    file_url = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
