import os
import platform

import django
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.functional import cached_property
from rest_framework.renderers import JSONRenderer
from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize
from sentry_sdk import capture_exception
from pika import BlockingConnection, URLParameters
from pika.exceptions import AMQPConnectionError
from tenacity import retry, retry_if_exception_type, stop_after_attempt

from .mixins import ModelSerializerMixin


class BusSerializerNotFound(Exception):
    pass


class MessageHandler:
    RECONNECT_ATTEMPT_COUNT = 5

    def __init__(self, connection_url):
        self.connection_url = connection_url

    @cached_property
    def _channel(self):
        return BlockingConnection(URLParameters(self.connection_url)).channel()

    @retry(
        stop=stop_after_attempt(RECONNECT_ATTEMPT_COUNT),
        retry=retry_if_exception_type(AMQPConnectionError),
        # Clear _channel cached_property.
        after=lambda retry_state: delattr(retry_state.args[0], '_channel'),
        reraise=True,
    )
    def handle(self, queue_name, json_message):
        channel = self._channel
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json_message)


class MessageProducer(ModelSerializerMixin):
    renderer_class = JSONRenderer
    _instance = NotImplemented
    _handler = None

    def __init__(self, instance):
        self._instance = instance
        self.handler = MessageHandler(settings.RABBITMQ_URL)

    def produce(self):
        try:
            self.handler.handle(self.queue_name, self.json_message)
        except BusSerializerNotFound:
            pass

    @property
    def payload(self):
        try:
            serializer = self.MODEL_SERIALIZER[
                self._instance.__class__.__name__]
        except KeyError as exc:
            raise BusSerializerNotFound(
                self._instance.__class__.__name__) from exc

        data = serializer(self._instance).to_representation(self._instance)
        data = camelize(data, **api_settings.JSON_UNDERSCOREIZE)
        if hasattr(serializer, 'camelization_hook'):
            return serializer.camelization_hook(data)
        return data

    @property
    def message(self):
        return {
            'messageType': self.queue_name,
            'message': self.payload,
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
    def queue_name(self):
        return self._instance.__class__.__name__

    @property
    def json_message(self):
        return self.renderer_class().render(self.message)


@receiver(post_save)
def push_model_instance_to_rabbit_queue(instance, **kwargs):
    if not settings.RABBITMQ_ENABLE:
        return
    try:
        MessageProducer(instance).produce()
    except Exception as exc:  # noqa: broad-except
        capture_exception(exc)
