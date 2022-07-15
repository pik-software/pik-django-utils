import logging
from django.conf import settings
from .settings import LOGGER_NAME


logger = logging.getLogger(__name__)


logstash_logger = None
if 'handlers' in settings.LOGGING and LOGGER_NAME in settings.LOGGING['handlers']:
    logstash_logger = logging.getLogger(LOGGER_NAME)


if not hasattr(settings, 'RABBITMQ_ACCOUNT_NAME'):
    raise AttributeError('RABBITMQ_ACCOUNT_NAME must be define in settings')


def capture_stats(event, entity_type, entity_guid, **kwargs):
    if not logstash_logger:
        return

    message = f'Send to logstash data at event "{event}" ' \
              f'for object "{entity_type}" with guid "{entity_guid}"'
    logstash_logger.info(msg=message, extra={
        **{
            'logger': settings.RABBITMQ_ACCOUNT_NAME,
            'type': entity_type,
            'guid': entity_guid,
        },
        **kwargs,
    })
