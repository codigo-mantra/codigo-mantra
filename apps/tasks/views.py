from core.views import BaseReadOnlyViewSet, BaseViewSet

from rest_framework import status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from tasks.models import TaskType, Task
from tasks.serializers import (
    TaskTypeSerializer, TaskSerializer,
    TaskCreateSerializer, TaskLightSerializer
)
from projects.models import Project


class TaskPagination(PageNumberPagination):
    page_size = 24


class TaskTypeViewSet(BaseViewSet):
    queryset = TaskType.objects.all()
    serializer_class = TaskTypeSerializer

    def get_queryset(self):
        queryset = self.queryset
        if self.kwargs != {}:
            if 'project_uuid' in self.kwargs:
                queryset = queryset.filter(project__uuid=self.kwargs['project_uuid'])
        return queryset

    def create(self, request, project_uuid=None):
        data = request.data
        user = request.user

        if not user.is_authenticated:
            return Response({'error':'The user is anonymous'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def update(self, request, project_uuid=None, pk=None):
        data = request.data
        user = request.user

        if not user.is_authenticated:
            return Response({'error':'The user is anonymous'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, project_uuid=None, pk=None):
        task_type = self.get_object()
        project = Project.objects.get(uuid=project_uuid)

        if project.user != request.user:
            return Response(
                {'error': 'User not authorized'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        task_type.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


class TaskViewSet(BaseViewSet):
    queryset = Task.objects.all()
    pagination_class = TaskPagination
    serializer_class = TaskSerializer

    serializer_action_classes = {
        'create': TaskCreateSerializer,
        'add_subtask': TaskLightSerializer,
        'remove_subtask': TaskLightSerializer
    }

    def get_queryset(self):
        queryset = self.queryset
        if self.kwargs != {}:
            if 'section_pk' in self.kwargs:
                section_pk = self.kwargs['section_pk']
        return queryset

    def create(self, request, project_uuid=None, board_pk=None, section_pk=None):
        data = request.data
        user = request.user

        if not user.is_authenticated:
            return Response(
                {'error':'The user is anonymous'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def update(self, request, project_uuid=None, board_pk=None, section_pk=None, pk=None):
        data = request.data
        user = request.user

        if not user.is_authenticated:
            return Response(
                {'error':'The user is anonymous'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, project_uuid=None, board_pk=None, section_pk=None, pk=None):
        task = self.get_object()
        if task.reporter != request.user:
            return Response(
                {'error': 'User not authorized'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        task.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'])
    def change_task_type(self, request, project_uuid=None, board_pk=None, section_pk=None, pk=None):
        task = self.get_object()
        data = request.data
        user = request.user
        if not user.is_authenticated:
            return Response(
                {'error':'The user is anonymous'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if task.reporter != request.user:
            return Response(
                {'error': 'User not authorized'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        task.task_type = data['task_type']
        task.save()
        return Response({'success': True}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'])
    def add_subtask(self, request, project_uuid=None, board_pk=None, section_pk=None, pk=None):
        task = self.get_object()
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"error": "User not authorized"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            task = data.pop('task', None)
            task_obj = None
            if 'id' in task.keys():
                task_obj = Task.objects.get(pk=task['id'])
            else:
                task_obj, created = Tag.objects.get_or_create(name=tag['name'])
            if task_obj is not None and task_obj not in task.subtasks.all():
                task.subtasks.add(task_obj)
        except Exception as e:
            return Response(
                {"error": str(e), "message": e.message},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(task_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'])
    def remove_subtask(self, request, project_uuid=None, board_pk=None, section_pk=None, pk=None):
        task = self.get_object()
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"error": "User not authorized"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            task = data.pop('task', None)
            task_obj = None
            if 'id' in task.keys():
                task_obj = Task.objects.get(pk=task['id'])
            if task_obj is not None and task_obj in task.subtasks.all():
                post.subtasks.remove(task_obj)
        except Exception as e:
            return Response({"error": str(e), "message": e.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True}, status=status.HTTP_200_OK)



from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from .models import Comment
from .serializers import CommentSerializer, CommentCreateSerializer

class CommentViewSet(BaseViewSet):
    queryset = Comment.objects.all()
    pagination_class = TaskPagination
    serializer_class = CommentSerializer

    serializer_action_classes = {
        'create': CommentCreateSerializer,
    }

    def get_queryset(self):
        queryset = self.queryset
        if self.kwargs.get('task_pk'):
            queryset = queryset.filter(task_id=self.kwargs['task_pk'])
        return queryset.order_by('-created_at') 

    def create(self, request, project_uuid=None, board_pk=None, section_pk=None, task_pk=None):
        user = request.user
        if not user.is_authenticated:
            return Response(
                {'error': 'The user is anonymous'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)
        if serializer.is_valid():
            serializer.save(user=user, task_id=task_pk)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, project_uuid=None, board_pk=None, section_pk=None, task_pk=None, pk=None):
        comment = self.get_object()
        user = request.user

        if comment.user != user:
            return Response(
                {'error': 'User not authorized'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data
        serializer = self.get_serializer(comment, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, project_uuid=None, board_pk=None, section_pk=None, task_pk=None, pk=None):
        comment = self.get_object()
        if comment.user != request.user:
            return Response(
                {'error': 'User not authorized'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        comment.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)

    def list(self, request, project_uuid=None, board_pk=None, section_pk=None, task_pk=None):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
