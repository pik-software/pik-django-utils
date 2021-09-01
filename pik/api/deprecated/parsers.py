import json

from django.conf import settings
from django.http.multipartparser import (
    MultiPartParser as DjangoMultiPartParser,
    MultiPartParserError,
)
from rest_framework.exceptions import ParseError

from rest_framework.parsers import (
    FormParser, MultiPartParser, DataAndFiles,
    JSONParser, )

from .utils import (
    replace_struct_keys, TO_ACTUAL_FIELD_RULES, to_actual_fields, )


class DeprecatedFormParser(FormParser):
    def parse(self, stream, media_type=None, parser_context=None):
        return replace_struct_keys(
            super().parse(stream, media_type, parser_context),
            rules=TO_ACTUAL_FIELD_RULES
        )


class DeprecatedMultiPartParser(MultiPartParser):
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
            return DataAndFiles(
                replace_struct_keys(data, replacer=to_actual_fields),
                replace_struct_keys(files, replacer=to_actual_fields),
            )
        except MultiPartParserError as exc:
            raise ParseError("Multipart form parse error - %s" % str(exc)
                             ) from exc


class DeprecatedJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        parser_context = parser_context or {}
        encoding = parser_context.get("encoding", settings.DEFAULT_CHARSET)

        try:
            data = stream.read().decode(encoding)
            return replace_struct_keys(
                json.loads(data), replacer=to_actual_fields)
        except ValueError as exc:
            raise ParseError("JSON parse error - %s" % str(exc)) from exc
