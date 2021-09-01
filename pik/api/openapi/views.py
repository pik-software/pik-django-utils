from django.conf import settings
from rest_framework.schemas import get_schema_view

from .openapi import PIKSchemaGenerator
from .renders import PIKRedocOpenAPIRenderer, \
    PIKJSONOpenAPIRenderer, PIKOpenAPIRenderer


def get_pik_schema_view(**kwargs):
    kwargs.setdefault('title', f'{settings.SERVICE_TITLE} API')
    kwargs.setdefault('description', settings.SERVICE_DESCRIPTION)
    kwargs.setdefault('renderer_classes', (
        PIKRedocOpenAPIRenderer,
        PIKJSONOpenAPIRenderer,
        PIKOpenAPIRenderer))
    kwargs.setdefault('generator_class', PIKSchemaGenerator)
    kwargs.setdefault('version', settings.SERVICE_RELEASE)
    return get_schema_view(**kwargs)
