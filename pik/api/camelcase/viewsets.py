from .parsers import (
    CamelCaseJSONParser, CamelCaseFormParser, CamelCaseMultiPartParser)
from .renderers import CalemizeJSONRenderer
from .openapi import PIKCamelCaseAutoSchema
from pik.utils.camelization import underscore, underscoreize


def camelcase_type_field_hook(serializer, obj):
    if hasattr(serializer, 'camelcase_type_field_hook'):
        return serializer.camelcase_type_field_hook(obj)
    return None


class CamelCaseViewSetMixIn:
    renderer_classes = [
        CalemizeJSONRenderer]

    parser_classes = [
        CamelCaseFormParser,
        CamelCaseMultiPartParser,
        CamelCaseJSONParser]

    schema = PIKCamelCaseAutoSchema()

    lookup_url_kwarg = 'guid'

    def dispatch(self, request, *args, **kwargs):
        request.GET = underscoreize(request.GET)
        for param in ['query', 'ordering']:
            if param in request.GET:
                request.GET[param] = underscore(request.GET[param])
        return super().dispatch(request, *args, **kwargs)

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            'type_field_hook': camelcase_type_field_hook}


def get_camelcase_viewset(viewset):
    return type(
        f'CamelCase{viewset.__name__}',
        (CamelCaseViewSetMixIn, viewset), {})
