import factory
from django.utils.crypto import get_random_string

from test_core_shortcuts.models import OverriddenQuerysetModel
from ..models import MySimpleModel, TestNameModel


class MySimpleModelFactory(factory.django.DjangoModelFactory):
    data = factory.LazyFunction(lambda: get_random_string(12))

    @factory.post_generation
    def names(self, create, extracted):
        if not create:
            return
        if extracted:
            for name in extracted:
                self.names.add(name)

    class Meta:
        model = MySimpleModel
        skip_postgeneration_save = True


class TestNameModelFactory(factory.django.DjangoModelFactory):
    __test__ = False  # prevent PytestCollectionWarning

    name = factory.LazyFunction(lambda: get_random_string(12))

    class Meta:
        model = TestNameModel


class OverriddenQuerysetModelFactory(factory.django.DjangoModelFactory):
    name = factory.LazyFunction(lambda: get_random_string(12))

    class Meta:
        model = OverriddenQuerysetModel
