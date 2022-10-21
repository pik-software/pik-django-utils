import json
from decimal import Decimal

from rest_framework.renderers import (
    JSONRenderer)
from rest_framework.utils import encoders


def encode_fakestr(func):
    def wrap(s):
        if isinstance(s, FakeStr):
            return repr(s)
        return func(s)
    return wrap


if __name__ == '__main__':
    json.encoder.encode_basestring = encode_fakestr(
        json.encoder.encode_basestring)
    json.encoder.encode_basestring_ascii = encode_fakestr(
        json.encoder.encode_basestring_ascii)


class FakeStr(str):
    def __init__(self, value):
        self._value = value

    def __repr__(self):
        return str(self._value)


class DecimalJSONEncoder(encoders.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return FakeStr(o)
        return super().default(o)


class DecimalJSONRenderer(JSONRenderer):
    """
    Renderer which serializes to JSON, numbers serializes without float.
    """
    encoder_class = DecimalJSONEncoder
