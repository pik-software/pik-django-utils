import logging
from importlib.metadata import (
    version as get_package_version,
    PackageNotFoundError,
)

from django.conf import settings
from django.utils.functional import cached_property
from pika import URLParameters

from pik.bus.settings import BUS_EVENT_LOGGER


class MDMEventCaptor:
    def capture(self, event, entity_type, entity_guid, **kwargs):
        if not self._mdm_logger:
            return

        message = f'Captured mdm event "{event}" ' \
                  f'for object "{entity_type}" guid "{entity_guid}"'
        self._mdm_logger.info(msg=message, extra={
            **{
                'logger': self._client_name,
                'event': event,
                'objectType': entity_type,
                'objectGuid': entity_guid,
            },
            **self._versions,
            **kwargs,
        })

    @cached_property
    def _client_name(self):  # noqa: no-self-use, to use cached_property
        return URLParameters(settings.RABBITMQ_URL).credentials.username

    @cached_property
    def _mdm_logger(self):  # noqa: no-self-use, to use cached_property
        return logging.getLogger(getattr(
            settings, BUS_EVENT_LOGGER, 'bus_event_logstash_logger'))

    @cached_property
    def _mdm_models_version(self):
        try:
            version = f"v{get_package_version('mdm_models')}"
        except PackageNotFoundError:
            version = None
        return version

    @cached_property
    def _schema_version(self):
        if self._mdm_models_version:
            schema_version = self._mdm_models_version.split(
                '.', maxsplit=3)[-1].replace('+', '.')
            return f"v{schema_version}"

    @cached_property
    def _versions(self):
        return {
            'mdm_models_version': self._mdm_models_version,
            'schema_version': self._schema_version,
        } if self._mdm_models_version else {}


mdm_event_captor = MDMEventCaptor()
