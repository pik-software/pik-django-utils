import os
import platform
import logging
import uuid
from contextlib import ContextDecorator
from typing import Dict, Union

import django
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from pika import BlockingConnection, URLParameters, spec
from pika.exceptions import (
    AMQPConnectionError, ChannelWrongStateError, ChannelClosedByBroker, )
from rest_framework.renderers import JSONRenderer
from rest_framework.serializers import Serializer

from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_fixed, )

from pik.utils.sentry import capture_exception
from pik.api.camelcase.viewsets import camelcase_type_field_hook
from pik.api_settings import api_settings
from pik.utils.case_utils import camelize
from pik.bus.mdm import mdm_event_captor
from pik.bus.exceptions import (
    ModelMissingError, MDMTransactionIsAlreadyStartedError)


logger = logging.getLogger(__name__)


def after_fail_retry(retry_state):
    logger.warning(
        'Reconnecting to RabbitMQ. Attempt number: %s',
        retry_state.attempt_number)
    if retry_state.attempt_number == MessageProducer.RECONNECT_ATTEMPT_COUNT:
        logger.error(
            'Reconnecting to RabbitMQ after %s attempt is fail',
            MessageProducer.RECONNECT_ATTEMPT_COUNT)

    if hasattr(retry_state.args[0], '_channel'):
        delattr(retry_state.args[0], '_channel')


class MessageProducer:
    renderer_class = JSONRenderer
    RECONNECT_ATTEMPT_COUNT = 32
    RECONNECT_WAIT_DELAY = 1

    transaction_guid = None
    _transaction_messages = None

    def __init__(self, connection_url, event_captor):
        self.connection_url = connection_url
        self._event_captor = event_captor

    @cached_property
    def _channel(self):
        channel = BlockingConnection(URLParameters(
            self.connection_url)).channel()
        channel.confirm_delivery()
        return channel

    def _publish(self, envelope, exchange='', routing_key=''):
        self._channel.basic_publish(
            exchange=exchange, routing_key=routing_key,
            body=self.renderer_class().render(envelope))

    @retry(
        wait=wait_fixed(RECONNECT_WAIT_DELAY),
        stop=stop_after_attempt(RECONNECT_ATTEMPT_COUNT),
        retry=retry_if_exception_type((
            AMQPConnectionError, ChannelWrongStateError,
            ChannelClosedByBroker)),
        after=after_fail_retry,
        reraise=True,
    )
    def _produce(self, envelope, exchange, routing_key):
        try:
            self._publish(envelope, exchange, routing_key)
        except ChannelClosedByBroker as error:
            self._capture_event(envelope, success=False, error=error)
            if error.reply_code != spec.SYNTAX_ERROR:
                raise
        except Exception as error:  # noqa: board-except
            self._capture_event(envelope, success=False, error=error)
            raise
        else:
            self._capture_event(envelope, success=True, error=None)

    def produce(self, envelope, exchange='', routing_key=''):
        if self._transaction_messages is not None:
            self._transaction_messages.append((
                envelope, exchange, routing_key))
            return
        self._produce(envelope, exchange, routing_key)

    def start_transaction(self):
        if self._transaction_messages is not None:
            raise MDMTransactionIsAlreadyStartedError
        self.transaction_guid = str(uuid.uuid4())
        self._transaction_messages = []

    def finish_transaction(self):
        try:
            self._send_transaction_messages()
        finally:
            self._transaction_messages = None
            self.transaction_guid = None

    def _send_transaction_messages(self):
        messages = self._transaction_messages or []
        for envelope, exchange, routing_key in messages:
            if len(self._transaction_messages) > 1:
                envelope.setdefault('headers', {})
                envelope['headers']['transactionGUID'] = self.transaction_guid
                envelope['headers']['transactionMessageCount'] = len(
                    self._transaction_messages)
            self._produce(envelope, exchange, routing_key)

    def _capture_event(self, envelope, **kwargs):
        entity_guid = envelope.get('message', {}).get('guid')
        # Wrong rendered uid format workaround
        entity_guid = str(entity_guid) if entity_guid is not None else None
        if envelope.get('headers', {}).get('transactionGUID'):
            kwargs = {
                'transactionGUID': envelope.get(
                    'headers', {}).get('transactionGUID'),
                'transactionMessageCount': envelope.get('headers', {}).get(
                    'transactionMessageCount'), **kwargs}

        self._event_captor.capture(
            event='publishing',
            entity_type=envelope.get('message', {}).get('type'),
            entity_guid=entity_guid,
            **kwargs)


message_producer = MessageProducer(settings.RABBITMQ_URL, mdm_event_captor)


class InstanceHandler:
    _models_dispatch_cache: Dict[
        str, Dict[str, Dict[str, Union[str, Serializer]]]] = {}

    def __init__(self, instance, event_captor, producer):
        self._instance = instance
        self._event_captor = event_captor
        self._producer = producer

    def handle(self):
        if self.model_name not in self.models_dispatch:
            return

        logger.info('Handling ESB model %s...', self.model_name)
        try:
            envelope = self._envelope
        except Exception as error:  # noqa broad-except
            self._capture_event(success=False, error=error)
            return
        self._capture_event(success=True, error=None)
        self._produce(envelope)

    @property
    def models_dispatch(self):
        """
        Caching _models_config property by class name key and return it.
        Key with class name necessary for correct work in inheritance case
        with override _models_info property.
        We want to build it once and use forever, but building it on startup is
        redundant for other workers and tests
        """

        key = self.__class__.__name__
        if key not in self._models_dispatch_cache:
            self._models_dispatch_cache[key] = self._models_dispatch
        return self._models_dispatch_cache[key]

    @property
    def _models_dispatch(self):
        """
        Example of return value:
        ```{
            model: {
               'serializer': serializer,
               'exchange': exchange
           },
           ...
        }```
        """

        return {
            import_string(serializer).Meta.model.__name__: {
                'serializer': import_string(serializer),
                'exchange': exchange}
            for exchange, serializer in self.producers_setting.items()}

    @property
    def producers_setting(self):
        return settings.RABBITMQ_PRODUCES

    @property
    def _envelope(self):
        message = self._message
        return {
            'messageType': [f'urn:message:PIK.MDM.Messages:{message["type"]}'],
            'message': message,
            'host': self.host,
            'headers': self.headers}

    @cached_property  # to avoid 2nd serialization via _capture_event
    def _message(self):
        data = self._serializer(
            self._instance, context=self.serializer_context).data
        data = camelize(data, **api_settings.JSON_UNDERSCORIZE)
        if hasattr(self._serializer, 'camelization_hook'):
            return self._serializer.camelization_hook(data)
        return data

    @property
    def _serializer(self) -> type(Serializer):
        try:
            return self.models_dispatch[self.model_name]['serializer']
        except KeyError as exc:
            raise ModelMissingError from exc

    @property
    def model_name(self):
        return self._instance.__class__.__name__

    @property
    def serializer_context(self):  # noqa: no-self-use, is property
        return {'type_field_hook': camelcase_type_field_hook}

    @property
    def host(self):
        return {
            'machineName': platform.node(),
            'processId': os.getpid(),
            'frameworkVersion': django.get_version(),
            'operatingSystemVersion': (
                f'{platform.system()} {platform.version()}'),
            # TODO: why it`s methods of MDMCaptor?
            **self._event_captor.service_version,
            **self._event_captor.generator_version,
            **self._event_captor.lib_version}

    @property
    def headers(self):
        return {
            # TODO: why it`s methods of MDMCaptor?
            **self._event_captor.entities_version}

    def _produce(self, envelope):
        self._producer.produce(envelope, exchange=self._exchange)

    @property
    def _exchange(self):
        try:
            return self.models_dispatch[self.model_name]['exchange']
        except KeyError as exc:
            raise ModelMissingError from exc

    def _capture_event(self, **kwargs):
        try:
            _type = self._message['type']
            _guid = str(self._message['guid'])
        except Exception:  # noqa: exception already captured
            _type, _guid = None, None
        self._event_captor.capture(
            event='serialization',
            entity_type=_type,
            entity_guid=_guid,
            **kwargs
        )


@receiver(post_save)
def push_model_instance_to_rabbit_queue(instance, **kwargs):
    if not settings.RABBITMQ_PRODUCER_ENABLE:
        return
    # Ignoring migration signals
    if instance.__module__ == '__fake__':
        return
    try:
        InstanceHandler(instance, mdm_event_captor, message_producer).handle()
    except Exception as exc:  # noqa: broad-except
        capture_exception(exc)


class MDMTransaction(ContextDecorator):
    def __enter__(self):
        message_producer.start_transaction()

    def __exit__(self, exc_type, exc_value, traceback):
        message_producer.finish_transaction()
