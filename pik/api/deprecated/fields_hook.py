from collections import OrderedDict


def process(data, rules: dict):
    """
    >>> process(data={'a': 1}, rules={'a': 'b'})
    OrderedDict([('b', 1)])

    >>> process(data={'a': {'b': 1}}, rules={'b': 'c'})
    OrderedDict([('a', OrderedDict([('c', 1)]))])

    >>> process(data={'a': {'b': 'c'}}, rules={'c': 'd'})
    OrderedDict([('a', OrderedDict([('b', 'd')]))])

    >>> process(data=[{'a': {'b': 'c'}}, 'a'], rules={'a': 'x'})
    [OrderedDict([('x', OrderedDict([('b', 'c')]))]), 'x']
    """

    if isinstance(data, dict):
        new_dict = OrderedDict()
        for key, value in data.items():
            new_value = process(value, rules)
            new_key = key
            if key in rules:
                new_key = rules[key]
            new_dict[new_key] = new_value
        return new_dict

    if isinstance(data, (list, tuple)):
        new_list_or_tuple = [process(item, rules) for item in data]
        new_list_or_tuple = type(data)(new_list_or_tuple)
        return new_list_or_tuple

    if isinstance(data, str):
        for key in rules:
            if key in data:
                data = data.replace(key, rules[key])

    return data
