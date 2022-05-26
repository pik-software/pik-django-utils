import io
import logging
from functools import partial
from hashlib import sha1

from django.conf import settings
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from rest_framework.parsers import JSONParser
from sentry_sdk import capture_exception
from pika import BlockingConnection, URLParameters
from pika.exceptions import AMQPConnectionError
from tenacity import retry, retry_if_exception_type, wait_fixed
from pik.utils.case_utils import underscoreize

from pik.api.exceptions import extract_exception_data
from pik.core.shortcuts import update_or_create_object

logger = logging.getLogger(__name__)


class BusQueueNotFound(Exception):
    pass


def log_after_retry_connect(retry_state):
    logger.error(
        'Connecting to RabbitMQ. Attempt number: %s',
        retry_state.attempt_number)


class MessageConsumer:
    RECONNECT_WAIT = 1
    PREFETCH_COUNT = 1

    _consumer_name = None
    _connection_url = None
    _queues = None
    _channel = None

    def __init__(self, connection_url, consumer_name, queues):
        self._consumer_name = consumer_name
        self._connection_url = connection_url
        self._queues = queues

    def consume(self):
        self._connect()
        self._config_channel()
        self._bind_queues()
        self._channel.start_consuming()

    @retry(
        wait=wait_fixed(RECONNECT_WAIT),
        retry=retry_if_exception_type(AMQPConnectionError),
        after=log_after_retry_connect)
    def _connect(self):
        self._channel = BlockingConnection(URLParameters(
            self._connection_url)).channel()

    def _config_channel(self):
        self._channel.basic_qos(prefetch_count=self.PREFETCH_COUNT)

    def _bind_queues(self):
        for queue in self._queues:
            self._channel.basic_consume(
                on_message_callback=partial(self._handle_message, queue=queue),
                queue=queue)

    @staticmethod
    def _handle_message(channel, method, properties, body, queue):
        try:
            MessageHandler(body, queue).handle()
        except Exception as exc:  # noqa: too-broad-except
            capture_exception(exc)
            channel.basic_nack(delivery_tag=method.delivery_tag)
        else:
            channel.basic_ack(delivery_tag=method.delivery_tag)


class QueueSerializerMissingExcpetion(Exception):
    pass


class MessageHandler:
    parser_class = JSONParser

    _payload = None
    _parsed_payload = None
    _message = None
    _queue = None
    _serializers = None
    exc_data = None

    def __init__(self, message, queue):
        self._message = message
        self._queue = queue

    def handle(self):
        try:
            self._fetch_payload()
            self._prepare_payload()
            self._update_instance()
            self._process_dependants()
            return True
        except Exception as exc:  # noqa: broad-except
            self._capture_exception(exc)
            return False

    def _fetch_payload(self):
        self._payload = self.parser_class().parse(
            io.BytesIO(self._message))['message']

    def _prepare_payload(self):
        self._payload = underscoreize(self._payload)

        if hasattr(self._serializer_class, 'underscorize_hook'):
            self._payload = self._serializer_class.underscorize_hook(
                self._payload)

    def _update_instance(self):
        self._serializer.is_valid(raise_exception=True)
        self._serializer.save()

    @cached_property
    def _serializer(self):
        return self._serializer_class(self._instance, self._payload)

    @cached_property
    def _instance(self):
        try:
            return self._queryset.get(uid=self._payload['guid'])
        except self._model.DoesNotExist:
            return self._model(uid=self._payload['guid'])

    @property
    def _model(self):
        return self._serializer_class.Meta.model

    @property
    def _queryset(self):
        return getattr(self._model, 'all_objects', self._model.objects)

    @property
    def _serializer_class(self):
        return self._get_serializer(self._queue)

    @classmethod
    def _get_serializer(cls, queue):
        """
            Queue name to serializer mapping dict `{queue:  serializer, ... }`

            We want to build it once and use forever, but building it on
                startup is redundant for other workers and tests
        """
        if cls._serializers is None:
            cls._serializers = {
                queue: import_string(serializer)
                for queue, serializer in settings.RABBITMQ_CONSUMES.items()
            }
        if not cls._serializers or queue not in cls._serializers:  # noqa: unsupported-membership-test
            raise QueueSerializerMissingExcpetion(
                f'Unable to find serializer for {queue}')
        return cls._serializers[queue]  # noqa: unsupported-membership-test

    def _process_dependants(self):
        from .models import PIKMessageException  # noqa: cyclic import workaround
        dependants = PIKMessageException.objects.filter(**{
            f'dependencies__{self._payload["type"]}': self._payload["guid"]})
        for dependant in dependants:
            self.__class__(dependant.message, dependant.queue).handle()
            dependant.delete()

    def _capture_exception(self, exc):
        from .models import PIKMessageException  # noqa: cyclic import workaround
        logger.info(exc)
        capture_exception(exc)
        self.exc_data = extract_exception_data(exc)

        if not isinstance(self._payload, dict) or 'guid' not in self._payload:
            uid = sha1(self._message).hexdigest()[:32]
            update_or_create_object(
                PIKMessageException, search_keys={
                    'queue': self._queue,
                    'uid': uid},
                uid=uid, queue=self._queue, message=self._message,
                exception=extract_exception_data(exc),
                exception_message=self.exc_data['message'],
                exception_type=self.exc_data['code']
            )
            return

        dependencies = {
            self._payload[field]['type']: self._payload[field]['guid']
            for field, errors in self.exc_data.get('detail', {}).items()
            for error in errors
            if error['code'] == 'does_not_exist'}

        update_or_create_object(
            PIKMessageException, search_keys={
                'entity_uid': self._payload.get('guid'),
                'queue': self._queue},
            exception_type=self.exc_data['code'],
            exception_message=self.exc_data['message'],
            entity_uid=self._payload.get('guid'),
            message=self._message, exception=self.exc_data, queue=self._queue,
            dependencies=dependencies
        )
