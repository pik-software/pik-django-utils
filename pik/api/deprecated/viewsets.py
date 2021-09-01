from .openapi import DeprecatedAutoSchema
from .parsers import (
    DeprecatedFormParser, DeprecatedMultiPartParser, DeprecatedJSONParser, )
from .renderer import DeprecatedJSONRenderer
from .utils import (
    replace_struct_keys, to_actual_filters, to_actual_fields,
    to_actual_ordering, )


class DeprecatedViewSetMixIn:
    renderer_classes = [
        DeprecatedJSONRenderer]

    parser_classes = [
        DeprecatedFormParser,
        DeprecatedMultiPartParser,
        DeprecatedJSONParser]

    schema = DeprecatedAutoSchema()

    def dispatch(self, request, *args, **kwargs):
        request.GET = replace_struct_keys(
            request.GET, replacer=to_actual_filters,
            ignore_fields=['ordering', 'query'])

        if 'ordering' in request.GET:
            request.GET['ordering'] = to_actual_ordering.replace(
                request.GET['ordering'])
        if 'query' in request.GET:
            request.GET['query'] = to_actual_fields.replace(
                request.GET['query'])
        return super().dispatch(request, *args, **kwargs)


def get_deprecated_viewset(view):
    return type(
        f'Deprecated{view.__class__.__name__}',
        (DeprecatedViewSetMixIn, view), {})
