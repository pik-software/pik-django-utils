import factory
from django.utils.crypto import get_random_string

from ..models import MySimpleModel


class MySimpleModelFactory(factory.django.DjangoModelFactory):
    data = factory.LazyFunction(get_random_string)

    class Meta:
        model = MySimpleModel
