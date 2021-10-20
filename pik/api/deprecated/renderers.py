from rest_framework.renderers import JSONRenderer

from .utils import replace_struct_keys, to_deprecated_fields


class DeprecatedJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type, renderer_context):  # noqa: arguments-differ
        data = replace_struct_keys(data, replacer=to_deprecated_fields)

        view = renderer_context['view']
        if hasattr(view, 'deprecated_render_hook'):
            data = view.deprecated_render_hook(data)

        result = super().render(data, accepted_media_type, renderer_context)
        return result
