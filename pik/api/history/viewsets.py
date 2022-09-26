from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from ..filters import StandardizedFieldFilters, StandardizedSearchFilter
from ..pagination import HistoryStandardizedCursorPagination

from .filters import get_history_filterset_class
from .serializers import get_history_serializer_class


class HistoryViewSetBase(ListModelMixin, GenericViewSet):
    pagination_class = HistoryStandardizedCursorPagination
    ordering_fields = ('updated', 'uid', 'history_date')

    serializer_class = None
    filterset_class = None

    filter_backends = (
        StandardizedFieldFilters, StandardizedSearchFilter)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        return queryset


def get_history_viewset(viewset):
    serializer_class = getattr(viewset, 'serializer_class', None)
    queryset = serializer_class.Meta.model.history
    model = queryset.model
    model_name = model._meta.object_name  # noqa: protected-access
    name = f'{model_name}ViewSet'

    serializer_class = get_history_serializer_class(
        model_name, serializer_class)
    filterset_class = get_history_filterset_class(model_name, viewset)

    select_related_fields = getattr(viewset, 'select_related_fields', None)
    if select_related_fields:
        select_related_fields = filter(
            lambda r: '__' not in r, select_related_fields)

    mixins = getattr(viewset, 'history_viewset_mixins', ())

    history_viewset = type(name, (HistoryViewSetBase, *mixins), {
        'select_related_fields': select_related_fields,
        'serializer_class': serializer_class,
        'filterset_class': filterset_class,
        'queryset': queryset
    })
    return history_viewset
