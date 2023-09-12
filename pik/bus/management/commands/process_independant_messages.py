import logging

from django.conf import settings
from django.utils.module_loading import import_string
from django.core.management.base import BaseCommand
from django.core.cache import cache
from tqdm import tqdm

from pik.bus.models import PIKMessageException
from pik.bus.mdm import mdm_event_captor
from pik.utils.sentry import capture_exception


CHUNK_SIZE = 2**10
LOCK_ID = 'process-independant-message'
LOCK_TIMEOUT = 60 * 60

logger = logging.getLogger(__name__)
handler_class = import_string(getattr(
    settings, 'RABBITMQ_MESSAGE_HANDLER_CLASS',
    'pik.bus.consumer.MessageHandler'))


class Command(BaseCommand):
    help = 'Processing independent PIKMessageException errors'

    def handle(self, *args, **options):
        logger.info(self.help)
        qs = PIKMessageException.objects.filter(has_dependencies=False)
        try:
            lock = cache.lock(f'bus-{LOCK_ID}', timeout=LOCK_TIMEOUT)
            with lock:
                with tqdm(total=qs.count()) as pbar:
                    for obj in qs.iterator(chunk_size=CHUNK_SIZE):
                        handler = handler_class(
                            obj.message, obj.queue, mdm_event_captor)
                        handler.handle()
                        pbar.update(1)

        except Exception as exc:  # noqa: broad-except
            capture_exception(exc)
