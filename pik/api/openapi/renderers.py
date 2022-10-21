import json

from rest_framework.renderers import (
    JSONOpenAPIRenderer, TemplateHTMLRenderer, OpenAPIRenderer)
from rest_framework.settings import api_settings
from rest_framework.utils.encoders import JSONEncoder


class JSONOpenPrettyRenderer(JSONOpenAPIRenderer):
    """ NonASCI OpenApi RENDERER """
    ensure_ascii = not api_settings.UNICODE_JSON

    def render(self, data, media_type=None, renderer_context=None):
        return json.dumps(
            data, indent=2, cls=JSONEncoder, ensure_ascii=self.ensure_ascii
        ).encode('utf-8')


class JSONOpenAPICachedRenderer(JSONOpenAPIRenderer):
    """ JSON OpenAPI Renderer with pre-rendered support """

    extension = 'json'


class RedocOpenAPIRenderer(TemplateHTMLRenderer):
    """ Redoc renderer https://github.com/Redocly/redoc """

    template_name = 'redoc.html'


class TemplateHTMLCachedRenderer(TemplateHTMLRenderer):
    """ Template Renderer with pre-rendered support """

    extension = 'html'


class PIKOpenAPIRenderer(OpenAPIRenderer):
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
