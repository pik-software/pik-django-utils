import codecs
from decimal import Decimal

from django.conf import settings
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.utils import json


class DecimalJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as JSON and returns the resulting data.
        """
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)

        try:
            decoded_stream = codecs.getreader(encoding)(stream)
            parse_constant = json.strict_constant if self.strict else None
            return json.load(
                decoded_stream, parse_constant=parse_constant,
                parse_float=Decimal)
        except ValueError as exc:
            raise ParseError(f'JSON parse error - {exc}') from exc
