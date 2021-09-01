import json
import os

from django.conf import settings
from rest_framework.renderers import JSONOpenAPIRenderer, BaseRenderer, \
    TemplateHTMLRenderer, OpenAPIRenderer
from rest_framework.settings import api_settings
from rest_framework.utils.encoders import JSONEncoder


class CachedRenderer(BaseRenderer):
    """ BaseRenderer with pre-rendered files support """
    extension = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        name = renderer_context['request'].path.replace('/', '_')
        path = os.path.join(settings.STATIC_ROOT, f'{name}.{self.extension}')
        if os.path.isfile(path):
            return open(path, 'r', encoding='utf-8')
        return super().render(data, accepted_media_type, renderer_context)


class JSONOpenPrettyRenderer(JSONOpenAPIRenderer):
    """ NonASCI OpenApi RENDERER """
    ensure_ascii = not api_settings.UNICODE_JSON

    def render(self, data, media_type=None, renderer_context=None):
        return json.dumps(
            data, indent=2, cls=JSONEncoder, ensure_ascii=self.ensure_ascii
        ).encode('utf-8')


class JSONOpenAPICachedRenderer(CachedRenderer, JSONOpenAPIRenderer):
    """ JSON OpenAPI Renderer with pre-rendered support """

    extension = 'json'


class RedocOpenAPIRenderer(TemplateHTMLRenderer):
    """ Redoc renderer https://github.com/Redocly/redoc """

    template_name = 'redoc.html'


class TemplateHTMLCachedRenderer(CachedRenderer, TemplateHTMLRenderer):
    """ Template Renderer with pre-rendered support """

    extension = 'html'


class PIKOpenAPIRenderer(
        CachedRenderer,
        OpenAPIRenderer):
    """ OpenAPI renderer with pre-rendered support """
    extension = 'yaml'


class PIKRedocOpenAPIRenderer(
        TemplateHTMLCachedRenderer,
        RedocOpenAPIRenderer):
    """ Redoc renderer with pre-rendered support """


class PIKJSONOpenAPIRenderer(
        JSONOpenAPICachedRenderer,
        JSONOpenPrettyRenderer):
    """ NonASCI OpenAPI JSON renderer with pre-rendered support """
