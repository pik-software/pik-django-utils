import io
import logging

from rest_framework.parsers import JSONParser
from djangorestframework_camel_case.util import underscoreize
from sentry_sdk import capture_exception
from pika import BlockingConnection, URLParameters
from pika.exceptions import AMQPConnectionError
from tenacity import retry, retry_if_exception_type, wait_fixed

from pik.bus.mixins import ModelSerializerMixin


logger = logging.getLogger(__name__)


class BusQueueNotFound(Exception):
    pass


def log_after_retry_connect(retry_state):
    logger.error(
        'Connecting to RabbitMQ. Attempt number: %s',
        retry_state.attempt_number)


class MessageConsume:
    RECONNECT_WAIT = 1

    _queue = None

    def __init__(self, connection_url, queue):
        self._queue = queue
        self.start_consume(connection_url, queue)

    @retry(
        wait=wait_fixed(RECONNECT_WAIT),
        retry=retry_if_exception_type(AMQPConnectionError),
        after=log_after_retry_connect,
    )
    def start_consume(self, connection_url, queue):
        channel = BlockingConnection(URLParameters(connection_url)).channel()
        channel.basic_consume(
            on_message_callback=self.consume,
            queue=queue,
        )
        channel.start_consuming()

    def consume(self, channel, method, properties, body):
        try:
            MessageHandler(body, self._queue).handle()
        except Exception as exc:  # noqa: board-except
            logger.exception(exc)
            capture_exception(exc)

        channel.basic_ack(delivery_tag=method.delivery_tag)


class MessageHandler(ModelSerializerMixin):
    parser_class = JSONParser

    _data = None
    _serializer_class = None

    def __init__(self, message, queue):
        self._data = message
        self._serializer_class = self.get_serializer(queue)

    def get_serializer(self, queue):
        for serializer_exchange in self.MODEL_SERIALIZER.values():
            if serializer_exchange[self.QUEUE_OR_EXCHANGE_OFFSET] == queue:
                return serializer_exchange[self.SERIALIZER_OFFSET]
        raise BusQueueNotFound()

    def fetch_message(self):
        self._data = io.BytesIO(self._data)  # drf parser accepts stream
        self._data = self.parser_class().parse(self._data)['message']

    def prepare_message(self):
        self._data = underscoreize(self._data)

        if hasattr(self._serializer_class, 'underscorize_hook'):
            self._data = self._serializer_class.underscorize_hook(self._data)

    def get_model(self):
        return self._serializer_class.Meta.model

    @staticmethod
    def get_qs(model):
        return getattr(model, 'all_objects', model.objects)

    def get_instance(self):
        model = self.get_model()
        qs = self.get_qs(model)

        try:
            return qs.get(uid=self._data.get('guid'))
        except model.DoesNotExist:
            return model(uid=self._data.get('guid'))

    def update_instance(self):
        instance = self.get_instance()
        self._serializer_class().update(instance, self._data)

    def handle(self):
        self.fetch_message()
        self.prepare_message()
        self.update_instance()
