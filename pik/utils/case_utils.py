import re
from collections import OrderedDict

from django.core.files import File
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_str
from django.utils.functional import Promise

from rest_framework.utils.serializer_helpers import ReturnDict


UNDERSOCREIZE_PATTERNS = [
    re.compile(r'(?<=[a-zA-Z_\d])(?=[A-Z])'),
    re.compile(r'(?<=[a-zA-Z_])(?=(\d+_|\d+$))')
]

CAMELIZE_RE = re.compile(r"[a-z0-9]?_[a-z0-9]")


def capitalize(match):
    group = match.group()
    if len(group) == 3:
        return group[0] + group[2].upper()
    return group[1].upper()


def underscore_to_camel(value: str) -> str:
    return re.sub(CAMELIZE_RE, capitalize, value)


def camelize(data, **options):
    # Handle lazy translated strings.
    ignore_fields = options.get("ignore_fields") or ()
    lower_camel_case = options.get("lower_camel_case", False)
    if isinstance(data, Promise):
        data = force_str(data)
    if isinstance(data, dict):
        if isinstance(data, ReturnDict):
            new_dict = ReturnDict(serializer=data.serializer)
        else:
            new_dict = OrderedDict()
        for key, value in data.items():
            if isinstance(key, Promise):
                key = force_str(key)
            if isinstance(key, str) and "_" in key:
                new_key = underscore_to_camel(key)
                if new_key and lower_camel_case:
                    new_key = f'{new_key[0].lower()}{new_key[1:]}'
            else:
                new_key = key
            if key not in ignore_fields and new_key not in ignore_fields:
                new_dict[new_key] = camelize(value, **options)
            else:
                new_dict[new_key] = value
        return new_dict
    if is_iterable(data) and not isinstance(data, str):
        return [camelize(item, **options) for item in data]
    return data


def camel_to_underscore(value: str) -> str:
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
        >>> camel_to_underscore('code1C')
        'code_1_c'
        >>> camel_to_underscore('code1c')
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
    for pattern in UNDERSOCREIZE_PATTERNS:
        value = re.sub(pattern, '_', value)
    return value.replace('-', '_').lower()


def _get_iterable(data):
    if isinstance(data, QueryDict):
        return data.lists()
    return data.items()


def underscorize(data, **options):
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
                new_dict[new_key] = underscorize(value, **options)
            else:
                new_dict[new_key] = value

        if isinstance(data, QueryDict):
            new_query = QueryDict(mutable=True)
            for key, value in new_dict.items():
                new_query.setlist(key, value)
            return new_query
        return new_dict
    if is_iterable(data) and not isinstance(data, (str, File)):
        return [underscorize(item, **options) for item in data]

    return data


def is_iterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    return True
