from .openapi import DeprecatedAutoSchema
from .parsers import (
    DeprecatedFormParser, DeprecatedMultiPartParser, DeprecatedJSONParser, )
from .renderers import DeprecatedJSONRenderer
from .utils import (
    replace_struct_keys, to_actual_filters, to_actual_fields,
    to_actual_ordering, )


def deprecated_type_field_hook(serializer, obj):
    if hasattr(serializer, 'deprecated_type_field_hook'):
        return serializer.deprecated_type_field_hook(obj)
    return None


class DeprecatedViewSetMixIn:
    renderer_classes = [
        DeprecatedJSONRenderer]

    parser_classes = [
        DeprecatedFormParser,
        DeprecatedMultiPartParser,
        DeprecatedJSONParser]

    schema = DeprecatedAutoSchema()

    lookup_url_kwarg = '_uid'

    def dispatch(self, request, *args, **kwargs):
        request.GET = replace_struct_keys(
            request.GET, replacer=to_actual_filters,
            ignore_fields=['ordering', 'query'])

        if hasattr(self.serializer_class, 'deprecated_filters_hook'):
            request.GET = self.serializer_class().deprecated_filters_hook(
                request.GET)

        if 'ordering' in request.GET:
            request.GET['ordering'] = to_actual_ordering.replace(
                request.GET['ordering'])
        if 'query' in request.GET:
            request.GET['query'] = to_actual_fields.replace(
                request.GET['query'])
        return super().dispatch(request, *args, **kwargs)

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            'type_field_hook': deprecated_type_field_hook}


def get_deprecated_viewset(viewset):
    return type(
        f'Deprecated{viewset.__name__}', (DeprecatedViewSetMixIn, viewset), {})
