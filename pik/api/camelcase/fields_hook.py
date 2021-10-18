from collections import OrderedDict

from .utils import camelize


def process(data, fields):
    """
    >>> process(data={'a':['abc_xyz', 'qwe_rty']}, fields=('a', ))
    OrderedDict([('a', ['abcXyz', 'qweRty'])])

    >>> process(data={'a':['abc_xyz']}, fields=('b', ))
    OrderedDict([('a', ['abc_xyz'])])

    >>> process( \
        data={'a':['abc_xyz'],'b':['qwe_rty'],'c':['asd_fgh']}, \
        fields=('a', 'c', ))
    OrderedDict([('a', ['abcXyz']), ('b', ['qwe_rty']), ('c', ['asdFgh'])])
    """

    if isinstance(data, dict):
        new_dict = OrderedDict()
        for key, value in data.items():
            new_key = key
            new_value = process(value, fields)
            for field in fields:
                if key == field and isinstance(value, list):
                    new_value = [camelize(elem) for elem in value]
            new_dict[new_key] = new_value
        return new_dict

    if isinstance(data, list):
        new_list = [process(i, fields) for i in data]
        return new_list
    return data
