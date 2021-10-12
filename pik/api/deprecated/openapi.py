from pik.api.openapi.openapi import PIKAutoSchema
from .utils import (
    replace_struct_keys, to_deprecated_fields, to_deprecated_filters, )

from .consts import JSONSCHEMA_TYPE_DICT_ITEMS


class DeprecatedAutoSchema(PIKAutoSchema):
    def map_serializer(self, serializer):
        """ Deprecating response schema """

        parent_result = super().map_serializer(serializer)
        result = replace_struct_keys(
            parent_result,
            replacer=to_deprecated_fields,
            ignore_dict_items=JSONSCHEMA_TYPE_DICT_ITEMS
        )

        if 'required' in result:
            result['required'] = [
                to_deprecated_fields.replace(required)
                for required in result['required']
            ]

        return result

    def get_operation(self, path, method):
        """ Deprecating url params """

        schema = super().get_operation(path, method)
        for param in schema['parameters']:
            param['name'] = to_deprecated_filters.replace(param['name'])

            if 'enum' in param['schema']:
                param['schema']['enum'] = [
                    to_deprecated_filters.replace(item)
                    for item in param['schema']['enum']]
        return schema
