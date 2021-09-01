from djangorestframework_camel_case.parser import (
    CamelCaseFormParser,
    CamelCaseMultiPartParser, CamelCaseJSONParser, )
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from djangorestframework_camel_case.util import (
    underscoreize,
    camel_to_underscore, )

from .openapi import PIKCamelCaseAutoSchema


class CamelCaseViewSetMixIn:

    renderer_classes = [
        CamelCaseJSONRenderer]

    parser_classes = [
        CamelCaseFormParser,
        CamelCaseMultiPartParser,
        CamelCaseJSONParser]

    schema = PIKCamelCaseAutoSchema()

    def dispatch(self, request, *args, **kwargs):
        request.GET = underscoreize(request.GET)
        for param in ['query', 'ordering']:
            if param in request.GET:
                request.GET[param] = camel_to_underscore(request.GET[param])
        return super().dispatch(request, *args, **kwargs)


def get_camelcase_viewset(view):
    return type(
        f'CamelCase{view.__class__.__name__}',
        (CamelCaseViewSetMixIn, view), {})
