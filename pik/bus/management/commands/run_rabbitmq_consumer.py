import asyncio
import logging

import django
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.functional import cached_property
from pika import URLParameters

from pik.bus.consumer import MessageConsumer, MessageHandler
from pik.bus.mdm import mdm_event_captor


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Starts worker, which consumes messages from rabbitmq queue.'
    _message_consumer = MessageConsumer
    _message_handler = MessageHandler

    def handle(self, *args, **options):
        django.setup()

        if not self._is_rabbitmq_enabled:
            logger.warning('RABBITMQ_CONSUMER_ENABLE is set to False')
            # Do nothing to prevent the container from closing.
            self._do_nothing()
        logger.info('Starting worker for queues %s"', self.queues)
        self._run_consumer()

    def get_consumer_kwargs(self, **kwargs):
        return {
            'connection_url': self.rabbitmq_url,
            'consumer_name': self.consumer_name,
            'queues': self.queues,
            'event_captor': self.event_captor,
            'message_handler': self._message_handler,
            **kwargs}

    def _run_consumer(self):
        self._message_consumer(**self.get_consumer_kwargs()).consume()

    @property
    def _is_rabbitmq_enabled(self):
        return settings.RABBITMQ_CONSUMER_ENABLE

    @staticmethod
    def _do_nothing():
        loop = asyncio.get_event_loop()
        try:
            loop.run_forever()
        finally:
            loop.close()

    @property
    def rabbitmq_url(self) -> str:
        return settings.RABBITMQ_URL

    @property
    def consumer_name(self) -> str:
        return URLParameters(settings.RABBITMQ_URL).credentials.username

    # @cached_property
    @property
    def queues(self) -> list:
        return list(settings.RABBITMQ_CONSUMES.keys())

    @property
    def event_captor(self):
        return mdm_event_captor
