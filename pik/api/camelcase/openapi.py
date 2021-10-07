import re

from djangorestframework_camel_case.util import camelize, underscore_to_camel
from rest_framework.schemas import AutoSchema

from pik.api.openapi.openapi import PIKAutoSchema


class CamelCaseAutoSchema(AutoSchema):
    RE = re.compile(
        r'(((?=[^_])[a-z0-9])_[a-z0-9])' r'|(^_[a-z0-9])' r'|(\W_[a-z0-9])')

    def map_serializer(self, serializer):
        parent_result = super().map_serializer(serializer)
        result = camelize(parent_result)
        return result

    def camelize(self, value):
        """ Correct filter modificators camelization

        >>> dict(camelize({'_with__filter': ''}))
        {'With_Filter': ''}

        >>> CamelCaseAutoSchema().camelize('_with__filter')
        'With__filter'
        """
        return self.RE.sub(underscore_to_camel, value)

    def get_operation(self, path, method):
        """ Camelizing url params escaping `__` construction """
        schema = super().get_operation(path, method)
        for param in schema['parameters']:
            param['name'] = self.camelize(param['name'])
        return schema

    def get_components(self, path, method):
        components = super().get_components(path, method)
        for key in components.keys():
            if 'required' in components[key]:
                components[key]['required'] = [
                    self.camelize(required)
                    for required in
                    components[key]['required']]
        return components


class PIKCamelCaseAutoSchema(
        CamelCaseAutoSchema,
        PIKAutoSchema):
    pass
