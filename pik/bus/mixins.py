from pydoc import locate as pydoc_locate
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=None)
def locate(class_full_path):
    return pydoc_locate(class_full_path)


class ModelSerializerMixin:
    MODEL_SERIALIZER = {
        locate(serializer).Meta.model.__name__: locate(serializer)
        for serializer in settings.RABBITMQ_SERIALIZERS
    }
