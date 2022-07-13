import logging
from django.conf import settings


logstash_logger = None
if 'logstash' in settings.LOGGING['handlers']:
    logstash_logger = logging.getLogger('logstash')


def statistic_captor(**kwargs):
    if not logstash_logger:
        return

    logstash_logger.info(msg='Send data to logstash', extra={
        **kwargs,
        **{
            'logger': settings.SERVICE_NAME,
        }
    })
