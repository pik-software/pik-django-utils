import re
from collections import OrderedDict

from django.utils.encoding import force_text
from django.utils.functional import Promise, cached_property
from rest_framework.utils.serializer_helpers import ReturnDict

from .consts import (
    TO_DEPRECATED_FIELD_RULES, TO_ACTUAL_FIELD_RULES,
    TO_ACTUAL_ORDERING_RULES, TO_DEPRECATED_ORDERING_RULES,
    TO_DEPRECATED_FILTER_RULES, TO_ACTUAL_FILTER_RULES, )


def replace_keys(field, replacer, **kwargs):
    """
    >>> replace_keys('version', KeysReplacer(TO_DEPRECATED_FIELD_RULES))
    '_version'
    >>> replace_keys('type', KeysReplacer(TO_DEPRECATED_FIELD_RULES))
    '_type'
    >>> replace_keys('guid', KeysReplacer(TO_DEPRECATED_FIELD_RULES))
    '_uid'
    >>> replace_keys('foo', KeysReplacer(TO_DEPRECATED_FIELD_RULES))
    'foo'

    >>> replace_keys('_uid', KeysReplacer(TO_ACTUAL_FIELD_RULES))
    'guid'
    >>> replace_keys('_type', KeysReplacer(TO_ACTUAL_FIELD_RULES))
    'type'
    >>> replace_keys('_version', KeysReplacer(TO_ACTUAL_FIELD_RULES))
    'version'
    >>> replace_keys('foo', KeysReplacer(TO_ACTUAL_FIELD_RULES))
    'foo'

    """
    if isinstance(field, str):
        return replacer.replace(field)
    return field



def replace_struct_keys(data, **options):  # noqa: Too many branches
    """
    Replaces `guid` with keys with `_uid`

    >>> replace_struct_keys( \
        {'guid': 1, 'type': 2}, replacer=to_deprecated_fields)
    OrderedDict([('_uid', 1), ('_type', 2)])
    >>> replace_struct_keys( \
        {'guid': {'guid': 1}}, replacer=to_deprecated_fields)
    OrderedDict([('_uid', OrderedDict([('_uid', 1)]))])
    >>> replace_struct_keys({'guid': 'foo'}, replacer=to_deprecated_fields)
    OrderedDict([('_uid', 'foo')])
    >>> replace_struct_keys(['guid', 'foo'], replacer=to_deprecated_fields)
    ['_uid', 'foo']
    >>> replace_struct_keys(('guid', 'foo'), replacer=to_deprecated_fields)
    ['_uid', 'foo']
    >>> replace_struct_keys('guid', replacer=to_deprecated_fields)
    '_uid'

    >>> replace_struct_keys({'foo': 'bar'}, replacer=to_deprecated_fields)
    OrderedDict([('foo', 'bar')])
    >>> replace_struct_keys({'foo': 'bar'}, replacer=to_deprecated_fields)
    OrderedDict([('foo', 'bar')])
    >>> replace_struct_keys(['foo', 'bar'], replacer=to_deprecated_fields)
    ['foo', 'bar']
    >>> replace_struct_keys(('foo', 'bar'), replacer=to_deprecated_fields)
    ['foo', 'bar']
    >>> replace_struct_keys('foo', replacer=to_deprecated_fields)
    'foo'

    >>> replace_struct_keys({'_uid': 'foo'}, replacer=to_actual_fields)
    OrderedDict([('guid', 'foo')])
    >>> replace_struct_keys(['_uid', 'foo'], replacer=to_actual_fields)
    ['guid', 'foo']
    >>> replace_struct_keys(('_uid', 'foo'), replacer=to_actual_fields)
    ['guid', 'foo']
    >>> replace_struct_keys('_uid', replacer=to_actual_fields)
    'guid'

    >>> replace_struct_keys({'foo': 'bar'}, replacer=to_actual_fields)
    OrderedDict([('foo', 'bar')])
    >>> replace_struct_keys({'foo': 'bar'}, replacer=to_actual_fields)
    OrderedDict([('foo', 'bar')])
    >>> replace_struct_keys(['foo', 'bar'], replacer=to_actual_fields)
    ['foo', 'bar']
    >>> replace_struct_keys(('foo', 'bar'), replacer=to_actual_fields)
    ['foo', 'bar']
    >>> replace_struct_keys('foo', replacer=to_actual_fields)
    'foo'

    >>> replace_struct_keys('some__uid', replacer=to_actual_filters)
    'some__guid'
    """
    ignore_fields = options.get("ignore_fields") or ()

    if isinstance(data, Promise):
        data = force_text(data)
    if isinstance(data, dict):
        if isinstance(data, ReturnDict):
            new_dict = ReturnDict(serializer=data.serializer)
        else:
            new_dict = OrderedDict()
        for key, value in data.items():
            if isinstance(key, Promise):
                key = force_text(key)
            new_key = replace_keys(key, **options)
            if key not in ignore_fields and new_key not in ignore_fields:
                new_dict[new_key] = replace_struct_keys(value, **options)
            else:
                new_dict[new_key] = value
        return new_dict
    if isinstance(data, str):
        return replace_keys(data, **options)
    if isinstance(data, (list, tuple)):
        return [replace_struct_keys(item, **options) for item in data]
    return data


class KeysReplacer:
    """ Rules based field/key replacer

    >>> replacer = KeysReplacer(rules={'foo': 'bar'})

    >>> replacer.replace('foo')
    'bar'
    >>> replacer.replace(' foo')
    ' bar'
    >>> replacer.replace('foo ')
    'bar '
    >>> replacer.replace('_foo')
    '_foo'
    >>> replacer.replace('__foo')
    '__bar'

    >>> replacer.replace('{foo}')
    '{bar}'
    >>> replacer.replace('{ foo }')
    '{ bar }'
    >>> replacer.replace('{foo,bar}')
    '{bar,bar}'
    >>> replacer.replace('{foo, bar}')
    '{bar, bar}'
    >>> replacer.replace('{ foo, bar }')
    '{ bar, bar }'
    >>> replacer.replace('{ foo,  bar }')
    '{ bar,  bar }'

    >>> replacer.replace('foo=')
    'bar='
    >>> replacer.replace('foo__in=')
    'bar__in='
    >>> replacer.replace('foo__foo=')
    'bar__bar='
    >>> replacer.replace('foo__lower__in=')
    'bar__lower__in='
    >>> replacer.replace('foo!=')
    'bar!='
    >>> replacer.replace('foo__in!=')
    'bar__in!='
    >>> replacer.replace('foo__lower__in!=')
    'bar__lower__in!='

    >>> replacer.replace('&foo=')
    '&bar='
    >>> replacer.replace('&foo__in=')
    '&bar__in='
    >>> replacer.replace('&foo__foo=')
    '&bar__bar='
    >>> replacer.replace('&foo__lower__in=')
    '&bar__lower__in='
    >>> replacer.replace('&foo!=')
    '&bar!='
    >>> replacer.replace('&foo__in!=')
    '&bar__in!='
    >>> replacer.replace('&foo__lower__in!=')
    '&bar__lower__in!='

    >>> replacer.replace('{foo, foo}')
    '{bar, bar}'
    >>> replacer.replace('{foo{foo}}')
    '{bar{bar}}'
    >>> replacer.replace('{foo=1,foo=2}')
    '{bar=1,bar=2}'
    >>> replacer.replace('foo: "foo"')
    'bar: "bar"'
    >>> replacer.replace('some__foo')
    'some__bar'
    """

    def __init__(self, rules):
        self._rules = rules

    def replace(self, value):
        return self._pattern.sub(self._replacer, value)

    def _replacer(self, match):
        return self._rules[match[0]]

    @cached_property
    def _pattern(self):
        fields = "|".join(map(str, self._rules.keys()))
        symbols = '\'":{}&!,.= '
        return re.compile(
            r'('
            f'(^{fields}$)'  # Excat match
            r'|'
            f'((?<=[{symbols}])({fields})$)'  # Starting
            r'|'
            f'(^({fields})(?=[_{symbols}]))'  # Ending
            r'|'
            f'((?<=[{symbols}])({fields})(?=[_{symbols}]))'  # Surounded
            r'|'
            f'((?<=__)({fields})(?=[_{symbols}]))'  # Subfield
            r'|'
            f'((?<=__)({fields})$)'  # Subfield
            r')')


to_deprecated_fields = KeysReplacer(TO_DEPRECATED_FIELD_RULES)
to_actual_fields = KeysReplacer(TO_ACTUAL_FIELD_RULES)
to_deprecated_ordering = KeysReplacer(TO_DEPRECATED_ORDERING_RULES)
to_actual_ordering = KeysReplacer(TO_ACTUAL_ORDERING_RULES)
to_deprecated_filters = KeysReplacer(TO_DEPRECATED_FILTER_RULES)
to_actual_filters = KeysReplacer(TO_ACTUAL_FILTER_RULES)
