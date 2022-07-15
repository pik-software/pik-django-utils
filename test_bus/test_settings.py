import pytest

from logstash_async.transport import HttpTransport

from pik.bus.settings import (
    LogstashLoggingSettingsExtendor, DuplicateLoggingKey)


class TestSettings:
    def _compare(self, actual_logging):
        assert actual_logging['formatters']['logstash'] == {
            '()': 'logstash_async.formatter.LogstashFormatter',
            'extra': {},
            'extra_prefix': '',
            'message_type': 'python-logstash'
        }
        assert actual_logging['loggers']['logstash'] == {
            'handlers': ['logstash'],
            'level': 'INFO'
        }
        transport = actual_logging['handlers']['logstash'].pop('transport')
        assert isinstance(transport, HttpTransport)
        assert actual_logging['handlers']['logstash'] == {
            'class': 'logstash_async.handler.AsynchronousLogstashHandler',
            'database_path': None,
            'formatter': 'logstash',
            'host': None,
            'port': None,
        }

    def test_with_logging_setting(self):
        actual_settings = LogstashLoggingSettingsExtendor({
            'LOGGING': {
                'loggers': {
                    'django': {'level': 'debug'},
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'verbose'
                    },
                },
                'formatters': {
                    'verbose': {
                        'format': '%(levelname)s %(asctime)s %(message)s'
                    }
                },
            },
            'LOGSTASH_URL': 'https://username:password@host:1024'
        }).extend()
        self._compare(actual_settings['LOGGING'])

    def test_without_logging_setting(self):
        actual_settings = LogstashLoggingSettingsExtendor({
            'LOGSTASH_URL': 'https://username:password@host:1024'
        }).extend()
        self._compare(actual_settings['LOGGING'])

    def test_with_partly_logging_setting(self):
        actual_settings = LogstashLoggingSettingsExtendor({
            'LOGGING': {
                'loggers': {
                    'django': {'level': 'debug'},
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'verbose'
                    },
                },
            },
            'LOGSTASH_URL': 'https://username:password@host:1024'
        }).extend()
        self._compare(actual_settings['LOGGING'])

    def test_duplicate_logging_key_exception(self):
        with pytest.raises(
                DuplicateLoggingKey,
                match='"logstash" key is already in "loggers" setting.'):
            LogstashLoggingSettingsExtendor({
                'LOGGING': {
                    'loggers': {
                        'django': {'level': 'debug'},
                        'logstash': {'level': 'debug'},
                    },
                    'handlers': {
                        'console': {
                            'class': 'logging.StreamHandler',
                            'formatter': 'verbose'
                        },
                    },
                },
                'LOGSTASH_URL': 'https://username:password@host:1024'
            }).extend()
