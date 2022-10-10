import os
from logging import getLogger
from typing import Optional
from urllib.parse import urlparse

from logstash_async.transport import HttpTransport


BUS_EVENT_LOGGER = 'bus_event_logstash_logger'
BUS_EVENT_HANDLER = 'bus_event_logstash_handler'
BUS_EVENT_FORMATTER = 'bus_event_logstash_logger'


logger = getLogger(__name__)


class LogstashBusLoggingSettingsExtender:
    _LOGGING_FORMATTER = {
        '()': 'logstash_async.formatter.LogstashFormatter',
        'message_type': 'python-logstash',
        'extra_prefix': '',
        'extra': {},
    }

    _LOGGING_HANDLER = {
        'class': 'logstash_async.handler.AsynchronousLogstashHandler',
        'transport': None,
        'formatter': BUS_EVENT_FORMATTER,
        'host': None,
        'port': None,
        'database_path': None,
    }

    _LOGGING_LOGGER = {
        'handlers': [BUS_EVENT_HANDLER],
        'level': 'INFO',
    }

    _url_warning = 'BUS_EVENT_LOGSTASH_URL is not set or set in incorrect ' \
                   'format in environment variables and settings param. ' \
                   'BUS_EVENT_LOGSTASH_URL must be in url format, for ' \
                   'example "https://user:pass@127.0.0.1:5044"'

    _host: Optional[str] = None
    _port = None
    _username = None
    _password = None

    def __init__(self, settings):
        self._settings = settings

    def extend(self):
        if self._is_logstash_url_valid:
            self._add_logstash_logger()

    @property
    def _is_logstash_url_valid(self):
        logstash_url = os.environ.get(
            'BUS_EVENT_LOGSTASH_URL',
            self._settings.get('BUS_EVENT_LOGSTASH_URL', ''))

        parsed = urlparse(logstash_url)
        self._host, self._port, self._username, self._password = (
            parsed.hostname, parsed.port, parsed.username, parsed.password)
        self._username = self._username or ''
        self._password = self._password or ''

        if not all((self._host, self._port)):
            logger.warning(self._url_warning)
            return False
        return True

    def _add_logstash_logger(self):
        self._settings.setdefault('LOGGING', {})

        logging = self._settings['LOGGING']
        for key in 'handlers', 'formatters', 'loggers':
            logging.setdefault(key, {})

        logging['formatters'][BUS_EVENT_FORMATTER] = {
            **self._LOGGING_FORMATTER}
        logging['loggers'][BUS_EVENT_LOGGER] = {**self._LOGGING_LOGGER}
        logging['handlers'][BUS_EVENT_HANDLER] = self._handler

    @property
    def _handler(self):
        return {**self._LOGGING_HANDLER, 'transport': HttpTransport(
            host=self._host,
            port=self._port,
            ssl_verify=True,
            username=self._username,
            password=self._password)}


class ConsumerBusSettingExtender:
    __ALL__ = '__ALL__'

    def __init__(self, settings, serializers):
        self._settings = settings
        self._serializers = serializers
        self._rabbitmq_account_name = getattr(
            self._settings, 'RABBITMQ_ACCOUNT_NAME', '')
        self._rabbitmq_consumes = getattr(
            self._settings, 'RABBITMQ_CONSUMES', '')
        self._rabbitmq_consumes_all = getattr(
            self._settings, 'RABBITMQ_CONSUMES_ALL', False)
        if self._is_rabbitmq_consumes_all_not_set:
            self._settings.RABBITMQ_CONSUMES_ALL = True

    @property
    def _is_rabbitmq_account_name_set(self):
        return bool(self._rabbitmq_account_name)

    @property
    def _is_rabbitmq_consumes_set_all(self):
        return bool(
            (isinstance(self._rabbitmq_consumes, str)
             and self._rabbitmq_consumes.lower() == self.__ALL__.lower())
            or self._rabbitmq_consumes_all)

    @property
    def _is_rabbitmq_consumes_all_not_set(self):
        return bool(
            not self._rabbitmq_consumes_all
            and self._is_rabbitmq_consumes_set_all)

    @property
    def _is_rabbitmq_consumes_rewrite_condition(self):
        return bool(
            self._is_rabbitmq_account_name_set
            and self._is_rabbitmq_consumes_set_all)

    def extend(self):
        if self._is_rabbitmq_consumes_rewrite_condition:
            self._settings.RABBITMQ_CONSUMES = {
                (f'{self._rabbitmq_account_name}.'
                 f'{queue.partition("Serializer")[0]}'):
                f'{serializer.__module__}.{serializer.__name__}'
                for queue, serializer in self._serializers.items()}
