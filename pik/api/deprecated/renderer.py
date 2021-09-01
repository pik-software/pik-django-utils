from rest_framework.renderers import JSONRenderer

from .utils import replace_struct_keys, to_deprecated_fields


class DeprecatedJSONRenderer(JSONRenderer):
    def render(self, data, *args, **kwargs):  # noqa: arguments-differ
        return super().render(
            replace_struct_keys(data, replacer=to_deprecated_fields),
            *args, **kwargs
        )
