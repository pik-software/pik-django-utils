from collections import OrderedDict

from django.conf import settings
from django.core.cache import cache
from rest_framework import fields as rest_fields
from rest_framework.serializers import Serializer, ListSerializer
from rest_framework.exceptions import PermissionDenied

from ..serializers import StandardizedModelSerializer
from ..user import UserSerializer


class HistoricalSerializerBase(Serializer):
    history_id = rest_fields.IntegerField()
    history_date = rest_fields.DateTimeField()
    history_change_reason = rest_fields.CharField()
    history_type = rest_fields.CharField()
    history_user_id = rest_fields.IntegerField()
    history_user = UserSerializer()

    class Meta:
        fields = ('history_id', 'history_date', 'history_change_reason',
                  'history_type', 'history_type', 'history_user_id',
                  'history_user')

    def update(self, instance, validated_data):  # noqa: no-self-use
        raise PermissionDenied()

    def create(self, validated_data):  # noqa: no-self-use
        raise PermissionDenied()

    def to_representation(self, instance):
        ret = OrderedDict()
        fields = self._readable_fields  # noqa

        for field in fields:
            # simplify_nested_serializer(field)
            ret[field.field_name] = None
            try:
                attribute = field.get_attribute(instance)
                if attribute is not None:
                    ret[field.field_name] = field.to_representation(attribute)
            except AttributeError:
                pass

        return ret


class CachedHistorySerializerMixin:
    SERIALIZER_CACHE_TTL_SEC = getattr(
        settings, 'HISTORY_SERIALIZER_CACHE_TTL_SEC', 600)
    SERIALIZER_CACHE_KEY_FORMAT = (
        '{serializer.__class__.__name__}'
        '.{instance.uid}.{instance.version}.{request.method}')

    def _get_cache_key(self, instance):
        """Get cache key of instance"""
        params = {'instance': instance,
                  'request': self.context['request'],
                  'serializer': self}
        return self.SERIALIZER_CACHE_KEY_FORMAT.format(**params)

    def to_representation(self, instance):
        """
        Checks if the representation of instance is cached and adds to cache
        if is not.
        """

        # Skipping nested serializers caching
        is_nested = self.parent and self.parent.parent
        if is_nested:
            return super().to_representation(instance)

        key = self._get_cache_key(instance)
        cached = cache.get(key)
        if cached:
            return cached

        result = super().to_representation(instance)
        cache.set(key, result, self.SERIALIZER_CACHE_TTL_SEC)
        return result


def simplify_nested_serializer(serializer):
    if isinstance(serializer, StandardizedModelSerializer):
        for _name, _field in list(serializer.fields.items()):
            if _name not in ('_uid', '_type'):
                serializer.fields.pop(_name)


def get_history_serializer_class(model_name, serializer_class):
    name = f'{model_name}Serializer'
    _model = serializer_class.Meta.model.history.model
    serializer = serializer_class()

    # Skipping not historical M2M and reverse (many=True) fields
    non_m2m_fields = tuple(
        field for field in serializer.Meta.fields
        if not isinstance(serializer.fields[field], ListSerializer))

    fields = (HistoricalSerializerBase.Meta.fields + non_m2m_fields)

    _meta = type(
        'Meta', (HistoricalSerializerBase.Meta, serializer_class.Meta), {
            'model': _model,
            'ref_name': _model._meta.object_name,  # noqa: protected-access
            'fields': fields})
    bases = (CachedHistorySerializerMixin, HistoricalSerializerBase,
             serializer_class)
    return type(name, bases, {'Meta': _meta})
