import json

from django.conf import settings
from django.http.multipartparser import (
    MultiPartParser as DjangoMultiPartParser,
    MultiPartParserError,
)
from rest_framework.exceptions import ParseError
from rest_framework.parsers import (
    FormParser, MultiPartParser, DataAndFiles, )

from pik.settings import api_settings
from pik.utils.case_utils import underscoreize


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


class CamelCaseJSONParser(api_settings.PARSER_CLASS):
    json_underscoreize = api_settings.JSON_UNDERSCOREIZE

    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        encoding = parser_context.get("encoding", settings.DEFAULT_CHARSET)

        try:
            data = stream.read().decode(encoding)
            json_data = underscoreize(
                json.loads(data), **self.json_underscoreize)
            view = parser_context['view']
            if hasattr(view.serializer_class, 'underscorize_hook'):
                json_data = view.serializer_class().underscorize_hook(
                    json_data)
        except ValueError as exc:
            raise ParseError(f'JSON parse error - {str(exc)}') from exc

        return json_data
