import re

from django.core.files import File
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict

PATTERNS = [
    re.compile(r'([A-Z\d]+)([A-Z\d][a-z])'),
    re.compile(r'([a-z])([A-Z\d])')
]


def underscore(word: str) -> str:
    """
    Make an underscored, lowercase form from the expression in the string.

    Example::

        >>> underscore('fullName')
        'full_name'
        >>> underscore('FullName')
        'full_name'
        >>> underscore('fullName1')
        'full_name_1'
        >>> underscore('full123Name')
        'full_123_name'
        >>> underscore('fullN1ame')
        'full_n_1ame'
        >>> underscore('full123N1ame')
        'full_123n_1ame'
        >>> underscore('Code1C')
        'code_1c'
        >>> underscore('CodeOIDP')
        'code_oidp'
        >>> underscore('CodeOIDP1')
        'code_oidp1'
        >>> underscore('OIDPCode')
        'oidp_code'
        >>> underscore('code-oidp')
        'code_oidp'
        >>> underscore('code-OIDP')
        'code_oidp'
        >>> underscore('code-OIDP-1')
        'code_oidp_1'

    """
    for pattern in PATTERNS:
        word = re.sub(pattern, r'\1_\2', word)
    return word.replace('-', '_').lower()


def _get_iterable(data):
    if isinstance(data, QueryDict):
        return data.lists()
    return data.items()


def underscoreize(data, **options):
    ignore_fields = options.get("ignore_fields") or ()
    if isinstance(data, dict):
        new_dict = {}
        if isinstance(data, MultiValueDict):
            new_data = MultiValueDict()
            for key, value in data.items():
                new_data.setlist(underscore(key, **options), data.getlist(key))
            return new_data
        for key, value in _get_iterable(data):
            if isinstance(key, str):
                new_key = underscore(key, **options)
            else:
                new_key = key

            if key not in ignore_fields and new_key not in ignore_fields:
                new_dict[new_key] = underscoreize(value, **options)
            else:
                new_dict[new_key] = value

        if isinstance(data, QueryDict):
            new_query = QueryDict(mutable=True)
            for key, value in new_dict.items():
                new_query.setlist(key, value)
            return new_query
        return new_dict
    if is_iterable(data) and not isinstance(data, (str, File)):
        return [underscoreize(item, **options) for item in data]

    return data


def is_iterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    else:
        return True
