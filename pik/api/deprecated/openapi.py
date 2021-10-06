from pik.api.openapi.openapi import PIKAutoSchema
from .utils import (
    replace_struct_keys, to_actual_filters, to_actual_fields,
    to_deprecated_fields, )

from .consts import JSONSCHEMA_TYPE_DICT_ELEMS


class DeprecatedAutoSchema(PIKAutoSchema):
    def map_serializer(self, serializer):
        """ Deprecating response schema """

        parent_result = super().map_serializer(serializer)
        result = replace_struct_keys(
            parent_result,
            replacer=to_deprecated_fields,
            ignore_fields=['ordering', 'query'],
            ignore_dict_elems=JSONSCHEMA_TYPE_DICT_ELEMS
        )

        return result

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
