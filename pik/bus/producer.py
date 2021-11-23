# TODO:
# - Камелизацию в API перевести на serializer
#

from pydoc import locate
import os
import platform
from retry import retry

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
from pika.exceptions import AMQPError, AMQPConnectionError


class BusSerializerNotFound(Exception):
    pass


class MessageHandler:
    def __init__(self, connection_url):
        self.connection_url = connection_url

    @cached_property
    def _connector(self):
        connection = BlockingConnection(URLParameters(self.connection_url))
        channel = connection.channel()
        return connection, channel

    def _reset_connector(self):
        connection, _ = self._connector
        if connection and not connection.is_closed:
            try:
                connection.close()
            except (ConnectionError, AMQPError):
                pass
        del self.__dict__['_connector']

    @staticmethod
    def _produce(channel, queue_name, json_message):
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json_message)

    @retry(AMQPConnectionError, tries=5, delay=2, backoff=2)
    def handle(self, queue_name, json_message):
        try:
            _, channel = self._connector
            self._produce(channel, queue_name, json_message)
        except AMQPConnectionError:
            try:
                self._reset_connector()
                _, channel = self._connector
                self._produce(channel, queue_name, json_message)
            except AMQPConnectionError as exc:
                raise AMQPConnectionError from exc
            except Exception as exc:  # noqa: broad-except
                capture_exception(exc)


handler = MessageHandler(settings.RABBITMQ_URL)


class MessageProducer:
    renderer_class = JSONRenderer
    _instance = NotImplemented

    MODEL_SERIALIZER = {
        locate(serializer).Meta.model: locate(serializer)
        for serializer in settings.RABBITMQ_SERIALIZERS
    }

    def __init__(self, instance):
        self._instance = instance

    def produce(self):
        try:
            handler.handle(self.queue_name, self.json_message)
        except BusSerializerNotFound:
            pass

    @property
    def payload(self):
        try:
            serializer = self.MODEL_SERIALIZER[self._instance.__class__]
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
    MessageProducer(instance).produce()
