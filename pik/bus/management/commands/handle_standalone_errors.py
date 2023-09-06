import logging

from django.conf import settings
from django.utils.module_loading import import_string
from django.core.management.base import BaseCommand

from pik.bus.models import PIKMessageException
from pik.bus.mdm import mdm_event_captor
from pik.utils.sentry import capture_exception


CHUNK_SIZE = 2**10

logger = logging.getLogger(__name__)
handler_class = import_string(getattr(
    settings, 'RABBITMQ_MESSAGE_HANDLER_CLASS',
    'pik.bus.consumer.MessageHandler'))


class Command(BaseCommand):
    help = 'Attempt to handle PIKMessageException errors without dependencies'

    def handle(self, *args, **options):
        logger.info(self.help)
        qs = PIKMessageException.objects.filter(has_dependencies=False)
        try:
            for obj in qs.iterator(chunk_size=CHUNK_SIZE):
                handler = handler_class(
                    obj.message, obj.queue, mdm_event_captor)
                handler.handle()
        except Exception as exc:  # noqa: broad-except
            capture_exception(exc)
