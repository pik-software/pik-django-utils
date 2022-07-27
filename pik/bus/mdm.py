import logging
from functools import cached_property

from django.conf import settings
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
            **kwargs,
        })

    @cached_property
    def _client_name(self):
        return URLParameters(settings.RABBITMQ_URL).credentials.username

    @cached_property
    def _mdm_logger(self):
        return logging.getLogger(getattr(
            settings, BUS_EVENT_LOGGER, 'bus_event_logstash_logger'))


mdm_event_captor = MDMEventCaptor()
