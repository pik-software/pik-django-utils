from django.http import Http404
from rest_framework import status
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from pik.api.permissions import CreateUpdateDjangoModelViewPermission


class BulkCreateModelMixin(CreateModelMixin):
    """
    Either create a single or many model instances in bulk by using the
    Serializers ``many=True``.

    Example:

        class ContactViewSet(StandartizedModelViewSet):
            ...
            allow_bulk_create = True
            ...
    """
    allow_bulk_create = False

    def create(self, request, *args, **kwargs):
        bulk = isinstance(request.data, list)

        if not bulk:
            return super().create(request, *args, **kwargs)

        if not self.allow_bulk_create:
            self.permission_denied(
                request,
                message='You do not have permission to create multiple objects'
            )

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_bulk_create(self, serializer):
        return self.perform_create(serializer)


class CreateOrUpdateMixin:
    permission_classes = (
        IsAuthenticated, CreateUpdateDjangoModelViewPermission)

    def update(self, request, *args, **kwargs):
        # Override default update implementation to support PUT create/update
        # https://developer.mozilla.org/ru/docs/Web/HTTP/Methods/PUT
        partial = kwargs.pop('partial', False)
        try:
            instance = self.get_object()
        except Http404 as exc:
            if partial is True:
                # PATCH with unknown resource id should raise 404
                raise exc
            instance = None

        if instance:
            status_code = status.HTTP_200_OK
            serializer = self.get_serializer(
                data=request.data, instance=instance, partial=partial)

        else:
            status_code = status.HTTP_201_CREATED
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}  # noqa: pylint==protected-access

        return Response(status=status_code, data=serializer.data)
