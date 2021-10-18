from djangorestframework_camel_case.parser import CamelCaseJSONParser
from .renderers import CamelcaseJSONRenderer
from djangorestframework_camel_case.util import (
    underscoreize,
    camel_to_underscore, )

from .openapi import PIKCamelCaseAutoSchema


class CamelCaseViewSetMixIn:

    renderer_classes = [
        CamelcaseJSONRenderer]

    parser_classes = [
        CamelCaseJSONParser]

    schema = PIKCamelCaseAutoSchema()

    lookup_url_kwarg = 'guid'

    def dispatch(self, request, *args, **kwargs):
        request.GET = underscoreize(request.GET)
        for param in ['query', 'ordering']:
            if param in request.GET:
                request.GET[param] = camel_to_underscore(request.GET[param])
        result = super().dispatch(request, *args, **kwargs)
        return result


def get_camelcase_viewset(viewset):
    camelcase_viewset = type(
        f'CamelCase{viewset.__name__}',
        (CamelCaseViewSetMixIn, viewset), {})
    return camelcase_viewset
