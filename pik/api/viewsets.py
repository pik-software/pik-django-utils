from django_restql.mixins import EagerLoadingMixin
from rest_framework import generics, mixins
from rest_framework.viewsets import ViewSetMixin

from .restql import DefaultRequestQueryParserMixin
from .mixins import BulkCreateModelMixin


class DeletedModelViewSetMixIn:
    def get_queryset(self):
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


class StandardizedModelViewSet(
    DeletedModelViewSetMixIn,
    BulkCreateModelMixin,
    mixins.RetrieveModelMixin,
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
