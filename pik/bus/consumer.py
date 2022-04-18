import io
import logging

from django.conf import settings
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from rest_framework.parsers import JSONParser
from djangorestframework_camel_case.util import underscoreize
from sentry_sdk import capture_exception
from pika import BlockingConnection, URLParameters
from pika.exceptions import AMQPConnectionError
from tenacity import retry, retry_if_exception_type, wait_fixed


logger = logging.getLogger(__name__)


class BusQueueNotFound(Exception):
    pass


def log_after_retry_connect(retry_state):
    logger.error(
        'Connecting to RabbitMQ. Attempt number: %s',
        retry_state.attempt_number)


class MessageConsumer:
    RECONNECT_WAIT = 1

    _consumer_name = None

    def __init__(self, connection_url, consumer_name, queues):
        self._consumer_name = consumer_name
        self.start_consume(connection_url, queues)

    @retry(
        wait=wait_fixed(RECONNECT_WAIT),
        retry=retry_if_exception_type(AMQPConnectionError),
        after=log_after_retry_connect,
    )
    def start_consume(self, connection_url, queues):
        channel = BlockingConnection(URLParameters(connection_url)).channel()
        for queue in queues:
            channel.basic_consume(
                on_message_callback=self.consume,
                queue=queue,
            )
        channel.start_consuming()

    def consume(self, channel, method, properties, body):
        try:
            queue_name = f'{self._consumer_name}.{method.exchange}'
            MessageHandler(body, queue_name).handle()
        except Exception as exc:  # noqa: board-except
            logger.exception(exc)
            capture_exception(exc)

        channel.basic_ack(delivery_tag=method.delivery_tag)


class MessageHandler:
    parser_class = JSONParser

    _data = None
    _serializer_class = None

    def __init__(self, message, queue):
        self._data = message
        self._queue = queue

    @cached_property
    def models_info(self):  # noqa: no-self-used
        """```{
            model: {
                'serializer': serializer,
                'queue': queue
            },
           ...
        }```"""
        return {
            import_string(serializer).Meta.model.__name__: {  # type: ignore
                'serializer': import_string(serializer),
                'queue': queue,
            }
            for queue, serializer
            in settings.RABBITMQ_CONSUMES.items()
        }

    @cached_property
    def serializer_class(self):
        for model_info in self.models_info.values():
            if model_info['queue'] == self._queue:
                return model_info['serializer']
        raise BusQueueNotFound()

    def fetch_message(self):
        self._data = io.BytesIO(self._data)  # drf parser accepts stream
        self._data = self.parser_class().parse(self._data)['message']

    def prepare_message(self):
        self._data = underscoreize(self._data)

        if hasattr(self._serializer_class, 'underscorize_hook'):
            self._data = self._serializer_class.underscorize_hook(self._data)

    @property
    def model(self):
        return self._serializer_class.Meta.model

    @property
    def queryset(self):
        return getattr(self.model, 'all_objects', self.model.objects)

    @property
    def instance(self):
        try:
            return self.queryset.get(uid=self._data.get('guid'))
        except self.model.DoesNotExist:
            return self.model(uid=self._data.get('guid'))

    def update_instance(self):
        serializer = self._serializer_class(self.instance, self._data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

    def handle(self):
        self.fetch_message()
        self.prepare_message()
        self.update_instance()
