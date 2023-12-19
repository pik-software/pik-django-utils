import asyncio
import logging

import django
from django.conf import settings
from django.core.management.base import BaseCommand
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

        if not self._consumer_enabled_settings:
            logger.warning('RABBITMQ_CONSUMER_ENABLE is set to False')
            # Do nothing to prevent the container from closing.
            self._do_nothing()
        logger.info('Starting worker for queues %s"', self.queues)
        self._run_consumer()

    @property
    def _consumer_enabled_settings(self):
        return getattr(settings, 'RABBITMQ_CONSUMER_ENABLE', False)

    @staticmethod
    def _do_nothing():
        loop = asyncio.get_event_loop()
        try:
            loop.run_forever()
        finally:
            loop.close()

    def _run_consumer(self):
        self._message_consumer(**self.get_consumer_kwargs()).consume()

    def get_consumer_kwargs(self, **kwargs):
        return {
            'connection_url': self.rabbitmq_url,
            'consumer_name': self.consumer_name,
            'queues': self.queues,
            'event_captor': self.event_captor,
            'message_handler': self._message_handler,
            **kwargs}

    @property
    def rabbitmq_url(self) -> str:
        return getattr(settings, 'RABBITMQ_URL', '')

    @property
    def consumer_name(self) -> str:
        return URLParameters(self.rabbitmq_url).credentials.username

    @property
    def queues(self) -> list:
        return list(self.consumes_setting.keys())

    @property
    def consumes_setting(self):
        return getattr(settings, 'RABBITMQ_CONSUMES', {})

    @property
    def event_captor(self):
        return mdm_event_captor
