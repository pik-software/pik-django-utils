from pika import BlockingConnection, URLParameters, exceptions
from sentry_sdk import capture_exception


class RabbitMQConnector:
    __instance = None
    __connection_url = None
    _connection = None
    _channel = None

    def __new__(cls, connection_url):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__connection_url = connection_url
            cls._connect()
        return cls.__instance

    @classmethod
    def _connect(cls):
        cls._connection = BlockingConnection(
            URLParameters(cls.__connection_url))
        cls._channel = cls._connection.channel()

    @classmethod
    def _disconnect(cls):
        if cls._connection and not cls._connection.is_closed:
            try:
                cls._connection.close()
            except (
                    exceptions.StreamLostError, exceptions.ConnectionClosed,
                    ConnectionError):
                pass

        cls._connection = None
        cls._channel = None

    @classmethod
    def produce(cls, queue_name, json_data):
        try:
            cls._produce(queue_name, json_data)
        except (exceptions.AMQPError, exceptions.ChannelError,
                exceptions.ReentrancyError, exceptions.StreamLostError,
                exceptions.ConnectionClosed, ConnectionError):
            cls._disconnect()
            cls._connect()

            try:
                cls._produce(queue_name, json_data)
            except (exceptions.AMQPError, exceptions.ChannelError,
                    exceptions.ReentrancyError) as exc:
                capture_exception(exc)

    @classmethod
    def _produce(cls, queue_name, json_data):
        cls._channel.queue_declare(queue=queue_name, durable=True)
        cls._channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json_data)

    @classmethod
    def consume(cls, queue_name, callback):
        cls._channel.queue_declare(queue=queue_name, durable=True)
        cls._channel.basic_consume(
            on_message_callback=callback,
            queue=queue_name,
        )

        cls._channel.start_consuming()
