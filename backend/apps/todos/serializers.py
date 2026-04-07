from rest_framework import serializers
from .models import TodoMember, TodoProject, TodoTask, TodoComment


class TodoMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TodoMember
        fields = '__all__'


class TodoCommentSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)

    class Meta:
        model = TodoComment
        fields = '__all__'


class TodoTaskSerializer(serializers.ModelSerializer):
    comments = TodoCommentSerializer(many=True, read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.name', read_only=True, default=None)

    class Meta:
        model = TodoTask
        fields = '__all__'


class TodoProjectSerializer(serializers.ModelSerializer):
    task_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = TodoProject
        fields = '__all__'
