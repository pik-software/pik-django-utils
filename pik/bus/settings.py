import logging
import os
from urllib.parse import urlparse
from logstash_async.transport import HttpTransport


logger = logging.getLogger(__name__)


class LogstashLoggingSettingsExtendor:
    _LOGGING = {
        'formatters': {
            'logstash': {
                '()': 'logstash_async.formatter.LogstashFormatter',
                'message_type': 'python-logstash',
                'extra_prefix': '',
                'extra': {},
            },
        },
        'handlers': {
            'logstash': {
                'class': 'logstash_async.handler.AsynchronousLogstashHandler',
                'transport': None,
                'formatter': 'logstash',
                'host': None,
                'port': None,
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

    _dependency_warning = '"Python Logstash Async" package is not found. ' \
                          'Install via pip: ' \
                          '"pip install python-logstash-async".'

    _url_warning = 'One of param user, pass, host or port in not set. ' \
                   'logstash_url must be in url format, for example ' \
                   '"https://user:pass@127.0.0.1:5044"'

    _settings_warning = '"LOGGING" setting is not found.'

    _host = None
    _port = None
    _username = None
    _password = None

    def __init__(self, settings):
        self._settings = settings

    # def _check_dependency(self):
    #     try:
    #         import logstash_async
    #     except ImportError:
    #         logger.warning(self._dependency_warning)
    #         return False
    #     return True

    def _check_url(self):
        logstash_url = os.environ.get(
            'LOGSTASH_URL', self._settings.get('LOGSTASH_URL', ''))

        parsed = urlparse(logstash_url)
        self._host, self._port, self._username, self._password = (
            parsed.hostname, parsed.port, parsed.username, parsed.password)

        for param in (self._host, self._port, self._username, self._password):
            if not param:
                logger.warning(self._url_warning)
                return False
        return True

    def _check_settings(self):
        if 'LOGGING' not in self._settings:
            logger.warning(self._settings_warning)
            return False
        return True

    def _check(self):
        # for method in (
        #         self._check_dependency, self._check_url, self._check_settings):
        for method in (self._check_url, self._check_settings):
            if not method():
                return False
        return True

    def _configure(self):
        # self._LOGGING['handlers']['logstash'].update(
        #     host=self._host,
        #     port=self._port,
        #     username=self._username,
        #     password=self._password,
        # )
        self._LOGGING['handlers']['logstash']['transport'] = HttpTransport(
            host=self._host,
            port=self._port,
            ssl_verify=True,
            username=self._username,
            password=self._password,
        )

    def _merge(self):
        _key_not_found_warning = '"{}" key not found in LOGGING setting.'
        _key_exist_warning = '"logstash" key is already in "{}" setting.'

        dst_logging = self._settings['LOGGING']

        for key, value in self._LOGGING.items():
            if key not in dst_logging:
                logger.warning(_key_not_found_warning.format(key))
            if 'logstash' in dst_logging[key]:
                logger.warning(_key_exist_warning.format(key))
            dst_logging[key]['logstash'] = value['logstash']

    def extend(self):
        if not self._check():
            return
        self._configure()
        self._merge()
