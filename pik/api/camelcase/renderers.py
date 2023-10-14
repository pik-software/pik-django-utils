from pik.api_settings import api_settings
from pik.utils.case_utils import camelize


class CamelizeJSONRenderer(api_settings.RENDERER_CLASS):
    def render(self, data, accepted_media_type, renderer_context):  # noqa: arguments-differ
        view = renderer_context['view']
        if hasattr(view.serializer_class, 'camelization_hook'):
            data = view.serializer_class().camelization_hook(data)

        return super().render(
            camelize(data, **api_settings.JSON_UNDERSCORIZE),
            accepted_media_type, renderer_context)
