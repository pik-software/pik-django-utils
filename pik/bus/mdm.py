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
    def _versions(self):  # noqa: no-self-use, to use cached_property
        service_version = {'service_version': os.environ.get('RELEASE')}
        if mdm_models:
            return {
                'generator_version': f"v{mdm_models.__generator_version__}",
                'entities_version': f"v{mdm_models.__entities_version__}",
                'library_version': f"v{mdm_models.__version__}",
                **service_version,
            }
        return {
            **service_version,
        }


mdm_event_captor = MDMEventCaptor()
