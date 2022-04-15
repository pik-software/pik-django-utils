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
from rest_framework import status
from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize
from sentry_sdk import capture_exception
from pika import BlockingConnection, URLParameters
from pika.exceptions import (
    AMQPConnectionError, ChannelWrongStateError, ChannelClosedByBroker, )
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_fixed, )

from pik.api.camelcase.viewsets import camelcase_type_field_hook


logger = logging.getLogger(__name__)

AMQP_ERRORS = (
    AMQPConnectionError, ChannelWrongStateError, ChannelClosedByBroker)


class BusModelNotFound(Exception):
    pass


def after_fail_retry(retry_state):
    logger.warning(
        'Reconnecting to RabbitMQ. Attempt number: %s',
        retry_state.attempt_number)
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
            if exc.reply_code != status.HTTP_502_BAD_GATEWAY:
                raise ChannelClosedByBroker from exc


producer = MessageProducer(settings.RABBITMQ_URL)


class InstanceHandler:
    renderer_class = JSONRenderer
    _instance = NotImplemented

    def __init__(self, instance):
        self._instance = instance

    @cached_property
    @staticmethod
    def models_info():
        """```{
            model: {
               'serializer': serializer,
               'exchange': exchange
           },
           ...
        }```"""
        return {
            import_string(serializer).Meta.model.__name__: {  # type: ignore
                'serializer': import_string(serializer),
                'exchange': exchange,
            }
            for exchange, serializer
            in settings.RABBITMQ_PRODUCES.items()
        }

    def handle(self):
        try:
            producer.produce(self.exchange, self.json_message)
        except BusModelNotFound:
            pass

    @property
    def payload(self):
        data = self.serializer(
            self._instance, context=self.get_serializer_context()).data
        data = camelize(data, **api_settings.JSON_UNDERSCOREIZE)
        if hasattr(self.serializer, 'camelization_hook'):
            return self.serializer.camelization_hook(data)
        return data

    @property
    def message(self):
        payload = self.payload
        return {
            'messageType': [payload['type'], ],
            'message': payload,
            'host': self.host,
        }

    @property
    def host(self):
        return {
            'machineName': platform.node(),
            'processId': os.getpid(),
            'frameworkVersion': django.get_version(),
            'operatingSystemVersion': (
                f'{platform.system()} {platform.version()}')
        }

    @property
    def serializer(self):
        try:
            return self.models_info[self.model_name]['serializer']
        except KeyError as exc:
            raise BusModelNotFound() from exc

    @property
    def exchange(self):
        try:
            return self.models_info[self.model_name]['exchange']
        except KeyError as exc:
            raise BusModelNotFound() from exc

    @property
    def model_name(self):
        return self._instance.__class__.__name__

    @property
    def json_message(self):
        return self.renderer_class().render(self.message)

    @staticmethod
    def get_serializer_context():
        return {'type_field_hook': camelcase_type_field_hook}


@receiver(post_save)
def push_model_instance_to_rabbit_queue(instance, **kwargs):
    if not settings.RABBITMQ_PRODUCER_ENABLE:
        return
    try:
        InstanceHandler(instance).handle()
    except Exception as exc:  # noqa: broad-except
        logger.error(
            'Reconnecting to RabbitMQ after %s attempt is fail',
            MessageProducer.RECONNECT_ATTEMPT_COUNT)
        logger.exception(exc)
        capture_exception(exc)
