from pik.api.openapi.openapi import PIKAutoSchema
from .utils import (
    replace_struct_keys, to_deprecated_fields, to_deprecated_filters, )

from .consts import JSONSCHEMA_TYPE_DICT_ITEMS


class DeprecatedAutoSchema(PIKAutoSchema):
    def map_serializer(self, serializer):
        """ Deprecating response schema """

        schema = replace_struct_keys(
            super().map_serializer(serializer),
            replacer=to_deprecated_fields,
            ignore_dict_items=JSONSCHEMA_TYPE_DICT_ITEMS
        )

        if 'required' in schema:
            schema['required'] = [
                to_deprecated_fields.replace(required)
                for required in schema['required']
            ]

        if hasattr(self.view.serializer_class, 'deprecated_render_hook'):
            schema = self.view.serializer_class().deprecated_render_hook(
                schema)

        return schema

    def get_operation(self, path, method):
        """ Deprecating url params """

        schema = super().get_operation(path, method)
        for param in schema['parameters']:
            param['name'] = to_deprecated_filters.replace(param['name'])

            if 'enum' in param['schema']:
                param['schema']['enum'] = [
                    to_deprecated_filters.replace(item)
                    for item in param['schema']['enum']]

        if hasattr(self.view.serializer_class, 'deprecated_render_hook'):
            schema = self.view.serializer_class().deprecated_render_hook(
                schema)

        return schema
