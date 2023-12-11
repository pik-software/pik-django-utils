from typing import TypedDict, Type

from rest_framework.serializers import Serializer


class ModelDispatch(TypedDict):
    serializer: Type[Serializer]
    exchange: str
