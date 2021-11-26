import io

from rest_framework.parsers import JSONParser
from djangorestframework_camel_case.util import underscoreize
from sentry_sdk import capture_exception
from pika import BlockingConnection, URLParameters

from .mixins import ModelSerializerMixin


class MessageConsume(ModelSerializerMixin):
    parser_class = JSONParser

    def __init__(self, connection_url, queue):
        channel = BlockingConnection(URLParameters(connection_url)).channel()
        channel.queue_declare(queue=queue, durable=True)
        channel.basic_consume(
            on_message_callback=self.consume,
            queue=queue,
        )
        channel.start_consuming()

    def consume(self, channel, method, properties, body):
        try:
            self.apply_payload(
                self.prepare_payload(
                    self.get_message_payload(body)),
                method.routing_key)
        except Exception as exc:  # noqa: board-except
            import traceback
            print(traceback.format_exc())
            capture_exception(exc)

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def get_message_payload(self, message):
        message = io.BytesIO(message)  # drf parser accepts stream
        return self.parser_class().parse(message)['message']

    @staticmethod
    def prepare_payload(payload):
        return underscoreize(payload)

    @staticmethod
    def apply_payload(payload, queue):
        serializer_class = MessageConsume.MODEL_SERIALIZER[queue]

        if hasattr(serializer_class, 'underscorize_hook'):
            payload = serializer_class.underscorize_hook(payload)

        model = serializer_class.Meta.model
        qs = getattr(model, 'all_objects', model.objects)
        try:
            instance = qs.get(uid=payload.get('guid'))
        except model.DoesNotExist:
            instance = model(uid=payload.get('guid'))

        serializer_class().update(instance, payload)
