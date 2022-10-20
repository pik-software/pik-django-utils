import json
from decimal import Decimal

from rest_framework.renderers import (
    JSONOpenAPIRenderer, TemplateHTMLRenderer, OpenAPIRenderer, JSONRenderer)
from rest_framework.settings import api_settings
from rest_framework.utils import encoders
from rest_framework.utils.encoders import JSONEncoder


def encode_fakestr(func):
    def wrap(s):
        if isinstance(s, fakestr):
            return repr(s)
        return func(s)
    return wrap


json.encoder.encode_basestring = encode_fakestr(json.encoder.encode_basestring)
json.encoder.encode_basestring_ascii = encode_fakestr(
    json.encoder.encode_basestring_ascii)


class fakestr(str):  # noqa: pylint=N801 / class names should use CapWords convention
    def __init__(self, value):
        self._value = value

    def __repr__(self):
        return str(self._value)


class DecimalJSONEncoder(encoders.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return fakestr(o)
        return super().default(o)


class DecimalJSONRenderer(JSONRenderer):
    """
    Renderer which serializes to JSON, numbers serializes without float.
    """
    encoder_class = DecimalJSONEncoder


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
