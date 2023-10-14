import functools
import hashlib

from django.core.cache import cache
from django.utils.encoding import force_bytes


def lock_decorator(key_maker=None):
    """
    When you want to lock a function from more than 1 call at a time.
    https://www.peterbe.com/plog/django-lock-decorator-with-django-redis
    """

    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            if key_maker:
                key = key_maker(*args, **kwargs)
            else:
                key = str(args) + str(kwargs)
            lock_key = hashlib.md5(force_bytes(key)).hexdigest()
            with cache.lock(lock_key):
                return func(*args, **kwargs)

        return inner

    return decorator


def skip_locked(lock_name):
    lock = cache.lock(lock_name)

    def decorator(method):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            if not lock.acquire(blocking=False):
                return None
            try:
                return method(*args, **kwargs)
            finally:
                lock.release()
        return wrapper
    return decorator
