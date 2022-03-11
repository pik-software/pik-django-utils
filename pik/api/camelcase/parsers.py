from django.conf import settings
from django.http.multipartparser import (
    MultiPartParser as DjangoMultiPartParser,
    MultiPartParserError,
)
from rest_framework.exceptions import ParseError
from rest_framework.parsers import (
    FormParser, MultiPartParser, DataAndFiles, )

from djangorestframework_camel_case.parser import (
    CamelCaseJSONParser as BaseCamelCaseJSONParser)


class CamelCaseFormParser(FormParser):
    def parse(self, stream, media_type=None, parser_context=None):
        form_data = super().parse(stream, media_type, parser_context)
        view = parser_context['view']
        if hasattr(view.serializer_class, 'underscorize_hook'):
            form_data = view.serializer_class().underscorize_hook(form_data)

        return form_data


class CamelCaseMultiPartParser(MultiPartParser):
    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        request = parser_context["request"]
        encoding = parser_context.get("encoding", settings.DEFAULT_CHARSET)
        meta = request.META.copy()
        meta["CONTENT_TYPE"] = media_type
        upload_handlers = request.upload_handlers

        try:
            parser = DjangoMultiPartParser(
                meta, stream, upload_handlers, encoding)
            data, files = parser.parse()
            view = parser_context['view']
            if hasattr(view.serializer_class, 'underscorize_hook'):
                data = view.serializer_class().underscorize_hook(data)
                files = view.serializer_class().underscorize_hook(files)
            return DataAndFiles(data, files)
        except MultiPartParserError as exc:
            raise ParseError(
                f"Multipart form parse error - {str(exc)}") from exc


class CamelCaseJSONParser(BaseCamelCaseJSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        json_data = super().parse(stream, media_type, parser_context)

        view = parser_context['view']
        if hasattr(view.serializer_class, 'underscorize_hook'):
            json_data = view.serializer_class().underscorize_hook(json_data)

        return json_data
