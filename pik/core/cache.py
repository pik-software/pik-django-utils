from inspect import getfullargspec
from functools import wraps
from typing import Any, Callable

from django.core.cache import caches


def cachedmethod(key: str, ttl: int = 5 * 60, cachename: str = 'default') \
        -> Callable:
    """
    Method result caching decorator

    Args:
        :param key: Template used to generate key with arguments
        :param ttl: cache ttl
        :param cachename: Name on django cache backend
        :return: value

    Examples:

        Keyword argument call:

            >>> @cachedmethod("keyword_{arg}")
            ... def calculate(arg: int) -> int:
            ...     return arg * 2
            >>> caches['default'].set('keyword_2', 10)
            True
            >>> calculate(arg=2)
            10

        Positional argument call:

            >>> @cachedmethod("positional_{a}")
            ... def calculate(a: int) -> int:
            ...     return a * 3
            >>> calculate(4)
            12
            >>> caches['default'].get('positional_4')
            12

        Default value call:

            >>> @cachedmethod("default_{b}_{c}")
            ... def calculate(a: int = 1, b: int = 3, c: int = 15) -> int:
            ...     return a + b * c
            >>> calculate()
            46
            >>> caches['default'].get('default_3_15')
            46
            >>> calculate(a=10000)
            46
            >>> calculate(10000)
            46
            >>> calculate(10000, b=3)
            46
            >>> calculate(a=10000, b=3)
            46
            >>> calculate(c=15, b=3, a=10000)
            46
            >>> calculate(**{'a': 1000})
            46
            >>> calculate(1000, a=2000)
            Traceback (most recent call last):
            ...
            TypeError: calculate() got multiple values for some argument

        Override ttl:

            >>> @cachedmethod("ttled_{a}_{b}_{c}", ttl=10*60)
            ... def calculate(a: int, b: int, c: int) -> int:
            ...     return a + b + c
            >>> calculate(1, 2, 3)
            6
            >>> calculate(1, 2, c=3)
            6

        Override cache:

            >>> @cachedmethod("othercache_{foo}", cachename="default")
            ... def calculate(foo: str) -> str:
            ...     return foo * 2
            >>> calculate('foo')
            'foofoo'

    """

    cache = caches[cachename]

    def wrapper(method: Callable) -> Callable:
        spec = getfullargspec(method)
        spec_keys = spec.defaults or ()
        defaults = dict(zip(spec.args[-len(spec_keys):], spec_keys))

        @wraps(method)
        def decorator(*args, **kwargs) -> Any:
            positional = dict(zip(spec.args, args))
            if set(positional) & set(kwargs):
                msg = '{name}() got multiple values for some argument'.format(
                    name=method.__name__)
                raise TypeError(msg)
            merged_kwargs = {**defaults, **positional, **kwargs}
            cachekey = key.format(**merged_kwargs)
            value = cache.get(cachekey)
            if value is None:
                value = method(*args, **kwargs)
                cache.set(cachekey, value, ttl)
            return value
        return decorator
    return wrapper
