import coreapi
from django.contrib.postgres.fields import ArrayField
from django.db.models import DateTimeField
from django_filters import OrderingFilter
from rest_framework.filters import (
    OrderingFilter as DRFOrderingFilter, SearchFilter)
from rest_framework_filters import (
    FilterSet, BaseCSVFilter, AutoFilter, IsoDateTimeFilter, BooleanFilter, )
from rest_framework_filters.backends import RestFrameworkFilterBackend
from .filters_mixins import StandardizedAPISearchIndex


UID_LOOKUPS = ('exact', 'gt', 'gte', 'lt', 'lte', 'in', 'isnull')
DATE_LOOKUPS = ('exact', 'gt', 'gte', 'lt', 'lte', 'in', 'isnull')
NUMBER_LOOKUPS = ('exact', 'gt', 'gte', 'lt', 'lte', 'in', 'isnull')
STRING_LOOKUPS = (
    'exact', 'iexact', 'in', 'startswith', 'endswith', 'contains', 'isnull')
BOOLEAN_LOOKUPS = ('exact', 'in', 'isnull')
ARRAY_LOOKUPS = (
    'contains', 'contained_by', 'overlap', 'len', 'isnull', 'exact')


class StandardizedFieldFilters(RestFrameworkFilterBackend):
    def get_schema_fields(self, view):
        # This is not compatible with widgets where the query param differs
        # from the filter's attribute name. Notably, this includes
        # `MultiWidget`, where query params will be of
        # the format `<name>_0`, `<name>_1`, etc...

        filterset_class = getattr(view, 'filterset_class', None)
        if filterset_class is None:
            try:
                filterset_class = self.get_filterset_class(
                    view, view.get_queryset())
            except Exception as exc:  # noqa
                raise RuntimeError(
                    f"{view.__class__} is not compatible with "
                    f"schema generation"
                ) from exc

        fields = []

        return self.get_flatten_schema_fields('', fields, filterset_class)

    def get_flatten_schema_fields(
            self, prefix, filters: list, filterset_class):
        for field_name, field in filterset_class.get_filters().items():
            # TODO: remove dependency from coreapi
            filters.append(coreapi.Field(
                name=f'{prefix}{field_name}',
                required=False,
                location='query',
                schema=self.get_coreschema_field(field)
            ))
        return filters


class StandardizedSearchFilter(StandardizedAPISearchIndex, SearchFilter):
    pass


class StandardizedOrderingFilter(DRFOrderingFilter):
    pass


class ArrayFilter(BaseCSVFilter, AutoFilter):
    DEFAULT_LOOKUPS = ARRAY_LOOKUPS

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('lookups', self.DEFAULT_LOOKUPS)
        super().__init__(*args, **kwargs)


class NamedFilterMixIn:
    name = AutoFilter(lookups=STRING_LOOKUPS)


class DeletedFilterMixIn(FilterSet):
    deleted = AutoFilter(lookups=DATE_LOOKUPS)


class BooleanQuerySetFilter(BooleanFilter):
    on_true = None
    on_false = None

    def __init__(self, **kwargs):
        self.on_true = kwargs.pop('on_true')
        self.on_false = kwargs.pop('on_false')
        super().__init__(**kwargs)

    def filter(self, qs, value):
        if value is None:
            return qs

        if self.exclude:
            value = not value
        if value is True:
            return getattr(qs, self.on_true)()
        if value is False:
            return getattr(qs, self.on_false)()
        return qs


class StandardizedFilterSet(FilterSet):
    FILTER_DEFAULTS = {**FilterSet.FILTER_DEFAULTS, **{
        ArrayField: {'filter_class': ArrayFilter},
        DateTimeField: {'filter_class': IsoDateTimeFilter},
    }}
    guid = AutoFilter('uid', lookups=UID_LOOKUPS)
    created = AutoFilter(lookups=DATE_LOOKUPS)
    updated = AutoFilter(lookups=DATE_LOOKUPS)
    order_by_field = 'ordering'
    ordering = OrderingFilter(fields=(
        ('uid', 'guid'),
        ('updated', 'updated'),
        ('created', 'created'),
        ('version', 'version'),
        ('uid', 'name'),
    ))

    class Meta:
        model = None
        fields: dict = {}


class SoftDeletedStandardizedFilterSet(StandardizedFilterSet):
    deleted = AutoFilter(lookups=DATE_LOOKUPS)
    ordering = OrderingFilter(fields=(
        ('uid', 'guid'),
        ('updated', 'updated'),
        ('created', 'created'),
        ('version', 'version'),
        ('deleted', 'deleted'),
    ))
    is_deleted = BooleanQuerySetFilter(
        on_true='is_deleted', on_false='is_not_deleted')


def get_ordering_fields(filterset):
    return (
        (v, k) for k, v in
        filterset.base_filters['ordering'].param_map.items())
