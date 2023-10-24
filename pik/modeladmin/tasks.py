from datetime import datetime
import logging

from django.core.cache import cache


LOCK_KEY = 'pik_progress_lock_key_{progress_id}'
CACHE_KEY = 'pik_progress_cache_key_{progress_id}'
CACHE_TIMEOUT = 7 * 24 * 60 * 60

logger = logging.getLogger('celery')


class PIKProgressor:
    _progress_id = None

    default = {
        'started': None,
        'successful': 0,
        'failed': 0,
        'finished': None,
        'error': None}

    def __init__(self, progress_id):
        self._progress_id = progress_id

    def get_progress(self, default=None):
        return cache.get(
            CACHE_KEY.format(progress_id=self._progress_id), default)

    def set_values(self, **kwargs):
        progress = {}
        if kwargs.get('error') is not None:
            progress['finished'] = datetime.now()
        self._save({
            **self.get_progress(self.default),
            **kwargs,
            **progress})

    def apply_item_status(self, success: bool):
        with cache.lock(LOCK_KEY.format(progress_id=self._progress_id)):
            progress = self.get_progress(self.default)
            key = 'successful' if success else 'failed'
            progress[key] += 1
            is_finished = (
                progress['total'] ==
                progress['successful'] + progress['failed'])
            if is_finished:
                progress['finished'] = datetime.now()
            self.set_values(**progress)

    def _save(self, progress):
        cache.set(
            key=CACHE_KEY.format(progress_id=self._progress_id),
            value=progress,
            timeout=CACHE_TIMEOUT)
