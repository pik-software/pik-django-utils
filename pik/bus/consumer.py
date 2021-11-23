import io
from pydoc import locate

from django.conf import settings
from rest_framework.parsers import JSONParser
from djangorestframework_camel_case.util import underscoreize
from sentry_sdk import capture_exception
from pika import BlockingConnection, URLParameters


MODEL_SERIALIZER = {
    serializer.split('.')[-1].replace('Serializer', ''): locate(serializer)
    for serializer in settings.RABBITMQ_SERIALIZERS
}


class QueueItemProcessor:
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
                    self.get_item_payload(body)),
                method.routing_key)
        except Exception as exc:  # noqa: board-except
            # TODO: add item to death letter queue?
            capture_exception(exc)

        channel.basic_ack(delivery_tag=method.delivery_tag)

    @staticmethod
    def get_item_payload(body):
        return JSONParser().parse(io.BytesIO(body))['message']

    @staticmethod
    def prepare_payload(payload):
        payload = underscoreize(payload)
        payload['uid'] = payload.pop('guid')
        return payload

    @staticmethod
    def apply_payload(payload, queue):
        serializer_class = MODEL_SERIALIZER[queue]

        if hasattr(serializer_class, 'underscorize_hook'):
            payload = serializer_class.underscorize_hook(payload)

        model = serializer_class.Meta.model
        try:
            # TODO: to for method all_objects
            instance = model.objects.get(uid=payload.get('guid'))
        except model.DoesNotExist:
            instance = model(uid=payload.get('guid'))

        serializer_class().update(instance, payload)
