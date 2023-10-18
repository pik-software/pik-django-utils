import logging
import time

from django.conf import settings
from django.utils.module_loading import import_string
from django.core.management.base import BaseCommand
from tqdm import tqdm

from pik.bus.models import PIKMessageExceptionAction as Action
from pik.bus.mdm import mdm_event_captor
from pik.utils.sentry import capture_exception


CHUNK_SIZE = 2**8
WAIT_TIME = 10

logger = logging.getLogger(__name__)
handler_class = import_string(getattr(
    settings, 'RABBITMQ_MESSAGE_HANDLER_CLASS',
    'pik.bus.consumer.MessageHandler'))


class Command(BaseCommand):
    help = 'Processing PIKMessageExceptionAction'

    def handle(self, *args, **options):
        try:
            self._run_process_loop()
        except Exception as exc:  # noqa: broad-except
            capture_exception(exc)

    def _run_process_loop(self):
        logger.info(self.help)
        while True:
            with Action.objects.all()[CHUNK_SIZE] as message_actions:
                if message_actions:
                    self._process_actions(message_actions)
                else:
                    time.sleep(WAIT_TIME)

    def _process_actions(self, qs):
        logger.info('Processing %s PIKMessageExceptionAction:', qs.count())
        for message_action in tqdm(qs, total=qs.count()):
            if message_action.action == Action.PROCESS:
                self._process_message(message_action.pik_message_exception)
            if message_action.action == Action.DELETE:
                self._delete_message(message_action.pik_message_exception)
            message_action.delete()

    @staticmethod
    def _process_message(pik_message_exception):
        handler_class(
            pik_message_exception.message, pik_message_exception.queue,
            mdm_event_captor).handle()

    @staticmethod
    def _delete_message(pik_message_exception):
        pik_message_exception.delete()
