import re
from collections import OrderedDict

from django.utils.encoding import force_str
from django.utils.functional import Promise, cached_property
from rest_framework.utils.serializer_helpers import ReturnDict

from pik.api.deprecated.consts import (
    TO_DEPRECATED_FIELD_RULES, TO_ACTUAL_FIELD_RULES,
    TO_ACTUAL_ORDERING_RULES, TO_DEPRECATED_ORDERING_RULES,
    TO_DEPRECATED_FILTER_RULES, TO_ACTUAL_FILTER_RULES, )
from pik.utils.case_utils import camel_to_underscore


class UnderscorizeHookMixIn:
    @staticmethod
    def _underscorize(data):
        if isinstance(data, str):
            data = camel_to_underscore(data)
        return data

    def underscorize_hook(self, data):
        """
        >>> d = UnderscorizeHookMixIn()

        >>> d.underscorize_hook( \
            data={'documentFields': ['abcXyz', 'qweRty']})
        OrderedDict([('document_fields', ['abc_xyz', 'qwe_rty'])])

        >>> d.underscorize_hook( \
            data={'documentFields': ['abcXyz'], 'f': ['asdZxc']})
        OrderedDict([('document_fields', ['abc_xyz']), ('f', ['asdZxc'])])

        >>> d.underscorize_hook( \
            data={'document_fields': ['abcXyz', 'qweRty']})
        OrderedDict([('document_fields', ['abc_xyz', 'qwe_rty'])])

        >>> d.underscorize_hook( \
            data={'document_fields': ['abcXyz'], 'f': ['asdZxc']})
        OrderedDict([('document_fields', ['abc_xyz']), ('f', ['asdZxc'])])
        """

        if isinstance(data, dict):
            new_dict = OrderedDict()
            for key, value in data.items():
                new_key = camel_to_underscore(key)
                new_value = self.underscorize_hook(value)
                if new_key == 'document_fields' and isinstance(value, list):
                    new_value = [self._underscorize(elem) for elem in value]
                new_dict[new_key] = new_value
            return new_dict

        if isinstance(data, list):
            new_list = [self.underscorize_hook(elem) for elem in data]
            return new_list
        return data


def replace_keys(field, replacer, **kwargs):
    """
    >>> replace_keys('version', to_deprecated_fields)
    '_version'
    >>> replace_keys('type', to_deprecated_fields)
    '_type'
    >>> replace_keys('guid', to_deprecated_fields)
    '_uid'
    >>> replace_keys('foo', to_deprecated_fields)
    'foo'

    >>> replace_keys('_uid', to_actual_fields)
    'guid'
    >>> replace_keys('_type', to_actual_fields)
    'type'
    >>> replace_keys('_version', to_actual_fields)
    'version'
    >>> replace_keys('foo', to_actual_fields)
    'foo'

    """
    if isinstance(field, str):
        return replacer.replace(field)
    return field


def replace_struct_keys(data, **options):  # noqa: Too many branches
    """
    Replaces `guid` with keys with `_uid`
    >>> replace_struct_keys({'foo_type': 1}, replacer=to_deprecated_fields)
    OrderedDict([('foo_type', 1)])

    >>> replace_struct_keys( \
        {'guid': 1, 'type': 2}, replacer=to_deprecated_fields)
    OrderedDict([('_uid', 1), ('_type', 2)])
    >>> replace_struct_keys( \
        {'guid': {'guid': 1}}, replacer=to_deprecated_fields)
    OrderedDict([('_uid', OrderedDict([('_uid', 1)]))])
    >>> replace_struct_keys({'guid': 'foo'}, replacer=to_deprecated_fields)
    OrderedDict([('_uid', 'foo')])
    >>> replace_struct_keys(['guid', 'foo'], replacer=to_deprecated_fields)
    ['guid', 'foo']
    >>> replace_struct_keys(('guid', 'foo'), replacer=to_deprecated_fields)
    ['guid', 'foo']
    >>> replace_struct_keys('guid', replacer=to_deprecated_fields)
    'guid'

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

    >>> replace_struct_keys( \
        {'guid': 1, 'type': 'string'}, replacer=to_deprecated_fields, \
        ignore_dict_items=(('type', 'string'), ))
    OrderedDict([('_uid', 1), ('type', 'string')])

    >>> replace_struct_keys({'_uid': 'foo'}, replacer=to_actual_fields)
    OrderedDict([('guid', 'foo')])
    >>> replace_struct_keys(['_uid', 'foo'], replacer=to_actual_fields)
    ['_uid', 'foo']
    >>> replace_struct_keys(('_uid', 'foo'), replacer=to_actual_fields)
    ['_uid', 'foo']
    >>> replace_struct_keys('_uid', replacer=to_actual_fields)
    '_uid'

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

    # >>> replace_struct_keys('some__uid', replacer=to_actual_filters)
    # 'some__guid'
    """
    ignore_fields = options.get("ignore_fields") or ()
    ignore_dict_items = options.get("ignore_dict_items") or ()

    if isinstance(data, Promise):
        data = force_str(data)
    if isinstance(data, dict):
        if isinstance(data, ReturnDict):
            new_dict = ReturnDict(serializer=data.serializer)
        else:
            new_dict = OrderedDict()
        for key, value in data.items():
            if (key, value) in ignore_dict_items:
                new_dict[key] = value
                continue
            if isinstance(key, Promise):
                key = force_str(key)
            new_key = replace_keys(key, **options)
            if key not in ignore_fields and new_key not in ignore_fields:
                new_dict[new_key] = replace_struct_keys(value, **options)
            else:
                new_dict[new_key] = value
        return new_dict
    if isinstance(data, (list, tuple)):
        return [replace_struct_keys(item, **options) for item in data]
    return data


class KeysReplacer:
    """ Rules based field/key replacer

    >>> replacer = KeysReplacer(rules={'type': '_type'})

    >>> replacer.replace('foo_type')
    'foo_type'

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

    >>> replacer.replace(None)

    """

    def __init__(self, rules):
        self._rules = rules

    def replace(self, value):
        if not isinstance(value, str):
            return value
        return self._pattern.sub(self._replacer, value)

    def _replacer(self, match):
        return self._rules[match[0]]

    @cached_property
    def _pattern(self):
        fields = "|".join(map(str, self._rules.keys()))
        symbols = '\'":{}&!,.= '
        return re.compile(
            r'('
            f'^({fields})$'  # Excat match
            r'|'
            f'((?<=[{symbols}])({fields}))$'  # Starting
            r'|'
            f'^(({fields})(?=[_{symbols}]))'  # Ending
            r'|'
            f'((?<=[{symbols}])({fields})(?=[_{symbols}]))'  # Surounded
            r'|'
            f'((?<=__)({fields})(?=[_{symbols}]))'  # Subfield
            r'|'
            f'((?<=__)({fields}))$'  # Subfield
            r')')


to_deprecated_fields = KeysReplacer(TO_DEPRECATED_FIELD_RULES)
to_actual_fields = KeysReplacer(TO_ACTUAL_FIELD_RULES)
to_deprecated_ordering = KeysReplacer(TO_DEPRECATED_ORDERING_RULES)
to_actual_ordering = KeysReplacer(TO_ACTUAL_ORDERING_RULES)
to_deprecated_filters = KeysReplacer(TO_DEPRECATED_FILTER_RULES)
to_actual_filters = KeysReplacer(TO_ACTUAL_FILTER_RULES)
