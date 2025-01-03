from django.db import models
from core.models import TimeStampedModel
from projects.models import Project
from boards.models import BoardSection
# from django.contrib.auth.models import User
from users.models import User


class TaskType(TimeStampedModel):
    title = models.CharField(max_length=30)
    project = models.ForeignKey(
        Project,
        related_name="task_types",
        on_delete=models.CASCADE
    )

    class Meta:
        ordering = ['title']
        verbose_name = "Task Type"
        verbose_name_plural = "Task Types"

    def __str__(self):
        return f"{self.title}"


class Task(TimeStampedModel):
    board_section = models.ForeignKey(
        BoardSection,
        on_delete=models.CASCADE,
        related_name="tasks"
    )
    type = models.ForeignKey(
        TaskType,
        on_delete=models.CASCADE,
        related_name="tasks"
    )
    summary = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(
        User,
        related_name="assigned_tasks",
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    reporter = models.ForeignKey(
        User,
        related_name="reported_tasks",
        on_delete=models.CASCADE
    )
    children = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='subtasks',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.type.title}: {self.summary}"



class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.task.summary}"
