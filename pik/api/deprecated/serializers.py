from collections import OrderedDict
from pik.utils.case_utils import camel_to_underscore


class UnderscorizeSerializerHookMixIn:
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
