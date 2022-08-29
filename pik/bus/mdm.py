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
            **self.versions,
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
    def service_version(self):  # noqa: no-self-use, to use cached_property
        return {'serviceVersion': os.environ.get('RELEASE')}

    @cached_property
    def entities_version(self):  # noqa: no-self-use, to use cached_property
        if not mdm_models:
            return {}
        return {'entitiesVersion': f"v{mdm_models.__entities_version__}"}

    @cached_property
    def generator_version(self):  # noqa: no-self-use, to use cached_property
        if not mdm_models:
            return {}
        return {'generatorVersion': f"v{mdm_models.__generator_version__}"}

    @cached_property
    def lib_version(self):  # noqa: no-self-use, to use cached_property
        if not mdm_models:
            return {}
        return {'libVersion': f"v{mdm_models.__version__}"}

    @cached_property
    def versions(self):  # noqa: no-self-use, to use cached_property
        return {
            **self.generator_version,
            **self.entities_version,
            **self.lib_version,
            **self.service_version,
        }


mdm_event_captor = MDMEventCaptor()
