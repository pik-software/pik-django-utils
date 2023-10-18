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

    def _process_actions(self, message_actions):
        logger.info('Processing %s error messages:', message_actions.count())
        strategies = {
            Action.PROCESS: self._process_message,
            Action.DELETE: self._delete_message}
        for message_action in tqdm(message_actions):
            strategy = strategies.get(
                message_action.action, self._pass_message)
            strategy(message_action)

    @staticmethod
    def _pass_message(message_action):
        logger.warning(
            '%s PIKMessageExceptionAction is passed', message_action.uid)

    @staticmethod
    def _process_message(message_action):
        handler_class(
            message_action.message.message, message_action.message.queue,
            mdm_event_captor).handle()
        message_action.delete()

    @staticmethod
    def _delete_message(message_action):
        message_action.message.delete()
        message_action.delete()
