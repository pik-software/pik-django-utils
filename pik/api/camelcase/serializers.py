from collections import OrderedDict
from pik.utils.case_utils import underscore_to_camel


class CamelizeSerializerHookMixIn:
    @staticmethod
    def _camelize(data):
        if isinstance(data, str):
            data = underscore_to_camel(data)
        return data

    def camelization_hook(self, data):
        """
        >>> d = CamelizeSerializerHookMixIn()

        >>> d.camelization_hook( \
            data={'document_fields': ['abc_xyz', 'qwe_rty']})
        OrderedDict([('documentFields', ['abcXyz', 'qweRty'])])

        >>> d.camelization_hook( \
            data={'document_fields':['abc_xyz'], 'f': ['asd_zxc']})
        OrderedDict([('documentFields', ['abcXyz']), ('f', ['asd_zxc'])])

        >>> d.camelization_hook( \
            data={'document_fields': ['abc_xyz', 'qwe_rty']})
        OrderedDict([('documentFields', ['abcXyz', 'qweRty'])])

        >>> d.camelization_hook( \
            data={'document_fields':['abc_xyz'], 'f': ['asd_zxc']})
        OrderedDict([('documentFields', ['abcXyz']), ('f', ['asd_zxc'])])
        """

        if isinstance(data, dict):
            new_dict = OrderedDict()
            for key, value in data.items():
                new_key = self._camelize(key)
                new_value = self.camelization_hook(value)
                if key == 'document_fields' and isinstance(value, list):
                    new_value = [self._camelize(elem) for elem in value]
                new_dict[new_key] = new_value
            return new_dict

        if isinstance(data, list):
            new_list = [self.camelization_hook(elem) for elem in data]
            return new_list
        return data
