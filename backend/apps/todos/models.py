from django.db import models


class TodoMember(models.Model):
    name = models.CharField(max_length=50, unique=True)
    avatar_color = models.CharField(max_length=20, default='#3B82F6')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'todo_members'


class TodoProject(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3B82F6')
    status = models.CharField(max_length=20, default='active', choices=[('active', '활성'), ('archived', '보관')])
    created_by = models.ForeignKey(TodoMember, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'todo_projects'


class TodoTask(models.Model):
    project = models.ForeignKey(TodoProject, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='waiting',
                              choices=[('waiting', '대기'), ('in_progress', '진행중'), ('review', '검토'), ('done', '완료'), ('hold', '보류')])
    priority = models.CharField(max_length=20, default='normal',
                                choices=[('low', '낮음'), ('normal', '보통'), ('high', '높음'), ('urgent', '긴급')])
    assigned_to = models.ForeignKey(TodoMember, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    due_date = models.DateField(null=True, blank=True)
    display_order = models.IntegerField(default=0)
    created_by = models.ForeignKey(TodoMember, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'todo_tasks'
        ordering = ['display_order', '-created_at']


class TodoComment(models.Model):
    task = models.ForeignKey(TodoTask, on_delete=models.CASCADE, related_name='comments')
    member = models.ForeignKey(TodoMember, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'todo_comments'
        ordering = ['created_at']
