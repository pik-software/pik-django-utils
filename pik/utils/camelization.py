import re

from django.core.files import File
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict

PATTERNS = [
    # re.compile(r'([A-Z\d]+)([A-Z\d][a-z])'),
    # re.compile(r'([a-z])([A-Z\d])')
    re.compile(r'(?<=[a-zA-Z_\d])(?=[A-Z])'),
    re.compile(r'(?<=[a-zA-Z_])(?=(\d+_|\d+$))')
]


def camel_to_underscore(word: str) -> str:
    """
    Make an underscored, lowercase form from the expression in the string.

    Example::

        >>> camel_to_underscore('fullName')
        'full_name'
        >>> camel_to_underscore('FullName')
        'full_name'
        >>> camel_to_underscore('fullName1')
        'full_name_1'
        >>> camel_to_underscore('full123Name')
        'full_123_name'
        >>> camel_to_underscore('fullN1ame')
        'full_n1ame'
        >>> camel_to_underscore('full123N1ame')
        'full_123_n1ame'
        >>> camel_to_underscore('Code1C')
        'code_1_c'
        >>> camel_to_underscore('Code1с')
        'code1c'
        >>> camel_to_underscore('CodeOIDP')
        'code_o_i_d_p'
        >>> camel_to_underscore('CodeOIDP1')
        'code_o_i_d_p_1'
        >>> camel_to_underscore('OIDPCode')
        'o_i_d_p_code'
        >>> camel_to_underscore('code-oidp')
        'code_oidp'
        >>> camel_to_underscore('code-OIDP')
        'code_o_i_d_p'
        >>> camel_to_underscore('code-OIDP-1')
        'code_o_i_d_p_1'
        >>> camel_to_underscore('created_Gte')
        'created__gte'

    """
    for pattern in PATTERNS:
        word = re.sub(pattern, '_', word)
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
                new_data.setlist(
                    camel_to_underscore(key), data.getlist(key))
            return new_data
        for key, value in _get_iterable(data):
            if isinstance(key, str):
                new_key = camel_to_underscore(key)
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
