import os
from urllib.parse import quote

from django.http import Http404
from django.utils.module_loading import import_string
from django.core.exceptions import ImproperlyConfigured
from django_restql.mixins import EagerLoadingMixin
from private_storage import appconfig
from private_storage.models import PrivateFile
from private_storage.servers import get_server_class
from private_storage.storage import private_storage
from rest_framework import generics, mixins
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSetMixin

from .permissions import CreateUpdateDjangoModelViewPermission
from .restql import DefaultRequestQueryParserMixin


class DeletedModelViewSetMixIn:
    def get_queryset(self):
        if self.queryset:
            return self.queryset
        if hasattr(self.serializer_class.Meta.model, 'all_objects'):
            return self.serializer_class.Meta.model.all_objects.all()
        return self.serializer_class.Meta.model.objects.all()


class StandardizedGenericViewSet(ViewSetMixin, generics.GenericAPIView):
    pass


class StandardizedReadOnlyModelViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    StandardizedGenericViewSet
):
    """
    A viewset that provides default `list()` and `retrieve()` actions.
    """


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


class StandardizedModelViewSet(
    CreateOrUpdateMixin,
    DeletedModelViewSetMixIn,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    StandardizedGenericViewSet
):
    """
    A viewset that provides default `create()`, `retrieve()`, `update()`,
    `partial_update()`, `destroy()` and `list()` actions.
    """


class RestQLStandardizedModelViewSet(
        DefaultRequestQueryParserMixin, EagerLoadingMixin,
        StandardizedModelViewSet):
    pass


class RestQLStandardizedReadOnlyModelViewSet(
        DefaultRequestQueryParserMixin, EagerLoadingMixin,
        StandardizedReadOnlyModelViewSet):
    pass


class PrivateStorageAPIView(APIView):
    """
       API View for sharing files from `private_storage`.
    """

    permission_classes = [IsAuthenticated]
    storage = private_storage

    #: The authorisation rule for accessing
    can_access_file = staticmethod(
        import_string(appconfig.PRIVATE_STORAGE_AUTH_FUNCTION))

    #: Import the server class once
    server_class = get_server_class(appconfig.PRIVATE_STORAGE_SERVER)

    #: Whether the file should be displayed ``inline`` or show a
    # download box (``attachment``).
    content_disposition = None

    #: The filename to use when :attr:`content_disposition` is set.
    content_disposition_filename = None

    #: Message to be displayed when the user cannot access the requested file.
    permission_denied_message = 'Private storage access denied'

    def get_path(self):
        """
        Determine the path for the object to provide.
        This can be overwritten to combine the view with a different
        object retrieval.
        """
        return self.kwargs['path']

    def get_storage(self):
        """
        Tell which storage to retrieve the file from.
        """
        return self.storage

    def get_private_file(self):
        """
        Return all relevant data in a single object, so this is easy to extend
        and server implementations can pick what they need.
        """
        return PrivateFile(
            request=self.request,
            storage=self.get_storage(),
            relative_name=self.get_path()
        )

    def get(self, request, *args, **kwargs):
        """
        Handle incoming GET requests
        """
        private_file = self.get_private_file()

        if not self.can_access_file(private_file):
            raise PermissionDenied(self.permission_denied_message)

        if not private_file.exists():
            return self.serve_file_not_found(private_file)

        return self.serve_file(private_file)

    @staticmethod
    def serve_file_not_found(private_file):
        """
        Display a response message telling that the file is not found.
        This can be overwritten to improve the customer experience.
        For example
        - redirect the user, and show a message.
        - render the message in the expected media type (e.g. PNG).
        - show a custom 404 page.

        :type private_file: :class:`private_storage.models.PrivateFile`
        :rtype: django.http.HttpResponse
        """
        raise Http404("File not found")

    def serve_file(self, private_file):
        """
        Serve the file that was retrieved from the storage.
        The relative path can be found with ``private_file.relative_name``.

        :type private_file: :class:`private_storage.models.PrivateFile`
        :rtype: django.http.HttpResponse
        """
        response = self.server_class().serve(private_file)

        if self.content_disposition:
            # Join syntax works in all Python versions.
            # Python 3 doesn't support b'..'.format(),
            # and % formatting was added for bytes in 3.5:
            # https://bugs.python.org/issue3982
            filename = self.get_content_disposition_filename(private_file)
            response['Content-Disposition'] = b'; '.join([
                self.content_disposition.encode(),
                self._encode_filename_header(filename)
            ])

        return response

    def get_content_disposition_filename(self, private_file):
        """
        Return the filename in the download header.
        """
        return self.content_disposition_filename or os.path.basename(
            private_file.relative_name)

    def _encode_filename_header(self, filename):
        """
        The filename, encoded to use in a ``Content-Disposition`` header.
        """
        # Based on https://www.djangosnippets.org/snippets/1710/
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        if 'WebKit' in user_agent:
            # Support available for UTF-8 encoded strings.
            # This also matches Edgee.
            return f'filename={filename}'.encode("utf-8")
        if 'MSIE' in user_agent:
            # IE does not support RFC2231 for internationalized headers,
            # but somehow percent-decodes it so this can be used instead.
            # Note that using the word "attachment" anywhere in the filename
            # overrides an inline content-disposition.
            url_encoded = quote(filename.encode('utf-8'))
            url_encoded = url_encoded.replace('attachment', 'a%74tachment')
            return f'filename={url_encoded}'.encode('utf-8')

        # For others like Firefox, we follow RFC2231
        # (encoding extension in HTTP headers).
        rfc2231_filename = quote(filename.encode('utf-8'))
        return f"filename*=UTF-8''{rfc2231_filename}".encode('utf-8')


class StandardizedObjPermissionModelViewSet(StandardizedModelViewSet):
    permission_classes = (DjangoObjectPermissions, IsAuthenticated)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for permission in self.permission_classes:
            if issubclass(permission, DjangoObjectPermissions):
                return
        raise ImproperlyConfigured(
            '`DjangoObjectPermissions` is required for per object viewset '
            'functionality')

    def check_permissions(self, request):
        """ Dropping global permission checking in order of later per object
        check through the `DjangoPerModelViewPermission` """

    def get_queryset(self):
        if not hasattr(self.request, 'user'):
            return super().get_queryset().none()
        return super().get_queryset().filter_by_user_grants(self.request.user)


class RestQLStandardizedObjPermissionModelViewSet(
        EagerLoadingMixin, StandardizedObjPermissionModelViewSet):
    pass
