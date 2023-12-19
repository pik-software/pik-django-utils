import logging
import os

from django.conf import settings
from django.utils.functional import cached_property
from pika import URLParameters

from pik.bus.settings import BUS_EVENT_LOGGER

try:
    import mdm_models
except ModuleNotFoundError:
    mdm_models = None  # noqa: invalid-name


# TODO: make as static class.
class LibraryVersions:
    @cached_property
    def versions(self):  # noqa: no-self-use, to use cached_property
        return {
            **self.generator_version,
            **self.entities_version,
            **self.lib_version,
            **self.service_version}

    @cached_property
    def generator_version(self):  # noqa: no-self-use, to use cached_property
        if not mdm_models:
            return {}
        return {'generatorVersion': f"v{mdm_models.__generator_version__}"}

    @cached_property
    def entities_version(self):  # noqa: no-self-use, to use cached_property
        if not mdm_models:
            return {}
        return {'entitiesVersion': f"v{mdm_models.__entities_version__}"}

    @cached_property
    def lib_version(self):  # noqa: no-self-use, to use cached_property
        if not mdm_models:
            return {}
        return {'libVersion': f"v{mdm_models.__version__}"}

    @cached_property
    def service_version(self):  # noqa: no-self-use, to use cached_property
        return {'serviceVersion': os.environ.get('RELEASE')}


library_versions = LibraryVersions()


class MDMEventCaptor:
    _library_versions = None

    def __init__(self, library_versions):  # noqa: pylint - redefined-outer-name
        self._library_versions = library_versions

    def capture(self, event, entity_type, entity_guid, **kwargs):
        if not self._is_bus_enabled:
            return

        if not self._mdm_logger:
            return

        message = (
            f'Captured mdm event "{event}" for object "{entity_type}" '
            f'guid "{entity_guid}"')
        self._mdm_logger.info(msg=message, extra={
            **{
                'logger': self._client_name,
                'event': event,
                'objectType': entity_type,
                'objectGuid': entity_guid},
            **self._library_versions.versions,
            **kwargs})

    @cached_property
    def _is_bus_enabled(self):
        return (
            self._producer_enabled_settings or self._consumer_enabled_settings)

    @property
    def _producer_enabled_settings(self):
        return getattr(settings, 'RABBITMQ_PRODUCER_ENABLE', False)

    @property
    def _consumer_enabled_settings(self):
        return getattr(settings, 'RABBITMQ_CONSUMER_ENABLE', False)

    @cached_property
    def _mdm_logger(self):  # noqa: no-self-use, to use cached_property
        return logging.getLogger(self._bus_event_logger_settings)

    @property
    def _bus_event_logger_settings(self):
        return getattr(settings, BUS_EVENT_LOGGER, 'bus_event_logstash_logger')

    @cached_property
    def _client_name(self):  # noqa: no-self-use, to use cached_property
        return URLParameters(self.rabbitmq_url).credentials.username

    @property
    def rabbitmq_url(self) -> str:
        return getattr(settings, 'RABBITMQ_URL', '')


mdm_event_captor = MDMEventCaptor(library_versions)
