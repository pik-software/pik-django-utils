import os
import platform
import logging

import django
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from rest_framework.renderers import JSONRenderer
from pika import BlockingConnection, URLParameters, spec
from pika.exceptions import (
    AMQPConnectionError, ChannelWrongStateError, ChannelClosedByBroker, )

from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_fixed, )

from pik.utils.sentry import capture_exception
from pik.api.camelcase.viewsets import camelcase_type_field_hook
from pik.api_settings import api_settings
from pik.utils.case_utils import camelize

from .mdm import mdm_event_captor

AMQP_ERRORS = (
    AMQPConnectionError, ChannelWrongStateError, ChannelClosedByBroker)
logger = logging.getLogger(__name__)


class BusModelNotFound(Exception):
    pass


def after_fail_retry(retry_state):
    logger.warning(
        'Reconnecting to RabbitMQ. Attempt number: %s',
        retry_state.attempt_number)
    if hasattr(retry_state.args[0], '_channel'):
        delattr(retry_state.args[0], '_channel')


class MessageProducer:
    RECONNECT_ATTEMPT_COUNT = 32
    RECONNECT_WAIT_DELAY = 1

    def __init__(self, connection_url):
        self.connection_url = connection_url

    @cached_property
    def _channel(self):
        channel = BlockingConnection(URLParameters(
            self.connection_url)).channel()
        channel.confirm_delivery()
        return channel

    @retry(
        wait=wait_fixed(RECONNECT_WAIT_DELAY),
        stop=stop_after_attempt(RECONNECT_ATTEMPT_COUNT),
        retry=retry_if_exception_type(AMQP_ERRORS),
        after=after_fail_retry,
        reraise=True,
    )
    def produce(self, exchange, json_message):
        try:
            self._channel.basic_publish(
                exchange=exchange,
                routing_key='',
                body=json_message)
        except ChannelClosedByBroker as exc:
            if exc.reply_code != spec.SYNTAX_ERROR:
                raise ChannelClosedByBroker from exc


producer = MessageProducer(settings.RABBITMQ_URL)


class InstanceHandler:
    renderer_class = JSONRenderer
    _instance = NotImplemented
    _type = None
    _guid = None
    _exchange = None
    _serializer = None
    _json_message = None

    def __init__(self, instance, event_captor):
        self._instance = instance
        self._event_captor = event_captor
        self._type = None
        self._guid = None
        self._exchange = None
        self._serializer = None
        self._json_message = None

    @cached_property
    def models_info(self):  # noqa: no-self-used Unable to combine static @method & @cached_property
        """```
        {
            model: {
               'serializer': serializer,
               'exchange': exchange
           },
           ...
        }
        ```"""
        return {
            import_string(serializer).Meta.model.__name__: {  # type: ignore
                'serializer': import_string(serializer),
                'exchange': exchange,
            }
            for exchange, serializer
            in settings.RABBITMQ_PRODUCES.items()
        }

    def _capture_event(self, event, **kwargs):
        self._event_captor.capture(
            event=event,
            entity_type=self._type,
            entity_guid=self._guid,
            **kwargs
        )

    def _serialize(self):
        try:
            self.get_serializer()
        except BusModelNotFound:
            return

        error = None
        try:
            self.get_json_message()
        except Exception as error:
            raise error
        finally:
            self._capture_event(
                event='serialization',
                **{
                    'success': not error,
                    'error': error,
                })

    def _produce(self):
        try:
            self.get_exchange()
        except BusModelNotFound:
            return

        error = None
        try:
            producer.produce(self._exchange, self._json_message)
        except Exception:  # noqa broad-except
            raise
        finally:
            self._capture_event(
                event='publishing',
                **{
                    'success': not error,
                    'error': error,
                })

    def handle(self):
        self._serialize()
        self._produce()

    def get_exchange(self):
        try:
            self._exchange = self.models_info[self.model_name]['exchange']
        except KeyError as exc:
            raise BusModelNotFound() from exc

    @property
    def model_name(self):
        return self._instance.__class__.__name__

    def get_json_message(self):
        self._json_message = self.renderer_class().render(self.message)

    @property
    def message(self):
        payload = self.payload
        return {
            'messageType': [payload['type'], ],
            'message': payload,
            'host': self.host,
        }

    @property
    def payload(self):
        data = self._serializer(
            self._instance, context=self.get_serializer_context()).data
        data = camelize(data, **api_settings.JSON_UNDERSCORIZE)
        if hasattr(self._serializer, 'camelization_hook'):
            return self._serializer.camelization_hook(data)

        self._type = data['type']
        self._guid = str(data['guid'])

        return data

    @property
    def host(self):
        return {
            'machineName': platform.node(),
            'processId': os.getpid(),
            'frameworkVersion': django.get_version(),
            'operatingSystemVersion': (
                f'{platform.system()} {platform.version()}')
        }

    def get_serializer(self):
        try:
            self._serializer = self.models_info[self.model_name]['serializer']
        except KeyError as exc:
            raise BusModelNotFound() from exc

    @staticmethod
    def get_serializer_context():
        return {'type_field_hook': camelcase_type_field_hook}


@receiver(post_save)
def push_model_instance_to_rabbit_queue(instance, **kwargs):
    if not settings.RABBITMQ_PRODUCER_ENABLE:
        return
    try:
        InstanceHandler(instance, mdm_event_captor).handle()
    except Exception as exc:  # noqa: broad-except
        logger.info(
            'Reconnecting to RabbitMQ after %s attempt is fail',
            MessageProducer.RECONNECT_ATTEMPT_COUNT)
        capture_exception(exc)
