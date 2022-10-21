import json
from decimal import Decimal

from rest_framework.renderers import (
    JSONRenderer)
from rest_framework.utils import encoders


def encode_fakestr(func):
    def wrap(obj):
        if isinstance(obj, FakeStr):
            return repr(obj)
        return func(obj)
    return wrap


if __name__ == '__main__':
    try:
        from _json import encode_basestring_ascii as c_encode_basestring_ascii
    except ImportError:
        c_encode_basestring_ascii = None
    try:
        from _json import encode_basestring as c_encode_basestring
    except ImportError:
        c_encode_basestring = None

    json.encoder.encode_basestring = encode_fakestr(
        c_encode_basestring or json.encoder.py_encode_basestring)
    json.encoder.encode_basestring_ascii = encode_fakestr(
        c_encode_basestring_ascii or json.encoder.py_encode_basestring_ascii)


class FakeStr(str):
    def __init__(self, value):  # noqa: pylint=super-init-not-called
        self._value = value

    def __repr__(self):
        return str(self._value)


class DecimalJSONEncoder(encoders.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return FakeStr(obj)
        return super().default(obj)


class DecimalJSONRenderer(JSONRenderer):
    """
    Renderer which serializes to JSON, numbers serializes without float.
    """
    encoder_class = DecimalJSONEncoder
