import factory
from django.utils.crypto import get_random_string

from test_core_shortcuts.models import OverriddenQuerysetModel
from ..models import MySimpleModel, TestNameModel


class MyDjangoModelFactory(factory.django.DjangoModelFactory):
    """
    DeprecationWarning resolving:
    https://factoryboy.readthedocs.io/en/latest/changelog.html (since 3.3.0)
    DjangoModelFactory will stop issuing a second call to save()
    on the created instance when Post-generation hooks return a value.
    """

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results and not cls._meta.skip_postgeneration_save:
            instance.save()


class MySimpleModelFactory(MyDjangoModelFactory):
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


class TestNameModelFactory(MyDjangoModelFactory):
    __test__ = False  # prevent PytestCollectionWarning

    name = factory.LazyFunction(lambda: get_random_string(12))

    class Meta:
        model = TestNameModel


class OverriddenQuerysetModelFactory(MyDjangoModelFactory):
    name = factory.LazyFunction(lambda: get_random_string(12))

    class Meta:
        model = OverriddenQuerysetModel
