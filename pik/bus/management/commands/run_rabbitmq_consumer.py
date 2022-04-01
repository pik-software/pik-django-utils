import logging
import asyncio
import django
from django.conf import settings
from django.core.management.base import BaseCommand
from pik.bus.consumer import MessageConsumer


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Starts worker, which consumes messages from rabbitmq queue.'

    @staticmethod
    def _do_nothing():
        loop = asyncio.get_event_loop()
        try:
            loop.run_forever()
        finally:
            loop.close()

    def handle(self, *args, **options):
        django.setup()

        if not settings.RABBITMQ_CONSUMER_ENABLE:
            logger.warning('RABBITMQ_CONSUMER_ENABLE is set to False')
            # Do nothing to prevent the container from closing.
            self._do_nothing()

        consumer_name = settings.RABBITMQ_ACCOUNT_NAME
        queues = list(settings.RABBITMQ_CONSUMES.keys())
        logger.info('Starting worker for queues %s"', queues)
        MessageConsumer(settings.RABBITMQ_URL, consumer_name, queues)
