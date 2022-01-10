from djangorestframework_camel_case.parser import (
    CamelCaseJSONParser as BaseCamelCaseJSONParser)


class CamelCaseJSONParser(BaseCamelCaseJSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        json_data = super().parse(
            stream, media_type=media_type, parser_context=parser_context)

        view = parser_context['view']
        if hasattr(view.serializer_class, 'underscorize_hook'):
            json_data = view.serializer_class().underscorize_hook(json_data)

        return json_data
