from djangorestframework_camel_case.render import CamelCaseJSONRenderer


class CamelcaseJSONRenderer(CamelCaseJSONRenderer):
    def render(self, data, accepted_media_type, renderer_context):  # noqa: arguments-differ
        view = renderer_context['view']
        if hasattr(view, 'dict_camelize_hook'):
            data = view.dict_camelize_hook(data)

        result = super().render(data, accepted_media_type, renderer_context)
        return result
