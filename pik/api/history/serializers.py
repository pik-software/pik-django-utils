from collections import OrderedDict

from rest_framework import fields as rest_fields
from rest_framework.serializers import Serializer

from ..serializers import StandardizedModelSerializer
from ..user import UserSerializer


class HistorySerializerMixIn(Serializer):
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

    def to_representation(self, instance):
        ret = OrderedDict()
        fields = self._readable_fields  # noqa

        for field in fields:
            simplify_nested_serializer(field)
            try:
                attribute = field.get_attribute(instance)
                if attribute is not None:
                    ret[field.field_name] = field.to_representation(
                        attribute)
                else:
                    ret[field.field_name] = None
            except AttributeError:
                ret[field.field_name] = None

        return ret


def simplify_nested_serializer(serializer):
    if isinstance(serializer, StandardizedModelSerializer):
        for _name, _field in list(serializer.fields.items()):
            if _name not in ('_uid', '_type'):
                serializer.fields.pop(_name)


def get_history_serializer_class(model_name, serializer_class):
    name = f'{model_name}Serializer'
    _model = serializer_class.Meta.model.history.model
    fields = HistorySerializerMixIn.Meta.fields + serializer_class.Meta.fields
    _meta = type(
        'Meta', (HistorySerializerMixIn.Meta, serializer_class.Meta), {
            'model': _model,
            'fields': fields})
    bases = HistorySerializerMixIn, serializer_class
    return type(name, bases, {'Meta': _meta})
