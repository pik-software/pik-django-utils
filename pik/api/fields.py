from rest_framework import serializers


class TypedJSONField(serializers.JSONField):
    type_name = None

    def __init__(self, _type, **kwargs):
        super().__init__(**kwargs)
        self._type = _type

    def to_representation(self, value):
        value.update({'_type': self._type})
        return value
