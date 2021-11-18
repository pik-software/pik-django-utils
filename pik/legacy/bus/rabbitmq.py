from pika import BlockingConnection, URLParameters


class RabbitMQConnector:
    _connection = None
    _channel = None

    def __init__(self, connection_url):
        self._connection = BlockingConnection(URLParameters(connection_url))
        self._channel = self._connection.channel()

    def produce(self, queue_name, json_data):
        self._channel.queue_declare(queue=queue_name, durable=True)
        self._channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json_data)

    def consume(self, queue_name, callback):
        self._channel.queue_declare(queue=queue_name, durable=True)
        self._channel.basic_consume(
            on_message_callback=callback,
            queue=queue_name,
        )

        self._channel.start_consuming()

    def __del__(self):
        self._connection.close()
