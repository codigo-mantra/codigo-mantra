from rest_framework import serializers

from tasks.models import TaskType, Task, Comment


class TaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        fields = ('id', 'title', 'project')
        read_only_fields = ('id',)

class TaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'id', 'type', 'board_section', 'summary', 'description',
            'assignee', 'reporter',
        )
        read_only_fields = ('id',)
        extra_kwargs = {
            'board_section': {'write_only': True},
        }

    def create(self, validated_data):
        return Task.objects.create(**validated_data)


class TaskLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'id', 'type', 'board_section', 'summary', 'description',
            'assignee', 'reporter', 'subtasks'
        )
        read_only_fields = ('id',)


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'id', 'type', 'board_section', 'summary', 'description',
            'assignee', 'reporter', 'subtasks'
        )
        read_only_fields = ('id',)

    def get_subtasks(self, validated_data):
        if hasattr(self, 'subtasks'):
            return TaskLightSerializer(self.subtasks.all(), many=True).data
        return []


from rest_framework import serializers
from .models import Comment

class CommentSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(source='task.id', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'task_id', 'content', 'created_at']

class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['content']
        
    def to_representation(self, instance):
        return CommentSerializer(instance).data
