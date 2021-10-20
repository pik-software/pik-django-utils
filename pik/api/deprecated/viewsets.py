from .openapi import DeprecatedAutoSchema
from .parsers import (
    DeprecatedFormParser, DeprecatedMultiPartParser, DeprecatedJSONParser, )
from .renderers import DeprecatedJSONRenderer
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

    lookup_url_kwarg = '_uid'

    def dispatch(self, request, *args, **kwargs):
        request.GET = replace_struct_keys(
            request.GET, replacer=to_actual_filters,
            ignore_fields=['ordering', 'query'])

        if hasattr(self, 'deprecated_filters_hook'):
            if callable(self.deprecated_filters_hook):
                request.GET = self.deprecated_filters_hook(request.GET)

        if 'ordering' in request.GET:
            request.GET['ordering'] = to_actual_ordering.replace(
                request.GET['ordering'])
        if 'query' in request.GET:
            request.GET['query'] = to_actual_fields.replace(
                request.GET['query'])
        return super().dispatch(request, *args, **kwargs)


def get_deprecated_viewset(viewset):
    return type(
        f'Deprecated{viewset.__name__}', (DeprecatedViewSetMixIn, viewset), {})
