from rest_framework.schemas.openapi import SchemaGenerator
from rest_framework.schemas.openapi import AutoSchema
# TODO: klimenkoas: Drop `drf_yasg` dependency
from drf_yasg.utils import get_serializer_ref_name


# This module provides two classes used for nested serializers openapi schema
# reference ($ref) processing.
# Builtin DRF openapi schema generation tool processes each view through its'
# own `AutoSchema` instance, so the only way of processing references is adding
# marks to result schema and reducing them on the final stage within
# `SchemaGenerator.get_schema`.


class ReferenceAutoSchema(AutoSchema):
    """Marks nested serializer schemas with `x-ref` and `x-ref-source` which
    have to be processed later by `RefSchemaGenerator`"""

    def _map_serializer(self, serializer):
        schema = super()._map_serializer(serializer)
        schema['x-ref'] = get_serializer_ref_name(serializer)

        # Marking non-nested serializer
        if not serializer.parent:
            schema['x-ref-source'] = True
        return schema
