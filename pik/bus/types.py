from typing import TypedDict

from rest_framework.serializers import Serializer


class ModelDispatch(TypedDict):
    serializer: Serializer
    exchange: str
