from datetime import datetime

from django.core.cache import cache


PROGRESS_KEY = 'progress_{task_id}'


def get_progress(task_id):
    return cache.get(PROGRESS_KEY.format(task_id=task_id))


def register_progress(task_id, **kwargs):
    progress_defaults = {
        'started': datetime.now(),
        'current': 0,
        'success': 0,
        'fail': 0,
        'total': 0,
        'error': None
    }
    print(task_id, kwargs)
    cache.set(PROGRESS_KEY.format(task_id=task_id), {
        **progress_defaults, **kwargs}, timeout=7 * 24 * 60 * 60)
