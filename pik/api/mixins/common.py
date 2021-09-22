from django.contrib.postgres.search import SearchQuery
from django.http import Http404
from rest_framework import status
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from pik.api.permissions import CreateUpdateDjangoModelViewPermission

from pik.api.consts import RUSSIAN_LANGUAGE_CONFIG


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
