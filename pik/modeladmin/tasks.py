from datetime import datetime
import logging

from django.core.cache import cache


LOCK_KEY = 'process_error_message_action_{action_id}'
PROGRESS_KEY = 'progress_{action_id}'
CACHE_TIMEOUT = 7 * 24 * 60 * 60

logger = logging.getLogger('celery')


class PIKMessageExceptionAction:
    _action_id = None

    def __init__(self, action_id):
        self._action_id = action_id

    def get_progress(self):
        default = {
            'started': None,
            'successful': 0,
            'failed': 0,
            'finished': None,
            'error': None}
        return cache.get(
            PROGRESS_KEY.format(action_id=self._action_id), default)

    def set_values(self, **kwargs):
        self._save({
            **self.get_progress(),
            **kwargs})

    def apply_message_status(self, success: bool):
        with cache.lock(LOCK_KEY.format(action_id=self._action_id)) as lock:
            lock.acquire(blocking=False)
            progress = self.get_progress()
            key = 'successful' if success else 'failed'
            progress[key] += 1
            self.set_values(**progress)
            if self._is_finished:
                self.set_values(finished=datetime.now())

    @property
    def _is_finished(self):
        progress = self.get_progress()
        return progress['total'] == progress['successful'] + progress['failed']

    def _save(self, progress):
        cache.set(
            key=PROGRESS_KEY.format(action_id=self._action_id),
            value=progress,
            timeout=CACHE_TIMEOUT)
