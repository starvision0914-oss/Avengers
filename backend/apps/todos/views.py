from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Count
from .models import TodoMember, TodoProject, TodoTask, TodoComment
from .serializers import TodoMemberSerializer, TodoProjectSerializer, TodoTaskSerializer, TodoCommentSerializer


class TodoMemberViewSet(viewsets.ModelViewSet):
    queryset = TodoMember.objects.all()
    serializer_class = TodoMemberSerializer


class TodoProjectViewSet(viewsets.ModelViewSet):
    serializer_class = TodoProjectSerializer

    def get_queryset(self):
        return TodoProject.objects.annotate(task_count=Count('tasks'))


class TodoTaskViewSet(viewsets.ModelViewSet):
    serializer_class = TodoTaskSerializer
    filterset_fields = ['project', 'status', 'priority', 'assigned_to']

    def get_queryset(self):
        return TodoTask.objects.select_related('assigned_to', 'created_by').prefetch_related('comments__member')

    @action(detail=True, methods=['patch'])
    def move(self, request, pk=None):
        task = self.get_object()
        new_status = request.data.get('status')
        new_order = request.data.get('display_order')
        if new_status:
            task.status = new_status
        if new_order is not None:
            task.display_order = new_order
        task.save()
        return Response(TodoTaskSerializer(task).data)


class TodoCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TodoCommentSerializer

    def get_queryset(self):
        task_id = self.kwargs.get('task_id')
        if task_id:
            return TodoComment.objects.filter(task_id=task_id).select_related('member')
        return TodoComment.objects.none()

    def perform_create(self, serializer):
        serializer.save(task_id=self.kwargs.get('task_id'))
