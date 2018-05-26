import factory

from ..models import MyDated, MyOwned, MyNullOwned, MyUided, MyPUided, \
    MyVersioned, MyStrictVersioned, MyHistorized, MyBasePHistorical, \
    MyBaseHistorical


class MyDatedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyDated


class MyOwnedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyOwned


class MyNullOwnedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyNullOwned


class MyUidedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyUided


class MyPUidedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyPUided


class MyVersionedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyVersioned


class MyStrictVersionedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyStrictVersioned


class MyHistorizedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyHistorized


class MyBasePHistoricalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyBasePHistorical


class MyBaseHistoricalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MyBaseHistorical
