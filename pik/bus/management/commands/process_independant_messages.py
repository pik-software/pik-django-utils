import logging

from django.conf import settings
from django.utils.module_loading import import_string
from django.core.management.base import BaseCommand
from django.core.cache import cache
from tqdm import tqdm

from pik.bus.models import PIKMessageException
from pik.bus.mdm import mdm_event_captor
from pik.utils.sentry import capture_exception


LOCK_KEY = 'bus-process-independant-message'
LOCK_TIMEOUT = 7 * 24 * 60 * 60
CHUNK_SIZE = 2**10

logger = logging.getLogger(__name__)
handler_class = import_string(getattr(
    settings, 'RABBITMQ_MESSAGE_HANDLER_CLASS',
    'pik.bus.consumer.MessageHandler'))


class Command(BaseCommand):
    help = 'Processing independent PIKMessageException errors'

    def handle(self, *args, **options):
        try:
            self._run_process()
        except Exception as exc:  # noqa: broad-except
            capture_exception(exc)

    def _run_process(self):
        logger.info(self.help)
        lock = cache.lock(LOCK_KEY, timeout=LOCK_TIMEOUT)
        locked = lock.acquire(blocking=False)
        if not locked:
            logger.info('Lock is not released now.')
            return
        self._process()

    @staticmethod
    def _process():
        qs = PIKMessageException.objects.filter(has_dependencies=False)
        for obj in tqdm(qs.iterator(chunk_size=CHUNK_SIZE), total=qs.count()):
            handler_class(obj.message, obj.queue, mdm_event_captor).handle()
