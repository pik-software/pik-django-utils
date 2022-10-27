from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from rest_framework.settings import APISettings

USER_SETTINGS = getattr(settings, "JSON_CAMEL_CASE", {})

DEFAULTS = {
    "RENDERER_CLASS": "pik.api.renderers.DecimalJSONRenderer",
    "PARSER_CLASS": "pik.api.parsers.DecimalJSONParser",
    "JSON_UNDERSCORIZE": {"ignore_fields": None, "lower_camel_case": False},
}

# List of settings that may be in string import notation.
IMPORT_STRINGS = ("RENDERER_CLASS", "PARSER_CLASS")

VALID_SETTINGS = {
    "RENDERER_CLASS": (
        "pik.api.renderers.DecimalJSONRenderer",
    ),
    "PARSER_CLASS": ("pik.api.parsers.DecimalJSONParser",),
}


def validate_settings(input_settings, valid_settings):
    for setting_name, valid_values in valid_settings.items():
        input_setting = input_settings.get(setting_name)
        if input_setting and input_setting not in valid_values:
            raise ImproperlyConfigured(setting_name)


validate_settings(USER_SETTINGS, VALID_SETTINGS)

api_settings = APISettings(USER_SETTINGS, DEFAULTS, IMPORT_STRINGS)
