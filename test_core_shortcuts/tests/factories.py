import factory
from django.utils.crypto import get_random_string

from ..models import MySimpleModel, TestNameModel


class MySimpleModelFactory(factory.django.DjangoModelFactory):
    data = factory.LazyFunction(get_random_string)

    @factory.post_generation
    def names(self, create, extracted):
        if not create:
            return
        if extracted:
            for name in extracted:
                self.names.add(name)

    class Meta:
        model = MySimpleModel


class TestNameModelFactory(factory.django.DjangoModelFactory):
    name = factory.LazyFunction(get_random_string)

    class Meta:
        model = TestNameModel
