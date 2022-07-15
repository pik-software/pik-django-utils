import logging
import os
from urllib.parse import urlparse
from logstash_async.transport import HttpTransport

LOGGER_NAME = 'logstash'
logger = logging.getLogger(__name__)


class DuplicateLoggingKey(Exception):
    pass


class LogstashLoggingSettingsExtendor:
    _LOGGING = {
        'formatters': {
            LOGGER_NAME: {
                '()': 'logstash_async.formatter.LogstashFormatter',
                'message_type': 'python-logstash',
                'extra_prefix': '',
                'extra': {},
            },
        },
        'handlers': {
            LOGGER_NAME: {
                'class': 'logstash_async.handler.AsynchronousLogstashHandler',
                'transport': None,
                'formatter': LOGGER_NAME,
                'host': None,
                'port': None,
                'database_path': None,
            },
        },
        'loggers': {
            LOGGER_NAME: {
                'handlers': [LOGGER_NAME],
                'level': 'INFO',
            },
        },
    }

    _url_warning = 'logstash_url must be in url format, for example ' \
                   '"https://user:pass@127.0.0.1:5044"'

    _host = None
    _port = None
    _username = None
    _password = None

    def __init__(self, settings):
        self._settings = settings

    def _check_url(self):
        logstash_url = os.environ.get(
            'LOGSTASH_URL', self._settings.get('LOGSTASH_URL', ''))

        parsed = urlparse(logstash_url)
        self._host, self._port, self._username, self._password = (
            parsed.hostname, parsed.port, parsed.username, parsed.password)
        self._username = self._username or ''
        self._password = self._password or ''

        for param in (self._host, self._port):
            if not param:
                logger.warning(self._url_warning)
                return False
        return True

    def _check(self):
        if not self._check_url():
            return False
        return True

    def _configure(self):
        self._LOGGING['handlers'][LOGGER_NAME]['transport'] = HttpTransport(
            host=self._host,
            port=self._port,
            ssl_verify=True,
            username=self._username,
            password=self._password,
        )

    def _merge(self):
        if 'LOGGING' not in self._settings:
            self._settings['LOGGING'] = {}
        dst_logging = self._settings['LOGGING']

        for key, value in self._LOGGING.items():
            if key not in dst_logging:
                dst_logging[key] = value
                continue
            if LOGGER_NAME in dst_logging[key]:
                raise DuplicateLoggingKey(
                    f'"{LOGGER_NAME}" key is already in "{key}" setting.')
            dst_logging[key][LOGGER_NAME] = value[LOGGER_NAME]

    def extend(self):
        if not self._check():
            return
        self._configure()
        self._merge()
        return self._settings
