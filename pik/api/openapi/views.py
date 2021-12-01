import os

from django.conf import settings
from django.http import HttpResponse
from rest_framework.schemas.views import SchemaView
from rest_framework.settings import api_settings

from .openapi import PIKSchemaGenerator
from .renderers import PIKRedocOpenAPIRenderer, \
    PIKJSONOpenAPIRenderer, PIKOpenAPIRenderer


class CachedSchemaViewMixIn:
    @property
    def pregenerated(self):
        name = self.request.path.replace('/', '_')
        extension = self.request.accepted_renderer.extension
        return os.path.join(settings.STATIC_ROOT, f'{name}.{extension}')

    def get(self, request, *args, **kwargs):
        if os.path.isfile(self.pregenerated):
            return HttpResponse(
                open(self.pregenerated, 'r', encoding='utf-8'),
                content_type=request.accepted_media_type)
        return super().get(request, *args, **kwargs)  # noqa: bad-super-call


class PIKSchemaView(CachedSchemaViewMixIn, SchemaView):
    pass


def get_pik_schema_view(**kwargs):
    kwargs.setdefault('title', f'{settings.SERVICE_TITLE} API')
    kwargs.setdefault('description', settings.SERVICE_DESCRIPTION)
    kwargs.setdefault('renderer_classes', (
        PIKRedocOpenAPIRenderer,
        PIKJSONOpenAPIRenderer,
        PIKOpenAPIRenderer))
    kwargs.setdefault('generator_class', PIKSchemaGenerator)
    kwargs.setdefault('version', settings.SERVICE_RELEASE)
    kwargs.setdefault('view_class', PIKSchemaView)
    kwargs.setdefault('urlconf', None)
    kwargs.setdefault('url', None)
    kwargs.setdefault('patterns', None)
    kwargs.setdefault('public', False)

    kwargs.setdefault(
        'authentication_classes', api_settings.DEFAULT_AUTHENTICATION_CLASSES,)
    kwargs.setdefault(
        'permission_classes', api_settings.DEFAULT_PERMISSION_CLASSES,)

    generator = kwargs['generator_class'](
        title=kwargs['title'], url=kwargs['url'],
        description=kwargs['description'], urlconf=kwargs['urlconf'],
        patterns=kwargs['patterns'], version=kwargs['description']
    )

    return kwargs['view_class'].as_view(
        renderer_classes=kwargs['renderer_classes'],
        schema_generator=generator,
        public=kwargs['public'],
        authentication_classes=kwargs['authentication_classes'],
        permission_classes=kwargs['permission_classes'],
    )
