from logstash_async.transport import HttpTransport

from pik.bus.settings import (
    LogstashBusLoggingSettingsExtender, BUS_EVENT_FORMATTER, BUS_EVENT_LOGGER,
    BUS_EVENT_HANDLER)


class TestSettings:
    @staticmethod
    def _compare(actual_logging):
        assert actual_logging['formatters'][BUS_EVENT_FORMATTER] == {
            '()': 'logstash_async.formatter.LogstashFormatter',
            'extra': {},
            'extra_prefix': '',
            'message_type': 'python-logstash'
        }
        assert actual_logging['loggers'][BUS_EVENT_LOGGER] == {
            'handlers': [BUS_EVENT_HANDLER],
            'level': 'INFO'
        }
        transport = actual_logging['handlers'][BUS_EVENT_HANDLER].pop(
            'transport')
        assert isinstance(transport, HttpTransport)
        assert actual_logging['handlers'][BUS_EVENT_HANDLER] == {
            'class': 'logstash_async.handler.AsynchronousLogstashHandler',
            'database_path': None,
            'formatter': BUS_EVENT_FORMATTER,
            'host': None,
            'port': None,
        }

    def test_with_logging_setting(self):
        settings = {
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
            'BUS_EVENT_LOGSTASH_URL': 'https://username:password@host:1024'
        }
        LogstashBusLoggingSettingsExtender(settings).extend()
        self._compare(settings['LOGGING'])

    def test_without_logging_setting(self):
        settings = {
            'BUS_EVENT_LOGSTASH_URL': 'https://username:password@host:1024'
        }
        LogstashBusLoggingSettingsExtender(settings).extend()
        self._compare(settings['LOGGING'])

    def test_with_partly_logging_setting(self):
        settings = {
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
            'BUS_EVENT_LOGSTASH_URL': 'https://username:password@host:1024'
        }
        LogstashBusLoggingSettingsExtender(settings).extend()
        self._compare(settings['LOGGING'])
