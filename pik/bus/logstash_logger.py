import sys
from urllib.parse import urlparse
import logging.config


class LogstashLogger:
    """
    >>> LogstashLogger('//127.0.0.1:5044')._logger
    <Logger logstash (INFO)>

    >>> LogstashLogger('127.0.0.1:5044')._logger
    """
    _LOGGER_CONFIG = {
        'version': 1,
        'formatters': {
            'logstash': {
                '()': 'logstash_async.formatter.LogstashFormatter',
                'message_type': 'python-logstash',
                'extra': {},
            },
        },
        'handlers': {
            'logstash': {
                'class': 'logstash_async.handler.AsynchronousLogstashHandler',
                'transport': 'logstash_async.transport.BeatsTransport',
                'formatter': 'logstash',
                'host': None,
                'port': None,
                'ssl_enable': False,
                'database_path': None,
            },
        },
        'loggers': {
            'logstash': {
                'handlers': ['logstash'],
                'level': 'INFO',
            },
        },
    }

    def __init__(self, logger_name, logstash_url):
        self._logger_name = logger_name
        self._logger = None
        if logstash_url:
            parsed = urlparse(logstash_url)
            if parsed.hostname is None or parsed.port is None:
                print(
                    'logstash_url must be in url format, for example '
                    '"//127.0.0.1:5044"', file=sys.stderr)
                return
            logstash = self._LOGGER_CONFIG['handlers']['logstash']
            logstash['host'] = parsed.hostname
            logstash['port'] = parsed.port
            logging.config.dictConfig(self._LOGGER_CONFIG)
            self._logger = logging.getLogger('logstash')

    def logging(self, **kwargs):
        if self._logger:
            self._logger.info('', extra={
                'statistics': {
                    **kwargs,
                    **{
                        'logger': self._logger_name
                    },
                }
            })
