from pik.api.openapi.openapi import PIKAutoSchema
from .utils import (
    replace_struct_keys, to_actual_filters, to_actual_fields,
    to_deprecated_fields, )


class DeprecatedAutoSchema(PIKAutoSchema):
    def map_serializer(self, serializer):
        """ Deprecating response schema """

        return replace_struct_keys(
            super().map_serializer(serializer),
            replacer=to_deprecated_fields)

    def get_operation(self, path, method):
        """ Deprecating url params """

        schema = super().get_operation(path, method)
        for param in schema['parameters']:
            param['name'] = to_actual_filters.replace(param['name'])

            if 'enum' in param['schema']:
                param['schema']['enum'] = [
                    to_actual_fields.replace(item)
                    for item in param['schema']['enum']]
        return schema
