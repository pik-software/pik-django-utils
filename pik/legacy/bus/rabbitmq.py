from pika import BlockingConnection, URLParameters, exceptions
from sentry_sdk import capture_exception


class RabbitMQConnector(object):
    __instance = None
    _connection_url = None
    _connection = None
    _channel = None

    def __new__(cls, connection_url):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._connection_url = connection_url
            cls._connect(cls.__instance)
        return cls.__instance

    def _connect(self):
        self._connection = BlockingConnection(
            URLParameters(self._connection_url))
        self._channel = self._connection.channel()

    def _disconnect(self):
        if self._connection and not self._connection.is_closed:
            try:
                self._connection.close()
            except (
                    exceptions.StreamLostError, exceptions.ConnectionClosed,
                    ConnectionError):
                pass

        self._connection = None
        self._channel = None

    def produce(self, queue_name, json_data):
        try:
            self._produce(queue_name, json_data)
        except (exceptions.AMQPError, exceptions.ChannelError,
                exceptions.ReentrancyError):
            self._disconnect()
            self._connect()

            try:
                self._produce(queue_name, json_data)
            except (exceptions.AMQPError, exceptions.ChannelError,
                    exceptions.ReentrancyError) as exc:
                capture_exception(exc)

    def _produce(self, queue_name, json_data):
        self._channel.queue_declare(queue=queue_name, durable=True)
        self._channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json_data)

    def consume(self, queue_name, callback):
        self._channel.basic_consume(
            on_message_callback=callback,
            queue=queue_name,
        )

        self._channel.start_consuming()

    def __del__(self):
        self._connection.close()
