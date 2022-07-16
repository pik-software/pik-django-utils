import logging
from django.conf import settings
from .settings import LOGGER_NAME


logger = logging.getLogger(__name__)


LOGSTASH_LOGGER = None
handler = getattr(
    settings, 'LOGGING', {}).get('handlers', {}).get(LOGGER_NAME, None)
if handler:
    LOGSTASH_LOGGER = logging.getLogger(LOGGER_NAME)


if not hasattr(settings, 'RABBITMQ_ACCOUNT_NAME'):
    LOGSTASH_LOGGER = None
    logger.warning(
        'RABBITMQ_ACCOUNT_NAME param is necessary for logstash logger, '
        'but not set in settings.')


def capture_stats(event, entity_type, entity_guid, **kwargs):
    if not LOGSTASH_LOGGER:
        return

    message = f'Send to logstash data at event "{event}" ' \
              f'for object "{entity_type}" with guid "{entity_guid}"'
    LOGSTASH_LOGGER.info(msg=message, extra={
        **{
            'logger': settings.RABBITMQ_ACCOUNT_NAME,
            'event': event,
            'objectType': entity_type,
            'objectGuid': entity_guid,
        },
        **kwargs,
    })
